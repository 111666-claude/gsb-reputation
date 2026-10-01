import unittest

from reputation.core import Reputation


class BasicTest(unittest.TestCase):
    def test_unknown_faction_is_zero(self):
        self.assertEqual(Reputation().score("ghost"), 0)

    def test_unknown_faction_is_neutral(self):
        self.assertEqual(Reputation().tier("ghost"), "中立")

    def test_add_returns_new_score(self):
        rep = Reputation()
        self.assertEqual(rep.add("e1", "guild", 30), 30)

    def test_different_events_accumulate(self):
        rep = Reputation()
        rep.add("e1", "guild", 100)
        rep.add("e2", "guild", 100)
        self.assertEqual(rep.score("guild"), 200)


class TierTest(unittest.TestCase):
    def test_zero_is_neutral(self):
        rep = Reputation()
        rep.add("e1", "guild", 0)
        self.assertEqual(rep.tier("guild"), "中立")

    def test_negative_score_is_not_top_tier(self):
        rep = Reputation()
        rep.add("e1", "guild", -100)
        self.assertNotEqual(rep.tier("guild"), "尊敬")


if __name__ == "__main__":
    unittest.main()
