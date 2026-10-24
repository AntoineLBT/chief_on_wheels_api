from django.db import models


class OrderIngredientActionType(models.TextChoices):
    ADD = "ADD", "add"
    REMOVE = "REMOVE", "remove"


class OrderStatus(models.TextChoices):
    TODO = "TODO", "todo"
    IN_PROGRESS = "IN_PROGRESS", "in_progress"
    DONE = "DONE", "done"


class IngredientUnit(models.TextChoices):
    KG = "KG", "kg"
    L = "L", "l"
    UNIT = "UNIT", "unit"


class FixedChargeFrequency(models.TextChoices):
    PER_SHIFT = "PER_SHIFT", "per_shift"
    MONTHLY = "MONTHLY", "monthly"
    YEARLY = "YEARLY", "yearly"
