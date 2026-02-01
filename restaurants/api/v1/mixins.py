from rest_framework.exceptions import NotFound
from rest_framework.request import Request


class RestaurantOwnerPermissionMixin:
    request = Request

    def check_restaurant_owner(self, restaurant, user):
        if restaurant.owner != user:
            raise NotFound("Restaurant not found")

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        self.check_restaurant_owner(restaurant, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        self.check_restaurant_owner(restaurant, self.request.user)
        serializer.save()
