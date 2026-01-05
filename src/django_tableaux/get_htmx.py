# This file handles all the hx-get requests coming from a tableaux
# self refers to the view instance

from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from django_htmx.http import trigger_client_event, HttpResponseClientRedirect

from django_tableaux.utils import define_columns, save_columns_dict, default_columns_dict, set_column, save_per_page, \
    visible_columns


def get_htmx(self, request, *args, **kwargs):
    # Some actions depend on trigger_name; others on trigger
    # if "_bp" in request.GET:
    #     self._bp = request.GET["_bp"]
    # if "_filter" in request.GET:
    #     return self.render_table()
    self._bp = self.query_dict.get("bp", "XXX")

    # Some actions depend on trigger_name; others on trigger
    trigger_name = request.htmx.trigger_name
    trigger = request.htmx.trigger

    if trigger_name is not None:
        match trigger_name:
            case "table_load":
                # Initiated by tableaux template tag
                self.prefix = request.GET.get("prefix", "")
                target = request.htmx.target[len(self.prefix):] if self.prefix else request.htmx.target
                return self.render_tableaux(hx_target=target)

            case "page":
                # Change of page
                return self.render_tableaux()

            case "filter_modal" if self.filterset_class:
                # Request to show filter form in a modal
                context = {
                    "prefix": self.prefix,
                    "filter": self.filterset_class(data=self.query_dict),
                    "filter_button": self.filter_button}
                response = TemplateResponse(request, self.templates["modal_filter"], context)
                return trigger_client_event(response, "tableaux_init", after="swap")

            case "filter_button":
                # apply filter button pressed
                return self.render_tableaux()

            case "filter_reset":
                # reset all filters
                keys = list(self.query_dict.keys())
                for key in keys:
                    if self.is_filter_name(key):
                        self.query_dict.pop(key)
                return self.render_tableaux()

            case _:
                # Check if it's a button
                buttons = self.get_buttons()
                if buttons:
                    for button in buttons:
                        if button.name == trigger_name:
                            result = self.handle_button(
                                request, button.original_name()
                            )
                            if result is not None:
                                return result
                            else:
                                raise ImproperlyConfigured(
                                    f"No handler for trigger_name {trigger_name}"
                                )

    if trigger is not None:
        # Unpack the data stored in the id
        if "~" in trigger:
            bits = trigger.split("~")
            self.prefix = bits[0]
            param = bits[2]
        else:
            param = None
        match trigger:
            case trigger if "tableaux" in trigger:
                # resize event
                return self.render_tableaux()

            case trigger if "filter_form" in trigger:
                self._filter_changed = True
                return self.render_tableaux()

            case trigger if "~remove~" in trigger:
                # remove a single filter
                self.query_dict.pop(param)
                return self.render_tableaux()

            case trigger if "~col~" in trigger:
                # Switch column visibility on or off
                col_name = param
                table = self.get_table()
                if col_name == "_reset":
                    # Reset to default columns
                    define_columns(table, self.get_breakpoint_values(), self._bp)
                    save_columns_dict(
                        request, table, self._bp, default_columns_dict(table)
                    )
                    # To make sure the column drop down is correct we update the whole tableaux
                    return self.render_tableaux()
                # Click on a checkbox in the column dropdown re-renders the table data with new column settings.
                # The column dropdown remains open
                checked = f"{self.prefix}~col~{col_name}" in request.GET
                set_column(request, table, self._bp, col_name, checked)
                return self.render_table()

            case trigger if "~row~" in trigger:
                # Change the number of rows to display
                save_per_page(request, param)
                self.query_dict["per_page"] = param
                return self.render_tableaux()

            case trigger if "~sort~" in trigger:
                # change order_by
                old_value = self.query_dict.get("order_by", "")
                old_field = ""
                if len(old_value) > 0:
                    old_field = old_value[1:] if old_value[0] == "-" else old_value
                if old_field == param:
                    value = param if old_value[0] == "-" else "-" + param
                else:
                    value = param
                self.query_dict["order_by"] = value
                self._order_by_changed = True
                return self.render_tableaux()

            case trigger if "~page~" in trigger:
                # new page
                self.query_dict["page"] = param
                return self.render_tableaux()

            case trigger if "_tr_" in trigger:
                # infinite scroll/load_more or click on row
                if "_scroll" in request.GET:
                    page = int(self.query_dict.get("_pagex", 1)) + 1
                    self.query_dict["page"] = str(page)
                    return self.render_template(self.templates["render_rows"], update_url=False)

                return self.row_clicked(
                    pk=trigger.split("_")[1],
                    target=request.htmx.target,
                    return_url=request.htmx.current_url,
                )

            case trigger if "modal_filter" in trigger:
                return self.render_tableaux()

            case trigger if "editcol" in trigger:
                # display a form to edit a cell inline
                bits = trigger.split("_")
                id = bits[-1]
                column = "_".join(bits[1:-1])
                return self.render_cell_form(id, column)

            case "table_data":
                # triggered refresh of table data after create or update
                return self.render_table()

            case trigger if "cell_" in trigger:
                # cell clicked
                bits = trigger.split("_")
                return self.edit_cell(
                    pk=bits[1],
                    column_name=visible_columns(
                        request,
                        self.table_class,
                        self.get_breakpoint_values(),
                        self._bp,
                    )[int(bits[2])],
                    target=request.htmx.target,
                )

            case trigger if "td_" in trigger:
                # cell clicked
                bits = trigger.split("_")
                visible = visible_columns(
                    request,
                    self.table_class,
                    self.get_breakpoint_values(),
                    self._bp,
                )
                index = int(bits[2])
                # todo this is a bit of a hack here
                if "selection" in visible and visible[0] != "selection":
                    index -= 1
                return self.cell_clicked(
                    pk=bits[1],
                    column_name=visible[index],
                    target=request.htmx.target,
                )

            case trigger if "id_" in trigger:
                if trigger == request.htmx.target:
                    # Clear filter value triggered by  click on X in input-prepend
                    qd = request.GET.copy()
                    qd.pop(trigger_name)
                    return HttpResponseClientRedirect(
                        f"{request.path}?{qd.urlencode()}"
                    )
                #
                # Filter value changed
                url = self._update_parameter(
                    request, trigger_name, request.GET.get(trigger_name, "")
                )
                return HttpResponseClientRedirect(url)

            case _:
                pass

    raise ValueError(f"Bad htmx get request. Trigger: {trigger} Trigger name: {trigger_name}")
