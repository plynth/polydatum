from polydatum import DataAccessLayer, DataManager as _BaseDataManager


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
