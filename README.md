# PTMSCRAPER

PTMSCRAPER is a lightweight scraper used to collect records from the Heartland web portal. The primary entrypoint is `heartland_harvester.py`, which pulls data using the credentials and settings defined in environment variables.

## Usage

The script can be executed directly from the command line. Below are examples of common invocations:

```bash
python heartland_harvester.py --limit 100 --dry-run
python heartland_harvester.py --limit 50 --output records.json
```

## Required environment variables

- `HEARTLAND_USERNAME` – account username used to authenticate with the service.
- `HEARTLAND_PASSWORD` – corresponding password for the account.
- `HEARTLAND_API_URL` – base URL of the Heartland API endpoint.

Ensure these variables are set in your environment before running the script.