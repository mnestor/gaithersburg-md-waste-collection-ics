#!/usr/bin/env python3
"""
Fetches Gaithersburg, MD waste collection data from RecycleCoach and
builds an .ics file. Designed to run as a scheduled GitHub Action so
the committed .ics file can be subscribed to via its raw.githubusercontent.com
URL, replacing RecycleCoach's now-defunct cal.recyclecoach.com feature.

Mirrors the endpoint fallback logic from the mampfes/hacs_waste_collection_schedule
project's recyclecoach_com.py source, since RecycleCoach's hosts have been
unreliable (dead hosts, TLS errors, private-IP redirects).
"""

import json
import sys
from datetime import datetime, timedelta, timezone

import requests

# --- Config: your address's identifiers ---
PROJECT_ID = "664"
DISTRICT_ID = "GAITH"
ZONE_ID = "zone-z15624"
OUTPUT_PATH = "docs/gaithersburg-waste-schedule.ics"
CAL_NAME = "Gaithersburg Trash & Recycling"
TIMEZONE_ID = "America/New_York"

SCHEDULE_URLS = [
    f"https://us-web.apigw.recyclecoach.com/zone-setup/zone/schedules?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}",
    f"https://api-city.recyclecoach.com/app_data_zone_schedules?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}",
    f"https://ca-web.apigw.recyclecoach.com/zone-setup/zone/schedules?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}",
]

COLLECTIONS_URLS = [
    f"https://us-web.apigw.recyclecoach.com/zone-setup/zone/collections?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}&lang_cd=en_US",
    f"https://api-city.recyclecoach.com/collections?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}&lang_cd=en_US",
    f"https://ca-web.apigw.recyclecoach.com/zone-setup/zone/collections?project_id={PROJECT_ID}&district_id={DISTRICT_ID}&zone_id={ZONE_ID}&lang_cd=en_US",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; waste-ics-mirror/1.0)"}


def fetch_json(urls, label):
    last_err = None
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data:
                print(f"[ok] {label} from {url}")
                return data
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            last_err = e
            print(f"[fail] {label} from {url}: {e}")
            continue
    raise RuntimeError(f"Could not fetch {label} from any known host") from last_err


def build_collection_type_map(collections_json):
    root = collections_json.get("collections") or collections_json.get("collection")
    if not root or "types" not in root:
        raise RuntimeError("Unexpected collections JSON shape")
    type_map = {}
    for key, val in root["types"].items():
        # key looks like "collection-3953"
        cid = int(key.split("-")[1])
        type_map[cid] = {
            "title": val.get("title", f"Collection {cid}"),
            "curbTime": val.get("curbTime", "07:00:00"),
        }
    return type_map


def ics_escape(text):
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def build_ics(schedule_json, type_map):
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gaithersburg Waste Schedule//RecycleCoach Mirror//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CAL_NAME}",
        f"X-WR-TIMEZONE:{TIMEZONE_ID}",
    ]

    event_count = 0
    for year_block in schedule_json["DATA"]:
        for month_block in year_block["months"]:
            for event in month_block["events"]:
                date_str = event["date"]
                date_compact = date_str.replace("-", "")
                for collection in event["collections"]:
                    if collection.get("status") == "is_none":
                        continue
                    cid = collection["id"]
                    ctype = type_map.get(cid)
                    title = ctype["title"] if ctype else f"Collection {cid}"
                    curb_time = ctype["curbTime"] if ctype else "07:00:00"
                    hh, mm, ss = curb_time.split(":")
                    dtstart_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
                        hour=int(hh), minute=int(mm), second=int(ss)
                    )
                    dtend_dt = dtstart_dt + timedelta(hours=1)
                    dtstart = dtstart_dt.strftime("%Y%m%dT%H%M%S")
                    dtend = dtend_dt.strftime("%Y%m%dT%H%M%S")
                    uid = f"{date_compact}-{cid}@gaithersburg-waste-mirror"
                    lines += [
                        "BEGIN:VEVENT",
                        f"UID:{uid}",
                        f"DTSTAMP:{now_stamp}",
                        f"DTSTART;TZID={TIMEZONE_ID}:{dtstart}",
                        f"DTEND;TZID={TIMEZONE_ID}:{dtend}",
                        f"SUMMARY:{ics_escape(title)}",
                        "END:VEVENT",
                    ]
                    event_count += 1

    lines.append("END:VCALENDAR")
    print(f"Built {event_count} events")
    return "\r\n".join(lines)


def main():
    schedule_json = fetch_json(SCHEDULE_URLS, "schedule data")
    collections_json = fetch_json(COLLECTIONS_URLS, "collection type definitions")
    type_map = build_collection_type_map(collections_json)
    ics_text = build_ics(schedule_json, type_map)

    with open(OUTPUT_PATH, "w", newline="\r\n") as f:
        f.write(ics_text)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
