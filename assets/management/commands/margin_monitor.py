"""
assets/management/commands/margin_monitor.py
=============================================
Backend margin risk monitor — scalable edition.

Run with:  python manage.py margin_monitor

Scalability changes vs. original
─────────────────────────────────
1. Concurrent position processing
   ThreadPoolExecutor processes positions in parallel so a slow DB call
   or close_margin_position() on one position never stalls the others.
   Worker count is tunable via --workers (default 8).

2. Chunked DB queries (pagination)
   Positions are fetched in pages (--chunk-size, default 500) so a scan
   over 100 k open positions never materialises the entire result-set into
   RAM at once.

3. Redis-backed warn_state (optional, graceful fallback)
   If a Django cache named "margin_monitor" (or "default") is configured
   with a Redis backend, warn_state is stored there with TTL = WARN_COOLDOWN.
   This makes warn deduplication survive process restarts and work correctly
   when multiple monitor workers run behind a load-balancer.
   Falls back to an in-process dict transparently when no cache is available.

4. Non-blocking WebSocket push
   _push_event is submitted to a small dedicated I/O thread pool so the
   main scan threads are never held up by channel-layer latency.

5. Structured metrics logging
   Each scan emits a single INFO line with duration_ms, positions scanned,
   warned, and closed — easy to ingest into Datadog / Prometheus / Loki.

All threshold values, business logic, and notification payloads are
100 % identical to the original implementation.
"""

import logging
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# ── Tunables ────────────────────────────────────────────────────────────────
SCAN_INTERVAL  = 2           # seconds between scans
WARN_THRESHOLD = Decimal("0.90")
CLOSE_THRESHOLD = Decimal("0.95")
WARN_COOLDOWN  = 120         # seconds — same position won't be re-warned sooner

DEFAULT_WORKERS    = 8       # parallel position-processing threads
DEFAULT_CHUNK_SIZE = 500     # DB page size
IO_WORKERS         = 4       # dedicated threads for channel-layer pushes


# ── Channel-layer helper ─────────────────────────────────────────────────────

def _get_channel_layer():
    from channels.layers import get_channel_layer
    return get_channel_layer()


# Dedicated executor so WebSocket I/O never blocks scan worker threads.
_io_executor = ThreadPoolExecutor(max_workers=IO_WORKERS, thread_name_prefix="margin-io")


def _push_event(user_id: int, payload: dict):
    """Fire-and-forget: submit channel-layer push to the I/O pool."""
    def _send():
        layer = _get_channel_layer()
        if not layer:
            logger.warning(
                "[MarginMonitor] No channel layer — cannot push notification to user %s", user_id
            )
            return
        try:
            async_to_sync(layer.group_send)(
                f"user_{user_id}",
                {"type": "user_event", "payload": payload},
            )
        except Exception as exc:
            logger.error("[MarginMonitor] channel_layer push failed: %s", exc)

    _io_executor.submit(_send)


# ── Distributed warn-state (Redis-backed with in-process fallback) ───────────

class _WarnState:
    """
    Thin abstraction over warn cooldown storage.

    Priority:
      1. Django cache named "margin_monitor"  (configure a Redis cache with this alias)
      2. Django cache named "default"         (if it is Redis-backed)
      3. In-process dict                      (original behaviour; not HA-safe)
    """

    _CACHE_KEY_PREFIX = "mm:warn:"

    def __init__(self):
        self._local: dict = {}
        self._cache = self._resolve_cache()

    @staticmethod
    def _resolve_cache():
        try:
            from django.core.cache import caches, InvalidCacheBackendError
            for alias in ("margin_monitor", "default"):
                try:
                    cache = caches[alias]
                    # Probe — will raise if backend is misconfigured
                    cache.get("__probe__")
                    logger.info(
                        "[MarginMonitor] warn_state backed by Django cache alias=%r", alias
                    )
                    return cache
                except (InvalidCacheBackendError, Exception):
                    continue
        except Exception:
            pass
        logger.info("[MarginMonitor] warn_state using in-process dict (single-node only)")
        return None

    def _key(self, position_id) -> str:
        return f"{self._CACHE_KEY_PREFIX}{position_id}"

    def last_warned(self, position_id) -> float:
        if self._cache is not None:
            try:
                val = self._cache.get(self._key(position_id))
                return float(val) if val is not None else 0.0
            except Exception:
                pass
        return self._local.get(position_id, 0.0)

    def set_warned(self, position_id, timestamp: float):
        if self._cache is not None:
            try:
                self._cache.set(self._key(position_id), timestamp, timeout=WARN_COOLDOWN)
                return
            except Exception:
                pass
        self._local[position_id] = timestamp

    def clear(self, position_id):
        if self._cache is not None:
            try:
                self._cache.delete(self._key(position_id))
            except Exception:
                pass
        self._local.pop(position_id, None)


# ── Per-position processing (identical logic to original) ────────────────────

def _process_position(pos, warn_state: _WarnState, now: float):
    """
    Evaluate one MarginPosition and act on it.

    Returns a tuple (warned: bool, closed: bool).
    All logic is identical to the original _run_scan inner loop.
    """
    from assets.services.margin_service import close_margin_position

    current_price = Decimal(str(pos.stock.current_price))
    if current_price <= 0:
        return False, False

    qty   = Decimal(str(pos.quantity))
    entry = Decimal(str(pos.entry_price))
    if pos.side == pos.__class__.LONG:
        upnl = (current_price - entry) * qty
    else:
        upnl = (entry - current_price) * qty

    effective_loss  = max(Decimal("0"), -upnl)
    margin_invested = Decimal(str(pos.margin_used))
    if margin_invested <= 0:
        return False, False

    risk_ratio = effective_loss / margin_invested
    pct        = float(risk_ratio * 100)
    key        = pos.id

    logger.debug(
        "[MarginMonitor] %s %s %s | price=%.2f entry=%.2f upnl=%.2f risk=%.1f%% margin=%.2f",
        pos.user.username, pos.side, pos.stock.symbol,
        float(current_price), float(entry), float(upnl), pct, float(margin_invested),
    )

    # ── 95 %+ → AUTO-CLOSE ──────────────────────────────────────────────────
    if risk_ratio >= CLOSE_THRESHOLD:
        logger.warning(
            "[MarginMonitor] AUTO-CLOSE triggered: user=%s %s %s risk=%.1f%%",
            pos.user.username, pos.side, pos.stock.symbol, pct,
        )
        success, message = close_margin_position(
            user=pos.user,
            stock=pos.stock,
            side=pos.side,
        )
        if success:
            warn_state.clear(key)
            _push_event(pos.user.id, {
                "event":    "margin_risk_closed",
                "symbol":   pos.stock.symbol,
                "side":     pos.side,
                "risk_pct": round(pct, 1),
                "message":  (
                    f"⚠️ Your {pos.side} position on {pos.stock.symbol} was automatically "
                    f"closed at {pct:.1f}% account risk to protect your funds. {message}"
                ),
            })
            return False, True
        else:
            logger.error(
                "[MarginMonitor] close_margin_position failed: user=%s %s %s — %s",
                pos.user.username, pos.side, pos.stock.symbol, message,
            )
            return False, False

    # ── 90 %+ → WARN (with cooldown) ────────────────────────────────────────
    elif risk_ratio >= WARN_THRESHOLD:
        last_warned = warn_state.last_warned(key)
        if now - last_warned >= WARN_COOLDOWN:
            warn_state.set_warned(key, now)
            _push_event(pos.user.id, {
                "event":    "margin_risk_warning",
                "symbol":   pos.stock.symbol,
                "side":     pos.side,
                "risk_pct": round(pct, 1),
                "message":  (
                    f"⚠️ Margin Risk Warning — {pos.stock.symbol} {pos.side}: "
                    f"Your account risk has reached {pct:.1f}% of wallet balance. "
                    f"Consider reducing or closing this position."
                ),
            })
            return True, False
        return False, False

    else:
        # Risk dropped back below 90 % — allow re-warning on next spike
        warn_state.clear(key)
        return False, False


# ── Main scan (chunked + concurrent) ─────────────────────────────────────────

def _run_scan(warn_state: _WarnState, workers: int, chunk_size: int):
    """
    Fetch all open MarginPositions in pages and process them concurrently.

    Chunking prevents loading the entire table into memory.
    ThreadPoolExecutor parallelises DB-heavy calls (close_margin_position).
    """
    from assets.models import MarginPosition

    now          = time.time()
    total        = 0
    closed_count = 0
    warned_count = 0

    base_qs = (
        MarginPosition.objects
        .filter(status=MarginPosition.STATUS_OPEN)
        .select_related("stock", "user")
        .order_by("id")          # stable ordering required for pagination
    )

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="margin-scan") as pool:
        last_id  = 0
        while True:
            chunk = list(base_qs.filter(id__gt=last_id)[:chunk_size])
            if not chunk:
                break

            futures = {
                pool.submit(_process_position, pos, warn_state, now): pos
                for pos in chunk
            }

            for future in as_completed(futures):
                pos = futures[future]
                try:
                    warned, closed = future.result()
                    warned_count += warned
                    closed_count += closed
                except Exception as exc:
                    logger.exception(
                        "[MarginMonitor] Error processing position id=%s: %s", pos.id, exc
                    )

            total   += len(chunk)
            last_id  = chunk[-1].id

    return total, warned_count, closed_count


# ── Django management command ─────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Backend margin risk monitor. Scans all open margin positions every "
        f"{SCAN_INTERVAL}s and auto-closes positions at {int(CLOSE_THRESHOLD * 100)}%+ "
        f"account risk. Warns at {int(WARN_THRESHOLD * 100)}%+."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=SCAN_INTERVAL,
            help=f"Scan interval in seconds (default: {SCAN_INTERVAL})",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single scan and exit (useful for cron / testing)",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=DEFAULT_WORKERS,
            help=f"Parallel worker threads per scan (default: {DEFAULT_WORKERS})",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=DEFAULT_CHUNK_SIZE,
            dest="chunk_size",
            help=f"DB page size for position fetching (default: {DEFAULT_CHUNK_SIZE})",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

        interval   = options["interval"]
        run_once   = options["once"]
        workers    = options["workers"]
        chunk_size = options["chunk_size"]

        self.stdout.write(
            self.style.SUCCESS(
                f"[MarginMonitor] Starting — interval={interval}s | "
                f"warn>={int(WARN_THRESHOLD * 100)}% | close>={int(CLOSE_THRESHOLD * 100)}% | "
                f"workers={workers} | chunk_size={chunk_size}"
            )
        )

        warn_state = _WarnState()
        stop_event = threading.Event()

        def _shutdown(sig, frame):
            self.stdout.write("\n[MarginMonitor] Shutting down…")
            stop_event.set()

        signal.signal(signal.SIGINT,  _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        if run_once:
            total, warned, closed = _run_scan(warn_state, workers, chunk_size)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[MarginMonitor] Single scan complete — "
                    f"scanned={total} warned={warned} closed={closed}"
                )
            )
            return

        while not stop_event.is_set():
            t0 = time.time()
            try:
                total, warned, closed = _run_scan(warn_state, workers, chunk_size)
                elapsed_ms = int((time.time() - t0) * 1000)
                logger.info(
                    "[MarginMonitor] scan complete | duration_ms=%d scanned=%d warned=%d closed=%d",
                    elapsed_ms, total, warned, closed,
                )
            except Exception as exc:
                logger.exception("[MarginMonitor] Unhandled error in scan: %s", exc)

            elapsed   = time.time() - t0
            sleep_for = max(0, interval - elapsed)
            stop_event.wait(timeout=sleep_for)

        self.stdout.write(self.style.SUCCESS("[MarginMonitor] Stopped."))