from rest_framework import serializers

from restaurants.models import (
    Ingredient,
    Order,
    OrderIngredient,
    OrderRecipe,
    Recipe,
    RecipeIngredient,
    Restaurant,
    Shift,
)


class SyncOrderIngredientSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField()

    class Meta:
        model = OrderIngredient
        fields = ["id", "ingredient", "action_type"]

    def create(self, validated_data):
        instance_id = validated_data.pop("id")
        return OrderIngredient.objects.get_or_create(
            id=instance_id, defaults={**validated_data}
        )[0]


class SyncOrderRecipeSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField()
    order_ingredients = SyncOrderIngredientSerializer(many=True)

    class Meta:
        model = OrderRecipe
        fields = ["id", "recipe", "order_ingredients"]

    def create(self, validated_data):
        instance_id = validated_data.pop("id")
        order_ingredients = validated_data.pop("order_ingredients")
        instance = OrderRecipe.objects.get_or_create(
            id=instance_id, defaults={**validated_data}
        )[0]

        for order_ingredient in order_ingredients:
            order_ingredient["order_recipe"] = instance
            SyncOrderIngredientSerializer().create(order_ingredient)

        return instance


class SyncOrderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    order_recipes = SyncOrderRecipeSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "picking_time",
            "status",
            "order_recipes",
        ]

    def create(self, validated_data):
        instance_id = validated_data.pop("id")
        order_recipes = validated_data.pop("order_recipes")
        instance = Order.objects.get_or_create(
            id=instance_id, defaults={**validated_data}
        )[0]

        for order_recipe in order_recipes:
            order_recipe["order"] = instance
            SyncOrderRecipeSerializer().create(order_recipe)

        return instance


class SyncShiftSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    orders = SyncOrderSerializer(many=True)

    class Meta:
        model = Shift
        fields = ["id", "restaurant", "date", "ended_at", "orders"]

    def create(self, validated_data):
        instance_id = validated_data.pop("id")
        orders = validated_data.pop("orders")
        instance = Shift.objects.get_or_create(
            id=instance_id, defaults={**validated_data}
        )[0]

        for order in orders:
            order["shift"] = instance
            SyncOrderSerializer().create(order)

        return instance


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
        fields = ["pk", "restaurant", "date", "ended_at"]
        read_only_fields = ["pk"]


class OrderSerializer(serializers.ModelSerializer):

    amount = serializers.FloatField(read_only=True)

    class Meta:
        model = Order
        fields = ["pk", "shift", "customer_name", "picking_time", "status", "amount"]
        read_only_fields = ["pk", "amount"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = ["pk", "recipe", "ingredient", "quantity_in_g"]
        read_only_fields = ["pk"]


class RecipeSerializer(serializers.ModelSerializer):

    recipe_ingredients = RecipeIngredientSerializer(
        many=True, read_only=True, source="recipeingredient_set"
    )

    class Meta:
        model = Recipe
        fields = ["pk", "restaurant", "name", "price", "recipe_ingredients"]
        read_only_fields = ["pk"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["pk", "restaurant", "name", "price_by_kg"]
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
