class TradingPanelController {
    constructor() {
        this.currentSymbol = null;
        this.side = 'buy'; // 'buy' or 'sell'
        this.inputMode = 'qty'; // 'qty' or 'amt'
        
        // Listen to global events
        document.addEventListener('symbol_change', (e) => {
            this.setSymbol(e.detail.symbol);
        });

        // Listen for balance updates if the backend pushes them
        document.addEventListener('balance_update', (e) => {
            this.updateBalanceUI(e.detail);
        });
        
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
            toggleQtyBtn.className = 'flex-1 py-1 rounded transition-all bg-blue-500/20 text-blue-400';
            toggleAmtBtn.className = 'flex-1 py-1 rounded transition-all text-slate-400 hover:text-white';
            inputLabel.textContent = 'Quantity';
            currencyDisplay.textContent = 'QTY';
            inputEl.placeholder = '0.00';
        } else {
            toggleAmtBtn.className = 'flex-1 py-1 rounded transition-all bg-blue-500/20 text-blue-400';
            toggleQtyBtn.className = 'flex-1 py-1 rounded transition-all text-slate-400 hover:text-white';
            inputLabel.textContent = 'Amount';
            currencyDisplay.textContent = 'USD'; // or INR etc., depending on base currency
            inputEl.placeholder = '0.00';
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
            const balanceEl = document.getElementById('wallet-balance');
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
            // Sell
            const posQtyEl = document.querySelector(`.sidebar-pos-qty[data-symbol="${this.currentSymbol}"]`);
            if (!posQtyEl) return;
            let availableQty = parseFloat(posQtyEl.textContent);
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
        
        if (data.balance !== undefined) {
             const formattedBalance = `₹${parseFloat(data.balance).toFixed(2)}`;
             if(balanceDisplay) balanceDisplay.textContent = formattedBalance;
             if(walletDisplay) walletDisplay.textContent = formattedBalance;
             if(statWallet) statWallet.textContent = formattedBalance;
        }
    }

    async submitOrder() {
        if(!this.currentSymbol) {
            Notifications.error('Please select a symbol to trade.');
            return;
        }

        const inputVal = parseFloat(document.getElementById('order-qty')?.value);
        if(isNaN(inputVal) || inputVal <= 0) {
            Notifications.warning(`Please enter a valid ${this.inputMode === 'qty' ? 'quantity' : 'amount'}.`);
            return;
        }

        const price = this.getCurrentPrice();
        if(!price) {
            Notifications.error('Missing or invalid price for chosen symbol.');
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
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData.toString()
            });

            const result = await response.json();
            
            if(response.ok && result.success) {
                Notifications.success(`Order placed: ${this.side.toUpperCase()} ${qty} ${this.currentSymbol}`);
                if(document.getElementById('order-qty')) document.getElementById('order-qty').value = '';
                if(document.getElementById('order-price')) document.getElementById('order-price').value = '';
            } else {
                Notifications.error(result.message || 'Failed to place order.');
            }
        } catch (e) {
            console.error('Order submission error:', e);
            Notifications.error('An error occurred while placing your order.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = this.side === 'buy' ? 'Buy / Long' : 'Sell / Short';
        }
    }

    async closePosition(symbol, quantity, btn) {
        if (!symbol || !quantity) return;
        
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '...';

        const formData = new URLSearchParams();
        formData.append('symbol', symbol);
        formData.append('order_type', 'SELL');
        formData.append('quantity', quantity.toString());

        try {
            const response = await fetch('/assets/initiate-order/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData.toString()
            });

            const result = await response.json();
            
            if(response.ok && result.success) {
                Notifications.success(`Position closed: Sold ${quantity} ${symbol}`);
                // Background update will be triggered by websocket order_update
            } else {
                Notifications.error(result.message || 'Failed to close position.');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (e) {
            console.error('Close position error:', e);
            Notifications.error('An error occurred while closing position.');
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
