"""Fast contract tests for the independent bounded-oracle implementation."""
import unittest

from src.adaptive import exact_policy
from src.budgets import (
    constant_capacity,
    fixed_pin_capacity,
    largest_safe_constant_horizon,
)
from src.exhaustive_validation import (
    _brute_partition_width,
    _brute_schedule,
    _pinned_reveals,
)


class ExhaustiveOracleContract(unittest.TestCase):
    def test_adaptive_assignment_count_has_no_unused_randomness(self):
        result = exact_policy()
        self.assertEqual(result["assignment_count"], 25)
        self.assertEqual(result["randomness_dimension"], 1)

    def test_independent_rank_hiding(self):
        self.assertFalse(_pinned_reveals(5, 3, [[1], [2], [3]], [[1], [1]]))

    def test_independent_rank_revealing(self):
        self.assertTrue(_pinned_reveals(5, 3, [[1], [2], [3]], [[1], [3]]))

    def test_brute_partition(self):
        self.assertEqual(_brute_partition_width([2, 2, 2, 2], [3, 3, 3]), 7)

    def test_brute_schedule_with_forbidden_boundary(self):
        self.assertIsNone(_brute_schedule([1, 1, 1], [0, 0], 3, [1, 1], [False, False]))

    def test_closed_form_helpers(self):
        self.assertEqual(constant_capacity(4, 2, 3), 7)
        self.assertEqual(fixed_pin_capacity([1, 3, 0, 2, 1], 2), 5)
        self.assertEqual(largest_safe_constant_horizon(2, 3, 8), 4)
        self.assertIsNone(largest_safe_constant_horizon(1, 1, 4))


if __name__ == "__main__":
    unittest.main()
