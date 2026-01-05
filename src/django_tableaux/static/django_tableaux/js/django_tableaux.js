'use strict';

const BreakpointService = (function () {
    const BREAKPOINTS = {
        sm: 480,
        md: 768,
        lg: 1024,
        xl: 1280
    };

    let currentBreakpoint = null;
    const listeners = new Set();

    function getCurrentBreakpoint() {
        const width = window.innerWidth;
        let current = 'xs';

        for (const [name, value] of Object.entries(BREAKPOINTS).sort((a, b) => a[1] - b[1])) {
            if (width >= value) current = name;
            else break;
        }
        return current;
    }

    function notify(newBreakpoint) {
        listeners.forEach(cb => cb(newBreakpoint));
    }

    window.addEventListener('resize', () => {
        const next = getCurrentBreakpoint();
        if (next === currentBreakpoint) return;

        currentBreakpoint = next;
        notify(next);
    });

    currentBreakpoint = getCurrentBreakpoint();

    return {
        get: () => currentBreakpoint,
        subscribe: cb => listeners.add(cb),
        unsubscribe: cb => listeners.delete(cb)
    };
})();


let tableaux = (function () {
    const tb = {};

    // // Define breakpoints once at the top level
    // const BREAKPOINTS = {
    //     sm: 480, md: 768, lg: 1024, xl: 1280
    // };
    //
    // tb.getCurrentBreakpoint = function () {
    //     const width = window.innerWidth;
    //     let current = 'xs'; // Default for widths below the smallest breakpoint
    //
    //     const breakpointEntries = Object.entries(BREAKPOINTS).sort((a, b) => a[1] - b[1]);
    //
    //     for (const [name, value] of breakpointEntries) {
    //         if (width >= value) {
    //             current = name;
    //         } else {
    //             break; // Stop once we've gone past the current width
    //         }
    //     }
    //     return current;
    // };
    //
    // tb.setupResizeListener = function (el) {
    //     let currentBreakpoint = tb.getCurrentBreakpoint();
    //     let resizePending = false;
    //
    //     const handleResize = () => {
    //         if (resizePending) return;
    //
    //         const newBreakpoint = tb.getCurrentBreakpoint();
    //         if (newBreakpoint === currentBreakpoint) return;
    //
    //         resizePending = true;
    //         currentBreakpoint = newBreakpoint;
    //         document.querySelectorAll('input[name="bp"]').forEach(el => {
    //             el.value = newBreakpoint
    //         });
    //         htmx.trigger(el, 'tableauxResize', {
    //             breakpoint: newBreakpoint
    //         });
    //
    //         // allow HTMX request cycle to complete
    //         requestAnimationFrame(() => {
    //             resizePending = false;
    //         });
    //     };
    //
    //     window.addEventListener('resize', handleResize);
    // };
    tb.initElement = function (el) {
        if (!el || el._tableController) return;
        el._tableController = new TableController(el, el.dataset.prefix || "");
        // tb.setupResizeListener(el);
    }

    tb.initTableaux = function () {
        document.querySelectorAll('[data-controller="tableaux"]').forEach(tb.initElement);
    }
    return tb;
})
();

window.addEventListener("load", tableaux.initTableaux);

document.body.addEventListener("initTableauxId", e => {
    const id = e.detail?.id;
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    tableaux.initElement(el);
});


class TableController {
    constructor(container, prefix = "") {
        this.container = container;
        this.prefix = prefix; // e.g. "orders" or ""
        this.selAll = container.querySelector("#select_all");
        this.selAllPage = container.querySelector("#select_all_page");
        this.lastChecked = null;

        this.breakpoint = BreakpointService.get();
        this.onBreakpointChange = this.onBreakpointChange.bind(this);
        BreakpointService.subscribe(this.onBreakpointChange);
        this.syncBreakpointInput(this.breakpoint);

        this.bind();
        this.countChecked();
    }

    /* ---------- bindings ---------- */

    bind() {
        this.selAll?.addEventListener("click", () => this.selectAll());
        this.selAllPage?.addEventListener("click", () => this.selectAllPage());

        this.container
            .querySelectorAll("table")
            .forEach(t => t.addEventListener("click", e => this.tableClick(e)));

        if (this.container.querySelector(".td_editing")) {
            document.addEventListener("keypress", this.loseFocus);
        }
    }

    syncBreakpointInput(bp) {
        this.container
            .querySelectorAll('input[name="bp"]')
            .forEach(input => {
                input.value = bp;
            });
    }

    onBreakpointChange(newBreakpoint) {
        if (newBreakpoint === this.breakpoint) return;

        this.breakpoint = newBreakpoint;
        this.syncBreakpointInput(newBreakpoint);

        // trigger HTMX refresh for THIS table only
        window.htmx.trigger(this.container, "tableauxResize", {
            breakpoint: newBreakpoint
        });
    }

    destroy() {
        BreakpointService.unsubscribe(this.onBreakpointChange);
    }


    loseFocus(e) {
        if (e.key === "Enter") {
            document.activeElement?.blur();
        }
    }

    /* ---------- selection ---------- */

    selectAllPage() {
        if (!this.selAllPage) return;

        const checked = this.selAllPage.checked;

        if (this.selAll?.parentElement) {
            this.selAll.parentElement.style.display = checked ? "block" : "none";
        }

        this.container
            .querySelectorAll("input[name='select-checkbox']")
            .forEach(box => box.checked = checked);

        this.lastChecked = null;
        this.countChecked();
    }

    selectAll() {
        if (!this.selAll) return;

        const checked = this.selAll.checked;
        const countEl = this.container.querySelector(".count");

        if (checked) {
            if (countEl) countEl.innerText = "All";
            this.selAllPage && (this.selAllPage.disabled = true);
        } else {
            this.selAllPage && (this.selAllPage.disabled = false);
        }

        this.container
            .querySelectorAll("input[name='select-checkbox']")
            .forEach(box => box.disabled = checked);

        this.lastChecked = null;
        this.countChecked();
    }

    countChecked() {
        if (this.selAll?.checked) return;

        const ids = [];

        this.container
            .querySelectorAll("input[name='select-checkbox']")
            .forEach(el => {
                const row = el.closest("tr");
                const table = el.closest("table");
                if (!row || !table) return;

                const selectedClass = table.getAttribute("selected");

                if (el.checked) {
                    ids.push(el.value);
                    selectedClass && row.classList.add(selectedClass);
                } else {
                    selectedClass && row.classList.remove(selectedClass);
                }
            });

        const hidden = this.container.querySelector("input[name='selected_ids']");
        if (hidden) hidden.value = ids.toString();

        const countEl = this.container.querySelector(".count");
        if (countEl) countEl.innerText = ids.length.toString();

        const actionMenu = this.container.querySelector(".selectActionMenu");
        if (actionMenu) {
            actionMenu.disabled = ids.length === 0 && !this.selAll?.checked;
        }
    }

    /* ---------- table click ---------- */

    tableClick(e) {
        const ClickAction = {
            NONE: "0",
            GET: "1",
            HX_GET: "2",
            CUSTOM: "3"
        };

        const target = e.target;
        const row = target.closest("tr");
        const table = target.closest("table");
        if (!row || !table) return;
        const bits = row.id.split("_");
        const prefix = bits[0];
        const pk = bits[2];
        const form = this.container.querySelector(".filter-form");
        const formData = new FormData(form);
        const formObject = Object.fromEntries(formData.entries());

        /* inline editing */
        if (target.classList.contains("td-editing")) {
            target.classList.toggle("open");
            return;
        }

        const openEditing = this.container.querySelector(".td-editing.open");
        if (openEditing) {
            const openRow = openEditing.closest("tr");
            window.htmx.ajax("POST", "", {
                source: `#${openEditing.id}`,
                target: `#${openEditing.id}`,
                values: {
                    id: openRow.dataset.pk,
                    column: target.name
                }
            });
            openEditing.classList.remove("open");
        }

        if (target.tagName === "TD") {
            if (target.querySelector('[name="select-checkbox"]')) return;

            const col = Array.from(row.children).indexOf(target);
            const idSuffix = `_cell_${pk}_${col}_${window.outerWidth}`;

            if (target.classList.contains("td-edit")) {
                target.id = idSuffix;
                window.htmx.ajax("GET", "", {
                    source: `#${target.id}`,
                    target: `#${target.id}`
                });
            } else if (table.dataset.url) {
                let url = table.dataset.url;
                if (table.dataset.pk) url += pk;

                if (table.dataset.click === ClickAction.GET) {
                    window.location.assign(url);
                } else if (table.dataset.click === ClickAction.HX_GET) {
                    window.htmx.ajax("GET", url, {
                        source: table,
                        target: table.dataset.target,
                        values: formObject
                    });
                }
            } else if (table.dataset.click === ClickAction.CUSTOM) {
                target.id = `_td_${pk}_${col}_${window.outerWidth}`;
                window.htmx.ajax("GET", "", {
                    source: `#${target.id}`,
                    target: `#${target.id}`,
                    values: formObject
                });
            }
        } else if (target.name === "select-checkbox") {
            this.selAllPage && (this.selAllPage.checked = false);

            if (!this.lastChecked) {
                this.lastChecked = target;
            } else if (e.shiftKey) {
                const boxes = Array.from(
                    this.container.querySelectorAll("input[name='select-checkbox']")
                );
                const start = boxes.indexOf(target);
                const end = boxes.indexOf(this.lastChecked);
                boxes
                    .slice(Math.min(start, end), Math.max(start, end) + 1)
                    .forEach(box => box.checked = target.checked);
                this.lastChecked = target;
            } else {
                this.lastChecked = target;
            }
            this.countChecked();
        }
    }
}

