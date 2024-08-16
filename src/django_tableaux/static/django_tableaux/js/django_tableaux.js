// Handle checkboxes in tables, and modal forms
'use strict';
let tableaux = (function () {
    let tb = {};
    let lastChecked = null
    let selAll = null
    let selAllPage = null
    tb.init = function () {
      let url = new URL(window.location.href)
      const w = url.searchParams.get("_width")
      if (w !== null) {
        if (parseInt(w) !== window.outerWidth) {
          window.location.href = window.location.href.replace(`_width=${w}`, `_width=${window.outerWidth}`)
        }
      }
      selAll = document.getElementById('select_all')
      selAllPage = document.getElementById('select_all_page')
      if (selAllPage) {
        selAllPage.addEventListener("click", selectAllPage)
        selectAllPage()
      }
      if (selAll) {
        selAll.addEventListener("click", selectAll)
        selectAll()
      }
      document.querySelectorAll("table").forEach(e => e.addEventListener("click", tableClick));
      document.querySelectorAll(".auto-submit").forEach(e => e.addEventListener("change", function () {
        document.getElementById("id_filter_form").submit()
      }));
      document.querySelectorAll(".filter-clear").forEach(e => e.addEventListener("click", filterClear))
      document.querySelectorAll(".form-group.hx-get").forEach(e => e.addEventListener("change", filterChanged))
      document.body.addEventListener("trigger", function (evt) {
        window.htmx.ajax('GET', evt.detail.url, {source: '#table_data', 'target': '#table_data'});
      })
      document.body.addEventListener("click", selectListClick)
      // When editing a cell inline enter key triggers blur
      if (document.querySelector(".td_editing")) {
        this.addEventListener("keypress", loseFocus)
      }
      countChecked()
      var mqls =[window.matchMedia("(min-width: 576px)"),
        window.matchMedia("(min-width: 768px)"),
        window.matchMedia("(min-width: 992px)"),
        window.matchMedia("(min-width: 1200px)")
        ]
      function handleWidthChange(mql){
        window.location.href=window.location.href
      }
      //handleWidthChange(mediaQueryList);
      for (var i=0; i<mqls.length; i++)
      {
        mqls[i].addEventListener("change", handleWidthChange)
      }
    }

    function loseFocus(e) {
      if (e.key == "Enter") {
        document.activeElement.blur();
      }
    }

    function filterChanged() {
      // filter within header changed
      window.htmx.ajax('GET', '', {source: '#' + this.firstChild.getAttribute("for"), target: '#table_data'});
    }

    function filterClear(e) {
      let input = window.htmx.closest(e.target, ".input-group").firstChild
      window.htmx.ajax('GET', '', {source: input, target: input});
    }

    function selectAllPage() {
      // Click on 'Select all on page' highlights all rows
      if (selAllPage) {
        let checked = selAllPage.checked
        if (selAll) {
          if (checked) {
            selAll.parentElement.style.display = 'block';
          } else {
            selAll.parentElement.style.display = 'none';
          }
        }
        Array.from(document.getElementsByClassName("select-checkbox")).forEach(function (box) {
          box.checked = checked
          //box.disabled = false;
          highlightRow(box)
        })
        countChecked()
        lastChecked = null
      }
    }

    function selectAll() {
      // Click on Select all highlights all rows and disables checkboxes
      let checked = selAll.checked
      if (checked) {
        document.getElementById('count').innerText = 'All';
        if (selAllPage) {
          selAllPage.disabled = true
        }
        ;
      } else {
        if (selAllPage) {
          selAllPage.disabled = false
        }
        ;
        //sslAllPage.checked = false;
      }
      Array.from(document.getElementsByClassName("select-checkbox")).forEach(function (box) {
        box.disabled = checked;
      })
      countChecked();
      lastChecked = null;
    }

    function tableClick(e) {
      // Handle any clicks within the table.
      // This catches clicks on elements that are added dynamically e.g. after infinite scroll
      if (e.target.classList.contains("td-editing")) {
        // click on open drop drop down hx-posts the value and closes the dropdown
        if (e.target.classList.contains("open")) {
          window.htmx.ajax('POST', "", {
            source: "#" + e.target.id,
            target: "#" + e.target.id,
            values: {"id": window.htmx.closest(e.target, "tr").id.split("_")[1]}
          })
          e.target.classList.remove("open")
        } else {
          // first click flags dropdown as open
          e.target.classList.add("open")
        }
      }else{
        let el = document.querySelector(".td-editing")
        // Clicking table outsoide dropdown posts existing value and closes dropdown
        if (el){
          window.htmx.ajax('POST', "", {
            source: "#" + el.id,
            target: "#" + el.id,
            values: {"id": window.htmx.closest(el, "tr").id.split("_")[1],
            "column": e.target.name}
          })
        }
      }

      if (e.target.tagName === 'TD') {
        // Ignore clicks in td holding select checkbox to handle near misses of checkbox
        if (e.target.innerHTML.search('select-checkbox') >= 0) {
          return
          /*
          let editing = document.getElementsByClassName("td-editing");
          if (editing.length > 0) {
            el = editing[0]
            if (el.classList.contains("open")){
              el.classList.remove("open")
                window.htmx.ajax('PATCH', "", {
                source: "#" + el.id,
                target: "#" + el.id,
                values: window.htmx.closest(el, 'tr')
              });
            }else{
              el.classList.add("open")
            }
            // clicking on a cell when already editing causes a patch
            // let el = editing[0].parentNode
            // window.htmx.ajax('PATCH', "", {
            //   source: "#" + el.id,
            //   target: "#" + el.id,
            //   values: window.htmx.closest(el, 'tr')
            // })
            */
        } else {
          let row = e.target.parentNode;
          let pk = row.id.slice(3);
          let table = row.parentNode.parentNode;
          let col = 0;
          let previous = e.target.previousElementSibling;
          while (previous) {
            previous = previous.previousElementSibling;
            col += 1;
          }
          let idSuffix = "_" + pk + "_" + col + "_" + window.outerWidth;
          if (e.target.classList.contains("td-edit")) {
            // fetch template for editable cell
            e.target.setAttribute("id", "cell" + idSuffix);
            window.htmx.ajax('GET', "", {source: '#cell' + idSuffix, target: '#cell' + idSuffix});
          } else if (table.dataset.url) {
            let url = table.dataset.url;
            if (table.dataset.pk) {
              url += pk;
            }
            //url += "?return=" +encodeURIComponent(window.location.pathname + window.location.search)
            if (table.dataset.click === "ClickAction.GET") {
              window.document.location.assign(url)
            } else if (table.dataset.click === "ClickAction.HX_GET") {
              window.htmx.ajax('GET', url, {source: '#' + row.id, target: table.dataset.target});
            }
          } else if (table.dataset.click === "ClickAction.CUSTOM") {
            e.target.setAttribute("id", "td" + idSuffix);
            window.htmx.ajax('GET', "", {
              source: '#td' + idSuffix,
              target: '#td' + idSuffix,
            });
          }
        }
      } else if (e.target.name === 'select-checkbox') {
        // Click on row's select checkbox - handle using shift to select multiple rows
        if (selAllPage) {
          selAllPage.checked = false
        }
        let chkBox = e.target
        highlightRow(chkBox)
        if (!lastChecked) {
          lastChecked = chkBox
        } else if (e.shiftKey) {
          let chkBoxes = checkBoxes()
          let start = chkBoxes.indexOf(chkBox)
          let end = chkBoxes.indexOf(lastChecked)
          chkBoxes.slice(Math.min(start, end), Math.max(start, end) + 1).forEach(function (box) {
            box.checked = chkBox.checked;
          });
          lastChecked = chkBox;
        } else {
          lastChecked = chkBox;
        }
        countChecked();
      }
    }

    function highlightRow(box) {
      let row = box.parentElement.parentElement;
      let cls = (("selected" in row.dataset) ? row.dataset.selected : "table-active");
      if (box.checked) {
        row.classList.add(cls)
      } else {
        row.classList.remove(cls)
      }
    }

    // Count the number of checked rows and nake sure they are highlighted
    // update hidden input with associated ids
    function countChecked() {
      if (selAll && selAll.checked) {
        return
      }
      let checked = Array.from(document.querySelectorAll(".select-checkbox:checked"));
      let ids = []
      checked.forEach(function (el) {
        let row = el.parentElement.parentElement
        row.classList.add((("selected" in row.dataset) ? row.dataset.selected : "table-active"))
        ids.push(el.value)
      });
      let hiddenInput = document.querySelector("input[name='selected_ids']")
      if (hiddenInput) {
        hiddenInput.value = ids.toString();
      }
      let count = checked.length;
      let countField = document.getElementById('count');
      if (countField) {
        countField.innerText = count.toString();
      }
      let actionMenu = document.getElementById('selectActionMenu');
      if (actionMenu) {
        actionMenu.disabled = (count === 0);
        actionMenu.enabled = (count > 0 || selAll.checked);
      }
    }

    return tb

    // Handle clicks on a select list drop down as used for row and columns
    function selectListClick(ev) {
      let el = ev.target.closest(".select-list")

    if (el) {
      let elOptions = el.querySelector(".select-options")
      if (ev.target.classList.contains("select-title")) {
        document.querySelectorAll(".select-options").forEach(function (e) {
          if (elOptions != e) {
            e.classList.remove("opened")
          }
        });
        ev.target.nextElementSibling.classList.toggle("opened");
      }else{
        if (el.classList.contains("multiple")){
          return
        }else{
          el.querySelector(".select-options").classList.remove("opened")
        }
      }
    } else {
      document.querySelectorAll(".select-options").forEach(e => e.classList.remove("opened"));
      }
    }
  }
)
();
window.addEventListener("load", tableaux.init)

function handleClick() {
  let me = document.querySelector(".editing");
  if (me.classList.contains("open")) {
    //alert("Open");
    me.classList.remove("open");
  } else {
    //alert("Adding class")
    me.classList.add("open");
  }
}


