from django.db import models

# These models are used inside the Tableaux view
class Pagination(models.TextChoices):
    PAGED = "paged", "Paged"
    INFINITE = "infinite", "Infinite scroll"
    LOAD = "load", "Infinite load more"
    NONE = "none", "No pagination"

class FilterStyle(models.TextChoices):
    NONE = "none", "No filter"
    TOOLBAR = "toolbar", "Toolbar above table"
    MODAL = "modal", "Modal"
    HEADER = "header", "In table header"

class ClickAction(models.TextChoices):
    NONE = "none", "No action"
    GET = "get", "GET request"
    HX_GET = "hx_get", "HX-GET request"
    CUSTOM = "custom", "Custom action"