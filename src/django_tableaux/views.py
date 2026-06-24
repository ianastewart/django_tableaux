import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qs

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import QueryDict, HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.utils.http import urlencode
from django.views.generic import TemplateView
from django_filters.filterset import filterset_factory
from django_htmx.http import (
    HttpResponseClientRefresh,
    HttpResponseClientRedirect,
    trigger_client_event,
    push_url,
    retarget,
    replace_url,
    reswap,
)
import django_tables2 as tables
from django_tables2.export.export import TableExport

from django_tableaux.get_htmx import get_htmx
from django_tableaux.models import Pagination, FilterStyle, ClickAction
from django_tableaux.table import build_table
from .utils import (
    breakpoints,
    visible_columns,
    build_templates_dictionary,
    strip_prefix_from_keys,
)

logger = logging.getLogger(__name__)


class TableauxView(TemplateView):
    title = ""
    caption = ""
    template_name = "django_tableaux/tableaux.html"
    template_library = "basic"

    table_data = None
    table_class = None
    model = None
    form_class = None
    #
    filterset_class = None
    filterset_fields = None
    filterset = None
    filter_style = FilterStyle.NONE
    filter_pills = False
    filter_button = False
    filter_clear_button = True
    filter_clear_field = True
    #
    pagination = Pagination.PAGED
    per_page = 20
    #
    columns_control = False
    column_reset = True
    rows_control = False
    toolbar = {
        "left": "actions",
        "right": ["filter_modal", "columns", "rows"],
    }
    toolbar_filter = {
        "left": ["filters", "filter_button", "filter_clear"],
    }
    toolbar_bottom = {
        "left": "record_count",
        "center": "paginator",
    }

    click_action = ClickAction.NONE
    click_url_name = ""
    click_target = "#modals-here"
    #
    sticky_header = True
    sticky_bottom_toolbar = True
    fixed_height = 0
    buttons = []

    object_name = ""
    #
    export_filename = "table"
    export_format = "csv"
    export_class = TableExport
    export_formats = (TableExport.CSV,)
    #
    update_url = True
    indicator = True
    prefix = ""

    debug = False
    responsive_settings = {}

    LOCAL_PARAMS = ["page", "per_page", "order_by"]

    def _apply_responsive_settings(self):
        if not self.responsive_settings or not self._bp:
            return
        bp_order = list(self.get_breakpoint_values().keys())
        current_index = bp_order.index(self._bp) if self._bp in bp_order else len(bp_order)
        defined = {k: i for i, k in enumerate(bp_order) if k in self.responsive_settings}
        if not defined:
            return
        # Above the largest defined bp → class-level defaults apply, no override
        if current_index > max(defined.values()):
            return
        # Below the smallest defined bp → fall backward to smallest defined config
        if current_index < min(defined.values()):
            smallest_key = min(defined.keys(), key=lambda k: bp_order.index(k))
            resolved = self.responsive_settings[smallest_key]
        else:
            # Fall-forward: use largest defined bp at or below current
            resolved = None
            for key in bp_order[: current_index + 1]:
                if key in self.responsive_settings:
                    resolved = self.responsive_settings[key]
            if not resolved:
                return
        for k, v in resolved.items():
            if not hasattr(self, k):
                raise ImproperlyConfigured(f"'{k}' in responsive_settings is not a valid TableauxView attribute")
            setattr(self, k, v)

    def get_table_class(self):
        if self.table_class:
            return self.table_class
        if self.model:
            return tables.table_factory(self.model)
        raise ImproperlyConfigured(
            f"You must either specify {type(self).__name__}.table_class or {type(self).__name__}.model"
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table = None
        self.selected_objects = None
        self.selected_ids = None
        self.query_dict = {}
        self.filter_data = {}
        self._order_by_changed = False
        self._filter_changed = False
        self._bp = ""

    def setup(self, request, *args, **kwargs):
        """
        Apply settings to attributes that are not already defined on the instance
        First do local settings dict then global one
        """

        def _setup(cls, my_settings):
            for k, v in my_settings.items():
                if hasattr(cls, k):
                    if k not in cls.__dict__:
                        setattr(cls, k, v)
                # else:
                #     raise ImproperlyConfigured(f"Invalid variable '{k}' in tableaux settings")

        super().setup(request, *args, **kwargs)
        # cls = type(self)
        if hasattr(self, "settings"):
            _setup(self, self.settings)
        if hasattr(settings, "DJANGO_TABLEAUX"):
            _setup(self, settings.DJANGO_TABLEAUX)
        self.templates = build_templates_dictionary(self.template_library)
        print(self.template_library)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.htmx:
            self.query_dict = request.GET.dict()
            # initial request from {% tableaux %} includes query_string
            query_string = self.query_dict.pop("query_string", None)
            if query_string:
                self.query_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(query_string).items()}
            else:
                # self.filter_data contains the old filter values
                # it is used to populate the filter form when this is a modal request
                # note values can be a list if checkboxes or multiselect
                filter_raw = self.query_dict.pop("~filter_data", None)
                has_prior_filter_state = bool(filter_raw)
                if has_prior_filter_state:
                    self.filter_data = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(filter_raw).items()}

                # Update query_dict with any filter data that is not already present
                # this will be the case when a modal filter is saved
                for k, v in self.filter_data.items():
                    if k not in self.query_dict:
                        self.query_dict[k] = v

                # Detect filter changes only when we have prior state to compare against.
                # Without it we cannot distinguish a genuinely new filter from a form field
                # that always renders with a default non-empty value (e.g. ChoiceFilter with
                # empty_label=None).  Explicit filter actions (filter_form, filter_button,
                # ~remove~, filter_reset) set _filter_changed directly in get_htmx.py.
                none_list = ["", (), {}, None]
                initial = self.get_initial_data()
                if has_prior_filter_state:
                    old_data = self._filter_cleaned_data(self.filter_data)
                    new_data = self._filter_cleaned_data(self.query_dict)
                    for k, v in new_data.items():
                        if self.is_filter_name(k) and v != old_data.get(k):
                            if k in initial and initial[k] == v:
                                continue
                            if v in none_list and old_data.get(k) in none_list:
                                continue
                            self._filter_changed = True
                            break

            self.prefix = self.query_dict.pop("prefix", "")
            return get_htmx(self, request, *args, **kwargs)
        else:
            self.prefix = request.GET.get("prefix", self.prefix)
            query_dict = request.GET.copy()
            # todo
            self.query_dict = strip_prefix_from_keys(data=query_dict, prefix=self.prefix)

        table_class = self.get_table_class()

        # If initial GET and table is responsive ask client to repeat the request with the breakpoint parameter
        if "bp" in request.GET:
            self._bp = request.GET["bp"]
            self._apply_responsive_settings()
        elif (hasattr(table_class, "Meta") and hasattr(table_class.Meta, "responsive")) or self.responsive_settings:
            return render(
                request,
                self.templates["bp_request"],
                context={"breakpoints": self.get_breakpoint_values()},
            )

        if "_export" in request.GET:
            return self.export_table()

        return self.render_template(self.template_name)

    def get_initial_data(self):
        # get initial data for the filterset
        return {}

    def is_filter_name(self, name: str) -> bool:
        if self.filterset_class is not None:
            if name in self.filterset_class.base_filters.keys() or name in self.filterset_class.declared_filters.keys():
                return True
        return False

    def is_state_param(self, name: str) -> bool:
        return name[0] == "~" or self.is_filter_name(name)

    def get_queryset(self):
        if hasattr(self, "queryset"):
            return self.queryset
        if self.model is not None:
            return self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
            )

    def get_filtered_object_list(self):
        self.object_list = self.table_data if self.table_data is not None else self.get_queryset()
        self.filterset = self.get_filterset(self.object_list)
        if self.filterset is not None:
            self.object_list = self.filterset.qs
        self.object_list = self.process_filtered_object_list()
        return self.object_list

    def process_filtered_object_list(self):
        """
        Overide this to do further processing on objects list after filtering
        """
        return self.object_list

    def make_query_string(self):
        # clean up the query string by removing empty parameters relating to this tableaux
        q_dict = {}
        for k, v in self.query_dict.items():
            if self.is_state_param(k):
                if v != "":
                    q_dict[k] = v
            else:
                q_dict[k] = v
        return urlencode(q_dict.items(), doseq=True)

    def render_template(
        self,
        template_name=None,
        hx_target=None,
        trigger_client=True,
        update_url=True,
        **kwargs,
    ):
        self.get_filtered_object_list()
        self.table = build_table(self, prefix=self.prefix, **kwargs)
        query_string = self.make_query_string()
        url = self.request.path
        if self.request.htmx:
            url = self.request.htmx.current_url
        parts = urlsplit(url)
        return_url = urlunsplit((parts.scheme, parts.netloc, parts.path, query_string, parts.fragment))

        context = self.get_context_data(return_url=return_url, query_string=query_string)
        template_name = template_name or self.template_name
        response = TemplateResponse(
            request=self.request,
            template=template_name,
            context=context,
        )
        tableaux_id = f"#{self.table.prefix}{hx_target}"
        if hx_target:
            response = retarget(response, tableaux_id)
            response = reswap(response, "outerHTML")
        if trigger_client:
            response = trigger_client_event(
                response,
                name="initTableauxId",
                params={"id": f"{self.table.prefix}tableaux"},
                after="swap",
            )
        if self.update_url and update_url:
            response = replace_url(response, return_url)
            response = push_url(response, return_url)
        return response

    def render_table(self):
        return self.render_template(
            template_name=self.templates["tableaux_table_wrapper"],
            hx_target="table_wrapper",
        )

    def render_tableaux(self, hx_target="tableaux", outer=False):
        key = "tableaux_outer" if outer else "tableaux"
        return self.render_template(
            template_name=self.templates[key],
            hx_target=hx_target,
        )

    def render_row(self, id=None, template_name=None):
        self.object_list = self.get_filtered_object_list().filter(id=id)
        self.table = build_table(self)
        context = self.get_context_data(oob=True, row=self.table.rows[0])
        template_name = template_name or self.templates["tableaux_row"]
        return self.render_to_response(template_name, context)

    def render_to_response(self, template_name, context, **response_kwargs):
        response_kwargs.setdefault("content_type", self.content_type)
        return TemplateResponse(
            request=self.request,
            template=[template_name],
            context=context,
            **response_kwargs,
        )

    def export_table(self):
        self.get_filtered_object_list()
        subset = self.request.GET.get("_subset", None)
        if subset:
            if subset == "selected":
                self.object_list = self.object_list.filter(id__in=self.request.session.get("selected_ids", []))
        export_format = self.request.GET.get("_export", self.export_format)
        # Use tablib to export in desired format
        table = build_table(self, prefix=self.prefix)
        exclude_columns = [k for k, v in table.columns.columns.items() if not v.visible]
        exclude_columns.append("selection")
        exporter = self.export_class(
            export_format=export_format,
            table=table,
            exclude_columns=exclude_columns,
        )
        return exporter.response(filename=f"{self.export_filename}.{export_format}")

    def get_record_count(self) -> int:
        if hasattr(self.table, "paginator"):
            try:
                return self.table.paginator.count
            except NotImplementedError:
                # lazy paginator does not support count
                pass
        try:
            return self.object_list.count()
        except AttributeError:
            return len(self.object_list)

    def _record_count_context(self) -> dict:
        total = self.get_record_count()
        paginated = hasattr(self.table, "paginator")
        if paginated:
            page = int(self.query_dict.get("~page", 1))
            per_page = int(self.query_dict.get("~per_page", self.per_page))
            start = (page - 1) * per_page + 1
            end = min(page * per_page, total)
        else:
            start = 1
            end = total
        if total == 0:
            start = 0
        return {
            "record_count": total,
            "record_start": start,
            "record_end": end,
        }

    def _toolbar_item_visible(self, item: str) -> bool:
        match item:
            case "actions":
                return bool(self.get_bulk_actions())
            case "buttons":
                return bool(self.get_buttons())
            case "columns":
                return self.columns_control
            case "rows":
                return self.rows_control
            case "filter_modal":
                return bool(self.filterset_class) and self.filter_style == FilterStyle.MODAL
            case "filters":
                return self.has_filter_toolbar
            case "filter_button":
                return self.filter_button and self.has_filter_toolbar
            case "filter_clear":
                return self.filter_clear_button and self.has_filter_toolbar
            case "paginator":
                return self.pagination == Pagination.PAGED
            case _:
                return True

    def _build_toolbar_areas(self, config: dict) -> dict:
        if not isinstance(config, dict):
            raise ImproperlyConfigured(
                f"toolbar/toolbar_filter must be a dict mapping area names to item lists, got {type(config).__name__}"
            )
        template_map = {key[3:]: key for key in self.templates if key.startswith("tb_")}
        result = {}
        for area, items in config.items():
            if isinstance(items, str):
                items = [items]
            paths = [
                self.templates[template_map[item]]
                for item in items
                if item in template_map and self._toolbar_item_visible(item)
            ]
            if paths:
                result[area] = paths
        return result

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = {
            "view": self,
            "url": self.request.path,
            "table": self.table,
            "filter": self.filterset,
            "object_list": self.get_filtered_object_list(),
            "templates": self.templates,
            "filters": [],
            "buttons": self.get_buttons(),
            "actions": self.get_bulk_actions(),
            "rows": self.rows_list(),
            "page": self.query_dict.get("~page", "1"),
            "per_page": self.query_dict.get("~per_page", 20),
            "order_by": self.query_dict.get("~order_by", ""),
            "bp": self._bp,
            "breakpoints": breakpoints(self.table),
            "breakpoint_values": self.get_breakpoint_values(),
            "toolbar_visible": bool(self.toolbar),
            "toolbar_areas": self._build_toolbar_areas(self.toolbar),
            "toolbar_filter_areas": self._build_toolbar_areas(self.toolbar_filter),
            "toolbar_bottom_areas": self._build_toolbar_areas(self.toolbar_bottom),
            **self._record_count_context(),
            "Pagination": Pagination,
            "FilterStyle": FilterStyle,
            "ClickAction": ClickAction,
        }
        context.update(kwargs)

        filter_dict = {}
        if self.filterset_class:
            initial = self.get_initial_data()
            filter_dict = {
                k: v
                for k, v in self.filterset.form.cleaned_data.items()
                if v not in (None, "", [], (), {}) and v != initial.get(k)
            }
            context["filter_dict"] = filter_dict
            context["filter_data"] = urlencode(filter_dict)
        return context

    def get_filterset(self, queryset=None):
        if self.filterset_class is None and self.filterset_fields:
            self.filterset_class = filterset_factory(self.model, fields=self.filterset_fields)
        data = self.get_initial_data()
        data.update(self.query_dict)
        return (
            self.filterset_class(data=data, queryset=queryset, request=self.request) if self.filterset_class else None
        )

    def _filter_cleaned_data(self, data: dict) -> dict:
        if self.filterset_class is None and self.filterset_fields:
            self.filterset_class = filterset_factory(self.model, fields=self.filterset_fields)
        if not self.filterset_class:
            return {}
        fs = self.filterset_class(data=data, queryset=self.get_queryset(), request=self.request)
        fs.form.is_valid()
        return getattr(fs.form, "cleaned_data", {})

    def rows_list(self):
        return [20, 50, 100]

    def get_buttons(self):
        return []

    def get_bulk_actions(self):
        """
        Return a list or tuple with element in format (action_name, "Action text")
        """
        return []

    def render_cell_form(self, id, column):
        """
        Override this method to show a form so user can edit the cell value
        """
        return HttpResponse(f"No form for column '{column}'")

    def patch(self, request, *args, **kwargs):
        # PATCH is used to update a cell after inline editing
        params = QueryDict(request.body)
        bits = request.htmx.target.split("_")
        # todo fix patch if needed
        column_name = visible_columns(request, self.table_class, self.get_breakpoint_values(), int(bits[3]))[
            int(bits[2])
        ]
        value = params.get(column_name, None)
        print(bits[1], value)
        if value:
            return self.cell_changed(
                record_pk=bits[1],
                column_name=column_name,
                value=params[column_name],
                target=request.htmx.target,
            )
        return HttpResponse("x")

    def post(self, request, *args, **kwargs):
        if request.htmx:
            # check for inline edit request
            if request.htmx.trigger and "editcol" in request.htmx.trigger:
                bits = request.htmx.trigger.split("_")
                id = bits[-1]
                column = "_".join(bits[1:-1])
                value = request.POST[column]
                return self.handle_cell_changed(id, column, value)

            # Assume this is an action performed on a queryset
            self.return_url = request.POST.get("return_url")
            self.selected_ids = None
            self.selected_objects = None
            if "select_all" in request.POST:
                subset = "all"
                self.selected_ids = []
                self.selected_objects = self.get_filtered_object_list()
            else:
                subset = "selected"
                if request.POST.get("selected_ids", None):
                    self.selected_ids = request.POST["selected_ids"].split(",")
                    self.selected_objects = self.get_filtered_object_list().filter(pk__in=self.selected_ids)
            if request.htmx.trigger_name:
                if "export" in request.htmx.trigger_name:
                    # Export is a special case. It redirects to a regular GET that returns the file
                    request.session["selected_ids"] = self.selected_ids
                    bits = request.htmx.trigger_name.split("_")
                    export_format = bits[-1] if bits[-1] != "export" else "csv"
                    separator = "&" if "?" in self.return_url else "?"
                    return HttpResponseClientRedirect(
                        f"{self.return_url}{separator}_export={export_format}&_subset={subset}"
                    )

                response = self.handle_action(request, request.htmx.trigger_name)
                if response:
                    return response
        return HttpResponseClientRefresh()

    def handle_cell_changed(self, id, column, value):
        """
        This handles the simple case of updating a field on a record
        For anything more complex, override this method.
        """
        record = self.get_queryset().filter(id=id).first()
        if hasattr(record, column):
            setattr(record, column, value)
            record.save()
            return self.render_row(id=id)
        return HttpResponse(f"Missing attribute {column} in handle_cell_edit()")

    def handle_action(self, request, action):
        """
        self.selected_objects is a queryset that contains the objects to be processed.
        self.selected_ids is a list of model ids that were selected, empty for 'All rows'
        Possible return values:
        - None: (default) - reloads the last path
        - HttpResponse to be returned
        """
        return None

    def handle_button(self, request, button_name):
        return None

    def cell_clicked(self, pk, column_name, target, return_url):
        """
        User clicked on a cell with custom action
        """
        return HttpResponseClientRefresh()

    def edit_cell(self, pk, column_name, target):
        """
        User clicked on an editable cell
        """
        if not self.model:
            raise ImproperlyConfigured(
                "Model must be specified or cell_clicked must be overriden for editable cells",
            )
        if not self.form_class:
            raise ImproperlyConfigured("You must specify the form_class for editable cells")
        try:
            record = self.model.objects.get(pk=pk)
            form = self.form_class({column_name: getattr(record, column_name)})
            context = {"field": form[column_name], "target": target}
            return render(self.request, self.templates["cell_form"], context)
        except Exception as e:
            raise ValueError(f"Error {str(e)} while editing field {column_name}")

    def cell_changed(self, record_pk, column_name, value, target):
        """
        Editable cell value changed
        """
        try:
            record = self.model.objects.get(pk=record_pk)
            setattr(record, column_name, value)
            record.save()
        except ValueError:
            return render(
                self.request,
                self.templates["cell_error"],
                {"error": "Value error", "column": column_name, "target": target},
            )
        return HttpResponseClientRefresh()

    def get_breakpoint_values(self):
        # This dictionary specifies the upper limit for each category
        # e.g. md >= 768
        return {"xs": 576, "sm": 768, "md": 992, "lg": 1200, "xl": 1400, "xxl": 1600}

    @staticmethod
    def _update_parameter(request, key, value):
        query_dict = request.GET.copy()
        query_dict[key] = value
        return f"{request.path}?{query_dict.urlencode()}"

    def has_filter_toolbar(self):
        return self.filterset is not None and self.filter_style == FilterStyle.TOOLBAR

    def has_filter_pills(self):
        return self.filter_pills


class SelectedMixin:
    """
    Use in views that are called to perform an action on selected objects.
    Selected objects can be obtained from a list of ids passed in the session,
    or from a query passed as GET parameters.
    Returns a queryset of the selected objects
    """

    model = None
    filterset_class = None
    return_url = None

    def get(self, *args, **kwargs):
        self.return_url = self.request.session.get("return_url")
        return super().get(*args, **kwargs)

    def get_query_set(self):
        if self.model is None:
            raise ImproperlyConfigured("Model must be specified for SelectedMixin")
        ids = self.request.session.get("selected_ids", [])
        if ids:
            return self.model.objects.filter(id__in=ids)
        query_set = self.model.objects.all()
        if self.filterset_class:
            return self.filterset_class(self.request.GET, queryset=query_set, request=self.request).qs
        return query_set


# class ModalMixin:
#     """Mixin to convert generic views to operate as modal views when called by hx-get"""
#
#     title = ""
#
#     def get_template_names(self):
#         # handle case where same view can have different templates
#         if self.request.htmx:
#             if hasattr(self, "modal_template_name"):
#                 return [self.modal_template_name]
#         if hasattr(self, "template_name"):
#             return [self.template_name]
#         raise ValueError("Template name missing")
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         url = self.request.resolver_match.route
#         if "<int:pk>" in url and self.object:
#             url = url.replace("<int:pk>", str(self.object.pk))
#         context["modal_url"] = "/" + url
#         return context
#
#     def reload_table(self):
#         response = HttpResponse("")
#         return trigger_client_event(response, "reload", {"url": self.request.htmx.current_url_abs_path})


