"""阵营声望：增减分数、按阈值判档、对立阵营联动、每日衰减、事件幂等。

缺陷：档位边界用严格大于、对立阵营不联动、衰减按调用次数算、分数不钳制、
同一个事件重复结算、查询每次扫全部阵营。
"""

TIERS = [(-500, "敌对"), (0, "冷淡"), (500, "中立"), (1000, "友善")]
TOP_TIER = "尊敬"
DAY_MS = 86400000


class Reputation:
    """阵营声望台账。"""

    def __init__(self, rivals=None, min_score=-2000, max_score=2000, decay_rate=0.1):
        self.rivals = dict(rivals or [])
        self.min_score = min_score
        self.max_score = max_score
        self.decay_rate = decay_rate
        self.scores = {}
        self.last_gain = {}
        self.handled = set()
        self.scanned = 0

    def add(self, event_id, faction, amount, now_ms=0):
        """结算一次声望变化。"""
        self.handled.add(event_id)
        self.scores[faction] = self.scores.get(faction, 0) + amount
        self.last_gain[faction] = now_ms
        return self.scores[faction]

    def score(self, faction):
        """当前声望。"""
        self.scanned += len(self.scores)
        return self.scores.get(faction, 0)

    def tier(self, faction):
        """当前档位。"""
        self.scanned += len(self.scores)
        value = self.scores.get(faction, 0)
        if value >= 1000:
            return TOP_TIER
        if value > 500:
            return "友善"
        if value >= 0:
            return "中立"
        if value >= -500:
            return "冷淡"
        return "敌对"

    def tick(self, now_ms):
        """结算衰减。"""
        for faction, value in self.scores.items():
            self.scores[faction] = int(value * (1 - self.decay_rate))
