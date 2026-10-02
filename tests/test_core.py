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


if __name__ == "__main__":
    unittest.main()


class ClampTest(unittest.TestCase):
    def test_score_clamped_to_max(self):
        rep = Reputation()
        rep.add("e1", "guild", 5000)
        self.assertEqual(rep.score("guild"), 2000)

    def test_score_clamped_to_min(self):
        rep = Reputation()
        rep.add("e1", "guild", -5000)
        self.assertEqual(rep.score("guild"), -2000)

    def test_custom_bounds(self):
        rep = Reputation(min_score=-10, max_score=10)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("guild"), 10)
        rep.add("e2", "guild", -100)
        self.assertEqual(rep.score("guild"), -10)


class TierBoundaryTest(unittest.TestCase):
    def _tier(self, score):
        rep = Reputation()
        rep.add("e1", "guild", score)
        return rep.tier("guild")

    def test_lower_bounds_belong_to_upper_tier(self):
        self.assertEqual(self._tier(1000), "尊敬")
        self.assertEqual(self._tier(500), "友善")
        self.assertEqual(self._tier(0), "中立")
        self.assertEqual(self._tier(-500), "冷淡")

    def test_just_below_bounds(self):
        self.assertEqual(self._tier(999), "友善")
        self.assertEqual(self._tier(499), "中立")
        self.assertEqual(self._tier(-1), "冷淡")
        self.assertEqual(self._tier(-501), "敌对")


class RivalTest(unittest.TestCase):
    def test_gain_hits_rival_by_floor_half(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("raiders"), -50)

    def test_floor_half_rounds_down(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 101)
        self.assertEqual(rep.score("raiders"), -50)

    def test_loss_lifts_rival(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", -100)
        self.assertEqual(rep.score("raiders"), 50)

    def test_rival_result_clamped(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "raiders", -1900)
        rep.add("e2", "guild", 300)
        self.assertEqual(rep.score("raiders"), -2000)

    def test_no_rivals_unaffected(self):
        rep = Reputation()
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("raiders"), 0)


class DecayTest(unittest.TestCase):
    def test_same_day_ticks_settle_once(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=0)
        rep.tick(DAY_MS)
        for hour in range(10):
            rep.tick(DAY_MS + hour * 3600000)
        self.assertEqual(rep.score("guild"), 900)

    def test_cross_days_settle_each_day(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=0)
        rep.tick(DAY_MS)
        rep.tick(2 * DAY_MS)
        self.assertEqual(rep.score("guild"), 810)

    def test_gain_day_skips_decay(self):
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=DAY_MS)
        rep.tick(2 * DAY_MS - 1)
        self.assertEqual(rep.score("guild"), 1000)

    def test_decay_truncates_toward_zero(self):
        rep = Reputation()
        rep.add("e1", "guild", -15, now_ms=0)
        rep.tick(DAY_MS)
        self.assertEqual(rep.score("guild"), -13)

    def test_decay_stays_in_bounds(self):
        rep = Reputation()
        rep.add("e1", "guild", 2000, now_ms=0)
        for day in range(1, 50):
            rep.tick(day * DAY_MS)
        self.assertGreaterEqual(rep.score("guild"), 0)
        self.assertLessEqual(rep.score("guild"), 2000)


class IdempotencyTest(unittest.TestCase):
    def test_duplicate_event_ignored(self):
        rep = Reputation()
        rep.add("e1", "guild", 100)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("guild"), 100)

    def test_duplicate_event_skips_rival(self):
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 100)
        rep.add("e1", "guild", 100)
        self.assertEqual(rep.score("raiders"), -50)

    def test_replay_same_sequence_is_stable(self):
        def run():
            rep = Reputation()
            rep.add("e1", "guild", 300, now_ms=0)
            rep.add("e1", "guild", 300, now_ms=0)
            rep.tick(DAY_MS)
            rep.add("e2", "guild", 100, now_ms=DAY_MS)
            rep.tick(2 * DAY_MS)
            return rep.score("guild")

        self.assertEqual(run(), run())


class ScanCostTest(unittest.TestCase):
    def test_scanned_does_not_scale_with_factions(self):
        rep = Reputation()
        for index in range(3000):
            rep.add("e-%d" % index, "f-%d" % index, 1)
        before = rep.scanned
        for _ in range(3000):
            rep.score("f-2999")
        self.assertLessEqual(rep.scanned - before, 6000)
