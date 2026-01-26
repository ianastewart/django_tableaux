class Dropdown {
    constructor(button, menu) {
        this.button = button;
        this.menu = menu;
        this.toggle = this.toggle.bind(this);
        this.close = this.close.bind(this);
        this.onClickOutside = this.onClickOutside.bind(this);

        // Attach events
        this.button.addEventListener("click", this.toggle);
        document.addEventListener("click", this.onClickOutside);
    }

    toggle(e) {
        e.stopPropagation();
        if (this.menu.hidden) {
            const r = this.button.getBoundingClientRect();
            this.menu.style.left = `${r.left + window.scrollX}px`;
            this.menu.style.top = `${r.bottom + window.scrollY}px`;
            this.menu.hidden = false;
            this.button.setAttribute("aria-expanded", "true");
        } else {
            this.close();
        }
    }

    close() {
        this.menu.hidden = true;
        this.button.setAttribute("aria-expanded", "false");
    }

    onClickOutside(e) {
        if (!this.menu.contains(e.target) && e.target !== this.button) {
            this.close();
        }
    }

    destroy() {
        this.button.removeEventListener("click", this.toggle);
        document.removeEventListener("click", this.onClickOutside);
        this.close();
    }
}

function initDropdowns(root = document) {
    root.querySelectorAll("[data-dropdown-button]").forEach(btn => {
        const menu = btn.nextElementSibling;
        if (!menu?.matches("[data-dropdown-menu]")) return;

        // Prevent double-binding
        if (btn._dropdown) return;

        btn._dropdown = new Dropdown(btn, menu);
    });
}

// Before HTMX swaps content, destroy old dropdowns
document.body.addEventListener("htmx:beforeSwap", e => {
    e.target.querySelectorAll("[data-dropdown-button]").forEach(btn => btn._dropdown?.destroy());
});

// After swap, re-initialize dropdowns in the new content
document.body.addEventListener("htmx:afterSwap", e => initDropdowns(e.target));

