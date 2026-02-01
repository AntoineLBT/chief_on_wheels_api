from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from restaurants.api.v1.views import OrderViewSet, RestaurantViewSet, ShiftViewSet

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")

restaurants_router = NestedDefaultRouter(router, "restaurants", lookup="restaurant")
restaurants_router.register(r"shifts", ShiftViewSet, basename="restaurant-shift")

shifts_router = NestedDefaultRouter(restaurants_router, "shifts", lookup="shift")
shifts_router.register(r"orders", OrderViewSet, basename="shift-order")

urlpatterns = router.urls + restaurants_router.urls + shifts_router.urls
