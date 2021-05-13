import pytest

from polydatum.middleware import PathSegment


def test_path_segment():
    """
    Verify that we can set and get the name attribute for a PathSegment,
    and that we can set arbitrary meta keyword arguments when constructing
    a PathSegment, and that they will be bundled together, and retrievable
    under a `meta` attribute.

    Verify that at least a name is present.
    Verify that no keyword args are necessary.
    Verify that kwargs are bundled under the meta dict.
    """
    # name is required
    with pytest.raises(TypeError):
        PathSegment()

    name = 'example'
    p = PathSegment(name)
    assert p.name == name
    assert p.meta == dict()

    p = PathSegment(name, example='foo')
    assert p.meta['example'] == 'foo'
