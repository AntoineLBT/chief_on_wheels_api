from typing import cast

from django.db import transaction
from django.db.models import Sum
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
from restaurants.models import Ingredient, Order, Recipe, Restaurant, Shift


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return Restaurant.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ShiftViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = ShiftSerializer

    def get_queryset(self):
        return Shift.objects.filter(restaurant__owner=self.request.user).select_related(
            "restaurant"
        )


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
            .annotate(amount=Coalesce(Sum("orderrecipe__recipe__price"), 0.0))
        )


class RecipeViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        return (
            Recipe.objects.filter(restaurant__owner=self.request.user)
            .select_related("restaurant")
            .prefetch_related("recipeingredient_set")
        )


class IngredientViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = IngredientSerializer

    def get_queryset(self):
        return Ingredient.objects.filter(
            restaurant__owner=self.request.user
        ).select_related("restaurant")


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
