from datetime import date, datetime

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
        return {"restaurant": None, "date": date.today()}

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
            picking_time=datetime.now(),
        )


class RecipeFixture:

    def any_recipe(self):
        return Recipe.objects.create(name="calzone", price=12.5)


class IngredientFixture:

    def any_ingredient(self, name: str | None = None):
        return Ingredient.objects.create(name=name or "sauce tomate", price_by_kg=5.4)


class OrderRecipeFixture(OrderFixture, RecipeFixture):

    def any_order_recipe(self):
        return OrderRecipe.objects.create(
            order=self.any_order(), recipe=self.any_recipe()
        )
