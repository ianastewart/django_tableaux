import pytest
from django.core.exceptions import ImproperlyConfigured

from django_tableaux.utils import build_templates_dictionary


def test_extra_template_resolves_to_project_override(settings):
    settings.DJANGO_TABLEAUX = {
        "template_library": "bootstrap",
        "extra_templates": ["tb_extra_demo"],
    }
    templates = build_templates_dictionary("bootstrap")
    assert templates["tb_extra_demo"] == "django_tableaux/bootstrap/tb_extra_demo.html"


def test_extra_template_does_not_override_existing_name(settings):
    settings.DJANGO_TABLEAUX = {
        "template_library": "bootstrap",
        "extra_templates": ["tb_total"],
    }
    templates = build_templates_dictionary("bootstrap")
    assert templates["tb_total"] == "django_tableaux/bootstrap/tb_total.html"


def test_extra_template_missing_raises(settings):
    settings.DJANGO_TABLEAUX = {
        "template_library": "bootstrap",
        "extra_templates": ["tb_does_not_exist"],
    }
    with pytest.raises(ImproperlyConfigured):
        build_templates_dictionary("bootstrap")