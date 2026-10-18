from django.db import models


class OrderIngredientActionType(models.TextChoices):
    ADD = "ADD", "add"
    REMOVE = "REMOVE", "remove"


class OrderStatus(models.TextChoices):
    TODO = "TODO", "todo"
    IN_PROGRESS = "IN_PROGRESS", "in_progress"
    DONE = "DONE", "done"
