class OrderbookController {
    constructor() {
        this.currentSymbol = null;
        
        // Listen to global events
        document.addEventListener('symbol_change', (e) => {
            this.setSymbol(e.detail.symbol);
        });

        document.addEventListener('book_update', (e) => {
            this.onBookUpdate(e.detail);
        });

        document.addEventListener('trade_update', (e) => {
            this.onTradeUpdate(e.detail);
        });

        document.addEventListener('price_update', (e) => {
            const updates = e.detail;
            if (!this.currentSymbol) return;
            const update = updates.find(u => u.symbol === this.currentSymbol);
            if (update) {
                this.generateMockBookAndTrades(update.current_price);
            }
        });
    }

    setSymbol(symbol) {
        this.currentSymbol = symbol;
        this.clearBooks();
        // Since we are using standard sockets, you might want to fetch a snapshot here
        // fetch(`/api/orderbook?symbol=${symbol}`) ...
    }

    clearBooks() {
        const bidsContainer = document.getElementById('bids-container');
        const asksContainer = document.getElementById('asks-container');
        const tradesContainer = document.getElementById('recent-trades-container');
        
        if(bidsContainer) bidsContainer.innerHTML = '';
        if(asksContainer) asksContainer.innerHTML = '';
        if(tradesContainer) tradesContainer.innerHTML = '';
    }

    onBookUpdate(data) {
        if(data.symbol !== this.currentSymbol) return;

        // Render bids (green)
        this.renderOrderList('bids-container', data.bids, 'text-green-400');
        
        // Render asks (red)
        this.renderOrderList('asks-container', data.asks, 'text-red-400');
    }

    generateMockBookAndTrades(centerPrice) {
        const asks = [];
        let currentAsk = centerPrice * 1.0001;
        for(let i = 0; i < 15; i++) {
            asks.push({ price: currentAsk, amount: Math.random() * 2 + 0.1 });
            currentAsk += (Math.random() * 0.0005 * centerPrice);
        }
        asks.sort((a,b) => b.price - a.price);

        const bids = [];
        let currentBid = centerPrice * 0.9999;
        for(let i = 0; i < 15; i++) {
            bids.push({ price: currentBid, amount: Math.random() * 2 + 0.1 });
            currentBid -= (Math.random() * 0.0005 * centerPrice);
        }

        const isBuy = Math.random() > 0.5;
        const tradePrice = isBuy ? asks[asks.length-1].price : bids[0].price;
        
        this.onBookUpdate({ symbol: this.currentSymbol, bids: bids, asks: asks });

        if (Math.random() > 0.3) {
            this.onTradeUpdate({
                symbol: this.currentSymbol,
                price: tradePrice,
                amount: Math.random() * 1.5 + 0.05,
                side: isBuy ? 'buy' : 'sell',
                time: Date.now()
            });
        }
    }

    renderOrderList(containerId, orders, colorClass) {
        const container = document.getElementById(containerId);
        if(!container || !orders) return;

        // Limit to 15 items max for UI performance
        const displayOrders = orders.slice(0, 15);
        
        container.innerHTML = displayOrders.map(order => `
            <div class="flex justify-between text-[11px] py-1 hover:bg-white/[0.05] cursor-pointer px-2">
                <span class="${colorClass}">${order.price.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</span>
                <span class="text-gray-300 font-mono">${order.amount.toFixed(4)}</span>
                <span class="text-gray-500 font-mono">${(order.price * order.amount).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</span>
            </div>
        `).join('');
    }

    onTradeUpdate(data) {
        if(data.symbol !== this.currentSymbol) return;
        
        const container = document.getElementById('recent-trades-container');
        if(!container) return;

        const colorClass = data.side === 'buy' ? 'text-green-400' : 'text-red-400';
        const timeStr = new Date(data.time || Date.now()).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

        const row = document.createElement('div');
        row.className = 'flex justify-between text-[11px] py-1 hover:bg-white/[0.05] px-2 font-mono';
        row.innerHTML = `
            <span class="${colorClass}">${data.price.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</span>
            <span class="text-gray-300">${data.amount.toFixed(4)}</span>
            <span class="text-gray-500">${timeStr}</span>
        `;

        container.prepend(row);
        
        if(container.children.length > 20) {
            container.lastChild.remove();
        }
    }
}

window.OrderbookManager = new OrderbookController();
