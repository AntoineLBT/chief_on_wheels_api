from rest_framework import viewsets
from rest_framework.exceptions import NotFound

from restaurants.api.v1.mixins import RestaurantOwnerPermissionMixin
from restaurants.api.v1.serializers import (OrderSerializer, RecipeSerializer,
                                            RestaurantSerializer,
                                            ShiftSerializer)
from restaurants.models import Order, Recipe, Restaurant, Shift


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
        return Order.objects.filter(
            shift__pk=shift_pk, shift__restaurant__owner=self.request.user
        ).select_related("shift", "shift__restaurant")


class RecipeViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        return Recipe.objects.filter(
            restaurant__owner=self.request.user
        ).select_related("restaurant")
