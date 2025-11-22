from django.db import models
from .constants import RestaurantType, OrderIngredientActionType
from users.models import User


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(
        choices=RestaurantType.choices,
        max_length=max([len(restaurant[0]) for restaurant in RestaurantType.choices]),
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class Shift(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    date = models.DateField()


class Order(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=255)
    picking_time = models.DateTimeField()

    def __str__(self):
        return f"{self.customer_name}_{self.picking_time}"


class Recipe(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    price_by_kg = models.FloatField()

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity_in_g = models.IntegerField()


class OrderRecipe(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.recipe}_{self.order}"


class OrderIngredient(models.Model):
    order_recipe = models.ForeignKey(OrderRecipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    action_type = models.CharField(
        choices=OrderIngredientActionType,
        max_length=max(
            [len(restaurant[0]) for restaurant in OrderIngredientActionType.choices]
        ),
    )
