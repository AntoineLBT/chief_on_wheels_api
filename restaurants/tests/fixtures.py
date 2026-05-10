from django.utils import timezone

from restaurants.constants import RestaurantType
from users.models import User
from users.tests.fixtures import UserFixture

from ..models import Ingredient, Order, OrderRecipe, Recipe, Restaurant, Shift


class RestaurantFixture(UserFixture):
    def any_restaurant(self, owner: User | None = None):
        return Restaurant.objects.create(
            name="MyFoodTruck",
            type=RestaurantType.PIZZERIA,
            owner=owner or self.any_user(),
        )


class ShiftFixture(RestaurantFixture):

    def any_shift_data(self):
        return {"restaurant": None, "date": timezone.now()}

    def any_shift(self, restaurant: Restaurant | None = None):

        data = self.any_shift_data()
        data["restaurant"] = (
            restaurant if isinstance(restaurant, Restaurant) else self.any_restaurant()
        )
        return Shift.objects.create(**data)


class OrderFixture(ShiftFixture):

    def any_order(self, restaurant: Restaurant | None = None):
        return Order.objects.create(
            shift=self.any_shift(restaurant),
            customer_name="Jean",
            picking_time=timezone.now(),
        )


class RecipeFixture(RestaurantFixture):

    def any_recipe(self, with_restaurant: Restaurant | None = None):

        restaurant = with_restaurant or self.any_restaurant()

        return Recipe.objects.create(name="calzone", price=12.5, restaurant=restaurant)


class IngredientFixture(RestaurantFixture):

    def any_ingredient(
        self, name: str | None = None, with_restaurant: Restaurant | None = None
    ):
        restaurant = with_restaurant or self.any_restaurant()
        return Ingredient.objects.create(
            name=name or "sauce tomate", price_by_kg=5.4, restaurant=restaurant
        )


class OrderRecipeFixture(OrderFixture, RecipeFixture):

    def any_order_recipe(self):
        return OrderRecipe.objects.create(
            order=self.any_order(), recipe=self.any_recipe()
        )
