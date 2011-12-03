from polydatum import DataLayer, Service
from polydatum import ctx

def test_polydatum():
	@service('users')
	class UserService(Service):
		@interface(User, id=selector('id'))
		def get(self, id):
			return 

		def update(self):
			pass

		def delete(self):
			pass

		@interface(User, id=selector('id'))
		def create(self, id):
			pass

		@interface(User, id=selector('id'))
		def get_or_create(self, id):
			user = self.get(id)
			if user:
				return user
			else:
				return self.create(id)


	@service('users.profile')
	class UserProfileService(Service):
		@interface(profile=selector('#profile,body', ProfileSchema))
		def update(self, profile):
			user_id = ctx.users.get_id()
			
			user = mongo.get_user(user_id)
			user.profile = mapper(profile, dict)
			user.save()			
			

		

	dal = DataLayer()
	dal.register_services(
		users=UserService().register_services(
			profile=UserProfileService()
		)
	)
	

	dal.users[id].get().name
	dal.users[id].profile().picture

	dal.users[id].update()
	dal.users[id].delete()

	dal.users[id].profile.get()
