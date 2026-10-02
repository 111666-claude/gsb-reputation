"""阵营声望：增减分数、按阈值判档、对立阵营联动、每日衰减、事件幂等。"""

TIERS = [(1000, "尊敬"), (500, "友善"), (0, "中立"), (-500, "冷淡")]
BOTTOM_TIER = "敌对"
TOP_TIER = TIERS[0][1]
DAY_MS = 86400000


class Reputation:
    """阵营声望台账。"""

    def __init__(self, rivals=None, min_score=-2000, max_score=2000, decay_rate=0.1):
        self.rivals = {}
        for left, right in (rivals or []):
            self.rivals.setdefault(left, set()).add(right)
            self.rivals.setdefault(right, set()).add(left)
        self.min_score = min_score
        self.max_score = max_score
        self.decay_rate = decay_rate
        self.scores = {}
        self.last_gain = {}
        self.handled = set()
        self.scanned = 0
        self.day = 0

    def _clamp(self, value):
        return max(self.min_score, min(self.max_score, value))

    def add(self, event_id, faction, amount, now_ms=0):
        """结算一次声望变化。"""
        if event_id in self.handled:
            return self.scores.get(faction, 0)
        self.handled.add(event_id)
        self.scores[faction] = self._clamp(self.scores.get(faction, 0) + amount)
        self.last_gain[faction] = now_ms
        for rival in self.rivals.get(faction, ()):
            self.scores[rival] = self._clamp(
                self.scores.get(rival, 0) - (amount // 2))
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
        if day <= self.day:
            return
        previous = self.day
        self.day = day
        factor = 1 - self.decay_rate
        for faction, value in self.scores.items():
            gained_day = self.last_gain.get(faction, 0) // DAY_MS
            decays = day - previous
            if previous < gained_day <= day:
                decays -= 1
            for _ in range(decays):
                value = int(value * factor)
            self.scores[faction] = self._clamp(value)
