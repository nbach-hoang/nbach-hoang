"""Create the first cards from a downloaded public GitHub contribution page.

Usage: python scripts/from_public_html.py contributions.html
The scheduled workflow uses the authenticated GraphQL builder instead.
"""

import datetime as dt
from html.parser import HTMLParser
import re
import sys
from pathlib import Path

from build_profile import LEVELS, ROOT, THEMES, render


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = []
        self.pending = None
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs and "data-level" in attrs:
            self.pending = {"date": attrs["data-date"], "level": int(attrs["data-level"])}
        elif tag == "tool-tip" and self.pending is not None:
            self.tooltip = []

    def handle_data(self, data):
        if self.tooltip is not None:
            self.tooltip.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tooltip is not None:
            label = " ".join(self.tooltip)
            found = re.search(r"([\d,]+) contributions?", label)
            self.pending["count"] = int(found.group(1).replace(",", "")) if found else 0
            self.days.append(self.pending)
            self.pending = self.tooltip = None


def main(path):
    parser = CalendarParser()
    parser.feed(Path(path).read_text(encoding="utf-8"))
    if len(parser.days) < 350:
        raise ValueError(f"Only {len(parser.days)} contribution days found")
    by_date = {day["date"]: day for day in parser.days}
    dates = sorted(by_date)
    weeks = []
    start = dt.date.fromisoformat(dates[0])
    end = dt.date.fromisoformat(dates[-1])
    for offset in range(0, (end - start).days + 1, 7):
        week = []
        for weekday in range(7):
            date = start + dt.timedelta(days=offset + weekday)
            item = by_date.get(date.isoformat())
            if item:
                week.append({"date": item["date"], "weekday": (date.weekday() + 1) % 7,
                             "contributionCount": item["count"],
                             "contributionLevel": next(k for k, v in LEVELS.items() if v == item["level"])})
        if week:
            weeks.append({"contributionDays": week})
    calendar = {"totalContributions": sum(day["count"] for day in parser.days), "weeks": weeks}
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme in THEMES:
        (assets / f"profile-{theme}.svg").write_text(render(calendar, theme), encoding="utf-8")
    print(f'Generated {calendar["totalContributions"]} public contributions from {dates[0]} to {dates[-1]}')


if __name__ == "__main__":
    main(sys.argv[1])
