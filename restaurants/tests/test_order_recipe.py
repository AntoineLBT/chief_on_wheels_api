from django.test import TestCase

from restaurants.tests.fixtures import OrderRecipeFixture


class TestOrderRecipeModel(TestCase, OrderRecipeFixture):

    def test_order_recipe_model(self):
        order_recipe = self.any_order_recipe()
        order_recipe.order.customer_name = "Bertrand"
        order_recipe.order.save()
        order_recipe.recipe.name = "Calzone"
        order_recipe.recipe.save()

        assert "Bertrand" in str(order_recipe)
        assert "Calzone" in str(order_recipe)
