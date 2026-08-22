# GlobeTrotter

Trip planning app - built for Odoo hackathon (virtual round).

## Screens included
- Login / Register
- Landing page
- Create Trip
- Build Itinerary (sections with budget)
- Itinerary View (day wise activities + expense)
- My Trips (ongoing / upcoming / completed)
- Profile

## Setup

```
pip install -r requirements.txt
python app.py
```

Runs on http://127.0.0.1:5000

DB file (globetrotter.db) gets auto created on first run, no manual setup needed.

## Notes
- SQLite is used, no external DB server needed
- Auth is basic session based, not production grade, fine for hackathon demo
- Admin panel, community tab, calendar view, search page are not built yet - can add if time permits
