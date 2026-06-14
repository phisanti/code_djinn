#!/usr/bin/env python
from djinn_sample.report import build_summary, render_summary


def main() -> None:
    summary = build_summary()
    print(render_summary())
    print(f"zeta_index={summary['zeta_index']}")


if __name__ == "__main__":
    main()
