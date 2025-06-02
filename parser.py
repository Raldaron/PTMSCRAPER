#!/usr/bin/env python3
import argparse


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="PTMSCRAPER argument parser")

    parser.add_argument("--all", action="store_true", help="Run all scraping tasks")
    parser.add_argument("--job-ads", action="store_true", help="Scrape job ads")
    parser.add_argument("--pdfs", action="store_true", help="Download PDFs")
    parser.add_argument("--subdomains", action="store_true", help="Scrape subdomains")
    parser.add_argument("--press", action="store_true", help="Scrape press releases")

    parsed = parser.parse_args(args)

    if not any([parsed.job_ads, parsed.pdfs, parsed.subdomains, parsed.press, parsed.all]):
        parsed.all = True

    return parsed


def main():
    args = parse_args()
    print(args)


if __name__ == "__main__":
    main()
