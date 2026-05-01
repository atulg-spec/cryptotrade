class TradingPanelController {
    constructor() {
        this.currentSymbol = null;
        this.side = 'buy'; // 'buy' or 'sell' (spot)
        this.tradeMode = 'spot'; // 'spot' or 'margin'
        this.marginSide = 'LONG'; // 'LONG' or 'SHORT'
        this.leverage = 10;
        this.inputMode = 'qty'; // 'qty' or 'amt'
        
        // Listen to global events
        document.addEventListener('symbol_change', (e) => {
            this.setSymbol(e.detail.symbol);
        });

        if (window.AppRealtime?.subscribeWallet) {
            window.AppRealtime.subscribeWallet((payload) => {
                this.updateBalanceUI(payload);
            });
        } else {
            document.addEventListener('balance_update', (e) => {
                this.updateBalanceUI(e.detail);
            });
        }
        
        document.addEventListener('DOMContentLoaded', () => {
             this.initListeners();
             this.updateMarginPositions(); // Initial fetch
        });
    }

    setSymbol(symbol) {
        this.currentSymbol = symbol;
        const els = ['trade-panel-symbol', 'sheet-symbol'];
        els.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.textContent = symbol;
        });
        this.updateMarginPreview();
    }

    initListeners() {
        // Main panel listeners
        const submitBtn = document.getElementById('submit-order-btn');
        if(submitBtn) submitBtn.addEventListener('click', this.submitOrder.bind(this));

        const toggleQtyBtn = document.getElementById('toggle-qty');
        const toggleAmtBtn = document.getElementById('toggle-amt');
        if(toggleQtyBtn && toggleAmtBtn) {
            toggleQtyBtn.addEventListener('click', () => this.setInputMode('qty'));
            toggleAmtBtn.addEventListener('click', () => this.setInputMode('amt'));
        }

        // Sheet listeners
        const sheetToggleQtyBtn = document.getElementById('sheet-toggle-qty');
        const sheetToggleAmtBtn = document.getElementById('sheet-toggle-amt');
        if(sheetToggleQtyBtn && sheetToggleAmtBtn) {
            sheetToggleQtyBtn.addEventListener('click', () => this.setInputMode('qty'));
            sheetToggleAmtBtn.addEventListener('click', () => this.setInputMode('amt'));
        }

        const inputEls = ['order-qty', 'sheet-order-qty', 'order-price'];
        inputEls.forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.addEventListener('input', (e) => {
                    // Sync values between main and sheet
                    const otherId = id === 'order-qty' ? 'sheet-order-qty' : (id === 'sheet-order-qty' ? 'order-qty' : null);
                    if (otherId) {
                        const otherEl = document.getElementById(otherId);
                        if (otherEl) otherEl.value = e.target.value;
                    }
                    this.updateEstimate();
                    this.updateMarginPreview();
                });
            }
        });

        // Global functions for inline handlers
        window.setTradeMode = this.setTradeMode.bind(this);
        window.setMarginSide = this.setMarginSide.bind(this);
        window.onLeverageChange = this.onLeverageChange.bind(this);
        window.setLeveragePreset = this.setLeveragePreset.bind(this);
        window.setQtyPercent = this.setQtyPercent.bind(this);
    }
    
    setTradeMode(mode) {
        this.tradeMode = mode;
        const suffixes = ['', 'sheet-'];
        
        suffixes.forEach(s => {
            const spotBtn = document.getElementById(s + 'mode-spot');
            const marginBtn = document.getElementById(s + 'mode-margin');
            const leverageRow = document.getElementById(s + 'leverage-row');
            const marginInfo = document.getElementById(s + 'margin-info-box');
            const marginSideRow = document.getElementById(s + 'margin-side-row');
            const spotToggle = document.getElementById(s + 'spot-qa-toggle');
            const inputLabel = document.getElementById(s + 'order-input-label');
            const submitBtn = document.getElementById(s + 'submit-order-btn') || document.getElementById(s + 'submit-btn');

            if (mode === 'margin') {
                if (spotBtn) { spotBtn.classList.remove('bg-slate-700', 'text-white'); spotBtn.classList.add('text-slate-500'); }
                if (marginBtn) { marginBtn.classList.add('bg-slate-700', 'text-white'); marginBtn.classList.remove('text-slate-500'); }
                leverageRow?.classList.remove('hidden');
                marginInfo?.classList.remove('hidden');
                marginSideRow?.classList.remove('hidden');
                spotToggle?.classList.add('hidden');
                if (inputLabel) inputLabel.textContent = 'Margin (₹)';
                if (submitBtn) submitBtn.textContent = this.marginSide === 'LONG' ? 'Buy / Long' : 'Sell / Short';
            } else {
                if (marginBtn) { marginBtn.classList.remove('bg-slate-700', 'text-white'); marginBtn.classList.add('text-slate-500'); }
                if (spotBtn) { spotBtn.classList.add('bg-slate-700', 'text-white'); spotBtn.classList.remove('text-slate-500'); }
                leverageRow?.classList.add('hidden');
                marginInfo?.classList.add('hidden');
                marginSideRow?.classList.add('hidden');
                spotToggle?.classList.remove('hidden');
                if (inputLabel) inputLabel.textContent = this.inputMode === 'qty' ? 'Quantity' : 'Amount (₹)';
                if (submitBtn) submitBtn.textContent = this.side === 'buy' ? 'Buy / Long' : 'Sell / Short';
            }
        });

        if (mode === 'margin') this.inputMode = 'amt';
        this.updateMarginPreview();
        this.updateEstimate();
    }

    setMarginSide(side) {
        this.marginSide = side;
        const suffixes = ['', 'sheet-'];
        suffixes.forEach(s => {
            const longBtn = document.getElementById(s + 'btn-long');
            const shortBtn = document.getElementById(s + 'btn-short');
            const submitBtn = document.getElementById(s + 'submit-order-btn') || document.getElementById(s + 'submit-btn');

            if (side === 'LONG') {
                if (longBtn) { longBtn.classList.add('bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/30'); longBtn.classList.remove('text-slate-500', 'border-slate-700'); }
                if (shortBtn) { shortBtn.classList.remove('bg-rose-500/20', 'text-rose-400', 'border-rose-500/30'); shortBtn.classList.add('text-slate-500', 'border-slate-700'); }
                if (submitBtn) { submitBtn.classList.replace('bg-rose-500', 'bg-emerald-500'); submitBtn.textContent = 'Buy / Long'; }
            } else {
                if (shortBtn) { shortBtn.classList.add('bg-rose-500/20', 'text-rose-400', 'border-rose-500/30'); shortBtn.classList.remove('text-slate-500', 'border-slate-700'); }
                if (longBtn) { longBtn.classList.remove('bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/30'); longBtn.classList.add('text-slate-500', 'border-slate-700'); }
                if (submitBtn) { submitBtn.classList.replace('bg-emerald-500', 'bg-rose-500'); submitBtn.textContent = 'Sell / Short'; }
            }
        });
        this.updateMarginPreview();
    }

    onLeverageChange(val) {
        this.leverage = parseInt(val);
        ['leverage-display', 'sheet-leverage-display'].forEach(id => {
            const d = document.getElementById(id);
            if (d) d.textContent = val + '×';
        });
        ['leverage-slider', 'sheet-leverage-slider'].forEach(id => {
            const s = document.getElementById(id);
            if (s) s.value = val;
        });
        this.updateMarginPreview();
    }

    setLeveragePreset(val) {
        this.onLeverageChange(val);
    }

    setInputMode(mode) {
        this.inputMode = mode;
        const suffixes = ['', 'sheet-'];
        suffixes.forEach(s => {
            const toggleQtyBtn = document.getElementById(s + 'toggle-qty');
            const toggleAmtBtn = document.getElementById(s + 'toggle-amt');
            const inputLabel = document.getElementById(s + 'order-input-label');
            const currencyDisplay = document.getElementById(s + 'order-currency-display');

            if (mode === 'qty') {
                if (toggleQtyBtn) { toggleQtyBtn.classList.add('bg-blue-500/15', 'text-blue-400'); toggleQtyBtn.classList.remove('text-slate-500'); }
                if (toggleAmtBtn) { toggleAmtBtn.classList.remove('bg-blue-500/15', 'text-blue-400'); toggleAmtBtn.classList.add('text-slate-500'); }
                if (inputLabel) inputLabel.textContent = 'Quantity';
                if (currencyDisplay) currencyDisplay.textContent = 'QTY';
            } else {
                if (toggleAmtBtn) { toggleAmtBtn.classList.add('bg-blue-500/15', 'text-blue-400'); toggleAmtBtn.classList.remove('text-slate-500'); }
                if (toggleQtyBtn) { toggleQtyBtn.classList.remove('bg-blue-500/15', 'text-blue-400'); toggleQtyBtn.classList.add('text-slate-500'); }
                if (inputLabel) inputLabel.textContent = 'Amount (₹)';
                if (currencyDisplay) currencyDisplay.textContent = '₹';
            }
        });
        this.updateEstimate();
    }

    getCurrentPrice() {
        if (!this.currentSymbol) return null;
        const priceElement = document.querySelector(`.price-display[data-symbol="${this.currentSymbol}"]`);
        const val = parseFloat((priceElement?.textContent || '').replace(/[^0-9.-]+/g,""));
        return isNaN(val) ? null : val;
    }

    updateEstimate() {
        const inputVal = parseFloat(document.getElementById('order-qty')?.value);
        const price = this.getCurrentPrice();
        const suffixes = ['', 'sheet-'];
        
        suffixes.forEach(s => {
            const estContainer = document.getElementById(s + 'order-estimate-container');
            const estLabel = document.getElementById(s + 'estimate-label');
            const estValue = document.getElementById(s + 'estimate-value');

            if (isNaN(inputVal) || inputVal <= 0 || this.tradeMode === 'margin' || !price) {
                estContainer?.classList.add('hidden');
                return;
            }

            estContainer?.classList.remove('hidden');
            if (this.inputMode === 'qty') {
                if (estLabel) estLabel.textContent = 'Est. Amount:';
                if (estValue) estValue.textContent = '₹' + (inputVal * price).toFixed(2);
            } else {
                if (estLabel) estLabel.textContent = 'Est. Qty:';
                if (estValue) estValue.textContent = (inputVal / price).toFixed(4);
            }
        });
    }

    updateMarginPreview() {
        if (this.tradeMode !== 'margin') return;
        const inputVal = parseFloat(document.getElementById('order-qty')?.value);
        const price = this.getCurrentPrice();

        const data = { ps: '--', q: '--', l: '--', r: '--' };

        if (!isNaN(inputVal) && inputVal > 0 && price) {
            const size = inputVal * this.leverage;
            const qty = size / price;
            const mmr = 0.004;
            const liq = this.marginSide === 'LONG' ? price * (1 - 1/this.leverage + mmr) : price * (1 + 1/this.leverage - mmr);
            
            data.ps = '₹' + size.toLocaleString('en-IN', {minimumFractionDigits:2});
            data.q = qty.toFixed(4);
            data.l = '₹' + liq.toLocaleString('en-IN', {minimumFractionDigits:2});
            data.r = (100/this.leverage).toFixed(2) + '%';
        }

        ['', 'sheet-'].forEach(s => {
            const psEl = document.getElementById(s + 'mp-position-size');
            const qEl = document.getElementById(s + 'mp-quantity');
            const lEl = document.getElementById(s + 'mp-liq-price');
            const rEl = document.getElementById(s + 'mp-margin-rate');
            if (psEl) psEl.textContent = data.ps;
            if (qEl) qEl.textContent = data.q;
            if (lEl) lEl.textContent = data.l;
            if (rEl) rEl.textContent = data.r;
        });
    }

    setQtyPercent(percent) {
        if (!this.currentSymbol) return;
        const inputEls = [document.getElementById('order-qty'), document.getElementById('sheet-order-qty')];
        const price = this.getCurrentPrice();
        
        let value = '';
        if (this.side === 'buy' || this.tradeMode === 'margin') {
            const balanceEl = document.getElementById('wallet-balance') || document.getElementById('topbar-wallet-balance');
            let balance = parseFloat((balanceEl?.textContent || '').replace(/[^0-9.-]+/g,""));
            if (!isNaN(balance)) {
                const targetAmount = (balance * percent) / 100;
                value = (this.tradeMode === 'margin' || this.inputMode === 'amt') ? targetAmount.toFixed(2) : (price ? (targetAmount / price).toFixed(4) : '');
            }
        } else {
            const posQtyEl = document.querySelector(`.sidebar-pos-qty[data-symbol="${this.currentSymbol}"]`);
            if (posQtyEl) {
                let availableQty = parseFloat(posQtyEl.textContent.match(/[\d.]+/)?.[0] || '0');
                if (!isNaN(availableQty)) {
                    const targetQty = (availableQty * percent) / 100;
                    value = (this.inputMode === 'qty') ? targetQty.toFixed(4) : (price ? (targetQty * price).toFixed(2) : '');
                }
            }
        }
        inputEls.forEach(el => { if(el) el.value = value; });
        this.updateEstimate();
        this.updateMarginPreview();
    }

    updateBalanceUI(data) {
        const balance = data.balance ?? data.wallet_balance;
        if (balance !== undefined) {
             const formattedBalance = `₹${parseFloat(balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
             document.querySelectorAll('[data-dashboard-total-assets]').forEach(el => el.textContent = formattedBalance);
             document.querySelectorAll('#wallet-balance, #sheet-wallet-balance, #topbar-wallet-balance').forEach(el => el.textContent = formattedBalance);
        }
    }

    showNotification(message, type) {
        if (window.Notifications) {
            switch(type) {
                case 'success': window.Notifications.success(message); break;
                case 'error': window.Notifications.error(message); break;
                default: window.Notifications.info(message);
            }
        } else {
            alert(message);
        }
    }

    async submitOrder() {
        if(!this.currentSymbol) {
            this.showNotification('Please select a symbol to trade.', 'error');
            return;
        }

        const inputVal = parseFloat(document.getElementById('order-qty')?.value);
        if(isNaN(inputVal) || inputVal <= 0) {
            this.showNotification('Please enter a valid amount.', 'warning');
            return;
        }

        const btns = [document.getElementById('submit-order-btn'), document.getElementById('sheet-submit-btn')];
        const originalHtmls = btns.map(b => b?.innerHTML);
        btns.forEach(b => { if(b) { b.disabled = true; b.innerHTML = '...'; } });

        try {
            let url, formData = new URLSearchParams();
            if (this.tradeMode === 'margin') {
                url = '/assets/margin/open/';
                formData.append('symbol', this.currentSymbol);
                formData.append('side', this.marginSide);
                formData.append('margin_amount', inputVal.toString());
                formData.append('leverage', this.leverage.toString());
            } else {
                url = '/assets/initiate-order/';
                formData.append('symbol', this.currentSymbol);
                formData.append('order_type', this.side.toUpperCase());
                if (this.inputMode === 'qty') formData.append('quantity', inputVal.toString());
                else formData.append('amount', inputVal.toString());
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            });

            const result = await response.json();
            if(result.success) {
                this.showNotification(result.message, 'success');
                document.getElementById('order-qty').value = '';
                document.getElementById('sheet-order-qty').value = '';
                this.updateMarginPositions();
                document.dispatchEvent(new CustomEvent('order_update', { detail: { status: 'completed' } }));
            } else {
                this.showNotification(result.message || 'Failed to place order.', 'error');
            }
        } catch (e) {
            this.showNotification('An error occurred.', 'error');
        } finally {
            btns.forEach((b, i) => { if(b) { b.disabled = false; b.innerHTML = originalHtmls[i]; } });
        }
    }

    async updateMarginPositions() {
        const tbody = document.getElementById('margin-positions-table-body');
        if (!tbody) return;

        try {
            const r = await fetch('/assets/margin/positions/');
            const data = await r.json();
            
            if (data.positions && data.positions.length > 0) {
                document.getElementById('margin-positions-banner')?.classList.remove('hidden');
                tbody.innerHTML = data.positions.map(p => {
                    const sideColor = p.side === 'LONG' ? 'text-emerald-400' : 'text-rose-400';
                    const pnlColor = p.unrealised_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
                    return `
                        <tr class="border-b border-slate-800/50 hover:bg-slate-800/40">
                            <td class="px-3 py-2 font-mono font-semibold text-blue-400">${p.symbol}</td>
                            <td class="px-3 py-2 text-center font-bold ${sideColor}">${p.side}</td>
                            <td class="px-3 py-2 text-center font-mono text-amber-400">${p.leverage}x</td>
                            <td class="px-3 py-2 text-right font-mono text-slate-300">₹${p.margin_used.toLocaleString()}</td>
                            <td class="px-3 py-2 text-right font-mono text-slate-300">₹${p.position_size.toLocaleString()}</td>
                            <td class="px-3 py-2 text-right font-mono text-slate-300">₹${p.entry_price.toLocaleString()}</td>
                            <td class="px-3 py-2 text-right font-mono text-rose-500 font-bold">₹${p.liquidation_price.toLocaleString()}</td>
                            <td class="px-3 py-2 text-right font-mono font-bold ${pnlColor}">${p.unrealised_pnl >= 0 ? '+' : ''}₹${p.unrealised_pnl.toLocaleString()}</td>
                            <td class="px-3 py-2 text-right font-mono font-bold ${pnlColor}">${p.roe_pct >= 0 ? '+' : ''}${p.roe_pct}%</td>
                            <td class="px-3 py-2 text-center">
                                <button class="rounded border border-rose-500/20 bg-rose-500/10 px-2 py-1 text-[9px] font-bold uppercase text-rose-400 hover:bg-rose-500 hover:text-white transition"
                                    onclick="TradingPanel.closeMarginPosition('${p.symbol}', '${p.side}', this)">Close</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            } else {
                document.getElementById('margin-positions-banner')?.classList.add('hidden');
                tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-8 text-center text-xs text-slate-600">No open margin positions</td></tr>';
            }
        } catch(e) {}
    }

    async closeMarginPosition(symbol, side, btn) {
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '...';
        const formData = new URLSearchParams();
        formData.append('symbol', symbol);
        formData.append('side', side);
        try {
            const r = await fetch('/assets/margin/close/', { method: 'POST', headers: { 'X-CSRFToken': this.getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest' }, body: formData });
            const result = await r.json();
            if (result.success) {
                this.showNotification(result.message, 'success');
                this.updateMarginPositions();
                document.dispatchEvent(new CustomEvent('order_update', { detail: { status: 'completed' } }));
            } else {
                this.showNotification(result.message, 'error');
                btn.disabled = false; btn.innerHTML = originalText;
            }
        } catch(e) { btn.disabled = false; btn.innerHTML = originalText; }
    }

    getCSRFToken() { return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''; }
}
window.TradingPanel = new TradingPanelController();
