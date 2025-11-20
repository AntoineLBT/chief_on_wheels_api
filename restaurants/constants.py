from django.db import models


class RestaurantType(models.TextChoices):
    PIZZERIA = "PIZZERIA", "Pizzeria"
    BURGER = "BURGER", "Burger"
    CREPERIE = "CREPERIE", "Crêperie"
    SALADERIE = "SALADERIE", "Saladerie"
    ROTISSERIE = "ROTISSERIE", "Rotisserie"


class OrderIngredientActionType(models.TextChoices):
    ADD = "ADD", "add"
    REMOVE = "REMOVE", "remove"
