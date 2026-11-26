import unittest

from discount import final_price


class TestFinalPrice(unittest.TestCase):
    def test_zero_amount(self):
        self.assertEqual(final_price(0), 0)

    def test_just_below_500_has_no_discount(self):
        self.assertAlmostEqual(final_price(499.99), 499.99)

    def test_500_gets_five_percent_discount(self):
        self.assertAlmostEqual(final_price(500), 475)

    def test_just_below_1000_gets_five_percent_discount(self):
        self.assertAlmostEqual(final_price(999.99), 949.9905)

    def test_1000_gets_ten_percent_discount(self):
        self.assertAlmostEqual(final_price(1000), 900)

    def test_large_amount_gets_ten_percent_discount(self):
        self.assertAlmostEqual(final_price(100000), 90000)

    def test_negative_amount_raises_value_error(self):
        with self.assertRaises(ValueError):
            final_price(-0.01)


if __name__ == "__main__":
    unittest.main()
