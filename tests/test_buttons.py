from src.django_tableaux.buttons import Button

def test_default_button():
    button = Button("Test button")
    html = button.render()
    assert "<button" in html
    assert 'type="button"' in html
    assert 'class="btn btn-primary"' in html
    assert 'name="btn_test_button"' in html
    assert ">Test button</button" in html


def test_button_renders_attributes():
    button = Button(
        "Test button",
        css="btn btn-secondary",
        type="submit",
        name="test_name",
        hx_get="/test",
        hx_target="#target",
    )
    html = button.render()
    assert 'class="btn btn-secondary"' in html
    assert 'type="submit"' in html
    assert 'name="btn_test_name"' in html
    assert 'hx-get="/test"' in html
    assert 'hx-target="#target"' in html


def test_link_button_when_href_present():
    button = Button("Test button", href="url")
    html = button.render()
    assert "<a" in html
    assert 'href="url"' in html
    assert "type" not in html