import argparse
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
CONTACT_HINTS = ("contact", "about", "reach", "support", "impressum")
USER_AGENT = "FindLeadsApp/1.0 (public business contact discovery)"


def search_places(query, api_key, max_results):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.nationalPhoneNumber,"
            "places.formattedAddress,places.websiteUri,places.rating,"
            "places.primaryTypeDisplayName,places.types,nextPageToken"
        ),
    }
    results = []
    page_token = None

    while len(results) < max_results:
        payload = {"textQuery": query, "pageSize": min(20, max_results - len(results))}
        if page_token:
            payload["pageToken"] = page_token

        response = requests.post(PLACES_URL, headers=headers, json=payload, timeout=30)
        if not response.ok:
            try:
                error_data = response.json().get("error", {})
            except ValueError:
                error_data = {}
            reason = next(
                (
                    detail.get("reason")
                    for detail in error_data.get("details", [])
                    if detail.get("reason")
                ),
                "",
            )
            message = error_data.get("message", response.text[:500])
            if reason == "API_KEY_INVALID":
                message = (
                    "Google rejected the API key. Check that it was copied completely, "
                    "belongs to the correct Google Cloud project, and has no extra spaces. "
                    "Enable Places API (New), attach billing, and check the key's API restrictions."
                )
            elif reason in ("SERVICE_DISABLED", "API_DISABLED"):
                message = "Places API (New) is not enabled for this key's Google Cloud project."
            elif response.status_code == 403:
                message = (
                    "Google denied this request. Check that billing is enabled and the API key "
                    "is allowed to use Places API (New)."
                )
            raise RuntimeError(f"Places API error {response.status_code}: {message}")

        data = response.json()
        results.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)

    return results[:max_results]


def email_from_website(website):
    if not website:
        return ""

    parsed = urlparse(website)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    urls = [website]
    found = set()

    for page_number in range(3):
        current_url = urls[page_number] if page_number < len(urls) else None
        if not current_url:
            break
        try:
            response = session.get(current_url, timeout=10, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException:
            continue

        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            continue

        html = response.text[:1_000_000]
        found.update(EMAIL_PATTERN.findall(html))
        if found:
            break

        soup = BeautifulSoup(html, "html.parser")
        if page_number == 0:
            for link in soup.find_all("a", href=True):
                label = " ".join((link.get_text(" ", strip=True), link["href"])).lower()
                if any(hint in label for hint in CONTACT_HINTS):
                    target = urljoin(response.url, link["href"])
                    target_parts = urlparse(target)
                    if target_parts.netloc == parsed.netloc and target not in urls:
                        urls.append(target)
            urls = urls[:3]
        time.sleep(0.25)

    return "; ".join(sorted(found))


def business_row(place, find_emails):
    display_name = place.get("displayName", {}).get("text", "")
    category = place.get("primaryTypeDisplayName", {}).get("text", "")
    if not category:
        category = ", ".join(place.get("types", [])[:3])
    website = place.get("websiteUri", "")
    email = email_from_website(website) if find_emails else ""
    return {
        "Name": display_name,
        "Phone": place.get("nationalPhoneNumber", ""),
        "Email": email,
        "Address": place.get("formattedAddress", ""),
        "Website": website,
        "Rating": place.get("rating", ""),
        "Category": category,
        "Place ID": place.get("id", ""),
    }


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Search Google Places and export business details to Excel."
    )
    parser.add_argument("query", nargs="?", help='Search phrase, e.g. "hotels in Nashik"')
    parser.add_argument("-o", "--output", default="business_leads.xlsx", help="Excel output filename")
    parser.add_argument("-n", "--limit", type=int, default=20, help="Maximum businesses (1-60)")
    parser.add_argument("--skip-emails", action="store_true", help="Do not scan business websites")
    args = parser.parse_args()

    query = args.query or input("What businesses should I search for? ").strip()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        parser.error("Set GOOGLE_MAPS_API_KEY in a .env file or your environment.")
    if not query:
        parser.error("A search phrase is required.")
    if not 1 <= args.limit <= 60:
        parser.error("--limit must be between 1 and 60.")

    try:
        places = search_places(query, api_key, args.limit)
        print(f"Found {len(places)} businesses. Preparing export...")
        rows = []
        for index, place in enumerate(places, start=1):
            name = place.get("displayName", {}).get("text", "(unnamed business)")
            print(f"[{index}/{len(places)}] {name}")
            try:
                rows.append(business_row(place, find_emails=not args.skip_emails))
            except (requests.RequestException, ValueError) as error:
                print(f"  Website lookup skipped: {error}", file=sys.stderr)

        columns = ["Name", "Phone", "Email", "Address", "Website", "Rating", "Category", "Place ID"]
        pd.DataFrame(rows, columns=columns).to_excel(args.output, index=False)
        print(f"Saved {len(rows)} rows to {args.output}")
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print(f"Search failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())