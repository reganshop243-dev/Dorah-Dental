from decimal import Decimal

from django.test import TestCase
from django.db.models import F, Sum, ExpressionWrapper, DecimalField

from .models import InventoryItem


class InventoryValuationTests(TestCase):
    def test_stock_value_is_sum_of_each_item_value(self):
        """Stock value must be Σ(quantity × unit_cost), not Σqty × Σcost."""
        InventoryItem.objects.create(
            name='Item A', quantity=10, unit_cost=Decimal('2000.00'), is_active=True
        )
        InventoryItem.objects.create(
            name='Item B', quantity=5, unit_cost=Decimal('1500.00'), is_active=True
        )
        InventoryItem.objects.create(
            name='Item C', quantity=2, unit_cost=Decimal('5000.00'), is_active=True
        )

        total = InventoryItem.objects.filter(is_active=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_cost'),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                )
            )
        )['total'] or Decimal('0.00')

        self.assertEqual(total, Decimal('37500.00'))
