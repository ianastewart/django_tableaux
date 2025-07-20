// Handle checkboxes in tables, and modal forms
'use strict';
let tableaux = (function () {
    const tb = {};
    let lastChecked = null;
    let selAll = null;
    let selAllPage = null;

    // Define breakpoints once at the top level
    const BREAKPOINTS = {
        sm: 480,
        md: 768,
        lg: 1024,
        xl: 1280
    };
    let currentBreakpoint = null;

    /**
     * A utility to delay the execution of a function until after a certain time has passed
     * without it being called again. This is useful for performance-heavy events like 'resize'.
     * @param {Function} func The function to debounce.
     * @param {number} delay The delay in milliseconds.
     * @returns {Function} The debounced function.
     */
    function debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    tb.getCurrentBreakpoint = function () {
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

    /**
     * Sets up a debounced event listener for window resize to handle breakpoint changes efficiently.
     */
    function setupResizeListener() {
        // Set the initial breakpoint on load
        currentBreakpoint = tb.getCurrentBreakpoint();
        let active = true;
        const handleResize = () => {
            const newBreakpoint = tb.getCurrentBreakpoint();
            if (active) {
                if (newBreakpoint !== currentBreakpoint) {
                    console.log(`Breakpoint changed from ${currentBreakpoint} to ${newBreakpoint}`);

                    active = false;
                    currentBreakpoint = newBreakpoint;
                    const url = new URL(window.location.href);
                    url.searchParams.set('_bp', newBreakpoint);
                    let count = 0;
                    // Find all tableaux tables and reload them with the new breakpoint
                    document.querySelectorAll(".tableaux").forEach(tableaux => {
                        count++;
                        htmx.ajax('GET', url.toString(), {
                            target: `#${tableaux.id}`,
                            swap: "outerHTML",
                            values: {_bp: newBreakpoint}
                        }).then(() => {
                                count--;
                            // If all tables reloaded but the breakpoint has further changed, trigger a resize
                            if (count === 0) {
                                    active = true
                                    if (tb.getCurrentBreakpoint() !== currentBreakpoint) {
                                        window.dispatchEvent(new Event('resize'))
                                    }
                                }
                            }
                        );
                    });
                }
            }
        };
        window.addEventListener('resize', handleResize)
    }


    tb.init = function () {
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
            document.getElementById("id_filter_form")?.submit();
        }));
        document.querySelectorAll(".filter-clear").forEach(e => e.addEventListener("click", filterClear));
        document.querySelectorAll(".form-group.hx-get").forEach(e => e.addEventListener("change", filterChanged));

        document.body.addEventListener("trigger", function (evt) {
            window.htmx.ajax('GET', evt.detail.url, {source: '#table_data', target: '#table_data'});
        });

        document.body.addEventListener("click", selectListClick);

        if (document.querySelector(".td_editing")) {
            document.addEventListener("keypress", loseFocus);
        }
        countChecked();

        // Set up the responsive breakpoint handler
        setupResizeListener();
    }

    function loseFocus(e) {
        if (e.key === "Enter") {
            document.activeElement.blur();
        }
    }

    function filterChanged() {
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
            return;
        }

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

        if (target.tagName === 'TD') {
            if (target.querySelector('[name="select-checkbox"]')) {
                return;
            }

            const row = target.closest("tr");
            const table = target.closest("table");
            if (!row || !table || !row.id) return;

            const pk = row.id.slice(3);
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
        } else if (target.name === 'select-checkbox') {
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
            actionMenu.disabled = (count === 0 && (!selAll || !selAll.checked));
        }
    }

    function selectListClick(ev) {
        const selectList = ev.target.closest(".select-list");

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

    return tb;
})();

window.addEventListener("load", tableaux.init);