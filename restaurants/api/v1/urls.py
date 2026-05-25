from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from restaurants.api.v1.views import (OrderViewSet, RecipeViewSet,
                                      RestaurantViewSet, ShiftViewSet,
                                      SyncView)

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")

restaurants_router = NestedDefaultRouter(router, "restaurants", lookup="restaurant")
restaurants_router.register(r"shifts", ShiftViewSet, basename="restaurant-shift")
restaurants_router.register(r"recipes", RecipeViewSet, basename="restaurant-recipe")

shifts_router = NestedDefaultRouter(restaurants_router, "shifts", lookup="shift")
shifts_router.register(r"orders", OrderViewSet, basename="shift-order")

urlpatterns = (
    router.urls
    + restaurants_router.urls
    + shifts_router.urls
    + [
        path("sync/", SyncView.as_view(), name="sync"),
    ]
)
