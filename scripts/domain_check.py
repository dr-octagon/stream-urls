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
    "sinewix": {
        "test": "/public/api/genres/latestmovies/all/9iQNC5HQwPlaFuJDkhncJ5XTJ8feGXOJatAA",
        "headers": {
            "hash256": "711bff4afeb47f07ab08a0b07e85d3835e739295e8a6361db77eebd93d96306b",
            "signature": "3082058830820370a00302010202145bbfbba9791db758ad12295636e094ab4b07dc24300d06092a864886f70d01010b05003074310b3009060355040613025553311330110603550408130a43616c69666f726e6961311630140603550407130d4d6f756e7461696e205669657731143012060355040a130b476f6f676c6520496e632e3110300e060355040b1307416e64726f69643110300e06035504031307416e64726f69643020170d3231313231353232303433335a180f32303531313231353232303433335a3074310b3009060355040613025553311330110603550408130a43616c69666f726e6961311630140603550407130d4d6f756e7461696e205669657731143012060355040a130b476f6f676c6520496e632e3110300e060355040b1307416e64726f69643110300e06035504031307416e64726f696430820222300d06092a864886f70d01010105000382020f003082020a0282020100a5106a24bb3f9c0aaf3a2b228f794b5eaf1757ba758b19736a39d1bdc73fc983a7237b8d5ca5156cfa999c1dab3418bbc2be0920e0ee001c8aa4812d1dae75d080f09e91e0abda83ff9a76e8384a4429f4849248069a59505b12ac2c14ba2e4d1a13afcdaf54e508697ff928a9f738e6f4a6fc27409c55329eb149b5ff89c5a2d7c06bf9e62086f955cad17d7be2623ee9d5ec56068eadc23cb0965a13ff97d49fe10ef41afc6eeca36b4ace9582097faff89f590bc831cdb3a69eec5d15b67c3f2cad49e37ed053733e3d2d400c47755b932bdbe15d749fd6ad1dce30ba5e66094dfb6ee6f64cafb807e11b19a990c5d078c6d6701cda0bdeb21e99404ff166074f4c89b04c418f4e7940db5c78647c475bcfb85d4c4e836ee7d7c1d53e9e736b5d96d4b4d8b98209064b729ac6a682d55a6a930e518d849898bb28329ca0aaa133b5e5270a9d5940cac6af4802a57fd971efda91abb602882dd6aa6ce2b236b57b52ee2481498f0cacbcc2c36c238bc84becad7eaaf1125b9a1ca9ded6c79f3f283a52050377809b2a9995d66e1636b0ed426fdd8685c47cb18e82077f4aefcc07887e1dc58b4d64be1632f0e7b4625da6f40c65a8512a6454a4b96963e7f876136e6c0069a519a79ad632078ed965aa12482458060c030ed50db706d854f88cb004630b49285d8af8b471ff8f6070687826412287b50049bcb7d1b6b62ef90203010001a310300e300c0603551d13040530030101ff300d06092a864886f70d01010b0500038202010051c0b7bd793181dc29ca777d3773f928a366c8469ecf2fa3cfb076e8831970d19bb2b96e44e8ccc647cf0696bb824ac61c23d958525d283cab26037b04d58aa79bf92192db843adf5c26a980f081d2f0e14f759fc5ff4c5bb3dce0860299bfe7b349a8155a2efaf731ba25ce796a80c1442c7bf80f8c1a7912ff0b6f6592264315337251a846460194fa594f81f38f9e5233a63201e931ad9cab5bf119f24025613f307194eaa6eb39a83f3c05a49ba34455b1aff7c6839bbb657d9392ffdf397432af6e56ba9534a8b07d7060fe09691c6cf07cb5324f67b3cc0871a8c621d81fe71d71085c55206a4f57e25f774fd4b979b299e8bb076b50fca42fa57da2d519fd35a4a7c0137babaed4345f8031b63b6a71f5e8268f709d658ccd7c2a58849379d25bfa598c3f4a2c3d9b7d89285fefeb7f0ec65137d38b08ce432a15688b624a179e6a4a505ebc3bcdfbc4d4330508ee2d8d0f016924dcec21a6838ef7d834c6f43bde4a5201ed0b3bb4e9bd377b470e36bcf5bc3d56169dbd8e39567aa7dce4d1a8a8a54a5e1aa6fb1a8aab0062669a966f96e15ccce6fe12ea5e6a8b8c8823bdc94988ca39759fd1cc8fd8ae5c3d74db50b174cf7d77655016c075c91d439ed01cc0a9f695c99fad3b5495fb6cb1e01a5fa020cc6022a85c07ec55f9eba89719f86e49d34ab5bd208c5f70cced2b7b7963c014f8404432979b506de29e",
            "User-Agent": "EasyPlex (Android 14; SM-A546B; Samsung Galaxy A54 5G; tr)",
            "Accept": "application/json"
        }
    },
    "fullhdfilmizlesene": {"test": "/arama/gladiator"},
    "tvdiziler":          {"test": "/search?qr=medcezir"},
    "dizimom":            {"test": "/?s=test"},
    "cinejoy":            {"test": "/"},
    "cinejoy_api":        {"test": "/servers"},
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


def check_url_cffi(url, custom_headers=None, timeout=8):
    """Check URL with curl_cffi and return redirect destination if changed.
    Uses step-by-step redirect tracking without blind follow so that 301/302
    redirects are captured even when destination servers block datacenter IPs (Cloudflare 403).
    """
    req_headers = {**HEADERS, **(custom_headers or {})}
    cur = url
    changed = False

    for _ in range(5):
        try:
            resp = session.get(
                cur,
                headers=req_headers,
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


def check_url_fallback(url, custom_headers=None, timeout=8):
    """Fallback standard urllib check with redirect tracking and probing."""
    req_headers = {**HEADERS, **(custom_headers or {})}
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
            req = urllib.request.Request(cur, headers=req_headers)
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


def check_url(url, custom_headers=None, timeout=8):
    if USE_CFFI:
        return check_url_cffi(url, custom_headers, timeout)
    return check_url_fallback(url, custom_headers, timeout)


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
        custom_headers = config.get("headers")
        new_url, changed = check_url(test_url, custom_headers=custom_headers)

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
