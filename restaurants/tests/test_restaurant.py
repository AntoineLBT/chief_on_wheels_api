from django.test import TestCase

from restaurants.constants import RestaurantType
from restaurants.tests.fixtures import RestaurantFixture

from ..models import Restaurant


class TestRestaurantModel(TestCase, RestaurantFixture):

    def test_restaurant_model(self):
        resto: Restaurant = self.any_restaurant()

        assert type(resto) is Restaurant
        assert resto.name is not None
        assert resto.type in RestaurantType.choices[0]
