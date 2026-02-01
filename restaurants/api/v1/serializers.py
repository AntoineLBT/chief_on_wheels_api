from rest_framework import serializers

from restaurants.models import (Ingredient, Order, OrderIngredient,
                                OrderRecipe, Recipe, RecipeIngredient,
                                Restaurant, Shift)


class RestaurantSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,  # Restrict queryset to prevent other users
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Restaurant
        fields = ["pk", "name", "type", "owner"]
        read_only_fields = ["pk"]


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["pk", "restaurant", "date"]
        read_only_fields = ["pk"]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["pk", "shift", "customer_name", "picking_time"]
        read_only_fields = ["pk"]


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ["pk", "restaurant", "name", "price"]
        read_only_fields = ["pk"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["pk", "restaurant", "name", "price_by_kg"]
        read_only_fields = ["pk"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = ["pk", "recipe", "ingredient", "quantity_in_g"]
        read_only_fields = ["pk"]


class OrderRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRecipe
        fields = ["pk", "order", "recipe"]
        read_only_fields = ["pk"]


class OrderIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderIngredient
        fields = ["pk", "order_recipe", "ingredient", "action_type"]
        read_only_fields = ["pk"]
