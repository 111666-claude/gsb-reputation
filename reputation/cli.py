"""命令行入口：跑声望样例。"""

import argparse

from .core import DAY_MS, Reputation


def build_parser():
    parser = argparse.ArgumentParser(prog="reputation", description="阵营声望")
    parser.add_argument("--sample", default="tier",
                        help="tier / rival / clamp / dup / decay / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "tier":
        rep = Reputation()
        rep.add("e1", "guild", 500)
        print("tier=%s" % rep.tier("guild"))
    elif args.sample == "rival":
        rep = Reputation(rivals=[("guild", "raiders")])
        rep.add("e1", "guild", 100)
        print("b=%d" % rep.score("raiders"))
    elif args.sample == "clamp":
        rep = Reputation()
        rep.add("e1", "guild", 5000)
        print("score=%d" % rep.score("guild"))
    elif args.sample == "dup":
        rep = Reputation()
        rep.add("e1", "guild", 100)
        rep.add("e1", "guild", 100)
        print("score=%d" % rep.score("guild"))
    elif args.sample == "decay":
        rep = Reputation()
        rep.add("e1", "guild", 1000, now_ms=0)
        rep.tick(DAY_MS)
        for hour in range(10):
            rep.tick(DAY_MS + hour * 3600000)
        print("score=%d" % rep.score("guild"))
    elif args.sample == "scan":
        rep = Reputation()
        for index in range(3000):
            rep.add("e-%d" % index, "f-%d" % index, 1)
        for _ in range(3000):
            rep.score("f-2999")
        print("scanned=%d" % rep.scanned)
    else:
        raise SystemExit("需要 --sample tier|rival|clamp|dup|decay|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
