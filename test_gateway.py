import unittest
from decimal import Decimal
from risk import calculate_quantity, floor_step, validate_prices
from gateway import validate_order

class V5Tests(unittest.TestCase):
    def setUp(self):
        self.filters = {
            "PRICE_FILTER":{"minPrice":"0.01","maxPrice":"1000000","tickSize":"0.01"},
            "LOT_SIZE":{"minQty":"0.001","maxQty":"1000","stepSize":"0.001"},
            "MIN_NOTIONAL":{"minNotional":"5"}}
    def test_valid_order(self):
        self.assertEqual(validate_order("100.00","0.1",self.filters),Decimal("10.000"))
    def test_bad_tick(self):
        with self.assertRaises(ValueError): validate_order("100.001","0.1",self.filters)
    def test_small_notional(self):
        with self.assertRaises(ValueError): validate_order("10","0.1",self.filters)
    def test_round_down(self):
        self.assertEqual(floor_step("0.1239","0.001"),Decimal("0.123"))
    def test_risk_qty(self):
        self.assertEqual(calculate_quantity("1000","100","95","0.001"),Decimal("0.998"))
    def test_stop_order_relationship(self):
        validate_prices("100","95","94.5","110","0.01")
    def test_invalid_bracket(self):
        with self.assertRaises(ValueError): validate_prices("100","101","100","110","0.01")
    def test_unaligned_price(self):
        with self.assertRaises(ValueError): validate_prices("100","95.001","94.5","110","0.01")

if __name__ == "__main__": unittest.main()
