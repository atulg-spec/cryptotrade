class WatchlistController {
    constructor() {
        this.activeSymbol = null;

        // Listen to global price updates
        document.addEventListener('price_update', (e) => {
            this.onPriceUpdate(e.detail);
        });
    }

    init() {
        this.searchInput = document.getElementById('watchlist-search-input');
        this.searchResults = document.getElementById('watchlist-search-results');

        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(() => {
                this.searchStocks(this.searchInput.value);
            }, 300));

            // Hide results on click outside
            document.addEventListener('click', (e) => {
                if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                    this.searchResults.classList.add('hidden');
                }
            });
        }

        this.bindWatchlistItems();

        // Set initial symbol from DOM structure if available
        const firstItem = document.querySelector('.watchlist-item[data-symbol]');
        if (firstItem && !this.activeSymbol) {
            this.setActiveSymbol(firstItem.getAttribute('data-symbol'));
        }
    }

    bindWatchlistItems() {
        document.querySelectorAll('.watchlist-item').forEach(item => {
            // Remove old listener if any (to avoid duplicates)
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);

            newItem.addEventListener('click', (e) => {
                if (e.target.closest('.favorite-star') || e.target.closest('button')) return;
                const symbol = newItem.getAttribute('data-symbol');
                if (symbol) this.setActiveSymbol(symbol);
            });
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async searchStocks(query) {
        if (query.length < 1) {
            this.searchResults.classList.add('hidden');
            return;
        }

        try {
            const response = await fetch(`/assets/watchlist/search/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderSearchResults(data.results);
        } catch (error) {
            console.error('Search failed:', error);
        }
    }

    renderSearchResults(results) {
        if (results.length === 0) {
            this.searchResults.innerHTML = '<div class="p-3 text-xs text-slate-500">No stocks found.</div>';
        } else {
            this.searchResults.innerHTML = results.map(s => `
                <div class="flex items-center justify-between p-3 hover:bg-white/[0.05] cursor-pointer border-b border-white/5 transition-colors" 
                    onclick="WatchlistManager.handleSearchResultClick('${s.symbol}', event)">
                    <div class="flex flex-col">
                        <span class="text-xs font-bold text-white">${s.symbol}</span>
                        <span class="text-[10px] text-slate-500 stock-name-label">${s.name}</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="text-right">
                            <div class="text-xs font-mono text-white">₹${s.price.toFixed(2)}</div>
                            <div class="text-[10px] font-mono ${s.change >= 0 ? 'text-green-400' : 'text-red-400'}">${s.change >= 0 ? '+' : ''}${s.change.toFixed(2)}%</div>
                        </div>
                        <svg onclick="WatchlistManager.toggleFavorite('${s.symbol}', event)" 
                            class="w-4 h-4 favorite-star ${s.is_in_watchlist ? 'text-amber-400' : 'text-slate-600'} hover:text-amber-400 transition-colors cursor-pointer"
                            fill="${s.is_in_watchlist ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                    </div>
                </div>
            `).join('');
        }
        this.searchResults.classList.remove('hidden');
    }

    handleSearchResultClick(symbol, event) {
        if (event.target.closest('button')) return;
        this.setActiveSymbol(symbol);
        this.searchResults.classList.add('hidden');
        this.searchInput.value = '';
    }

    async addToWatchlist(symbol, event) {
        if (event) event.stopPropagation();
        try {
            const response = await fetch(`/assets/watchlist/add/${symbol}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });
            const data = await response.json();
            if (data.success) {
                // If we're calling this, we want to add it to the DOM immediately
                const favContent = document.getElementById('fav-content');
                if (favContent && !favContent.querySelector(`.watchlist-item[data-symbol="${symbol}"]`)) {
                    const html = this.createWatchlistItemHTML({ symbol: symbol, name: symbol, exchange: 'BINANCE' });
                    const emptyMsg = favContent.querySelector('.text-center.py-8');
                    if (emptyMsg) emptyMsg.remove();
                    favContent.insertAdjacentHTML('afterbegin', html);
                    this.bindWatchlistItems();

                    // Switch to fav tab to show the new item
                    if (typeof switchTab === 'function') switchTab('fav');
                }
                Notifications.success(data.message);
            } else {
                Notifications.error(data.message);
            }
        } catch (error) {
            console.error('Failed to add to watchlist:', error);
        }
    }

    async removeFromWatchlist(symbol, event) {
        if (event) event.stopPropagation();
        try {
            const response = await fetch(`/assets/watchlist/remove/${symbol}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });
            const data = await response.json();
            if (data.success) {
                document.querySelectorAll(`.watchlist-item[data-symbol="${symbol}"]`).forEach(el => el.remove());
                this.checkEmptyWatchlist();

                // Also update star in search results if visible
                document.querySelectorAll(`.favorite-star[onclick*="'${symbol}'"]`).forEach(s => {
                    s.classList.remove('text-amber-400');
                    s.classList.add('text-slate-600');
                    s.setAttribute('fill', 'none');
                });

                Notifications.success(data.message);
            } else {
                Notifications.error(data.message);
            }
        } catch (error) {
            console.error('Failed to remove from watchlist:', error);
        }
    }

    setActiveSymbol(symbol) {
        if (this.activeSymbol === symbol) return;
        this.activeSymbol = symbol;

        // Highlight active item
        document.querySelectorAll('.watchlist-item').forEach(item => {
            item.classList.remove('bg-white/[0.1]', 'border-blue-500/50');
            if (item.getAttribute('data-symbol') === symbol) {
                item.classList.add('bg-white/[0.1]', 'border-blue-500/50');
            }
        });

        // Broadcast symbol change to the rest of the application
        document.dispatchEvent(new CustomEvent('symbol_change', {
            detail: { symbol: symbol }
        }));
    }

    onPriceUpdate(updates) {
        if (!Array.isArray(updates)) return;

        updates.forEach(update => {
            const stockId = update.id;
            const symbol = update.symbol;

            // Standard display boxes might be mapped via symbol
            // Support both .watchlist-item (desktop) and .witem (mobile)
            const elements = document.querySelectorAll(`[data-symbol="${symbol}"]`);
            elements.forEach(item => {
                const priceEl = item.querySelector('.price-display');
                const changeEl = item.querySelector('.change-display');

                if (priceEl && update.current_price) {
                    const oldPrice = parseFloat(priceEl.textContent.replace(/[^0-9.-]+/g, "")) || update.current_price;
                    const newPrice = update.current_price;

                    priceEl.textContent = newPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

                    // Color transitions
                    priceEl.classList.remove('text-green-400', 'text-red-400', 'text-white');
                    if (newPrice > oldPrice) {
                        priceEl.classList.add('text-green-400');
                    } else if (newPrice < oldPrice) {
                        priceEl.classList.add('text-red-400');
                    } else {
                        priceEl.classList.add('text-white');
                    }
                }

                if (changeEl && update.percentage_change !== undefined) {
                    const isPositive = update.percentage_change >= 0;
                    changeEl.className = `change-display font-mono text-[10px] ${isPositive ? 'text-green-400' : 'text-red-400'}`;
                    changeEl.textContent = `${isPositive ? '+' : ''}${update.percentage_change.toFixed(2)}%`;
                }
            });
        });
    }

    async toggleFavorite(symbol, event) {
        if (event) event.stopPropagation();

        // Support both desktop (.favorite-star) and mobile (.star-btn) elements
        const starBtn = event.target.closest('.star-btn, .favorite-star');
        const isFavorite = starBtn?.classList.contains('fav') || starBtn?.classList.contains('text-amber-400');
        const url = isFavorite ? `/assets/watchlist/remove/${symbol}/` : `/assets/watchlist/add/${symbol}/`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            if (data.success) {
                // Update all star buttons for this symbol (both desktop and mobile)
                document.querySelectorAll(`.star-btn[onclick*="'${symbol}'"], .favorite-star[onclick*="'${symbol}'"]`).forEach(btn => {
                    if (isFavorite) {
                        // Remove favorite
                        btn.classList.remove('fav');
                        btn.classList.remove('text-amber-400');
                        btn.classList.add('text-slate-600');
                        // Update SVG fill
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            svg.setAttribute('fill', 'none');
                        }
                    } else {
                        // Add favorite
                        btn.classList.add('fav');
                        btn.classList.remove('text-slate-600');
                        btn.classList.add('text-amber-400');
                        // Update SVG fill
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            svg.setAttribute('fill', 'currentColor');
                        }
                    }
                });

                // Update watchlist items (both desktop and mobile)
                const items = document.querySelectorAll(`[data-symbol="${symbol}"]`);
                items.forEach(item => {
                    if (item.closest('#fav-content')) {
                        item.remove();
                    }
                });
                this.checkEmptyWatchlist();

                // If adding favorite, also update search result stars and add to watchlist
                if (!isFavorite) {
                    document.querySelectorAll(`.favorite-star[onclick*="'${symbol}'"]`).forEach(s => {
                        s.classList.remove('text-slate-600');
                        s.classList.add('text-amber-400');
                        s.setAttribute('fill', 'currentColor');
                    });

                    // Dynamically add to watchlist if not already there
                    const favContent = document.getElementById('fav-content');
                    if (favContent && !favContent.querySelector(`.watchlist-item[data-symbol="${symbol}"]`)) {
                        // We need some stock data to render. If we're coming from search, we might have it.
                        const searchItem = event.target.closest('.flex.items-center.justify-between.p-3');
                        let name = "Stock";
                        if (searchItem) {
                            const nameLabel = searchItem.querySelector('.stock-name-label');
                            name = nameLabel ? nameLabel.textContent : "Stock";
                        }

                        const html = this.createWatchlistItemHTML({
                            symbol: symbol,
                            name: name,
                            exchange: 'BINANCE'
                        });

                        // Remove "No favorites" if present
                        const emptyMsg = favContent.querySelector('.text-center.py-8');
                        if (emptyMsg) emptyMsg.remove();

                        favContent.insertAdjacentHTML('afterbegin', html);
                        this.bindWatchlistItems();

                        // Switch to fav tab to show the new item
                        if (typeof switchTab === 'function') switchTab('fav');
                    }
                }
                Notifications.success(data.message);
            } else {
                Notifications.error(data.message || 'Failed to update favorite');
            }
        } catch (error) {
            console.error('Toggle favorite failed:', error);
        }
    }

    createWatchlistItemHTML(fav) {
        return `
            <div class="watchlist-item flex items-center justify-between px-3 py-2.5 cursor-pointer border-b border-white/[0.02] hover:bg-white/[0.05] transition-colors group" data-symbol="${fav.symbol}">
                <div class="flex items-center gap-2">
                    <svg onclick="WatchlistManager.toggleFavorite('${fav.symbol}', event)" 
                        class="w-3.5 h-3.5 favorite-star text-amber-400 hover:text-amber-400 transition-colors"
                        fill="currentColor" stroke="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    <div>
                        <div class="text-sm font-semibold text-white">${fav.symbol}</div>
                        <div class="text-[10px] text-slate-500">${fav.exchange || 'BINANCE'}</div>
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <div class="text-right">
                        <div class="font-mono text-sm font-semibold price-display" data-symbol="${fav.symbol}">--</div>
                        <div class="font-mono text-[10px] change-display" data-symbol="${fav.symbol}">--</div>
                    </div>
                    <button onclick="WatchlistManager.removeFromWatchlist('${fav.symbol}', event)" 
                        class="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all text-slate-600">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    checkEmptyWatchlist() {
        const favContent = document.getElementById('fav-content');
        if (favContent && favContent.querySelectorAll('.watchlist-item').length === 0) {
            favContent.innerHTML = '<div class="text-center py-8 text-slate-500 text-sm">No favorites added.</div>';
        }
    }

    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

window.WatchlistManager = new WatchlistController();
document.addEventListener('DOMContentLoaded', () => {
    WatchlistManager.init();
});     