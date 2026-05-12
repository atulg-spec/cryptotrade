window.TradingToast = {
    ensureContainer(modalRoot) {
        let container = modalRoot.querySelector('.sheet-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'sheet-toast-container absolute left-4 right-4 top-4 z-[99999] space-y-2 pointer-events-none';
            modalRoot.appendChild(container);
        }
        return container;
    },

    show(modalRoot, message, type = 'info') {
        if (!modalRoot) return;

        const classes = {
            success: 'bg-emerald-500/95 border-emerald-400/50',
            error: 'bg-rose-500/95 border-rose-400/50',
            warning: 'bg-amber-500/95 border-amber-400/50',
            info: 'bg-blue-500/95 border-blue-400/50',
        };

        const container = this.ensureContainer(modalRoot);
        const toast = document.createElement('div');
        toast.className = `${classes[type] || classes.info} border text-slate-100 text-sm font-medium rounded-xl px-4 py-3 shadow-lg backdrop-blur-md pointer-events-auto transition-all duration-300 ease-out -translate-y-2 opacity-0`;
        toast.textContent = message;
        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.remove('-translate-y-2', 'opacity-0');
        });

        setTimeout(() => {
            toast.classList.add('-translate-y-2', 'opacity-0');
            setTimeout(() => {
                toast.remove();
                if (container.children.length === 0) container.remove();
            }, 300);
        }, 3000);
    },
};
