"""
assets/services/margin_service.py
==================================
Margin (leveraged) trading service — mirrors Binance Isolated Margin logic.

Key concepts
────────────
• Margin (collateral)  : real wallet funds deducted (e.g. ₹1 000)
• Leverage             : multiplier (e.g. 10×)
• Position size        : notional value = margin × leverage (e.g. ₹10 000)
• Quantity             : position_size / entry_price
• Liquidation price    : the market price at which the margin is fully wiped out
      Long  : entry × (1 − 1/leverage + MMR)
      Short : entry × (1 + 1/leverage − MMR)
  where MMR = maintenance margin ratio (0.4 % Binance default)

Profit / Loss formula (Long example)
──────────────────────────────────────
  Unrealised P&L = (current_price − entry_price) × quantity
  ROE%           = unrealised_pnl / margin_used × 100

Admin-level rules enforced here
────────────────────────────────
• Minimum margin    : ₹1
• Maximum leverage  : 125× (hard cap)
• Funding fee       : not applied (simplified)
• Liquidation       : closes position, returns zero to wallet
"""

from decimal import Decimal, ROUND_DOWN
import logging

from django.db import transaction
from django.utils import timezone

from accounts.wallet.utils import add_amount, deduct_amount
from assets.models import MarginPosition, order as Order

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
MAX_LEVERAGE = 200
MIN_MARGIN = Decimal('1')
MAINT_MARGIN_RATIO = Decimal('0.004')   # 0.4 % — same as Binance tier-1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _liq_price(entry: Decimal, leverage: int, side: str) -> Decimal:
    """Compute liquidation price."""
    lev = Decimal(str(leverage))
    mmr = MAINT_MARGIN_RATIO
    if side == MarginPosition.LONG:
        return (entry * (1 - 1 / lev + mmr)).quantize(Decimal('0.01'))
    else:
        return (entry * (1 + 1 / lev - mmr)).quantize(Decimal('0.01'))


def _weighted_avg_entry(old_qty, old_entry, new_qty, new_price):
    """Compute new weighted average entry when adding to a position."""
    old_qty = Decimal(str(old_qty))
    old_entry = Decimal(str(old_entry))
    new_qty = Decimal(str(new_qty))
    new_price = Decimal(str(new_price))
    total = old_qty + new_qty
    if total == 0:
        return Decimal('0')
    return ((old_qty * old_entry + new_qty * new_price) / total).quantize(Decimal('0.00001'))


def _get_open_margin_pos(user, stock, side):
    """Return the open margin position for user+stock+side, or None."""
    return MarginPosition.objects.filter(
        user=user, stock=stock, side=side, status=MarginPosition.STATUS_OPEN
    ).first()


# ── Public API ───────────────────────────────────────────────────────────────

def execute_margin_trade(user, stock, margin_amount, leverage, side):
    """
    Open or add to a margin position.

    Parameters
    ----------
    user         : CustomUser
    stock        : Stock  (must have .current_price)
    margin_amount: Decimal — collateral to lock from wallet
    leverage     : int    — position multiplier (1–125)
    side         : 'LONG' | 'SHORT'

    Returns
    -------
    tuple[bool, str] : (success, message)
    """
    # ── Validate inputs ────────────────────────────────────────────────
    margin_amount = Decimal(str(margin_amount)).quantize(Decimal('0.01'))
    leverage = int(leverage)

    if leverage < 1 or leverage > MAX_LEVERAGE:
        return False, f'Leverage must be between 1× and {MAX_LEVERAGE}×.'
    if margin_amount < MIN_MARGIN:
        return False, f'Minimum margin is ₹{MIN_MARGIN}.'
    if side not in (MarginPosition.LONG, MarginPosition.SHORT):
        return False, 'Invalid side — must be LONG or SHORT.'

    wallet_balance = Decimal(str(user.wallet))
    if margin_amount > wallet_balance:
        return False, 'Insufficient wallet balance for this margin.'

    entry_price = Decimal(str(stock.current_price))
    if entry_price <= 0:
        return False, 'Cannot open margin position: invalid stock price.'

    position_size = (margin_amount * Decimal(str(leverage))).quantize(Decimal('0.01'))
    quantity = (position_size / entry_price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

    if quantity <= 0:
        return False, 'Calculated quantity is too small — increase margin or reduce leverage.'

    with transaction.atomic():
        # Deduct margin from wallet immediately (it's locked collateral)
        deduct_amount(user, margin_amount)

        existing = _get_open_margin_pos(user, stock, side)

        if existing:
            # Add to existing position (scale up)
            new_entry = _weighted_avg_entry(
                existing.quantity, existing.entry_price, quantity, entry_price
            )
            existing.quantity = Decimal(str(existing.quantity)) + quantity
            existing.margin_used = Decimal(str(existing.margin_used)) + margin_amount
            existing.position_size = Decimal(str(existing.position_size)) + position_size
            existing.entry_price = new_entry
            # liquidation_price recomputed in .save()
            existing.save()
            pos = existing
            action = 'Added to'
        else:
            # Create new margin position
            pos = MarginPosition.objects.create(
                user=user,
                stock=stock,
                side=side,
                leverage=leverage,
                margin_used=margin_amount,
                position_size=position_size,
                quantity=quantity,
                entry_price=entry_price,
                # liquidation_price set in .save()
            )
            action = 'Opened'

        # Record the order
        Order.objects.create(
            user=user,
            stock=stock,
            price=entry_price,
            amount=position_size,   # notional value in order log
            quantity=quantity,
            order_type='BUY' if side == MarginPosition.LONG else 'SELL',
            status='completed',
            charges=Decimal('0'),
            leverage=leverage,
            is_margin=True,
        )

    logger.info(
        f'{action} margin position: {user.username} {side} {stock.symbol} '
        f'x{leverage} margin=₹{margin_amount} qty={quantity}'
    )
    return True, (
        f'{action} {side} position: {quantity:.4f} {stock.symbol} '
        f'@ ₹{entry_price:.2f} | Liq: ₹{pos.liquidation_price:.2f}'
    )


def close_margin_position(user, stock, side, close_qty=None):
    """
    Close (fully or partially) a margin position.

    Parameters
    ----------
    user      : CustomUser
    stock     : Stock
    side      : 'LONG' | 'SHORT'
    close_qty : Decimal | None — None means close all

    Returns
    -------
    tuple[bool, str]
    """
    with transaction.atomic():
        pos = _get_open_margin_pos(user, stock, side)
        if not pos:
            return False, f'No open {side} margin position for {stock.symbol}.'

        current_price = Decimal(str(stock.current_price))
        total_qty = Decimal(str(pos.quantity))

        if close_qty is None:
            close_qty = total_qty
        else:
            close_qty = Decimal(str(close_qty)).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

        if close_qty <= 0 or close_qty > total_qty:
            return False, 'Invalid close quantity.'

        entry_price = Decimal(str(pos.entry_price))
        partial_ratio = close_qty / total_qty        # fraction being closed

        # P&L for the closed portion
        if pos.side == MarginPosition.LONG:
            pnl = (current_price - entry_price) * close_qty
        else:
            pnl = (entry_price - current_price) * close_qty

        # Margin to return = locked margin × fraction + P&L
        margin_to_return = (Decimal(str(pos.margin_used)) * partial_ratio + pnl).quantize(Decimal('0.01'))

        # Update position
        pos.realised_pnl = (Decimal(str(pos.realised_pnl)) + pnl).quantize(Decimal('0.00001'))
        pos.close_price = current_price

        if close_qty >= total_qty:
            # Full close
            pos.quantity = Decimal('0')
            pos.margin_used = Decimal('0')
            pos.position_size = Decimal('0')
            pos.status = MarginPosition.STATUS_CLOSED
            pos.closed_at = timezone.now()
        else:
            # Partial close
            pos.quantity = total_qty - close_qty
            pos.margin_used = (Decimal(str(pos.margin_used)) * (1 - partial_ratio)).quantize(Decimal('0.01'))
            pos.position_size = (Decimal(str(pos.position_size)) * (1 - partial_ratio)).quantize(Decimal('0.01'))

        pos.save()

        # Return margin + P&L to wallet (floored at 0 — loss eats margin)
        returned = max(margin_to_return, Decimal('0'))
        if returned > 0:
            add_amount(user, returned)

        # Record closing order
        Order.objects.create(
            user=user,
            stock=stock,
            price=current_price,
            amount=(current_price * close_qty).quantize(Decimal('0.01')),
            quantity=close_qty,
            order_type='SELL' if pos.side == MarginPosition.LONG else 'BUY',
            status='completed',
            charges=Decimal('0'),
            leverage=pos.leverage,
            is_margin=True,
        )

    label = 'Closed' if pos.status == MarginPosition.STATUS_CLOSED else 'Partially closed'
    logger.info(
        f'{label} margin position: {user.username} {side} {stock.symbol} '
        f'qty={close_qty} pnl={pnl:.2f} returned=₹{returned:.2f}'
    )
    return True, f'{label} {side} {stock.symbol}: P&L ₹{pnl:.2f}, returned ₹{returned:.2f}'


def liquidate_position(user, stock, side):
    """
    Force-liquidate a margin position (called when price hits liquidation price).
    Wallet receives nothing — all margin is consumed.
    """
    with transaction.atomic():
        pos = _get_open_margin_pos(user, stock, side)
        if not pos:
            return False, 'No position to liquidate.'

        current_price = Decimal(str(stock.current_price))
        if pos.side == MarginPosition.LONG:
            pnl = (current_price - Decimal(str(pos.entry_price))) * Decimal(str(pos.quantity))
        else:
            pnl = (Decimal(str(pos.entry_price)) - current_price) * Decimal(str(pos.quantity))

        pos.realised_pnl = (Decimal(str(pos.realised_pnl)) + pnl).quantize(Decimal('0.00001'))
        pos.close_price = current_price
        pos.status = MarginPosition.STATUS_LIQUIDATED
        pos.closed_at = timezone.now()
        pos.quantity = Decimal('0')
        pos.margin_used = Decimal('0')
        pos.position_size = Decimal('0')
        pos.save()

    logger.warning(
        f'LIQUIDATED: {user.username} {side} {stock.symbol} @ ₹{current_price}'
    )
    return True, f'Position liquidated at ₹{current_price:.2f}. Margin lost.'
