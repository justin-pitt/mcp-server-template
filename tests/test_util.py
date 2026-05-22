from pkg.util import create_response


def test_create_response_wraps_data():
    out = create_response(data={"foo": "bar"})
    assert '"foo"' in out
    assert '"bar"' in out


def test_create_response_with_error():
    out = create_response(error="bad input")
    assert "bad input" in out
