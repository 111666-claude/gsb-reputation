"""阵营声望：增减分数、按阈值判档、对立阵营联动、每日衰减、事件幂等。

口径以 README 为准：
- 分数永远钳制在 [min_score, max_score]。
- 档位左闭右开，正好等于下界按上一档算。
- 对立阵营联动：A 加 amount 时 B 减 floor(amount/2)，A 减时 B 加。
- 每个 86400000ms 服务日最多衰减一次，当日获得过声望则不衰减，朝 0 截断。
- 同一 event_id 只结算一次。
- score/tier 查询 O(1)。
"""

import math

TIERS = [(1000, "尊敬"), (500, "友善"), (0, "中立"), (-500, "冷淡")]
TOP_TIER = "尊敬"
BOTTOM_TIER = "敌对"
DAY_MS = 86400000


class Reputation:
    """阵营声望台账。"""

    def __init__(self, rivals=None, min_score=-2000, max_score=2000, decay_rate=0.1):
        self.rivals = {}
        for faction_a, faction_b in (rivals or []):
            self.rivals.setdefault(faction_a, set()).add(faction_b)
            self.rivals.setdefault(faction_b, set()).add(faction_a)
        self.min_score = min_score
        self.max_score = max_score
        self.decay_rate = decay_rate
        self.scores = {}
        self.last_gain_day = {}
        self.settled_day = {}
        self.handled = set()
        self.scanned = 0

    def _clamp(self, value):
        return max(self.min_score, min(self.max_score, value))

    def _settle(self, faction, target_day):
        """把 faction 的衰减补结算到 target_day（含）。"""
        day = self.settled_day.get(faction)
        if day is None:
            return
        factor = 1 - self.decay_rate
        while day < target_day:
            day += 1
            self.settled_day[faction] = day
            if day == self.last_gain_day.get(faction):
                continue
            value = self.scores.get(faction, 0)
            self.scores[faction] = self._clamp(math.trunc(value * factor))

    def add(self, event_id, faction, amount, now_ms=0):
        """结算一次声望变化。"""
        if event_id in self.handled:
            return self.scores.get(faction, 0)
        day = now_ms // DAY_MS
        self._settle(faction, day - 1)
        current = self.scores.get(faction, 0)
        self.scores[faction] = self._clamp(current + amount)
        self.last_gain_day[faction] = day
        self.settled_day[faction] = day
        half = abs(amount) // 2
        if half:
            rival_delta = -half if amount > 0 else half
            for rival in self.rivals.get(faction, ()):
                self._settle(rival, day - 1)
                rival_score = self.scores.get(rival, 0) + rival_delta
                self.scores[rival] = self._clamp(rival_score)
        self.handled.add(event_id)
        return self.scores[faction]

    def score(self, faction):
        """当前声望。"""
        self.scanned += 1
        return self.scores.get(faction, 0)

    def tier(self, faction):
        """当前档位。"""
        self.scanned += 1
        value = self.scores.get(faction, 0)
        for threshold, name in TIERS:
            if value >= threshold:
                return name
        return BOTTOM_TIER

    def tick(self, now_ms):
        """结算衰减。"""
        day = now_ms // DAY_MS
        for faction in list(self.scores):
            self._settle(faction, day)
