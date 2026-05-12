class FinanceFormatter {
    toNumber(value) {
        if (value === null || value === undefined || value === '') return null;
        const parsed = Number(String(value).replace(/[^\d.-]/g, ''));
        return Number.isFinite(parsed) ? parsed : null;
    }

    formatCurrency(value, options = {}) {
        const {
            decimals = 2,
            signed = false,
            compact = false,
            placeholder = '--'
        } = options;

        const number = this.toNumber(value);
        if (number === null) return placeholder;

        if (compact) {
            const sign = signed ? (number >= 0 ? '+' : '-') : '';
            return `${sign}$${this.formatCompactNumber(Math.abs(number), { decimals })}`;
        }

        const sign = signed ? (number >= 0 ? '+' : '-') : '';
        return `${sign}$${Math.abs(number).toLocaleString('en-IN', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        })}`;
    }

    formatPercentage(value, options = {}) {
        const {
            decimals = 2,
            signed = true,
            placeholder = '--'
        } = options;

        const number = this.toNumber(value);
        if (number === null) return placeholder;

        const sign = signed ? (number >= 0 ? '+' : '-') : '';
        return `${sign}${Math.abs(number).toFixed(decimals)}%`;
    }

    formatCompactNumber(value, options = {}) {
        const {
            decimals = 1,
            placeholder = '--'
        } = options;

        const number = this.toNumber(value);
        if (number === null) return placeholder;

        return new Intl.NumberFormat('en', {
            notation: 'compact',
            maximumFractionDigits: decimals
        }).format(number);
    }

    polarityClass(value, positiveClass = 'text-green-400', negativeClass = 'text-red-400', neutralClass = 'text-slate-300') {
        const number = this.toNumber(value);
        if (number === null || number === 0) return neutralClass;
        return number > 0 ? positiveClass : negativeClass;
    }
}

class FinancialUISync {
    constructor() {
        this.formatter = new FinanceFormatter();
        this.state = {
            prices: new Map(),
            wallet: {
                balance: null,
                total_equity: null,
                total_unrealised_pnl: null,
                positions_count: null
            },
            portfolio: {
                positions: [],
                total_investment: null,
                total_current_value: null,
                total_unrealised_pnl: null,
                wallet_balance: null,
                total_equity: null,
                positions_count: null
            }
        };
        this.unsubscribers = [];
        this.bound = false;
    }

    init() {
        if (this.bound || !window.AppRealtime) return;
        this.bound = true;

        this.unsubscribers.push(
            window.AppRealtime.subscribePrices(({ updates }) => {
                requestAnimationFrame(() => {
                    this.ingestPrices(updates || []);
                });
            }),
            window.AppRealtime.subscribeWallet((payload) => {
                requestAnimationFrame(() => {
                    this.ingestWallet(payload || {});
                });
            }),
            window.AppRealtime.subscribePortfolio((payload) => {
                requestAnimationFrame(() => {
                    this.ingestPortfolio(payload || {});
                });
            }),
            window.AppRealtime.subscribe('connection:status', ({ state }) => {
                if (state === 'reconnecting' || state === 'failed') {
                    document.documentElement.dataset.realtimeState = state;
                } else if (state === 'connected') {
                    document.documentElement.dataset.realtimeState = 'connected';
                }
            })
        );

        window.addEventListener('pagehide', () => this.destroy(), { once: true });
    }

    destroy() {
        this.unsubscribers.forEach(unsubscribe => {
            if (typeof unsubscribe === 'function') unsubscribe();
        });
        this.unsubscribers = [];
        this.bound = false;
    }

    ingestPrices(updates) {
        updates.forEach(update => {
            if (update?.symbol) {
                this.state.prices.set(update.symbol, update);
            }
        });

        this.renderPriceDisplays();
        this.renderActiveSymbolDisplays();
        this.renderDerivedPositionMetrics();
    }

    ingestWallet(payload) {
        this.state.wallet = {
            ...this.state.wallet,
            ...payload,
            balance: payload.balance ?? payload.wallet_balance ?? this.state.wallet.balance,
            total_equity: payload.total_equity ?? this.state.wallet.total_equity,
            total_unrealised_pnl: payload.total_unrealised_pnl ?? this.state.wallet.total_unrealised_pnl,
            positions_count: payload.positions_count ?? this.state.wallet.positions_count
        };

        this.renderWalletDisplays();
    }

    ingestPortfolio(payload) {
        this.state.portfolio = {
            ...this.state.portfolio,
            ...payload,
            positions: Array.isArray(payload.positions) ? payload.positions : this.state.portfolio.positions
        };

        this.ingestWallet({
            balance: payload.wallet_balance,
            total_equity: payload.total_equity,
            total_unrealised_pnl: payload.total_unrealised_pnl,
            positions_count: payload.positions_count
        });

        this.renderPortfolioTotals();
        this.renderPortfolioCounts();
        this.renderDerivedPositionMetrics();
    }

    setText(selectorOrElements, text) {
        const elements = typeof selectorOrElements === 'string'
            ? document.querySelectorAll(selectorOrElements)
            : selectorOrElements;

        elements.forEach(el => {
            if (el) el.textContent = text;
        });
    }

    findWalletCardValue(labelText) {
        const labels = Array.from(document.querySelectorAll('span, p, div'));
        const label = labels.find(el => (el.textContent || '').trim() === labelText);
        if (!label) return null;

        const card = label.closest('.stat-card, .bg-dark-800\\/50, .bg-dark-800\\/50, .bg-dark-800\\/50');
        if (!card) return null;

        return card.querySelector('.font-mono');
    }

    setMoneyText(selectorOrElements, value, options = {}) {
        this.setText(selectorOrElements, this.formatter.formatCurrency(value, options));
    }

    setPercentText(selectorOrElements, value, options = {}) {
        this.setText(selectorOrElements, this.formatter.formatPercentage(value, options));
    }

    applySignedClass(elements, value, positiveClass = 'text-green-400', negativeClass = 'text-red-400', neutralClass = 'text-slate-300') {
        elements.forEach(el => {
            if (!el) return;
            
            const toRemove = [positiveClass, negativeClass, neutralClass, 'green', 'red']
                .flatMap(c => (c || '').split(' '))
                .filter(Boolean);
            
            if (toRemove.length > 0) {
                el.classList.remove(...toRemove);
            }
            
            const klass = this.formatter.polarityClass(value, positiveClass, negativeClass, neutralClass);
            klass.split(' ').forEach(token => {
                if (token) el.classList.add(token);
            });

            if (positiveClass === 'green' || negativeClass === 'red') {
                if (value > 0) el.classList.add('green');
                if (value < 0) el.classList.add('red');
            }
        });
    }

    renderPriceDisplays() {
        this.state.prices.forEach((price, symbol) => {
            document.querySelectorAll(`.price-display[data-symbol="${symbol}"]`).forEach(el => {
                el.textContent = this.formatter.formatCurrency(price.current_price);
                this.applySignedClass([el], price.percentage_change, 'text-green-400', 'text-red-400', 'text-white');
            });

            document.querySelectorAll(`.change-display[data-symbol="${symbol}"]`).forEach(el => {
                el.textContent = this.formatter.formatPercentage(price.percentage_change);
                this.applySignedClass([el], price.percentage_change, 'text-green-400', 'text-red-400', 'text-slate-300');
            });

            document.querySelectorAll(`.market-price[data-symbol="${symbol}"]`).forEach(el => {
                el.textContent = this.formatter.formatCurrency(price.current_price);
            });

            document.querySelectorAll(`[data-mini-buy="${symbol}"]`).forEach(el => {
                const buy = price.ask ?? price.current_price;
                el.textContent = this.formatter.formatCurrency(buy).replace('$', '');
            });

            document.querySelectorAll(`[data-mini-sell="${symbol}"]`).forEach(el => {
                const sell = price.bid ?? price.current_price;
                el.textContent = this.formatter.formatCurrency(sell).replace('$', '');
            });
        });

        const quickPrice = document.getElementById('quick-price');
        if (quickPrice && window.sheetSymbol && this.state.prices.has(window.sheetSymbol)) {
            quickPrice.textContent = this.formatter.formatCurrency(this.state.prices.get(window.sheetSymbol).current_price);
        }
    }

    renderActiveSymbolDisplays() {
        const activeSymbolText = (
            document.getElementById('active-symbol-header')?.textContent ||
            document.getElementById('sheet-symbol')?.textContent ||
            ''
        ).trim();

        if (!activeSymbolText || !this.state.prices.has(activeSymbolText)) return;
        const price = this.state.prices.get(activeSymbolText);

        const activePriceEl = document.getElementById('active-symbol-price');
        const activeChangeEl = document.getElementById('active-symbol-change');
        const tradeBidEl = document.getElementById('trade-bid');
        const tradeAskEl = document.getElementById('trade-ask');

        if (activePriceEl) {
            activePriceEl.textContent = this.formatter.formatCurrency(price.current_price);
            this.applySignedClass([activePriceEl], price.percentage_change, 'green', 'red', 'desk-price');
        }

        if (activeChangeEl) {
            activeChangeEl.textContent = this.formatter.formatPercentage(price.percentage_change);
            this.applySignedClass([activeChangeEl], price.percentage_change, 'pos', 'neg', 'desk-chg');
        }

        if (tradeBidEl) tradeBidEl.textContent = this.formatter.formatCurrency(price.bid ?? price.current_price);
        if (tradeAskEl) tradeAskEl.textContent = this.formatter.formatCurrency(price.ask ?? price.current_price);

        const sheetPriceEl = document.getElementById('sheet-price');
        const topBarPriceEl = document.getElementById('tb-price');
        if (sheetPriceEl && document.getElementById('sheet-symbol')?.textContent?.trim() === activeSymbolText) {
            sheetPriceEl.textContent = this.formatter.formatCurrency(price.current_price);
            this.applySignedClass([sheetPriceEl], price.percentage_change, 'green', 'red', '');
        }
        if (topBarPriceEl && document.getElementById('tb-symbol')?.textContent?.trim() === activeSymbolText) {
            topBarPriceEl.textContent = this.formatter.formatCurrency(price.current_price);
        }
    }

    renderWalletDisplays() {
        const balance = this.state.wallet.balance;
        const totalEquity = this.state.wallet.total_equity;
        const totalPnl = this.state.wallet.total_unrealised_pnl;

        if (balance !== null) {
            this.setMoneyText([
                document.getElementById('wallet-balance'),
                document.getElementById('stat-wallet'),
                document.getElementById('sheet-wallet-balance'),
                document.getElementById('wallet-page-available-balance'),
                this.findWalletCardValue('Available Balance')
            ].filter(Boolean), balance);
        }

        if (totalEquity !== null) {
            document.querySelectorAll('[data-dashboard-total-assets]').forEach(el => {
                el.textContent = this.formatter.formatCurrency(totalEquity);
            });
            this.setMoneyText([
                document.getElementById('wallet-page-total-equity'),
                document.getElementById('stat-total-portfolio'),
                this.findWalletCardValue('Total Equity')
            ].filter(Boolean), totalEquity);
        }

        if (totalPnl !== null) {
            const pnlTargets = [
                document.getElementById('dashboard-unrealised-pnl'),
                document.getElementById('wallet-page-total-pnl')
            ].filter(Boolean);

            pnlTargets.forEach(el => {
                el.textContent = this.formatter.formatCurrency(totalPnl, { signed: true });
            });
            this.applySignedClass(pnlTargets, totalPnl, 'text-green-400', 'text-red-400', 'text-slate-300');
        }
    }

    renderPortfolioTotals() {
        const portfolio = this.state.portfolio;

        if (portfolio.total_investment !== null) {
            document.querySelectorAll('[data-portfolio-total-investment]').forEach(el => {
                el.textContent = this.formatter.formatCurrency(portfolio.total_investment);
            });

            this.setMoneyText([
                document.getElementById('wallet-page-invested-amount'),
                document.getElementById('stat-invested'),
                this.findWalletCardValue('In Positions')
            ].filter(Boolean), portfolio.total_investment);
        }

        if (portfolio.total_current_value !== null) {
            document.querySelectorAll('[data-portfolio-current-value]').forEach(el => {
                el.textContent = this.formatter.formatCurrency(portfolio.total_current_value);
            });
        }
    }

    renderPortfolioCounts() {
        const count = this.state.portfolio.positions_count ?? this.state.wallet.positions_count;
        if (count === null || count === undefined) return;

        this.setText([
            document.getElementById('mobile-positions-count'),
            document.getElementById('desktop-open-positions-count'),
            document.getElementById('wallet-page-positions-count')
        ].filter(Boolean), String(count));

        const inPositionsCard = this.findWalletCardValue('In Positions');
        if (inPositionsCard?.nextElementSibling) {
            inPositionsCard.nextElementSibling.innerHTML = `${count} open positions`;
        }
    }

    renderDerivedPositionMetrics() {
        let totalUnrealised = 0;
        let currentHoldingsValue = 0;
        let anyPosition = false;

        document.querySelectorAll('.pnl-value[data-symbol]').forEach(pnlEl => {
            const symbol = pnlEl.dataset.symbol;
            const price = this.state.prices.get(symbol);
            const avg = this.formatter.toNumber(pnlEl.dataset.avg);
            const qty = this.formatter.toNumber(pnlEl.dataset.qty);
            const current = price?.current_price ?? this.formatter.toNumber(document.querySelector(`.market-price[data-symbol="${symbol}"]`)?.textContent);

            if (avg === null || qty === null || current === null) return;

            anyPosition = true;
            const pnl = (current - avg) * qty;
            const pnlPct = avg > 0 ? ((current - avg) / avg) * 100 : 0;
            const pnlPercentEl = document.querySelector(`.pnl-percent[data-symbol="${symbol}"]`);

            pnlEl.textContent = this.formatter.formatCurrency(pnl, { signed: true });
            this.applySignedClass([pnlEl], pnl, 'text-green-400', 'text-red-400', 'text-slate-300');

            if (pnlPercentEl) {
                pnlPercentEl.textContent = this.formatter.formatPercentage(pnlPct);
                this.applySignedClass([pnlPercentEl], pnlPct, 'text-green-400', 'text-red-400', 'text-slate-300');
            }

            totalUnrealised += pnl;
            currentHoldingsValue += current * qty;
        });

        if (anyPosition) {
            const walletBalance = this.state.wallet.balance ?? this.state.portfolio.wallet_balance ?? 0;
            this.state.wallet.total_unrealised_pnl = totalUnrealised;

            const unrealisedTargets = [
                document.getElementById('dashboard-unrealised-pnl'),
                document.getElementById('wallet-page-total-pnl')
            ].filter(Boolean);

            unrealisedTargets.forEach(el => {
                el.textContent = this.formatter.formatCurrency(totalUnrealised, { signed: true });
            });
            this.applySignedClass(unrealisedTargets, totalUnrealised, 'text-green-400', 'text-red-400', 'text-slate-300');

            const totalEquity = walletBalance + currentHoldingsValue;
            if (Number.isFinite(totalEquity)) {
                document.querySelectorAll('[data-dashboard-total-assets]').forEach(el => {
                    el.textContent = this.formatter.formatCurrency(totalEquity);
                });
                this.setMoneyText([
                    document.getElementById('wallet-page-total-equity'),
                    document.getElementById('stat-total-portfolio')
                ].filter(Boolean), totalEquity);
            }
        }
    }
}

window.FinanceFormatter = new FinanceFormatter();
window.FinancialUI = new FinancialUISync();
window.FinancialUI.init();
