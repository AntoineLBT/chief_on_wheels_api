from ..models import User


class UserFixture:

    def any_user_data(self):
        return {
            "first_name": "Francky",
            "last_name": "Pizza",
            "email": "francky.pizza@mail.com",
            "password": "password",
            "username": "francky_pizza",
            "is_active": True,
        }

    def any_user(self):
        return User.objects.create(**self.any_user_data())
