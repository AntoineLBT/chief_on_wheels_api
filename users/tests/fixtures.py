from ..models import User


class UserFixture:

    def any_user_data(self):
        return {
            "first_name": "Francky",
            "last_name": "Pizza",
            "email": "francky.pizza@mail.com",
            "phone": "+33123456789",
            "password": "password",
            "username": "francky_pizza",
            "is_active": True,
        }

    def any_user(self):
        user = User.objects.create(**self.any_user_data())
        user.set_password(self.any_user_data()["password"])
        user.save()
        return user

    def any_token(self, with_user=None):
        user = with_user or self.any_user()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
