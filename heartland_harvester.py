#!/usr/bin/env python3
"""Minimal Heartland harvester stub."""
import argparse


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Heartland harvester")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of records")
    parser.add_argument("--dry-run", action="store_true", help="Run without side effects")
    parser.add_argument("--output", help="Output file path")
    return parser.parse_args(argv)


def main(argv=None):
    parse_args(argv)


if __name__ == "__main__":
    main()
