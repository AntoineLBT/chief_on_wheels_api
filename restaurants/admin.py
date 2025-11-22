from django.contrib import admin

from .models import (Ingredient, Order, OrderIngredient, OrderRecipe, Recipe,
                     RecipeIngredient, Restaurant, Shift)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["restaurant__name", "date"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["customer_name", "picking_time", "shift__date", "shift__id"]


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["name", "price"]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "price_by_kg"]


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ["recipe__name", "ingredient__name", "quantity_in_g"]


@admin.register(OrderRecipe)
class OrderRecipeAdmin(admin.ModelAdmin):
    list_display = ["order", "recipe"]


@admin.register(OrderIngredient)
class OrderIngredientAdmin(admin.ModelAdmin):
    list_display = ["order_recipe", "ingredient", "action_type"]
