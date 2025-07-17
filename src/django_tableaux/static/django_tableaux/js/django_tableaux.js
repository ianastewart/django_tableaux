// Handle checkboxes in tables, and modal forms
'use strict';
let tableaux = (function () {
    const tb = {};
    let lastChecked = null;
    let selAll = null;
    let selAllPage = null;

    tb.init = function () {
        // request_width();

        selAll = document.getElementById('select_all');
        selAllPage = document.getElementById('select_all_page');

        if (selAllPage) {
            selAllPage.addEventListener("click", selectAllPage);
            selectAllPage();
        }
        if (selAll) {
            selAll.addEventListener("click", selectAll);
            selectAll();
        }

        document.querySelectorAll("table").forEach(e => e.addEventListener("click", tableClick));
        document.querySelectorAll(".auto-submit").forEach(e => e.addEventListener("change", function () {
            // Use a null check in case the form isn't on the page
            document.getElementById("id_filter_form")?.submit();
        }));
        document.querySelectorAll(".filter-clear").forEach(e => e.addEventListener("click", filterClear));
        document.querySelectorAll(".form-group.hx-get").forEach(e => e.addEventListener("change", filterChanged));

        document.body.addEventListener("trigger", function (evt) {
            window.htmx.ajax('GET', evt.detail.url, {source: '#table_data', target: '#table_data'});
        });

        // FIX: Moved selectListClick inside the IIFE so it's defined correctly
        document.body.addEventListener("click", selectListClick);

        // When editing a cell inline enter key triggers blur
        if (document.querySelector(".td_editing")) {
            // FIX: Changed `this` to `document` for correct event binding
            document.addEventListener("keypress", loseFocus);
        }
        countChecked();

        const breakpoints = {
            sm: 480,
            md: 768,
            lg: 1024,
            xl: 1280
        };

        // Convert object to sorted array of [name, value] pairs (ascending by value)
        const breakpointEntries = Object.entries(breakpoints).sort((a, b) => a[1] - b[1]);

        function getCurrentBreakpoint() {
            const width = window.innerWidth;
            let current = 'xs'; // default for widths below the smallest breakpoint

            for (const [name, value] of breakpointEntries) {
                if (width >= value) {
                    current = name;
                } else {
                    break; // stop once we've gone past the current width
                }
            }
            return current;
        }

        // Extract existing breakpoint from URL (if any)
        function getBreakpointFromURL() {
            const params = new URLSearchParams(window.location.search);
            return params.get('breakpoint');
        }

        let currentBreakpoint = getCurrentBreakpoint();
        let urlBreakpoint = getBreakpointFromURL();

        window.addEventListener('resize', () => {
            const newBreakpoint = getCurrentBreakpoint();
            if (newBreakpoint !== currentBreakpoint) {
                const url = new URL(window.location.href);
                url.searchParams.set('_bp', newBreakpoint);
                window.location.href = url.toString(); // Reload with updated breakpoint param
            }
            currentBreakpoint = newBreakpoint;
        });
    };


    //
    // const bp = new BreakpointHandler()


    // build media queries for the table's breakpoints
    // FIX: Added a null check to prevent errors if #breakpoints doesn't exist
    // const breakpointsEl = document.getElementById("breakpoints");
    // if (breakpointsEl) {
    //     const bps = JSON.parse(breakpointsEl.textContent);
    //     const mqls = [];
    //     for (let i = 0; i < bps.length; i++) {
    //         let mq = `(min-width: ${bps[i]}px)`;
    //         mqls.push(window.matchMedia(mq));
    //     }
    //
    //     function handleWidthChange(mql) {
    //         request_width();
    //     }
    //
    //     for (let i = 0; i < mqls.length; i++) {
    //         mqls[i].addEventListener("change", handleWidthChange);
    //     }
    // }
// }

    function request_width() {
        const width = window.outerWidth;
        const url = new URL(window.location.href);
        const w = url.searchParams.get("_width");
        if (w !== null && parseInt(w) !== width) {
            url.searchParams.set("_width", width);
            window.location.href = url.toString();
        }
    }

    function loseFocus(e) {
        if (e.key === "Enter") {
            document.activeElement.blur();
        }
    }

    function filterChanged() {
        // filter within header changed
        const input = this.querySelector('input, select');
        if (input) {
            window.htmx.ajax('GET', '', {source: `#${input.id}`, target: '#table_data'});
        }
    }

    function filterClear(e) {
        const inputGroup = e.target.closest(".input-group");
        if (inputGroup) {
            const input = inputGroup.querySelector('input, select');
            if (input) {
                window.htmx.ajax('GET', '', {source: input, target: input});
            }
        }
    }

    function selectAllPage() {
        // Click on 'Select all on page' highlights all rows
        if (!selAllPage) return;

        const checked = selAllPage.checked;
        if (selAll && selAll.parentElement) {
            selAll.parentElement.style.display = checked ? 'block' : 'none';
        }

        document.getElementsByName("select-checkbox").forEach(box => {
            box.checked = checked;
        });
        countChecked();
        lastChecked = null;
    }

    function selectAll() {
        if (!selAll) return;
        const checked = selAll.checked;
        const countEl = document.getElementById('count');

        if (checked) {
            if (countEl) countEl.innerText = 'All';
            if (selAllPage) selAllPage.disabled = true;
        } else {
            if (selAllPage) selAllPage.disabled = false;
        }

        document.getElementsByName("select-checkbox").forEach(box => {
            box.disabled = checked;
        });
        countChecked();
        lastChecked = null;
    }

    function tableClick(e) {
        const ClickAction = {
            NONE: "0",
            GET: "1",
            HX_GET: "2",
            CUSTOM: "3"
        };

        const target = e.target;

        // Handle inline editing dropdowns
        if (target.classList.contains("td-editing")) {
            if (target.classList.contains("open")) {
                const row = target.closest("tr");
                if (row && row.id) {
                    window.htmx.ajax('POST', "", {
                        source: `#${target.id}`,
                        target: `#${target.id}`,
                        values: {"id": row.id.split("_")[1]}
                    });
                }
                target.classList.remove("open");
            } else {
                target.classList.add("open");
            }
            return; // Exit after handling this specific case
        }

        // Close any open dropdowns when clicking elsewhere
        const openEditingEl = document.querySelector(".td-editing.open");
        if (openEditingEl) {
            const row = openEditingEl.closest("tr");
            if (row && row.id) {
                window.htmx.ajax('POST', "", {
                    source: `#${openEditingEl.id}`,
                    target: `#${openEditingEl.id}`,
                    values: {
                        "id": row.id.split("_")[1],
                        "column": target.name
                    }
                });
            }
            openEditingEl.classList.remove("open");
        }

        // Handle clicks on table cells (TD)
        if (target.tagName === 'TD') {
            // IMPROVEMENT: More robust check for the checkbox cell
            if (target.querySelector('[name="select-checkbox"]')) {
                return;
            }

            const row = target.closest("tr");
            const table = target.closest("table");
            if (!row || !table || !row.id) return;

            const pk = row.id.slice(3);
            // IMPROVEMENT: More robust way to get column index
            const col = Array.from(row.children).indexOf(target);
            const idSuffix = `_${pk}_${col}_${window.outerWidth}`;

            if (target.classList.contains("td-edit")) {
                target.id = "cell" + idSuffix;
                window.htmx.ajax('GET', "", {source: `#${target.id}`, target: `#${target.id}`});
            } else if (table.dataset.url) {
                let url = table.dataset.url;
                if (table.dataset.pk) {
                    url += pk;
                }
                if (table.dataset.click === ClickAction.GET) {
                    window.document.location.assign(url);
                } else if (table.dataset.click === ClickAction.HX_GET) {
                    window.htmx.ajax('GET', url, {source: `#${row.id}`, target: table.dataset.target});
                }
            } else if (table.dataset.click === ClickAction.CUSTOM) {
                target.id = "td" + idSuffix;
                window.htmx.ajax('GET', "", {
                    source: `#${target.id}`,
                    target: `#${target.id}`,
                });
            }
        }
        // Handle clicks on checkboxes for shift-selection
        else if (target.name === 'select-checkbox') {
            if (selAllPage) {
                selAllPage.checked = false;
            }
            if (!lastChecked) {
                lastChecked = target;
            } else if (e.shiftKey) {
                const chkBoxes = Array.from(document.getElementsByName("select-checkbox"));
                const start = chkBoxes.indexOf(target);
                const end = chkBoxes.indexOf(lastChecked);
                chkBoxes.slice(Math.min(start, end), Math.max(start, end) + 1).forEach(box => {
                    box.checked = target.checked;
                });
                lastChecked = target;
            } else {
                lastChecked = target;
            }
            countChecked();
        }
    }

    function countChecked() {
        if (selAll && selAll.checked) {
            return;
        }
        const ids = [];
        const boxes = document.querySelectorAll("input[name=select-checkbox]");
        boxes.forEach(el => {
            const row = el.closest("tr");
            const table = el.closest("table");
            if (!row || !table) return;

            const selectedClass = table.getAttribute("selected");
            if (el.checked) {
                ids.push(el.value);
                if (selectedClass) {
                    row.classList.add(selectedClass);
                }
            } else {
                if (selectedClass) {
                    row.classList.remove(selectedClass);
                }
            }
        });

        const hiddenInput = document.querySelector("input[name='selected_ids']");
        if (hiddenInput) {
            hiddenInput.value = ids.toString();
        }

        const count = ids.length;
        const countField = document.getElementById('count');
        if (countField) {
            countField.innerText = count.toString();
        }

        const actionMenu = document.getElementById('selectActionMenu');
        if (actionMenu) {
            // FIX: Removed invalid `.enabled` property and simplified logic
            actionMenu.disabled = (count === 0 && (!selAll || !selAll.checked));
        }
    }

// Handle clicks on a select list drop down as used for row and columns
    function selectListClick(ev) {
        const selectList = ev.target.closest(".select-list");

        // Close all other dropdowns first
        document.querySelectorAll(".select-options.opened").forEach(openedEl => {
            if (!selectList || !openedEl.parentElement.isEqualNode(selectList)) {
                openedEl.classList.remove("opened");
            }
        });

        if (selectList) {
            if (ev.target.classList.contains("select-title")) {
                selectList.querySelector(".select-options")?.classList.toggle("opened");
            } else if (!selectList.classList.contains("multiple")) {
                selectList.querySelector(".select-options")?.classList.remove("opened");
            }
        }
    }

// FIX: Moved return statement to the end of the IIFE
    return tb;
})
();

window.addEventListener("load", tableaux.init);
document.body.addEventListener("tableaux_init", tableaux.init);

// This function is in the global scope. If it's unused, it can be removed.
// If it is used, consider moving it inside the `tableaux` module for better encapsulation.
function handleClick() {
    let me = document.querySelector(".editing"); // Note: class is 'editing', not 'td-editing'
    if (me) {
        me.classList.toggle("open");
    }
}