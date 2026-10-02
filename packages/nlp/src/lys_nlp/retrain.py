"""Huấn luyện lại từ CSV nhãn đã xác nhận; đánh giá baseline/candidate cùng tập giữ lại."""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    subprocess.run([sys.executable, "-m", "lys_nlp.train", "--train", args.train, "--validation", args.validation, "--output", args.output, "--version", args.version], check=True)
    for name, path in [("before", args.baseline), ("after", args.output)]:
        subprocess.run([sys.executable, "-m", "lys_nlp.evaluate", "--data", args.test, "--model", path, "--output", f"{args.output}/{name}.json"], check=True)


if __name__ == "__main__":
    main()
