from rest_framework import viewsets

from restaurants.api.v1.mixins import RestaurantOwnerPermissionMixin
from restaurants.api.v1.serializers import (
    OrderSerializer,
    RecipeSerializer,
    RestaurantSerializer,
    ShiftSerializer,
)
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


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        shift_pk = self.kwargs.get("shift_pk")
        return Order.objects.filter(
            shift__pk=shift_pk, shift__restaurant__owner=self.request.user
        ).select_related("shift", "shift__restaurant")


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        return Recipe.objects.filter(
            shift__restaurant__owner=self.request.user
        ).select_related("shift", "shift__restaurant")
