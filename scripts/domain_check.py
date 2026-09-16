#!/usr/bin/env python3
"""Stream Providers Dynamic Domain Resolver

Checks provider and extractor endpoints, verifies redirect locations,
and updates urls.json automatically.
"""

import json
import os
import sys
from urllib.parse import urlparse

try:
    from curl_cffi import requests as session
    USE_CFFI = True
except ImportError:
    import urllib.request
    import ssl
    USE_CFFI = False

# Path to urls.json
URLS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "urls.json")

# Providers and their health test endpoints
PROVIDERS = {
    "4khdhub":          {"test": "/?s=test"},
    "uhdmovies":        {"test": "/search/test"},
    "hubcloud":         {"test": "/"},
    "vcloud":           {"test": "/"},
    "driveleech":       {"test": "/"},
    "driveseed":        {"test": "/"},
    "dizipal":          {"test": "/"},
    "dizipaloriginal":  {"test": "/"},
    "hdfilmcehennemi":  {"test": "/"},
    "fullhdfilm":       {"test": "/"},
    "dizibox":          {"test": "/"},
    "sezonlukdizi":     {"test": "/"},
    "cinestream":       {"test": "/"},
    "vaplayer":         {"test": "/"},
    "vidrock":          {"test": "/"},
    "fshare":           {"test": "/"},
    "m4ufree":          {"test": "/"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_urls():
    """Read existing urls.json."""
    if os.path.exists(URLS_JSON_PATH):
        with open(URLS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_urls(data):
    """Save updated urls.json."""
    with open(URLS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def check_url_cffi(url, timeout=12):
    """Check URL with curl_cffi and return redirect destination if changed."""
    try:
        resp = session.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            impersonate="chrome120",
            verify=False,
        )
        final_url = str(resp.url)
        final_parsed = urlparse(final_url)
        original_parsed = urlparse(url)

        if resp.status_code < 400:
            if final_parsed.netloc and final_parsed.netloc != original_parsed.netloc:
                new_base = f"{final_parsed.scheme}://{final_parsed.netloc}"
                return new_base, True
            return url, False
        else:
            print(f"  [WARN] HTTP {resp.status_code} — {url}")
            return url, False
    except Exception as e:
        print(f"  [ERROR] Connection failed: {url} — {e}")
        return url, False


def check_url_fallback(url, timeout=12):
    """Fallback standard urllib check."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        final_url = resp.geturl()
        final_parsed = urlparse(final_url)
        original_parsed = urlparse(url)

        if final_parsed.netloc and final_parsed.netloc != original_parsed.netloc:
            new_base = f"{final_parsed.scheme}://{final_parsed.netloc}"
            return new_base, True
        return url, False
    except Exception as e:
        print(f"  [ERROR] Connection failed: {url} — {e}")
        return url, False


def check_url(url, timeout=12):
    if USE_CFFI:
        return check_url_cffi(url, timeout)
    return check_url_fallback(url, timeout)


def main():
    urls = load_urls()
    if not urls:
        print("[ERROR] urls.json not found or empty!")
        sys.exit(1)

    print(f"Checking {len(PROVIDERS)} providers...\n")
    changes = 0

    for provider_key, config in PROVIDERS.items():
        current_url = urls.get(provider_key)
        if not current_url:
            print(f"[SKIP] {provider_key}: not defined in urls.json")
            continue

        test_endpoint = config.get("test", "/")
        test_url = current_url.rstrip("/") + test_endpoint

        print(f"[CHECK] {provider_key}: {current_url} ...")
        new_url, changed = check_url(test_url)

        if changed:
            new_base = new_url.rstrip("/")
            print(f"  [UPDATED] Domain changed: {current_url} -> {new_base}")
            urls[provider_key] = new_base
            changes += 1
        else:
            print(f"  [OK] Active: {current_url}")

    if changes > 0:
        print(f"\n[INFO] {changes} domains updated, saving urls.json...")
        save_urls(urls)
    else:
        print("\n[OK] All domains verified, no changes.")


if __name__ == "__main__":
    main()
