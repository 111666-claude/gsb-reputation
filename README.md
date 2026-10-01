# reputation

阵营声望：增减分数、按阈值判档、对立阵营联动、每日衰减与事件幂等。
只用 Python 标准库。

```
python3 -m reputation.cli --sample tier
python3 -m reputation.cli --sample rival
python3 -m reputation.cli --sample clamp
python3 -m reputation.cli --sample dup
python3 -m reputation.cli --sample decay
python3 -m reputation.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **分数范围**：任何时候分数都被钳制在 `[min_score, max_score]`（默认 -2000 到 2000）。
- **档位阈值**：区间左闭右开——`[-500, 0)` 冷淡、`[0, 500)` 中立、`[500, 1000)` 友善、
  `[1000, +∞)` 尊敬、低于 -500 敌对。正好等于下界时按上一档算，不许用严格大于判。
- **对立联动**：`rivals` 里成对的阵营互相牵制。给 A 加 `amount` 时，
  对立的 B 减 `floor(amount / 2)`；给 A 减 `amount` 时 B 加 `floor(amount / 2)`。
  联动后的结果同样要钳制。
- **每日衰减**：每满一个 86400000ms 的服务日，没有在该日获得过声望的阵营，
  分数变成 `trunc(score * (1 - decay_rate))`，朝 0 方向收缩；
  同一个服务日里多次调用 `tick` 只结算一次，跨了几天就结算几次。
- **事件幂等**：同一个 `event_id` 只结算一次，重复上报不改变任何阵营的分数。
- **不变量**：分数永远在 `[min_score, max_score]`；同一串增加、tick 序列
  重复执行结果相同。
- **查询代价**：`score` 与 `tier` 查询 O(1)，`scanned` 不随阵营数线性增长。
- **规模**：10 万阵营、每秒 10 万次查询，单次摊还 O(1)。

## 输出契约（不改格式）

```
tier=..
b=..
score=..
scanned=..
```

## 目录

```
reputation/core.py   增减、档位、联动与衰减
reputation/cli.py    命令行入口
tests/               unittest 用例
```
