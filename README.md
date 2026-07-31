# Gaithersburg Waste Schedule → ICS

Replaces RecycleCoach's discontinued `cal.recyclecoach.com` calendar
subscription feature. Runs weekly via GitHub Actions, pulls the current
collection schedule for `project_id=664`, `district_id=GAITH`,
`zone_id=zone-z15624` (105 Winnie Pl, Gaithersburg), and commits an
updated `.ics` file to this repo.

## Setup

1. Create a new **public** GitHub repo (must be public for the raw file
   URL to be freely subscribable without auth) and push this directory
   to it.
2. That's it — the workflow runs automatically every Monday at 08:00 UTC,
   and also on-demand via the "Run workflow" button under the Actions tab.
3. On first run, it'll create `docs/gaithersburg-waste-schedule.ics`.

## Subscribing to the calendar

Once the first run has completed, subscribe to:

```
https://raw.githubusercontent.com/<your-username>/<your-repo>/main/docs/gaithersburg-waste-schedule.ics
```

- **Apple Calendar**: File → New Calendar Subscription → paste the URL.
- **Google Calendar**: Other calendars → + → From URL → paste the URL.
- **Outlook**: Add calendar → Subscribe from web → paste the URL.

Calendar apps typically poll subscribed URLs every 12–24 hours on their
own schedule, independent of how often this Action runs.

## Notes

- If RecycleCoach changes your `project_id`/`zone_id` again (as they did
  once already), the workflow will start failing — check the Actions tab
  for the error, look up the new ID via
  `https://api-city.recyclecoach.com/city/search?term=Gaithersburg, Maryland`,
  and update the constants at the top of `build_ics.py`.
- The script tries multiple known RecycleCoach hostnames in order (matching
  the fallback logic in the `mampfes/hacs_waste_collection_schedule`
  Home Assistant integration), since their infrastructure has been
  inconsistent (dead hosts, TLS failures, internal-IP redirects).
