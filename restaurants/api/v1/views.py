from datetime import date
from decimal import Decimal
from typing import cast

from django.db import transaction
from django.db.models import (Count, DecimalField, ExpressionWrapper, OuterRef,
                              RestrictedError, Subquery, Sum)
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurants.accounting import (Charge, ShiftSales, months_of,
                                    period_bounds, period_figures,
                                    period_status, shift_figures, shift_rows)
from restaurants.api.v1.mixins import RestaurantOwnerPermissionMixin
from restaurants.api.v1.serializers import (AccountingQuerySerializer,
                                            FixedChargeCloseSerializer,
                                            FixedChargeReviseSerializer,
                                            FixedChargeSerializer,
                                            IngredientSerializer,
                                            OrderSerializer, RecipeSerializer,
                                            RestaurantSerializer,
                                            ShiftSerializer,
                                            SyncShiftSerializer)
from restaurants.models import (FixedCharge, Ingredient, Order,
                                OrderIngredient, OrderRecipe, Recipe,
                                Restaurant, Shift)


def snapshot_total(order_path: str, recipe_field: str, extra_field: str):
    """Σ recipe_field of the order recipes + Σ extra_field of their ingredient
    modifications, for the orders reached through order_path from OuterRef.

    One subquery per table: a single query joining both would count each
    recipe line once per ingredient modification.
    """
    recipes_total = (
        OrderRecipe.objects.filter(**{order_path: OuterRef("pk")})
        .values(order_path)  # GROUP BY
        .annotate(total=Sum(recipe_field))
        .values("total")
    )
    extras_path = f"order_recipe__{order_path}"
    extras_total = (
        OrderIngredient.objects.filter(**{extras_path: OuterRef("pk")})
        .values(extras_path)  # GROUP BY
        .annotate(total=Sum(extra_field))
        .values("total")
    )
    # Coalesce: an order without lines or modifications sums to NULL.
    return ExpressionWrapper(
        Coalesce(Subquery(recipes_total), Decimal("0"))
        + Coalesce(Subquery(extras_total), Decimal("0")),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )


def order_amount():
    """Σ unit_price + Σ extra_price, from the snapshots taken at order creation."""
    return snapshot_total("order", "unit_price", "extra_price")


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return Restaurant.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ShiftViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    queryset = Shift.objects.select_related("restaurant")

    def perform_create(self, serializer):
        serializer.save(restaurant=self.restaurant, vat_rate=self.restaurant.vat_rate)


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


class FixedChargeViewSet(RestaurantOwnerPermissionMixin, viewsets.ModelViewSet):
    serializer_class = FixedChargeSerializer
    queryset = FixedCharge.objects.select_related("restaurant")
    # Charges are revised or closed, never overwritten nor deleted.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        # A rename has no accounting effect: the only in-place change.
        if set(request.data) - {"name"}:
            raise ValidationError(
                {
                    "detail": "Only the name can be changed in place: "
                    "revise the charge instead."
                }
            )
        return super().partial_update(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        # Closed charges only matter to the accounting. They stay reachable by
        # pk so that acting on one answers 400 rather than 404.
        if self.action == "list":
            return queryset.filter(end_date__isnull=True)
        return queryset

    def validate_action(self, request) -> tuple[FixedCharge, date, dict]:
        """Validate a revise or close on an active charge, returning the
        charge, the effective date and the other validated fields."""
        charge = self.get_object()
        if charge.end_date is not None:
            raise ValidationError({"detail": "This charge is already closed."})
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "charge": charge},
        )
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        return charge, changes.pop("effective_date"), changes

    @action(detail=True, methods=["post"], serializer_class=FixedChargeReviseSerializer)
    def revise(self, request, *args, **kwargs):
        charge, effective_date, changes = self.validate_action(request)
        successor = charge.revise(effective_date, **changes)
        return Response(
            FixedChargeSerializer(successor).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], serializer_class=FixedChargeCloseSerializer)
    def close(self, request, *args, **kwargs):
        charge, effective_date, _ = self.validate_action(request)
        charge.end_date = effective_date
        charge.save(update_fields=["end_date"])
        return Response(FixedChargeSerializer(charge).data)


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


class AccountingView(RestaurantOwnerPermissionMixin, APIView):
    """Accounting of the synced shifts of a restaurant, over a period."""

    def get(self, request, *args, **kwargs):
        query = AccountingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        charges = self.charges()
        shifts = self.shifts()

        period = params["period"]
        if period == "shift":
            return Response(self.shift_report(charges, shifts, params["shift"]))
        start, end = period_bounds(period, params["date"])
        report = {
            "period": period,
            "start": start,
            "end": end,
            "totals": period_figures(charges, shifts, start, end),
        }
        if period == "year":
            today = timezone.localdate()
            report["to_date"] = period_figures(charges, shifts, start, min(end, today))
            report["breakdown"] = [
                {
                    "start": month_start,
                    "end": month_end,
                    "status": period_status(month_start, month_end, today),
                    **period_figures(charges, shifts, month_start, month_end),
                }
                for month_start, month_end in months_of(start.year)
            ]
        else:
            report["breakdown"] = shift_rows(charges, shifts, start, end)
            # A month bears its charges even without a shift to carry them.
            if period == "month" and not report["breakdown"]:
                report["breakdown"] = [
                    {"shift": None, "date": None, **report["totals"]}
                ]
        return Response(report)

    def shift_report(self, charges, shifts, shift_pk) -> dict:
        shift = next((s for s in shifts if s.pk == str(shift_pk)), None)
        if shift is None:
            raise NotFound("Shift not found")
        orders = (
            Order.objects.filter(shift_id=shift_pk)
            .annotate(
                amount=order_amount(),
                cost=snapshot_total("order", "unit_cost", "extra_cost"),
            )
            .order_by("picking_time", "pk")
        )
        return {
            "period": "shift",
            "shift": shift.pk,
            "start": shift.day,
            "end": shift.day,
            "totals": shift_figures(charges, shifts, shift),
            "breakdown": [
                {
                    "order": str(order.pk),
                    "customer_name": order.customer_name,
                    "picking_time": timezone.localtime(order.picking_time),
                    "amount": order.amount,
                    "cost": order.cost,
                }
                for order in orders
            ],
        }

    def charges(self) -> list[Charge]:
        return [
            Charge(c.amount, c.frequency, c.start_date, c.end_date)
            for c in FixedCharge.objects.filter(restaurant=self.restaurant)
        ]

    def shifts(self) -> list[ShiftSales]:
        """Every shift of the restaurant: the fixed charges of a shift depend
        on the number of shifts in its month."""
        shifts = (
            Shift.objects.filter(restaurant=self.restaurant)
            .annotate(
                revenue=snapshot_total("order__shift", "unit_price", "extra_price"),
                material_cost=snapshot_total("order__shift", "unit_cost", "extra_cost"),
                order_count=Count("order"),
            )
            .order_by("date")
        )
        return [
            ShiftSales(
                pk=str(shift.pk),
                # The local day: a shift at 00:30 in Paris belongs to that day.
                day=timezone.localtime(shift.date).date(),
                vat_rate=shift.vat_rate,
                revenue_incl_vat=shift.revenue,
                material_cost=shift.material_cost,
                order_count=shift.order_count,
            )
            for shift in shifts
        ]
