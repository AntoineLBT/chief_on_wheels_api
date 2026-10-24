from datetime import date
from decimal import Decimal

from django.utils import timezone

from restaurants.constants import FixedChargeFrequency, IngredientUnit
from users.models import User
from users.tests.fixtures import UserFixture

from ..models import (FixedCharge, Ingredient, Order, OrderRecipe, Recipe,
                      RecipeIngredient, Restaurant, Shift)


class RestaurantFixture(UserFixture):
    def any_restaurant(self, owner: User | None = None):
        return Restaurant.objects.create(
            name="MyFoodTruck",
            owner=owner or self.any_user(),
        )


class ShiftFixture(RestaurantFixture):

    def any_shift_data(self):
        return {"restaurant": None, "date": timezone.now(), "vat_rate": Decimal("0")}

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

        return Recipe.objects.create(
            name="calzone", price=Decimal("12.50"), restaurant=restaurant
        )


class IngredientFixture(RestaurantFixture):

    def any_ingredient(
        self, name: str | None = None, with_restaurant: Restaurant | None = None
    ):
        restaurant = with_restaurant or self.any_restaurant()
        return Ingredient.objects.create(
            name=name or "sauce tomate",
            unit=IngredientUnit.KG,
            price_per_unit=Decimal("5.40"),
            restaurant=restaurant,
        )


class RecipeIngredientFixture(RecipeFixture, IngredientFixture):

    def any_recipe_ingredient(
        self,
        with_recipe: Recipe | None = None,
        with_ingredient: Ingredient | None = None,
        quantity: int = 100,
    ) -> RecipeIngredient:

        recipe = with_recipe or self.any_recipe()
        ingredient = with_ingredient or self.any_ingredient("patate", recipe.restaurant)

        return RecipeIngredient.objects.create(
            recipe=recipe, ingredient=ingredient, quantity=quantity
        )


class OrderRecipeFixture(OrderFixture, RecipeFixture):

    def any_order_recipe(self):
        recipe = self.any_recipe()
        return OrderRecipe.objects.create(
            order=self.any_order(),
            recipe=recipe,
            unit_price=recipe.price,
            unit_cost=Decimal("3.00"),
        )


class FixedChargeFixture(RestaurantFixture):

    def any_fixed_charge(
        self,
        with_restaurant: Restaurant | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FixedCharge:
        return FixedCharge.objects.create(
            restaurant=with_restaurant or self.any_restaurant(),
            name="Loyer",
            amount=Decimal("300.00"),
            frequency=FixedChargeFrequency.MONTHLY,
            start_date=start_date or date(2026, 1, 1),
            end_date=end_date,
        )
