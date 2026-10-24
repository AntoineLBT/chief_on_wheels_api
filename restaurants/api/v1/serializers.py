from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from restaurants.models import (FixedCharge, Ingredient, Order,
                                OrderIngredient, OrderRecipe, Recipe,
                                RecipeIngredient, Restaurant, Shift)


class SyncOrderIngredientSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField()

    class Meta:
        model = OrderIngredient
        fields = ["id", "ingredient", "action_type", "extra_price", "extra_cost"]

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
        fields = ["id", "recipe", "unit_price", "unit_cost", "order_ingredients"]

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
    # Only closed shifts are synced: once on the server, a shift never changes.
    ended_at = serializers.DateTimeField()
    orders = SyncOrderSerializer(many=True)

    class Meta:
        model = Shift
        fields = ["id", "restaurant", "date", "ended_at", "vat_rate", "orders"]

    def validate(self, attrs):
        if attrs["ended_at"] < attrs["date"]:
            raise serializers.ValidationError(
                {"ended_at": "A shift cannot end before it starts."}
            )
        return attrs

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
        fields = ["pk", "name", "vat_rate", "owner"]
        read_only_fields = ["pk"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = ["pk", "ingredient", "quantity"]
        read_only_fields = ["pk"]

    def validate_ingredient(self, ingredient):
        # Answer like an unknown pk: other catalogues stay invisible.
        if ingredient.restaurant != self.context["view"].restaurant:
            raise serializers.ValidationError("Ingredient not found.")
        return ingredient


class RecipeSerializer(serializers.ModelSerializer):

    recipe_ingredients = RecipeIngredientSerializer(
        many=True, required=False, source="recipeingredient_set"
    )
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "pk",
            "restaurant",
            "name",
            "price",
            "is_active",
            "recipe_ingredients",
            "cost",
        ]
        read_only_fields = ["pk", "restaurant"]

    def validate_recipe_ingredients(self, lines):
        ingredients = [line["ingredient"] for line in lines]
        if len(set(ingredients)) != len(ingredients):
            raise serializers.ValidationError("Each ingredient may appear only once.")
        return lines

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("recipeingredient_set", [])
        recipe = super().create(validated_data)
        self.set_lines(recipe, lines)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("recipeingredient_set", None)
        recipe = super().update(instance, validated_data)
        # Sent lines replace the whole set; omitted lines leave it untouched.
        if lines is not None:
            recipe.recipeingredient_set.all().delete()
            self.set_lines(recipe, lines)
        return recipe

    @staticmethod
    def set_lines(recipe, lines):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(recipe=recipe, **line) for line in lines
        )


class IngredientSerializer(serializers.ModelSerializer):

    EXTRA_FIELDS = ["extra_price", "extra_quantity"]

    class Meta:
        model = Ingredient
        fields = [
            "pk",
            "restaurant",
            "name",
            "unit",
            "price_per_unit",
            "has_extra",
            "extra_price",
            "extra_quantity",
        ]
        read_only_fields = ["pk", "restaurant"]

    def validate(self, attrs):
        # Partial updates: fall back on the stored values for omitted fields.
        def value(field):
            return attrs.get(field, getattr(self.instance, field, None))

        if not value("has_extra"):
            return {**attrs, **{field: None for field in self.EXTRA_FIELDS}}

        missing = [field for field in self.EXTRA_FIELDS if value(field) is None]
        if missing:
            raise serializers.ValidationError(
                {field: "Required when has_extra is true." for field in missing}
            )
        return attrs


class FixedChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedCharge
        fields = [
            "pk",
            "restaurant",
            "name",
            "amount",
            "frequency",
            "start_date",
            "end_date",
        ]
        read_only_fields = ["pk", "restaurant", "end_date"]


class FixedChargeReviseSerializer(serializers.ModelSerializer):
    effective_date = serializers.DateField(default=timezone.localdate)

    class Meta:
        model = FixedCharge
        fields = ["amount", "frequency", "effective_date"]
        extra_kwargs = {"amount": {"required": False}, "frequency": {"required": False}}

    def validate_effective_date(self, effective_date):
        # The current charge must keep at least its first day.
        start_date = self.context["charge"].start_date
        if effective_date <= start_date:
            raise serializers.ValidationError(
                "The effective date must be after the start of the charge "
                f"({start_date.isoformat()})."
            )
        return effective_date


class FixedChargeCloseSerializer(serializers.Serializer):
    effective_date = serializers.DateField(default=timezone.localdate)

    def validate_effective_date(self, effective_date):
        # end_date is inclusive: closing on the start date keeps one day.
        start_date = self.context["charge"].start_date
        if effective_date < start_date:
            raise serializers.ValidationError(
                "The effective date must not be before the start of the charge "
                f"({start_date.isoformat()})."
            )
        return effective_date


class AccountingQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=["year", "month", "week", "shift"])
    # Any day of the period; the shift itself for period=shift.
    date = serializers.DateField(required=False)
    shift = serializers.UUIDField(required=False)

    def validate(self, attrs):
        field = "shift" if attrs["period"] == "shift" else "date"
        if field not in attrs:
            raise serializers.ValidationError({field: "This field is required."})
        return attrs
