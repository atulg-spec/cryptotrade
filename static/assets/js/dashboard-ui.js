class DashboardUIController {
    constructor() {
        this.config = null;
        this.managed = true;
        this.unsubscribers = [];
        this.initialized = false;
        this.activeSymbol = null;
    }

    init(config = {}) {
        this.config = {
            watchlistItemSelector: '.watchlist-item[data-symbol]',
            activeItemClass: 'watchlist-item-active',
            activeSymbolHeaderId: 'active-symbol-header',
            activePriceId: 'active-symbol-price',
            activeChangeId: 'active-symbol-change',
            activeChangeResetClass: '',
            tradePanelSymbolId: 'trade-panel-symbol',
            avatarId: null,
            refreshIds: [],
            refreshCallback: null,
            onSymbolActivated: null,
            onOrderCompleted: null,
            defaultSymbol: null,
            ...config
        };

        this.bindRealtimeHandlers();
        this.bindDefaultSymbol();
        this.initialized = true;
    }

    bindRealtimeHandlers() {
        if (window.AppRealtime?.subscribeOrders) {
            this.unsubscribers.push(window.AppRealtime.subscribeOrders((order) => {
                if (window.Notifications?.info) {
                    window.Notifications.info(`Order Status: ${order.status} for ${order.symbol || 'your order'}`);
                }
                if (order.status === 'completed' && typeof this.config.onOrderCompleted === 'function') {
                    this.config.onOrderCompleted(order);
                }
            }));
        }

        if (window.AppRealtime?.subscribePortfolio) {
            this.unsubscribers.push(window.AppRealtime.subscribePortfolio(() => {
                this.refreshSectionsFromCurrentPage();
            }));
        }

        document.addEventListener('symbol_change', this.handleSymbolChange);
        window.addEventListener('pagehide', () => this.destroy(), { once: true });
    }

    destroy = () => {
        document.removeEventListener('symbol_change', this.handleSymbolChange);
        this.unsubscribers.forEach(unsubscribe => {
            if (typeof unsubscribe === 'function') unsubscribe();
        });
        this.unsubscribers = [];
    };

    bindDefaultSymbol() {
        const { defaultSymbol } = this.config;
        if (!defaultSymbol) return;
        this.setActiveSymbolUI(defaultSymbol);
        document.dispatchEvent(new CustomEvent('symbol_change', { detail: { symbol: defaultSymbol } }));
    }

    getActiveSymbolHeader() {
        return document.getElementById(this.config.activeSymbolHeaderId);
    }

    getTradePanelSymbol() {
        return document.getElementById(this.config.tradePanelSymbolId);
    }

    clearActiveStates() {
        document.querySelectorAll(this.config.watchlistItemSelector).forEach(item => {
            item.classList.remove(this.config.activeItemClass);
        });
    }

    setActiveSymbolUI(symbol, el = null) {
        this.activeSymbol = symbol;
        this.clearActiveStates();

        const target = el || document.querySelector(`${this.config.watchlistItemSelector}[data-symbol="${symbol}"]`);
        if (target) target.classList.add(this.config.activeItemClass);

        const header = this.getActiveSymbolHeader();
        const tradeSymbol = this.getTradePanelSymbol();
        const avatar = this.config.avatarId ? document.getElementById(this.config.avatarId) : null;

        if (header) header.textContent = symbol;
        if (tradeSymbol) tradeSymbol.textContent = symbol;
        if (avatar && symbol) avatar.textContent = symbol.charAt(0).toUpperCase();
    }

    resetActivePriceDisplays() {
        const priceEl = document.getElementById(this.config.activePriceId);
        const changeEl = document.getElementById(this.config.activeChangeId);

        if (priceEl) priceEl.textContent = '--';
        if (changeEl) {
            changeEl.textContent = '--';
            if (this.config.activeChangeResetClass) {
                changeEl.className = this.config.activeChangeResetClass;
            }
        }
    }

    selectSymbol(symbol, el = null) {
        this.setActiveSymbolUI(symbol, el);
        if (typeof this.config.onSymbolActivated === 'function') {
            this.config.onSymbolActivated(symbol, el);
        }
        document.dispatchEvent(new CustomEvent('symbol_change', { detail: { symbol } }));
    }

    handleSymbolChange = (event) => {
        const symbol = event.detail?.symbol;
        if (!symbol) return;
        this.setActiveSymbolUI(symbol);
        this.resetActivePriceDisplays();
    };

    refreshSectionsFromCurrentPage() {
        const refreshIds = Array.isArray(this.config.refreshIds) ? this.config.refreshIds : [];
        const refreshCallback = this.config.refreshCallback;
        if (!refreshIds.length && typeof refreshCallback !== 'function') return;

        fetch(window.location.href)
            .then(response => response.text())
            .then(html => {
                const doc = new DOMParser().parseFromString(html, 'text/html');
                refreshIds.forEach(id => {
                    const nextEl = doc.getElementById(id);
                    const currentEl = document.getElementById(id);
                    if (!nextEl || !currentEl) return;
                    currentEl.innerHTML = nextEl.innerHTML;
                });

                if (typeof refreshCallback === 'function') {
                    refreshCallback(doc);
                }
            })
            .catch(error => console.error('Dashboard section refresh failed', error));
    }
}

window.DashboardUI = new DashboardUIController();
