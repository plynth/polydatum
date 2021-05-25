from polydatum.middleware import DalCommand, PathSegment


def test_deferred_attribute_access(path_segment_factory):
    """
    Verify that we can access non-existent attributes on this class and
    that we can access arbitrarily deep non-existent attributes.
    """
    dc = DalCommand(lambda: None, path_segment_factory())
    assert isinstance(dc.foo, DalCommand)
    assert isinstance(dc.foo.bar, DalCommand)
    assert isinstance(dc.foo.bar.baz, DalCommand)

    # Use a different non-existent service, to help make it clear that there
    # is nothing special about the `foo` service above.
    assert isinstance(dc.anything, DalCommand)
    assert isinstance(dc.example, DalCommand)


def test_dal_deferred_attr_access_handler_chain(path_segment_factory):
    """
    Verify that the handler for a DalCommand instance is preserved
    regardless of how deep a deferred attribute lookup chain is.

    Ultimately this class is responsible for deferring attribute access and
    calling the handler with a built up chain of PathSegments. We want to
    make sure that the handler is the same regardless of where in the
    deferred attribute access it is finally called.
    """

    # The impl here doesn't matter, we are only checking
    # for identity with this callable.
    # Even the signature of this callable doesn't matter right here.
    def specific_handler():
        pass

    dc = DalCommand(specific_handler, path_segment_factory())
    assert dc.foo._handler is specific_handler
    assert dc.foo.bar._handler is specific_handler
    assert dc.foo.bar.baz._handler is specific_handler


def test_dal_deferred_attr_access_handler_called(path_segment_factory):
    """
    Verify that the handler for a DalCommand gets called when the
    DalCommand is called.
    """

    def handler(path_chain, *args, **kwargs):
        return path_chain, args, kwargs

    test_path_segment = path_segment_factory()
    dc = DalCommand(handler, test_path_segment)
    test_args = ("foo", "bar")
    test_kwargs = dict(example="test", other="monkey")
    for requester in [dc, dc.foo.bar, dc.monkey.gorilla.orangutan]:
        called_path_segment, called_args, called_kwargs = requester(
            *test_args, **test_kwargs
        )
        assert isinstance(called_path_segment[0], PathSegment)
        assert called_path_segment[0].name == test_path_segment[0].name
        assert called_args == test_args
        assert called_kwargs == test_kwargs


def test_dal_deferred_attr_access_path_chaining(path_segment_factory):
    """
    Verify that deeper attribute access on a DalCommand will
    nest path segments when building up the path call chain.

    Maintaining order is important.

        dc = DalCommand()
        deep_dc = dc.foo.bar.baz.method
        assert deep_dc.path = (PathSegment(name=foo), PathSegment(name=bar), ...)
        assert deep_dc.non_existent.path == (deep_dc.path + PathSegment(name=non_existent))
    """
    dc = DalCommand(lambda: None, path_segment_factory("animals"))
    nested_dc = dc.foo.bar.baz.monkey.gorilla
    expected_path_chain = (
        PathSegment(name="animals"),
        PathSegment(name="foo"),
        PathSegment(name="bar"),
        PathSegment(name="baz"),
        PathSegment(name="monkey"),
        PathSegment(name="gorilla"),
    )
    assert nested_dc.path == expected_path_chain


def test_dal_deferred_attr_access_reusability(path_segment_factory):
    """
    Verify the same dal attributes can be re-used
    """
    req = DalCommand(lambda: None, path_segment_factory("req"))
    bar = req.foo.bar
    bar2 = req.foo.bar

    assert bar != bar2
    assert bar.path == bar2.path

    zap = bar.zap
    zap2 = bar2.zap

    assert zap != zap2
    assert zap.path == zap2.path
