class ChartManager {
  constructor(defaultContainerId) {
    this.defaultContainerId = defaultContainerId;
    this.widgets = {};
    this.currentSymbol = null;
    this.currentInterval = "60";

    document.addEventListener("symbol_change", (e) => {
      if (e.detail && e.detail.symbol) {
        this.currentSymbol = e.detail.symbol;

        if (document.getElementById(this.defaultContainerId)) {
          this.loadChart(e.detail.symbol, this.defaultContainerId);
        }
      }
    });

    document.addEventListener("chart_interval_change", (e) => {
      if (e.detail && e.detail.interval) {
        this.currentInterval = e.detail.interval;
        const symbol = this.currentSymbol || "BTCUSDT";

        if (document.getElementById(this.defaultContainerId)) {
          this.loadChart(symbol, this.defaultContainerId);
        }

        const stockSheet = document.getElementById("stock-sheet");
        const mobileContainer = document.getElementById("sheet-tv-chart");

        if (stockSheet && mobileContainer && stockSheet.classList.contains("open")) {
          this.loadChart(symbol, "sheet-tv-chart");
        }
      }
    });
  }

  init() {
    const initialSymbol =
      (window.WatchlistManager && window.WatchlistManager.activeSymbol) || "BTCUSDT";

    this.currentSymbol = initialSymbol;

    if (document.getElementById(this.defaultContainerId)) {
      this.loadChart(initialSymbol, this.defaultContainerId);
    }
  }

  formatSymbol(symbol) {
    let sym = String(symbol || "").toUpperCase().trim();

    if (sym === "XAUUSD") return "OANDA:XAUUSD";
    if (sym === "BTCUSD" || sym === "BTC/USD") return "BINANCE:BTCUSDT";
    if (sym === "ETHUSD" || sym === "ETH/USD") return "BINANCE:ETHUSDT";
    if (sym.endsWith("USDT")) return `BINANCE:${sym}`;

    return sym.includes(":") ? sym : `BINANCE:${sym}`;
  }

  destroyChart(containerId = this.defaultContainerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";
    this.widgets[containerId] = null;
  }

  loadChart(symbol, containerId = this.defaultContainerId) {
    if (!symbol) symbol = "BTCUSDT";

    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Chart container not found: ${containerId}`);
      return;
    }

    if (typeof TradingView === "undefined") {
      console.error("TradingView script not loaded");
      return;
    }

    const formattedSymbol = this.formatSymbol(symbol);
    this.currentSymbol = symbol;

    this.destroyChart(containerId);

    try {
      // Check if mobile (screen width < 1024px)
      const isMobile = window.innerWidth < 1024;
      
      this.widgets[containerId] = new TradingView.widget({
        container_id: containerId,
        width: "100%",
        height: "100%",
        autosize: true,
        symbol: formattedSymbol,
        interval: this.currentInterval,
        timezone: "Etc/UTC",
        theme: "dark",
        style: "1",
        locale: "en",
        toolbar_bg: "#131c2b",
        backgroundColor: "#131c2b",
        gridColor: "rgba(255,255,255,0.05)",
        enable_publishing: false,
        allow_symbol_change: false,
        hide_top_toolbar: isMobile, // Show top toolbar on desktop, hide on mobile (we'll use custom bottom bar)
        hide_side_toolbar: true, // Always hide side toolbar - we use custom bottom bar on mobile
        hide_legend: false,
        withdateranges: isMobile, // Show date ranges on mobile as part of bottom bar
        details: false,
        hotlist: false,
        calendar: false,
        save_image: false,
        disabled_features: [
          "header_resolutions",
          "timeframes_toolbar",
          "header_compare",
          "header_symbol_search",
          "symbol_search_hot_key",
          "header_screenshot",
          "display_market_status",
          "go_to_date",
          "show_hide_button_in_legend",
          "border_around_the_chart"
        ]
      });
    } catch (err) {
      console.error(`TradingView widget failed for ${containerId}:`, err);
      container.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;font-family:sans-serif;">
          Chart failed to load
        </div>
      `;
    }
  }

  loadSymbol(symbol, containerId = this.defaultContainerId) {
    this.loadChart(symbol, containerId);
  }
}

window.TradingChart = new ChartManager("tv-chart-container");

document.addEventListener("DOMContentLoaded", () => {
  window.TradingChart.init();
});


