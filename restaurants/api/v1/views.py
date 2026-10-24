from decimal import Decimal
from typing import cast

from django.db import transaction
from django.db.models import (DecimalField, ExpressionWrapper, OuterRef,
                              RestrictedError, Subquery, Sum)
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurants.api.v1.mixins import RestaurantOwnerPermissionMixin
from restaurants.api.v1.serializers import (IngredientSerializer,
                                            OrderSerializer, RecipeSerializer,
                                            RestaurantSerializer,
                                            ShiftSerializer,
                                            SyncShiftSerializer)
from restaurants.models import (Ingredient, Order, OrderIngredient,
                                OrderRecipe, Recipe, Restaurant, Shift)


def order_amount():
    """Σ unit_price + Σ extra_price, from the snapshots taken at order creation.

    One subquery per table: a single query joining both would count each
    recipe price once per ingredient modification.
    """
    recipes_total = (
        OrderRecipe.objects.filter(order=OuterRef("pk"))
        .values("order")  # GROUP BY order
        .annotate(total=Sum("unit_price"))
        .values("total")
    )
    extras_total = (
        OrderIngredient.objects.filter(order_recipe__order=OuterRef("pk"))
        .values("order_recipe__order")  # GROUP BY order
        .annotate(total=Sum("extra_price"))
        .values("total")
    )
    # Coalesce: an order without lines or modifications sums to NULL.
    return ExpressionWrapper(
        Coalesce(Subquery(recipes_total), Decimal("0"))
        + Coalesce(Subquery(extras_total), Decimal("0")),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return Restaurant.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ShiftViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    queryset = Shift.objects.select_related("restaurant")


class OrderViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def check_restaurant_owner(self, restaurant, user):
        if restaurant.owner != user:
            raise NotFound("Restaurant not found")

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("shift").restaurant
        self.check_restaurant_owner(restaurant, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        restaurant = serializer.validated_data.get("shift").restaurant
        self.check_restaurant_owner(restaurant, self.request.user)
        serializer.save()

    def get_queryset(self):
        shift_pk = self.kwargs.get("shift_pk")

        return (
            Order.objects.filter(
                shift__pk=shift_pk, shift__restaurant__owner=self.request.user
            )
            .select_related("shift", "shift__restaurant")
            .annotate(amount=order_amount())
        )


class RecipeViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    # Recipes are deactivated, never deleted.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    queryset = Recipe.objects.select_related("restaurant").prefetch_related(
        "recipeingredient_set__ingredient"
    )


class IngredientViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.select_related("restaurant")

    def destroy(self, request, *args, **kwargs):
        ingredient = self.get_object()
        try:
            ingredient.delete()
        except RestrictedError:
            recipes = (
                Recipe.objects.filter(recipeingredient__ingredient=ingredient)
                .distinct()
                .order_by("name")
                .values("pk", "name")
            )
            return Response(
                {
                    "detail": "Ingredient used in recipes or orders.",
                    "recipes": list(recipes),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SyncView(APIView):

    @transaction.atomic
    def post(self, request):

        sync_shift_serializer = SyncShiftSerializer(data=request.data)

        sync_shift_serializer.is_valid(raise_exception=True)

        validated_data = cast(dict, sync_shift_serializer.validated_data)

        restaurant = validated_data["restaurant"]

        if restaurant.owner != request.user:
            raise NotFound("Restaurant not found")

        sync_shift_serializer.save()

        return Response(status=status.HTTP_201_CREATED)
