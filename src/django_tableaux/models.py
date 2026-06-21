from django.db import models
from django.conf import settings


class UserTableSettings(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=100)
    breakpoint = models.CharField(max_length=5)
    visible_columns = models.JSONField(default=dict)

    class Meta:
        unique_together = ("user", "table_name", "breakpoint")


# These models are used inside the Tableaux view
class Pagination(models.TextChoices):
    NONE = "", "No pagination"
    PAGED = "paged", "Paged at bottom"
    PAGED_TOP = "paged_top", "Paged at top"
    INFINITE = "infinite", "Infinite scroll"
    LOAD = "load", "Infinite load more"


class FilterStyle(models.TextChoices):
    NONE = "", "No filter"
    TOOLBAR = "toolbar", "Toolbar above table"
    MODAL = "modal", "Modal"
    HEADER = "header", "In table header"


class ClickAction(models.TextChoices):
    NONE = "", "No action"
    GET = "get", "GET request"
    HX_GET = "hx_get", "HX-GET request"
    CUSTOM = "custom", "Custom action"
