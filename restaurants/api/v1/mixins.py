from functools import cached_property

from rest_framework.exceptions import NotFound
from rest_framework.request import Request

from restaurants.models import Restaurant


class RestaurantOwnerPermissionMixin:
    """Scopes a viewset nested under /restaurants/{restaurant_pk}/ to that
    restaurant, which must belong to the requesting user."""

    request = Request

    @cached_property
    def restaurant(self) -> Restaurant:
        restaurant = Restaurant.objects.filter(
            pk=self.kwargs["restaurant_pk"], owner=self.request.user
        ).first()
        if restaurant is None:
            raise NotFound("Restaurant not found")
        return restaurant

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Resolve the restaurant before any validation, so that a foreign
        # restaurant answers 404 whatever the payload.
        self.restaurant

    def get_queryset(self):
        return super().get_queryset().filter(restaurant=self.restaurant)

    def perform_create(self, serializer):
        serializer.save(restaurant=self.restaurant)
