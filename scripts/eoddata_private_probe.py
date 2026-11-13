"""Non-publishing, personal-use EODData connectivity check.

EODData's personal subscription does not permit public-site redistribution.
This tool never writes market data, prints an API key, or runs on scheduled scans.
For licensed public import, use import_licensed_history.py with a verified grant.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = 'https://api.eoddata.com'

def exchange_listing(api_key: str, opener=urlopen) -> object:
    if not api_key or len(api_key.strip()) < 8:
        raise ValueError('Missing EODDATA_API_KEY in the process environment')
    # The provider specifies apiKey as a query parameter. Keep URL out of error logs.
    url = BASE + '/Exchange/List?' + urlencode({'apiKey': api_key.strip()})
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Stockwatch-private-check/1.0'})
    try:
        with opener(req, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f'EODData HTTP {response.status}')
            raw = response.read(512_000)
            if len(raw) >= 512_000:
                raise RuntimeError('Provider response exceeds bounded diagnostic size')
            return json.loads(raw)
    except HTTPError as exc:
        # Never include exc, request URL, response body, headers, or API key.
        raise RuntimeError(f'EODData request failed with HTTP {exc.code}') from None
    except URLError:
        raise RuntimeError('EODData could not be reached') from None

def main() -> int:
    parser = argparse.ArgumentParser(description='Check EODData privately; does NOT import/publish quotes')
    parser.add_argument('--list-exchanges', action='store_true', help='Check metadata entitlement only')
    args = parser.parse_args()
    if not args.list_exchanges:
        parser.error('Pass --list-exchanges to explicitly authorize one API request')
    key = os.environ.get('EODDATA_API_KEY', '')
    try:
        data = exchange_listing(key)
        total = len(data) if isinstance(data, list) else 'response received'
        print(f'EODData API reachable; exchange metadata: {total}. No prices were saved or published.')
        print('PUBLIC DISPLAY DISABLED: obtain verified commercial redistribution rights first.')
        return 0
    except (ValueError, RuntimeError, json.JSONDecodeError):
        print('EODData private test failed. Confirm key, plan permissions and account status; no data was published.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
