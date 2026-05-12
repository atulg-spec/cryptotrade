class RealtimeManager {
    constructor() {
        this.bus = new EventTarget();
        this.sockets = new Map();
        this.reconnectAttempts = new Map();
        this.reconnectTimers = new Map();
        this.connectionState = new Map();
        this.maxReconnects = 8;
        this.initialized = false;
        this.socketDefinitions = {};
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        this.socketDefinitions = {
            market: `${protocol}//${host}/ws/watchlist/`,
            user: `${protocol}//${host}/ws/user-events/`
        };

        Object.entries(this.socketDefinitions).forEach(([name, url]) => {
            this.connect(name, url);
        });

        window.addEventListener('beforeunload', () => this.destroy());
    }

    destroy() {
        this.reconnectTimers.forEach(timer => clearTimeout(timer));
        this.reconnectTimers.clear();

        this.sockets.forEach(socket => {
            try {
                socket.onopen = null;
                socket.onmessage = null;
                socket.onclose = null;
                socket.onerror = null;
                socket.close();
            } catch (error) {
                console.error('Failed to close realtime socket:', error);
            }
        });

        this.sockets.clear();
        this.initialized = false;
    }

    connect(name, url) {
        const existing = this.sockets.get(name);
        if (existing && (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)) {
            return;
        }

        this.setConnectionState(name, 'connecting');
        const socket = new WebSocket(url);
        this.sockets.set(name, socket);

        socket.onopen = () => {
            this.reconnectAttempts.set(name, 0);
            this.setConnectionState(name, 'connected');
        };

        socket.onmessage = event => {
            try {
                const raw = JSON.parse(event.data);
                const events = this.normalizeSocketPayload(name, raw);
                events.forEach(eventInfo => this.publish(eventInfo.channel, eventInfo.payload, eventInfo.options));
            } catch (error) {
                console.error(`Error parsing realtime payload from [${name}]`, error);
            }
        };

        socket.onclose = () => {
            this.setConnectionState(name, 'disconnected');
            this.scheduleReconnect(name, url);
        };

        socket.onerror = error => {
            console.error(`Realtime socket error on [${name}]`, error);
            this.setConnectionState(name, 'error');
        };
    }

    scheduleReconnect(name, url) {
        const attempts = (this.reconnectAttempts.get(name) || 0) + 1;
        this.reconnectAttempts.set(name, attempts);

        if (attempts > this.maxReconnects) {
            this.publish('connection:status', {
                socket: name,
                state: 'failed',
                attempts
            });
            if (window.Notifications?.error) {
                window.Notifications.error('Live connection lost. Some data may stop updating.');
            }
            return;
        }

        const delay = Math.min(1000 * attempts, 10000);
        this.setConnectionState(name, 'reconnecting', { attempts, delay });

        const timer = setTimeout(() => {
            this.connect(name, url);
        }, delay);

        this.reconnectTimers.set(name, timer);
    }

    setConnectionState(name, state, extra = {}) {
        this.connectionState.set(name, state);
        this.publish('connection:status', {
            socket: name,
            state,
            ...extra,
            at: Date.now()
        }, { legacy: false });
    }

    isConnected(name) {
        if (!name) {
            return Array.from(this.connectionState.values()).every(state => state === 'connected');
        }
        return this.connectionState.get(name) === 'connected';
    }

    subscribe(channel, handler) {
        if (typeof handler !== 'function') {
            return () => {};
        }

        const wrapped = event => handler(event.detail);
        this.bus.addEventListener(channel, wrapped);
        return () => this.bus.removeEventListener(channel, wrapped);
    }

    publish(channel, payload, options = {}) {
        this.bus.dispatchEvent(new CustomEvent(channel, { detail: payload }));

        if (options.legacyEvent) {
            document.dispatchEvent(new CustomEvent(options.legacyEvent, {
                detail: options.legacyDetail !== undefined ? options.legacyDetail : payload
            }));
        }
    }

    publishLocal(channel, payload, options = {}) {
        this.publish(channel, {
            ...payload,
            source: payload?.source || 'local'
        }, options);
    }

    subscribePrices(handler) {
        return this.subscribe('market:prices', handler);
    }

    subscribeOrders(handler) {
        return this.subscribe('orders:update', handler);
    }

    subscribePortfolio(handler) {
        return this.subscribe('portfolio:update', handler);
    }

    subscribeWallet(handler) {
        return this.subscribe('wallet:update', handler);
    }

    subscribeWatchlist(handler) {
        return this.subscribe('watchlist:update', handler);
    }

    normalizeSocketPayload(socketName, raw) {
        if (socketName === 'market' && raw.type === 'price_update') {
            const updates = Array.isArray(raw.updates) ? raw.updates.map(update => ({
                id: update.id,
                symbol: update.symbol,
                name: update.name || '',
                current_price: Number(update.current_price || 0),
                price_change: Number(update.change ?? update.price_change ?? 0),
                percentage_change: Number(update.percentage_change ?? 0),
                open: Number(update.open ?? update.open_price ?? 0),
                high: Number(update.high ?? update.high_price ?? 0),
                low: Number(update.low ?? update.low_price ?? 0),
                volume: Number(update.volume ?? 0),
                bid: update.bid !== undefined ? Number(update.bid) : undefined,
                ask: update.ask !== undefined ? Number(update.ask) : undefined,
                last_updated: update.last_updated || null
            })) : [];

            return [{
                channel: 'market:prices',
                payload: {
                    updates,
                    source: 'socket',
                    received_at: Date.now()
                },
                options: {
                    legacyEvent: 'price_update',
                    legacyDetail: updates
                }
            }];
        }

        if (socketName === 'user') {
            const eventName = raw.event || raw.type;

            if (eventName === 'order_update') {
                const order = {
                    order_id: raw.order_id,
                    status: raw.status,
                    symbol: raw.symbol,
                    order_type: raw.order_type,
                    amount: Number(raw.amount || 0),
                    price: Number(raw.price || 0),
                    quantity: Number(raw.quantity || 0),
                    created_at: raw.created_at || null,
                    source: 'socket'
                };

                return [{
                    channel: 'orders:update',
                    payload: order,
                    options: {
                        legacyEvent: 'order_update',
                        legacyDetail: order
                    }
                }];
            }

            /* ── Backend margin risk alerts ── */
            if (eventName === 'margin_risk_warning' || eventName === 'margin_risk_closed') {
                const alert = {
                    event:    eventName,
                    symbol:   raw.symbol,
                    side:     raw.side,
                    risk_pct: raw.risk_pct,
                    message:  raw.message,
                };
                return [{
                    channel: `margin:${eventName}`,
                    payload: alert,
                    options: {
                        legacyEvent: eventName,
                        legacyDetail: alert,
                    }
                }];
            }


            if (eventName === 'portfolio_update') {
                const positions = Array.isArray(raw.positions) ? raw.positions.map(position => ({
                    stock_id: position.stock_id,
                    symbol: position.symbol,
                    name: position.name,
                    quantity: Number(position.quantity || 0),
                    avg_buy_price: Number(position.avg_buy_price || 0),
                    current_price: Number(position.current_price || 0),
                    current_value: Number(position.current_value || 0),
                    unrealised_pnl: Number(position.unrealised_pnl || 0),
                    pnl_percentage: Number(position.pnl_percentage || 0)
                })) : [];

                const portfolioPayload = {
                    positions,
                    total_investment: Number(raw.total_investment || 0),
                    total_current_value: Number(raw.total_current_value || 0),
                    total_unrealised_pnl: Number(raw.total_unrealised_pnl || 0),
                    wallet_balance: Number(raw.wallet_balance || 0),
                    total_equity: Number(raw.total_equity || 0),
                    positions_count: Number(raw.positions_count || positions.length),
                    source: 'socket'
                };

                return [
                    {
                        channel: 'portfolio:update',
                        payload: portfolioPayload,
                        options: {
                            legacyEvent: 'portfolio_update',
                            legacyDetail: portfolioPayload
                        }
                    },
                    {
                        channel: 'wallet:update',
                        payload: {
                            balance: portfolioPayload.wallet_balance,
                            total_equity: portfolioPayload.total_equity,
                            positions_count: portfolioPayload.positions_count,
                            total_unrealised_pnl: portfolioPayload.total_unrealised_pnl,
                            source: 'socket'
                        },
                        options: {
                            legacyEvent: 'balance_update',
                            legacyDetail: {
                                balance: portfolioPayload.wallet_balance,
                                total_equity: portfolioPayload.total_equity,
                                positions_count: portfolioPayload.positions_count,
                                total_unrealised_pnl: portfolioPayload.total_unrealised_pnl
                            }
                        }
                    }
                ];
            }
        }

        if (raw.type === 'book_update') {
            return [{
                channel: 'market:book',
                payload: raw,
                options: {
                    legacyEvent: 'book_update',
                    legacyDetail: raw
                }
            }];
        }

        if (raw.type === 'trade_update') {
            return [{
                channel: 'market:trade',
                payload: raw,
                options: {
                    legacyEvent: 'trade_update',
                    legacyDetail: raw
                }
            }];
        }

        return [];
    }
}

window.AppRealtime = new RealtimeManager();
window.WSManager = window.AppRealtime;
window.AppRealtime.init();
