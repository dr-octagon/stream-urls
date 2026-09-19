#!/usr/bin/env python3
"""Stream Providers Dynamic Domain Resolver

Checks provider and extractor endpoints, verifies redirect locations,
and updates urls.json automatically.
"""

import json
import os
import re
import sys
from urllib.parse import urlparse, urljoin

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


def probe_numeric_domain(url):
    """If a numeric pattern domain like dizipal1581.com is dead or not redirecting,
    probe +1, +2, +3 to detect active successors.
    """
    m = re.match(r"^(https?://(?:www\.)?[a-zA-Z]+)(\d+)(\.[a-z]+)$", url)
    if not m:
        return None
    prefix, num_str, suffix = m.groups()
    base_num = int(num_str)
    for offset in range(1, 4):
        test_url = f"{prefix}{base_num + offset}{suffix}"
        try:
            if USE_CFFI:
                resp = session.get(
                    test_url,
                    headers=HEADERS,
                    timeout=5,
                    allow_redirects=False,
                    impersonate="chrome120",
                    verify=False,
                )
                status = resp.status_code
                loc = resp.headers.get("location") or resp.headers.get("Location")
            else:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(test_url, headers=HEADERS)
                resp = urllib.request.urlopen(req, timeout=5, context=ctx)
                status = resp.getcode()
                loc = resp.headers.get("location")
            if status < 500 or loc:
                print(f"  [PROBE SUCCESS] Found active successor: {test_url} (HTTP {status})")
                return test_url
        except Exception:
            continue
    return None


def check_url_cffi(url, timeout=8):
    """Check URL with curl_cffi and return redirect destination if changed.
    Uses step-by-step redirect tracking without blind follow so that 301/302
    redirects are captured even when destination servers block datacenter IPs (Cloudflare 403).
    """
    cur = url
    changed = False

    for _ in range(5):
        try:
            resp = session.get(
                cur,
                headers=HEADERS,
                timeout=timeout,
                allow_redirects=False,
                impersonate="chrome120",
                verify=False,
            )
            loc = resp.headers.get("location") or resp.headers.get("Location")
            if resp.status_code in (301, 302, 303, 307, 308) and loc:
                target = urljoin(cur, loc)
                target_parsed = urlparse(target)
                cur_parsed = urlparse(cur)
                if target_parsed.netloc and target_parsed.netloc != cur_parsed.netloc:
                    new_base = f"{target_parsed.scheme}://{target_parsed.netloc}"
                    print(f"  [REDIRECT] {cur} -> {new_base} (HTTP {resp.status_code})")
                    cur = new_base
                    changed = True
                    continue
                else:
                    cur = target
                    continue

            if changed:
                return cur, True
            return url, False
        except Exception as e:
            if changed:
                return cur, True
            print(f"  [WARN] Request to {cur} failed: {e}")
            break

    if not changed:
        probed = probe_numeric_domain(url)
        if probed:
            return probed, True

    return (cur, True) if changed else (url, False)


def check_url_fallback(url, timeout=8):
    """Fallback standard urllib check with redirect tracking and probing."""
    cur = url
    changed = False

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(NoRedirectHandler)

    for _ in range(5):
        try:
            req = urllib.request.Request(cur, headers=HEADERS)
            resp = opener.open(req, timeout=timeout)
            if changed:
                return cur, True
            return url, False
        except urllib.error.HTTPError as e:
            loc = e.headers.get("location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                target = urljoin(cur, loc)
                target_parsed = urlparse(target)
                cur_parsed = urlparse(cur)
                if target_parsed.netloc and target_parsed.netloc != cur_parsed.netloc:
                    new_base = f"{target_parsed.scheme}://{target_parsed.netloc}"
                    print(f"  [REDIRECT] {cur} -> {new_base} (HTTP {e.code})")
                    cur = new_base
                    changed = True
                    continue
                else:
                    cur = target
                    continue
            if changed:
                return cur, True
            break
        except Exception as e:
            if changed:
                return cur, True
            break

    if not changed:
        probed = probe_numeric_domain(url)
        if probed:
            return probed, True

    return (cur, True) if changed else (url, False)


def check_url(url, timeout=8):
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
