import unittest

from reputation.core import DAY_MS, Reputation


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


class TierBoundaryTest(unittest.TestCase):
    def test_left_closed_right_open(self):
        cases = [
            (1000, "尊敬"), (1500, "尊敬"),
            (999, "友善"), (500, "友善"),
            (499, "中立"), (0, "中立"),
            (-1, "冷淡"), (-500, "冷淡"),
            (-501, "敌对"), (-2000, "敌对"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                rep = Reputation()
                rep.add("e1", "guild", value)
                self.assertEqual(rep.tier("guild"), expected)


class ClampTest(unittest.TestCase):
    def test_gain_above_max_is_clamped(self):
        rep = Reputation()
        rep.add("e1", "guild", 5000)
        self.assertEqual(rep.score("guild"), 2000)

    def test_loss_below_min_is_clamped(self):
        rep = Reputation()
        rep.add("e1", "guild", -5000)
        self.assertEqual(rep.score("guild"), -2000)

    def test_custom_range(self):
        rep = Reputation(min_score=-10, max_score=10)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("guild"), 10)


class RivalTest(unittest.TestCase):
    def test_gain_costs_rival_half_floored(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 101)
        self.assertEqual(rep.score("guild"), 101)
        self.assertEqual(rep.score("raiders"), -50)

    def test_loss_boosts_rival_half(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", -100)
        self.assertEqual(rep.score("raiders"), 50)

    def test_linkage_is_bidirectional(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "raiders", 100)
        self.assertEqual(rep.score("guild"), -50)

    def test_rival_result_is_clamped(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 100)
        rep.add("e2", "guild", 5000)
        self.assertEqual(rep.score("raiders"), -2000)


class DecayTest(unittest.TestCase):
    def test_same_day_ticks_settle_once(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=0)
        rep.tick(DAY_MS)
        for hour in range(10):
            rep.tick(DAY_MS + hour * 3600000)
        self.assertEqual(rep.score("guild"), 900)

    def test_crossing_days_settles_each_day(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=0)
        rep.tick(2 * DAY_MS)
        self.assertEqual(rep.score("guild"), 810)

    def test_gain_on_entered_day_skips_decay(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=DAY_MS)
        rep.tick(DAY_MS)
        self.assertEqual(rep.score("guild"), 1000)
        rep.tick(2 * DAY_MS)
        self.assertEqual(rep.score("guild"), 900)

    def test_decay_truncates_toward_zero(self):
        rep = Reputation()
        rep.add("e1", "guild", 105, now_ms=0)
        rep.tick(DAY_MS)
        self.assertEqual(rep.score("guild"), 94)
        rep = Reputation()
        rep.add("e1", "guild", -105, now_ms=0)
        rep.tick(DAY_MS)
        self.assertEqual(rep.score("guild"), -94)

    def test_inactive_faction_decays_without_gain(self):
        rep = Reputation()
        rep.add("e1", "guild", 100, now_ms=0)
        rep.tick(DAY_MS)
        self.assertEqual(rep.score("guild"), 90)


class IdempotencyTest(unittest.TestCase):
    def test_duplicate_event_ignored(self):
        rep = Reputation()
        rep.add("e1", "guild", 100)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("guild"), 100)

    def test_duplicate_event_does_not_touch_rival(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 100)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("raiders"), -50)

    def test_same_event_id_for_other_faction_ignored(self):
        rep = Reputation()
        rep.add("e1", "guild", 100)
        rep.add("e1", "raiders", 100)
        self.assertEqual(rep.score("raiders"), 0)

    def test_repeated_sequence_is_deterministic(self):
        def run():
            rep = Reputation(rivals=[("guild", "raiders")])
            rep.add("e1", "guild", 300, now_ms=0)
            rep.add("e2", "raiders", -100, now_ms=0)
            rep.tick(DAY_MS)
            rep.add("e3", "guild", 50, now_ms=DAY_MS)
            rep.tick(2 * DAY_MS)
            return rep.score("guild"), rep.score("raiders")
        self.assertEqual(run(), run())


class ScanTest(unittest.TestCase):
    def test_queries_are_constant_cost(self):
        rep = Reputation()
        for index in range(3000):
            rep.add("e-%d" % index, "f-%d" % index, 1)
        for _ in range(3000):
            rep.score("f-2999")
            rep.tier("f-2999")
        self.assertLessEqual(rep.scanned, 6000)

    def test_invariant_scores_stay_in_range(self):
        rep = Reputation(rivals=[("guild", "raiders")], decay_rate=0.5)
        rep.add("e1", "guild", 10 ** 9, now_ms=0)
        rep.add("e2", "guild", -10 ** 9, now_ms=0)
        rep.tick(3 * DAY_MS)
        for value in rep.scores.values():
            self.assertGreaterEqual(value, -2000)
            self.assertLessEqual(value, 2000)


if __name__ == "__main__":
    unittest.main()
