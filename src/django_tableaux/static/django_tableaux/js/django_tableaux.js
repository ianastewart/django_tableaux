
const BREAKPOINTS = {
    sm: 480, md: 768, lg: 1024, xl: 1280
};
getCurrentBreakpoint = function () {
        const width = window.innerWidth;
        let current = 'xs'; // Default for widths below the smallest breakpoint

        const breakpointEntries = Object.entries(BREAKPOINTS).sort((a, b) => a[1] - b[1]);

        for (const [name, value] of breakpointEntries) {
            if (width >= value) {
                current = name;
            } else {
                break; // Stop once we've gone past the current width
            }
        }
        return current;
    };

class TableController {
    constructor(container, prefix = "") {
        this.container = container;
        this.prefix = prefix; // e.g. "orders" or ""
        this.selAll = container.querySelector("#select_all");
        this.selAllPage = container.querySelector("#select_all_page");
        this.lastChecked = null;
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

        this.container
            .querySelectorAll(".filter-clear")
            .forEach(el => el.addEventListener("click", filterClear));

        this.container
            .querySelectorAll(".filter-submit")
            .forEach(el => el.addEventListener("change", filterChanged));

        if (this.container.querySelector(".td_editing")) {
            document.addEventListener("keypress", this.loseFocus);
        }
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

        // const pk = row.dataset.pk;
        const form = this.container.querySelector(".action-form");
        // if (!pk || !form) return;

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

function initTableaux(root = document) {
    root
        .querySelectorAll('[data-controller="tableaux"]')
        .forEach(el => {
            if (!el._tableController) {
                el._tableController = new TableController(el);
            }
        });
}

window.addEventListener("load", () => initTableaux());
document.body.addEventListener("htmx:afterSwap", e => initTableaux(e.target));

