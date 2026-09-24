import unittest
from src.pinned import validate_pinned,to_trace,increment_coefficients
from src.pinned_producer import produce_pinned
from src.pinned_checker import verify_pinned
from src.budgets import capacities,bottleneck_partition,minimum_cost_schedule,lower_trace,verify_transport,root_certificate

class PinnedContract(unittest.TestCase):
    def test_empty_pin_increment(self):
        self.assertEqual(increment_coefficients([], [2,3],3,5),[0,2,3])
    def test_saturated_pins(self):
        self.assertEqual(increment_coefficients([1,2],[],3,5),[0,0,0])
    def test_duplicate_pins_rejected(self):
        with self.assertRaises(ValueError):validate_pinned({'field':5,'threshold':3,'epochs':2,'pins':[[1,1]],'exposed':[[],[]]})
    def test_pin_budget_separate(self):
        c={'field':29,'threshold':12,'epochs':12,'pins':[list(range(1,25)) for _ in range(11)],'exposed':[list(range(1,6)) for _ in range(12)]}
        self.assertEqual(len(to_trace(c)['observations']),324)
    def test_balanced_cut(self):
        b=[2]*4;u=[3]*3
        self.assertEqual(capacities(b,u)['capacity'],7)
        self.assertEqual(bottleneck_partition(b,u)['width'],7)
    def test_zero_observations(self):
        self.assertEqual(capacities([0,0,0],[24,24])['capacity'],0)
    def test_transport_mutation(self):
        r=lower_trace([1,1,1],[1,1],3,5);self.assertTrue(verify_transport(r))
        r['interpolation_weights'][0]=(r['interpolation_weights'][0]+1)%5
        self.assertFalse(verify_transport(r))
    def test_explicit_offline_schedule(self):
        r=minimum_cost_schedule([1]*7,[1,0,2,0,1,1],4,[3,1,4,1,5,2])
        self.assertEqual((r['cost'],r['refresh_boundaries']),(2,[2,4]))
    def test_forbidden_boundaries(self):
        r=minimum_cost_schedule([1,1,1],[0,0],3,[1,1],[False,False])
        self.assertEqual(r['kind'],'impossible')
    def test_false_root_certificate(self):
        c={'field':5,'threshold':3,'epochs':3,'pins':[[1],[3]],'exposed':[[1],[2],[3]]}
        with self.assertRaises(ValueError):root_certificate(c,[0,1,2,3])
