from django.test import TestCase

from restaurants.tests.fixtures import IngredientFixture


class TestIngredientModel(TestCase, IngredientFixture):

    def test_ingredient_model(self):
        ingredient = self.any_ingredient()
        ingredient.name = "patate"
        ingredient.save()

        assert "patate" in str(ingredient)
