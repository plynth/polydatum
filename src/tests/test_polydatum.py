from polydatum import DataManager, Service
from polydatum.context import current_context
from polydatum.resources import Resource
from uuid import uuid4

class MockStoreConnection(object):
    def __init__(self, store):        
        self._store = store

    def get(self, item_id):
        return self._store._data.get(item_id, None)

    def delete(self, item_id):
        if item_id in self._store._data:
            del self._store._data[item_id]
            return True
        return False

    def save(self, record):
        if not record.get('id', None):
            record['id'] = str(uuid4())

        self._store._data[record['id']] = record        
        return record

    def close(self):        
        self._store._pool.append(self)


class MockStore(object):
    def __init__(self):
        self._data = {}

        # Simulate a connection pool
        self._pool = [
            MockStoreConnection(self),
            MockStoreConnection(self),
            MockStoreConnection(self),
        ]

    def connect(self):
        # Get a connection from a pool
        return self._pool.pop()

class MockStoreResource(Resource):
    def __init__(self, store):
        super(MockStoreResource, self).__init__()
        self._store = store

    def __call__(self, context):
        """
        Yield a connection from the pool and closed when done.
        """ 
        connection = self._store.connect()
        try:
            yield connection
        finally:
            connection.close()

class UserService(Service): 
    @property 
    def _store(self):
        return current_context.user_db

    def get(self, id):
        return self._store.get(id)

    def update(self, id, user):
        user['id'] = id
        self._store.save(user)
        return user

    def delete(self, id):
        self._dal.users.profile.delete(id)
        return self._store.delete(id)

    def create(self, user):
        self._store.save(user)
        return user

class UserProfileService(Service):
    @property 
    def _store(self):
        return current_context.user_profile_db

    def get(self, user_id):
        return self._store.get(user_id)

    def update(self, user_id, profile):
        profile['id'] = user_id
        self._store.save(profile)
        return profile

    def delete(self, user_id):
        return self._store.delete(user_id)

def get_dam():
    data_manager = DataManager()
    data_manager.register_services(
        users=UserService().register_services(
            profile=UserProfileService()
        )
    )
    data_manager.register_resources(
        user_db=MockStoreResource(MockStore()),
        user_profile_db=MockStoreResource(MockStore()),
    )
    return data_manager

def test_service():
    data_manager = get_dam()
    with data_manager.dal() as dal:
        user = {
            'name': str(uuid4())
        }

        saved_user = dal.users.create(user)
        assert saved_user['id']
        assert saved_user['name'] == user['name']

        got_user = dal.users.get(saved_user['id'])
        assert got_user['id'] == saved_user['id']

        deleted = dal.users.delete(saved_user['id'])
        assert deleted

def test_sub_service():
    data_manager = get_dam()
    with data_manager.dal() as dal:
        user = {
            'name': str(uuid4())
        }

        user = dal.users.create(user)
        profile = dal.users.profile.get(user['id'])
        assert not profile

        uuid = str(uuid4())
        profile = dal.users.profile.update(user['id'], dict(uuid=uuid))
        assert profile
        assert profile['id'] == user['id']
        assert profile['uuid'] == uuid

        deleted = dal.users.delete(user['id'])
        assert deleted        

        profile = dal.users.profile.get(user['id'])
        assert not profile