class TradingPanelController {
    constructor() {
        this.currentSymbol = null;
        this.side = 'buy'; // 'buy' or 'sell'
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
        });
    }

    setSymbol(symbol) {
        this.currentSymbol = symbol;
        const symbolLabel = document.getElementById('trade-panel-symbol');
        if(symbolLabel) symbolLabel.textContent = symbol;
    }

    initListeners() {

        const submitBtn = document.getElementById('submit-order-btn');
        if(submitBtn) {
            submitBtn.addEventListener('click', this.submitOrder.bind(this));
        }

        const toggleQtyBtn = document.getElementById('toggle-qty');
        const toggleAmtBtn = document.getElementById('toggle-amt');

        if(toggleQtyBtn && toggleAmtBtn) {
            toggleQtyBtn.addEventListener('click', () => this.setInputMode('qty'));
            toggleAmtBtn.addEventListener('click', () => this.setInputMode('amt'));
        }

        const inputEl = document.getElementById('order-qty');
        const priceInputEl = document.getElementById('order-price');
        if(inputEl) {
            inputEl.addEventListener('input', () => this.updateEstimate());
        }
        if(priceInputEl) {
            priceInputEl.addEventListener('input', () => this.updateEstimate());
        }

        // We make setQtyPercent globally visible so inline onclick handlers can use it
        window.setQtyPercent = this.setQtyPercent.bind(this);
    }
    
    setInputMode(mode) {
        this.inputMode = mode;
        const toggleQtyBtn = document.getElementById('toggle-qty');
        const toggleAmtBtn = document.getElementById('toggle-amt');
        const inputLabel = document.getElementById('order-input-label');
        const currencyDisplay = document.getElementById('order-currency-display');
        const inputEl = document.getElementById('order-qty');

        if (mode === 'qty') {
            // Use the qa-btn class pattern from the mobile UI
            if (toggleQtyBtn) {
                toggleQtyBtn.classList.add('active');
                toggleQtyBtn.classList.remove('text-slate-400');
            }
            if (toggleAmtBtn) {
                toggleAmtBtn.classList.remove('active');
                toggleAmtBtn.classList.add('text-slate-400');
            }
            if (inputLabel) inputLabel.textContent = 'Quantity';
            if (currencyDisplay) currencyDisplay.textContent = 'QTY';
            if (inputEl) inputEl.placeholder = '0.00';
        } else {
            if (toggleAmtBtn) {
                toggleAmtBtn.classList.add('active');
                toggleAmtBtn.classList.remove('text-slate-400');
            }
            if (toggleQtyBtn) {
                toggleQtyBtn.classList.remove('active');
                toggleQtyBtn.classList.add('text-slate-400');
            }
            if (inputLabel) inputLabel.textContent = 'Amount (₹)';
            if (currencyDisplay) currencyDisplay.textContent = '₹';
            if (inputEl) inputEl.placeholder = '0.00';
        }
        this.updateEstimate();
    }

    getCurrentPrice() {
        if (!this.currentSymbol) return null;
        const priceElement = document.querySelector(`.price-display[data-symbol="${this.currentSymbol}"]`);
        const val = parseFloat((priceElement?.textContent || '').replace(/[^0-9.-]+/g,""));
        return isNaN(val) ? null : val;
    }

    updateEstimate() {
        const inputEl = document.getElementById('order-qty');
        const estContainer = document.getElementById('order-estimate-container');
        const estLabel = document.getElementById('estimate-label');
        const estValue = document.getElementById('estimate-value');
        
        const val = parseFloat(inputEl.value);
        if (isNaN(val) || val <= 0) {
            estContainer.classList.add('hidden');
            return;
        }

        const price = this.getCurrentPrice();
        if (!price) {
            estContainer.classList.add('hidden');
            return;
        }

        estContainer.classList.remove('hidden');
        if (this.inputMode === 'qty') {
            estLabel.textContent = 'Est. Amount:';
            estValue.textContent = '₹' + (val * price).toFixed(2);
        } else {
            estLabel.textContent = 'Est. Qty:';
            estValue.textContent = (val / price).toFixed(4);
        }
    }

    setQtyPercent(percent) {
        if (!this.currentSymbol) return;
        const inputEl = document.getElementById('order-qty');
        const price = this.getCurrentPrice();
        
        if (this.side === 'buy') {
            // Support both old and new balance element IDs
            const balanceEl = document.getElementById('wallet-balance') || 
                              document.getElementById('trade-panel-wallet-balance') ||
                              document.getElementById('topbar-wallet-balance');
            let balance = parseFloat((balanceEl?.textContent || '').replace(/[^0-9.-]+/g,""));
            if (isNaN(balance)) return;
            const targetAmount = (balance * percent) / 100;
            
            if (this.inputMode === 'amt') {
                inputEl.value = targetAmount.toFixed(2);
            } else {
                if (!price) return;
                inputEl.value = (targetAmount / price).toFixed(4);
            }
        } else {
            // Sell - support both old and new position quantity element selectors
            const posQtyEl = document.querySelector(`.sidebar-pos-qty[data-symbol="${this.currentSymbol}"]`) ||
                             document.querySelector(`[data-symbol="${this.currentSymbol}"] .w-ex`);
            if (!posQtyEl) return;
            // Extract quantity from text like "Qty: 0.5432"
            const qtyText = posQtyEl.textContent;
            const qtyMatch = qtyText.match(/[\d.]+/);
            if (!qtyMatch) return;
            let availableQty = parseFloat(qtyMatch[0]);
            if (isNaN(availableQty)) return;
            
            const targetQty = (availableQty * percent) / 100;
            if (this.inputMode === 'qty') {
                inputEl.value = targetQty.toFixed(4);
            } else {
                if (!price) return;
                inputEl.value = (targetQty * price).toFixed(2);
            }
        }
        this.updateEstimate();
    }

    updateBalanceUI(data) {
        const balanceDisplay = document.querySelector('[data-dashboard-total-assets]');
        const walletDisplay = document.getElementById('wallet-balance');
        const statWallet = document.getElementById('stat-wallet');
        
        const balance = data.balance ?? data.wallet_balance;
        if (balance !== undefined) {
             data.balance = balance;
             const formattedBalance = `₹${parseFloat(data.balance).toFixed(2)}`;
             if(balanceDisplay) balanceDisplay.textContent = formattedBalance;
             if(walletDisplay) walletDisplay.textContent = formattedBalance;
             if(statWallet) statWallet.textContent = formattedBalance;
        }
    }

    /**
     * Show notification inside the stock sheet modal if open, otherwise use global notifications
     */
    showNotification(message, type) {
        // Check if stock sheet is open
        const stockSheet = document.getElementById('stock-sheet');
        if (stockSheet && stockSheet.classList.contains('open')) {
            this.showStockSheetNotification(message, type);
        } else if (window.Notifications) {
            switch(type) {
                case 'success': window.Notifications.success(message); break;
                case 'error': window.Notifications.error(message); break;
                case 'warning': window.Notifications.warning(message); break;
                default: window.Notifications.info(message);
            }
        }
    }

    /**
     * Show notification inside the stock sheet modal
     */
    showStockSheetNotification(message, type) {
        type = type || 'info';
        const stockSheet = document.getElementById('stock-sheet');
        if (!stockSheet) return;

        // Remove existing toast container if any
        let container = stockSheet.querySelector('.sheet-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'sheet-toast-container';
            container.style.cssText = 'position: absolute; top: 16px; left: 16px; right: 16px; z-index: 99999; pointer-events: none;';
            stockSheet.appendChild(container);
        }

        const colors = {
            success: 'background: rgba(0, 214, 143, 0.95); border: 1px solid rgba(0, 214, 143, 0.5);',
            error: 'background: rgba(255, 77, 109, 0.95); border: 1px solid rgba(255, 77, 109, 0.5);',
            warning: 'background: rgba(245, 166, 35, 0.95); border: 1px solid rgba(245, 166, 35, 0.5);',
            info: 'background: rgba(79, 140, 255, 0.95); border: 1px solid rgba(79, 140, 255, 0.5);'
        };

        const toast = document.createElement('div');
        toast.style.cssText = (colors[type] || colors.info) + 
            ' backdrop-filter: blur(12px); border-radius: 10px; padding: 12px 16px; color: #e8edf7; font-size: 13px; font-family: var(--fui); display: flex; align-items: center; gap: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); pointer-events: auto; transform: translateY(-10px); opacity: 0; transition: all 0.3s ease;';
        toast.innerHTML = '<span style="flex: 1; font-weight: 500;">' + message + '</span>';

        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        });

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                toast.remove();
                if (container.children.length === 0) container.remove();
            }, 300);
        }, 3000);
    }

    /**
     * Update balance display across all balance elements
     */
    updateBalanceDisplay() {
        // Fetch fresh balance from server
        fetch(window.location.href, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(r => r.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update all balance-related elements
            const balanceIds = [
                'topbar-wallet-balance',
                'trade-panel-wallet-balance',
                'wallet-balance',
                'stat-wallet',
                'sheet-wallet-balance'
            ];
            
            balanceIds.forEach(id => {
                const newEl = doc.getElementById(id);
                const oldEl = document.getElementById(id);
                if (newEl && oldEl) {
                    oldEl.textContent = newEl.textContent;
                }
            });
            
            // Update total assets
            const newTotalAssets = doc.querySelector('[data-dashboard-total-assets]');
            const oldTotalAssets = document.querySelector('[data-dashboard-total-assets]');
            if (newTotalAssets && oldTotalAssets) {
                oldTotalAssets.textContent = newTotalAssets.textContent;
            }
            
            // Update unrealized P&L
            const newPnl = doc.getElementById('dashboard-unrealised-pnl');
            const oldPnl = document.getElementById('dashboard-unrealised-pnl');
            if (newPnl && oldPnl) {
                oldPnl.textContent = newPnl.textContent;
                oldPnl.className = newPnl.className;
            }
        })
        .catch(err => console.error('Balance update failed:', err));
    }

    async submitOrder() {
        if(!this.currentSymbol) {
            this.showNotification('Please select a symbol to trade.', 'error');
            return;
        }

        const inputVal = parseFloat(document.getElementById('order-qty')?.value);
        if(isNaN(inputVal) || inputVal <= 0) {
            this.showNotification(`Please enter a valid ${this.inputMode === 'qty' ? 'quantity' : 'amount'}.`, 'warning');
            return;
        }

        const price = this.getCurrentPrice();
        if(!price) {
            this.showNotification('Missing or invalid price for chosen symbol.', 'error');
            return;
        }

        let qty, amount;
        if (this.inputMode === 'qty') {
            qty = inputVal;
            amount = qty * price;
        } else {
            amount = inputVal;
            qty = amount / price;
        }

        const formData = new URLSearchParams();
        formData.append('symbol', this.currentSymbol);
        formData.append('order_type', this.side.toUpperCase());
        
        // Use 'amount' or 'quantity' depending on trade parameters accepted by backend
        // Standardizing it: the backend might calculate the other, but let's pass both just in case, or what it expects
        if(this.side === 'buy') {
            formData.append('amount', amount.toString());
            // optionally pass quantity if the backend allows literal quantities for buys
            formData.append('quantity', qty.toString());
        } else {
            formData.append('quantity', qty.toString());
            // optional amount
            formData.append('amount', amount.toString());
        }


        const submitBtn = document.getElementById('submit-order-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Processing...';

        try {
            const response = await fetch('/assets/initiate-order/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const result = await response.json();
            
            if(response.ok && result.success) {
                this.showNotification(`Order placed: ${this.side.toUpperCase()} ${this.currentSymbol} - ₹${amount.toFixed(2)}`, 'success');
                
                if (window.AppRealtime && !window.AppRealtime.isConnected('user')) {
                    this.updateBalanceDisplay();
                    window.AppRealtime.publishLocal('orders:update', {
                        status: 'completed',
                        symbol: this.currentSymbol,
                        order_type: this.side.toUpperCase(),
                        amount: amount,
                        quantity: qty,
                        optimistic: true
                    }, {
                        legacyEvent: 'order_update'
                    });
                }
                
                if(document.getElementById('order-qty')) document.getElementById('order-qty').value = '';
                if(document.getElementById('order-price')) document.getElementById('order-price').value = '';
            } else {
                this.showNotification(result.message || 'Failed to place order.', 'error');
            }
        } catch (e) {
            console.error('Order submission error:', e);
            this.showNotification('An error occurred while placing your order.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = this.side === 'buy' ? 'Buy / Long' : 'Sell / Short';
        }
    }

    async closePosition(symbol, quantity, btn) {
        if (!symbol || !quantity) return;
        
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = 'Closing...';

        const formData = new FormData();
        formData.append('symbol', symbol);
        formData.append('order_type', 'SELL');
        formData.append('quantity', quantity.toString());

        try {
            const response = await fetch('/assets/initiate-order/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const result = await response.json();
            
            if(response.ok && result.success) {
                this.showNotification(`Position closed: Sold ${quantity} ${symbol}`, 'success');
                
                if (window.AppRealtime && !window.AppRealtime.isConnected('user')) {
                    this.updateBalanceDisplay();
                    window.AppRealtime.publishLocal('orders:update', {
                        status: 'completed',
                        symbol: symbol,
                        order_type: 'SELL',
                        quantity: Number(quantity),
                        optimistic: true
                    }, {
                        legacyEvent: 'order_update'
                    });
                }
            } else {
                this.showNotification(result.message || 'Failed to close position.', 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (e) {
            console.error('Close position error:', e);
            this.showNotification('An error occurred while closing position.', 'error');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

window.TradingPanel = new TradingPanelController();
