#!/usr/bin/env python3
"""Heartland Harvester

Automates discovery of organizations referencing Heartland Payroll across
various OSINT sources. Evidence is written to CSV for sales intelligence.

Dependencies: httpx, beautifulsoup4, PyPDF2, tqdm (optional), rich (optional).

Example:
    python heartland_harvester.py --limit 100 --threads 5 --out leads.csv
"""
import argparse
import asyncio
import csv
import datetime as dt
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable, List, Set, TYPE_CHECKING

try:
    import httpx
except ImportError:  # pragma: no cover - allow script to run without httpx
    httpx = None
if TYPE_CHECKING:
    import httpx as httpx_type
try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore
try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - optional
    def tqdm(x, **kwargs):
        return x

CSV_HEADERS = ["company_name", "source_type", "evidence_url", "evidence_snippet"]

@dataclass
class Evidence:
    company_name: str
    source_type: str
    evidence_url: str
    evidence_snippet: str


def normalize_name(name: str) -> str:
    """Normalize company name for deduping."""
    name = re.sub(r"[\s\W]+", " ", name or "").strip()
    return name.lower()


def dedupe_evidence(items: Iterable[Evidence]) -> List[Evidence]:
    seen: Set[str] = set()
    out: List[Evidence] = []
    for ev in items:
        key = (normalize_name(ev.company_name), ev.source_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out

async def fetch(client: "httpx_type.AsyncClient", url: str) -> "httpx_type.Response":
    """Fetch a URL with exponential backoff."""
    delay = 1
    for attempt in range(5):
        try:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 503}:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
        except httpx.RequestError:
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError(f"Failed to fetch {url}")

async def serpapi_job_ads(client: "httpx_type.AsyncClient", api_key: str, limit: int) -> List[Evidence]:
    """Search SerpAPI for job ads mentioning Heartland Payroll."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": 'site:easyapply.co "Heartland Payroll"',
        "api_key": api_key,
        "num": min(limit, 100),
    }
    resp = await fetch(client, url + "?" + httpx.QueryParams(params).to_str())
    data = resp.json()
    results = []
    for r in data.get("organic_results", []):
        title = r.get("title", "")
        link = r.get("link")
        snippet = r.get("snippet", "")
        company = title.split("-")[0].strip()
        results.append(Evidence(company, "job-ad", link, snippet))
        if len(results) >= limit:
            break
    return results

async def search_pdfs(client: "httpx_type.AsyncClient", api_key: str, limit: int) -> List[Evidence]:
    """Search PDFs via SerpAPI and extract snippets."""
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is required for PDF parsing")
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": '"Heartland Payroll" filetype:pdf',
        "api_key": api_key,
        "num": min(limit, 10),
    }
    resp = await fetch(client, url + "?" + httpx.QueryParams(params).to_str())
    results = []
    for r in resp.json().get("organic_results", []):
        pdf_resp = await fetch(client, r.get("link"))
        reader = PdfReader(pdf_resp.content)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        idx = text.lower().find("heartland payroll")
        snippet = text[max(idx - 100, 0) : idx + 120] if idx != -1 else ""
        company = r.get("title", "").split("-")[0]
        results.append(Evidence(company, "pdf", r.get("link"), snippet))
        if len(results) >= limit:
            break
    return results

async def press_releases(client: "httpx_type.AsyncClient", limit: int) -> List[Evidence]:
    """Parse PR Newswire RSS for Heartland Payroll announcements."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required for press release parsing")
    feed_url = (
        "https://www.prnewswire.com/rss/search/?" +
        httpx.QueryParams({"q": "\"Heartland Payroll\" (implements OR selects OR partners)"}).to_str()
    )
    resp = await fetch(client, feed_url)
    soup = BeautifulSoup(resp.text, "xml")
    results = []
    for item in soup.find_all("item"):
        title = item.title.text
        link = item.link.text
        snippet = item.description.text
        company = title.split("-")[0].strip()
        results.append(Evidence(company, "press", link, snippet))
        if len(results) >= limit:
            break
    return results

async def censys_subdomains(client: "httpx_type.AsyncClient", api_id: str, api_secret: str, limit: int) -> List[Evidence]:
    """Search Censys for subdomains of myheartlandpayroll.com."""
    url = "https://search.censys.io/api/v2/hosts/search"
    params = {"q": "services.tls.certificates.leaf_data.subject_dn: myheartlandpayroll.com", "per_page": min(limit, 100)}
    auth = (api_id, api_secret)
    resp = await client.get(url, params=params, auth=auth, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for host in data.get("result", {}).get("hits", []):
        domain = host.get("name") or host.get("ip")
        link = f"https://{domain}"
        results.append(Evidence(domain, "portal", link, "discovered via Censys"))
        if len(results) >= limit:
            break
    return results


def write_csv(path: str, items: Iterable[Evidence]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for ev in items:
            writer.writerow([ev.company_name, ev.source_type, ev.evidence_url, ev.evidence_snippet])


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heartland Payroll OSINT Harvester")
    parser.add_argument("--limit", type=int, default=50, help="Maximum results per module")
    parser.add_argument("--threads", type=int, default=5, help="Concurrent requests")
    parser.add_argument("--out", help="Output CSV path")
    parser.add_argument("--dry-run", action="store_true", help="Skip network calls")
    parser.add_argument("--job-ads", action="store_true", help="Search job ads")
    parser.add_argument("--pdfs", action="store_true", help="Scan PDFs")
    parser.add_argument("--subdomains", action="store_true", help="Discover subdomains")
    parser.add_argument("--press", action="store_true", help="Parse press releases")
    parser.add_argument("--all", action="store_true", help="Run all modules (default)")
    args = parser.parse_args(list(argv) if argv else None)
    if not any([args.job_ads, args.pdfs, args.subdomains, args.press, args.all]):
        args.all = True
    return args

async def gather_evidence(args: argparse.Namespace) -> List[Evidence]:
    items: List[Evidence] = []
    if args.dry_run:
        return items
    if httpx is None:
        raise RuntimeError("httpx is required for network operations")
    async with httpx.AsyncClient() as client:
        serp_key = os.getenv("SERPAPI_KEY")
        if (args.job_ads or args.all) and serp_key:
            try:
                items += await serpapi_job_ads(client, serp_key, args.limit)
            except Exception as exc:
                logging.error("job ads failed: %s", exc)
        if (args.pdfs or args.all) and serp_key:
            try:
                items += await search_pdfs(client, serp_key, args.limit)
            except Exception as exc:
                logging.error("pdf search failed: %s", exc)
        if (args.press or args.all):
            try:
                items += await press_releases(client, args.limit)
            except Exception as exc:
                logging.error("press releases failed: %s", exc)
        censys_id = os.getenv("CENSYS_API_ID")
        censys_secret = os.getenv("CENSYS_SECRET")
        if (args.subdomains or args.all) and censys_id and censys_secret:
            try:
                items += await censys_subdomains(client, censys_id, censys_secret, args.limit)
            except Exception as exc:
                logging.error("censys failed: %s", exc)
        return items

async def main(argv: Iterable[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    start = dt.datetime.utcnow()
    items = await gather_evidence(args)
    items = dedupe_evidence(items)
    out_path = args.out or f"heartland_leads_{start:%Y%m%d}.csv"
    write_csv(out_path, items)
    runtime = dt.datetime.utcnow() - start
    logging.info("Wrote %d records to %s in %s", len(items), out_path, runtime)

if __name__ == "__main__":
    asyncio.run(main())
