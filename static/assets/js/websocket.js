class WebSocketManager {
    constructor() {
        this.sockets = {};
        this.reconnectAttempts = {};
        this.maxReconnects = 5;
    }

    init() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        // Connect to public prices
        this.connect('prices', `${protocol}//${host}/ws/watchlist/`);

        // Connect to authenticated user events
        this.connect('user_events', `${protocol}//${host}/ws/user-events/`);
    }

    connect(name, url) {
        this.reconnectAttempts[name] = this.reconnectAttempts[name] || 0;

        console.log(`Connecting to WebSocket [${name}]: ${url}`);
        const ws = new WebSocket(url);
        this.sockets[name] = ws;

        ws.onopen = () => {
            console.log(`WebSocket [${name}] connected.`);
            this.reconnectAttempts[name] = 0;
            if (name === 'prices') {
                // Notifications.success('Connected to live data stream');
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // The backend sends type="price_update" or event="order_update"
                const eventType = data.type || data.event;
                const payload = data.updates || data.payload || data;

                if (eventType) {
                    // Dispatch a global CustomEvent
                    document.dispatchEvent(new CustomEvent(eventType, {
                        detail: payload
                    }));
                }
            } catch (e) {
                console.error(`Error parsing WebSocket message from [${name}]:`, e);
            }
        };

        ws.onclose = () => {
            console.warn(`WebSocket [${name}] disconnected.`);
            this.attemptReconnect(name, url);
        };

        ws.onerror = (error) => {
            console.error(`WebSocket error on [${name}]:`, error);
        };
    }

    attemptReconnect(name, url) {
        if (this.reconnectAttempts[name] < this.maxReconnects) {
            this.reconnectAttempts[name]++;
            const delay = Math.min(2000 * this.reconnectAttempts[name], 10000);
            setTimeout(() => {
                this.connect(name, url);
            }, delay);
        } else {
            console.error(`Max reconnect attempts reached for [${name}]`);
            Notifications.error('Connection lost. Please refresh the page.');
        }
    }
}

window.WSManager = new WebSocketManager();
