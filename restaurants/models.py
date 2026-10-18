from decimal import Decimal
from uuid import uuid4

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from users.models import User

from .constants import IngredientUnit, OrderIngredientActionType, OrderStatus


class Restaurant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class Shift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    date = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=255)
    picking_time = models.DateTimeField()
    status = models.CharField(
        choices=OrderStatus.choices,
        max_length=max([len(status[0]) for status in OrderStatus.choices]),
        default=OrderStatus.TODO,
    )

    def __str__(self):
        return f"{self.customer_name}_{self.picking_time}"


class Recipe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.FloatField()

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    unit = models.CharField(
        choices=IngredientUnit.choices,
        max_length=max(len(unit) for unit in IngredientUnit.values),
    )
    price_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    has_extra = models.BooleanField(default=False)
    # Charged to the customer on each ADD of this ingredient.
    extra_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    # Portion used by an extra, in the base unit (g / ml / piece).
    extra_quantity = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    # RESTRICT, not PROTECT: still deletable when its restaurant is deleted.
    ingredient = models.ForeignKey(Ingredient, on_delete=models.RESTRICT)
    quantity_in_g = models.IntegerField()


class OrderRecipe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.recipe}_{self.order}"


class OrderIngredient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    order_recipe = models.ForeignKey(OrderRecipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.RESTRICT)
    action_type = models.CharField(
        choices=OrderIngredientActionType,
        max_length=max(
            [len(restaurant[0]) for restaurant in OrderIngredientActionType.choices]
        ),
    )
