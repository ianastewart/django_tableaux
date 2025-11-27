from django_tableaux.utils import set_query_parameter, clear_query_parameters, handle_sort_parameter

def test_set_query_parameter():
    url = "http://example.com/?sort=field1&page=2"
    new_url=set_query_parameter(url, "sort", "field2")
    assert "sort=field2" in new_url
    new_url = set_query_parameter(url, "extra", "value")
    assert "extra=value" in new_url

def test_clear_query_parameters():
    url = "http://example.com/?sort=field1&page=2&extra=value"
    new_url=clear_query_parameters(url, ["sort", "page"])
    assert new_url == "http://example.com/?extra=value"
    new_url = clear_query_parameters(url, ["missing"])
    assert new_url == url

def test_handle_sort_parameter():
    url = "http://example.com/?sort=field1"
    url = handle_sort_parameter(url, "sort", "field1")
    assert "sort=-field1" in url
    url = handle_sort_parameter(url, "sort", "field1")
    assert "sort=field1" in url