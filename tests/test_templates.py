import pytest
import os
from src.django_tableaux.utils import define_columns, build_templates_dictionary, template_paths, get_template_path
from django.conf import settings
DEFAULT_LIB = "bootstrap4"

def test_default_template_paths():
    settings.DJANGO_TABLEAUX_LIBRARY = DEFAULT_LIB
    paths = template_paths()
    assert "django_tableaux" in paths[0]
    assert DEFAULT_LIB in paths[0]
    assert paths[1] is None

def test_alternative_built_in_template_paths():
    library ="picocss"
    settings.DJANGO_TABLEAUX_LIBRARY = library
    paths = template_paths()
    assert DEFAULT_LIB  in paths[0]
    assert library in paths[1]

def test_external_template_path():
    settings.DJANGO_TABLEAUX_LIBRARY = DEFAULT_LIB
    my_path = os.path.dirname(os.path.realpath(__file__))
    library = my_path + "/template_library"
    settings.DJANGO_TABLEAUX_LIBRARY = library
    paths = template_paths()
    assert "tests" in paths[1]
    assert "template_library" in paths[1]

def test_get_template_path_custom():
    # requires full template name
    settings.DJANGO_TABLEAUX_LIBRARY = "picocss"
    template_name="render_rows.html"
    path = get_template_path(template_name)
    assert os.path.join(DEFAULT_LIB, template_name ) in path
    template_name="tb_rows.html"
    path = get_template_path(template_name)
    assert os.path.join("picocss", template_name ) in path

def test_only_default_templates_library():
    settings.DJANGO_TABLEAUX_LIBRARY = DEFAULT_LIB
    templates = build_templates_dictionary()
    assert "bootstrap4" in templates["render_rows"]
    assert "bootstrap4" in templates["modal_base"]


def test_bootstrap5_templates():
    templates = build_templates_dictionary("bootstrap5")
    assert "bootstrap4" in templates["render_rows"]
    assert "bootstrap5" in templates["modal_base"]


def test_external_templates():
    my_path = os.path.dirname(os.path.realpath(__file__))
    library = my_path + "/template_library"
    templates = build_templates_dictionary(library)
    assert "template_library" in templates["render_rows"]
    assert "template_library" in templates["modal_base"]
