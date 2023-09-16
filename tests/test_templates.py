import pytest
import os
from src.django_tableaux.utils import define_columns, build_templates_dictionary


def test_default_templates():
    templates = build_templates_dictionary()
    assert "bootstrap4" in templates["render_body"]
    assert "bootstrap4" in templates["modal_base"]


def test_bootstrap5_templates():
    templates = build_templates_dictionary("bootstrap5")
    assert "bootstrap4" in templates["render_body"]
    assert "bootstrap5" in templates["modal_base"]


def test_external_templates():
    my_path = os.path.dirname(os.path.realpath(__file__))
    library = my_path + "/template_library"
    templates = build_templates_dictionary(library)
    assert "template_library" in templates["render_body"]
    assert "template_library" in templates["modal_base"]
