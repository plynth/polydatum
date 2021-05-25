from polydatum import DataAccessLayer, DataManager as _BaseDataManager, Service


def test_custom_dal():
    """
    Verify that a custom DataAccessLayer can be passed to DataManager
    """

    class TestDal(object):
        """
        Test dal class
        """
        def __init__(self, data_manager):
            self._services = {}
            self._data_manager = data_manager

    class TestDataManager(_BaseDataManager):
        """
        DataManager wrapper for test
        """
        DataAccessLayer = TestDal

        def __init__(self, resource_manager=None):
            super(TestDataManager, self).__init__(resource_manager)

    # Verify self._dal is set to the default DataAccessLayer class
    dm = _BaseDataManager()
    assert isinstance(dm._dal, DataAccessLayer)

    # Verify self._dal is set to the optional DataAccessLayer class i.e. TestDal class
    dm = TestDataManager()
    assert isinstance(dm._dal, TestDal)


def test_dal_getitem_access():
    """
    Verify `__getitem__` is identical to `__getattr__`
    """

    expected = "foo"

    class SampleService(Service):
        def sample_method(self):
            return expected

    dm = _BaseDataManager()
    dm.register_services(sample=SampleService())

    with dm.context() as ctx:
        assert ctx.dal['sample.sample_method']() == expected
