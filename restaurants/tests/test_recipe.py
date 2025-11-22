from django.test import TestCase

from restaurants.tests.fixtures import RecipeFixture


class TestRecipeModel(TestCase, RecipeFixture):

    def test_recipe_model(self):
        recipe = self.any_recipe()
        recipe.name = "Margharita"
        recipe.save()

        assert "Margharita" in str(recipe)
