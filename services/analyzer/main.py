"""analyzer is a Python service built with a hermetic CPython toolchain.

It uses only the standard library, so the build needs no pip dependencies —
keeping the focus on Bazel's hermetic Python toolchain rather than packaging.
"""

import sys
from collections import Counter


def analyze(text: str) -> Counter:
    return Counter(text.split())


def main() -> None:
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    for word, count in analyze(text).most_common(10):
        print(f"{count:>4}  {word}")


if __name__ == "__main__":
    main()
