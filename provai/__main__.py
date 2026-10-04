import argparse
import importlib
from pathlib import Path

from .graph import check


def main():
    ap = argparse.ArgumentParser(prog="python -m provai")
    sub = ap.add_subparsers(dest="command", required=True)
    conv = sub.add_parser("convert", help="convert captured runs into PROV-AI records")
    conv.add_argument("framework")
    conv.add_argument("runs", nargs="+")
    ev = sub.add_parser("evaluate", help="ask every competency question of every run, spans only and fully integrated")
    ev.add_argument("frameworks", nargs="*")
    sub.add_parser("test", help="check every record, the shapes, a conflicting write, and a read across requests")
    args = ap.parse_args()
    if args.command == "test":
        from .tests import run_tests
        results = run_tests()
        for name, ok in results:
            print(f"{'pass' if ok else 'FAIL'}  {name}")
        print(f"{sum(ok for _, ok in results)} of {len(results)} passed")
        return 0 if all(ok for _, ok in results) else 1
    if args.command == "evaluate":
        from .evaluate import evaluate, show
        show(evaluate(args.frameworks))
        return 0
    converter = importlib.import_module(f"provai.converters.{args.framework}")
    for run in args.runs:
        rec = converter.convert(Path(run))
        (Path(run) / "record.ttl").write_text(rec.turtle())
        ok, messages = check(rec.g)
        print(f"{run}: {len(rec.g)} triples, {'conforms' if ok else 'does not conform'}")
        for m in sorted(set(messages)):
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
