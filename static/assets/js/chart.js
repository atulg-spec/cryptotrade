class ChartManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.widget = null;
        this.currentSymbol = null;

        // Listen to global symbol changes
        document.addEventListener('symbol_change', (e) => {
            this.loadChart(e.detail.symbol);
        });
    }

    init() {
        // If symbol is already selected via global scope or WatchlistManager, load it seamlessly
        if (window.WatchlistManager && window.WatchlistManager.activeSymbol) {
            this.loadChart(window.WatchlistManager.activeSymbol);
        }
    }

    formatSymbol(symbol) {
        let sym = symbol.toUpperCase();
        if (sym.endsWith("USDT")) {
            return `BINANCE:${sym}`;
        }
        return sym;
    }

    loadChart(symbol) {
        if (this.currentSymbol === symbol) return;
        this.currentSymbol = symbol;

        const container = document.getElementById(this.containerId);
        if (!container) return;

        container.innerHTML = ""; // Clear old chart

        if (typeof TradingView === 'undefined') {
            console.error('TradingView script not loaded');
            return;
        }

        this.widget = new TradingView.widget({
            width: "100%",
            height: "100%",
            symbol: this.formatSymbol(symbol),
            interval: "1",
            timezone: "Asia/Kolkata",
            theme: "dark",
            style: "1",
            locale: "en",
            toolbar_bg: "#0b101e",
            enable_publishing: false,
            allow_symbol_change: false,
            container_id: this.containerId,
            backgroundColor: "#0f172a",
            gridColor: "rgba(255,255,255,0.02)",
            hide_top_toolbar: false,
            hide_side_toolbar: false,
            hide_legend: false,
            details: false,
            hotlist: false,
            calendar: false,
            save_image: false
        });
    }
}

window.TradingChart = new ChartManager('tv-chart-container');
