from restaurants.constants import RestaurantType
from users.tests.fixtures import UserFixture
from ..models import Restaurant


class RestaurantFixture(UserFixture):
    def any_restaurant(self):
        return Restaurant.objects.create(
            name="MyFoodTruck", type=RestaurantType.PIZZERIA, owner=self.any_user()
        )
