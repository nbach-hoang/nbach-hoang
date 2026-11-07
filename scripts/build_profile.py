#!/usr/bin/env python3
"""Build an animated, isometric contribution skyline for a GitHub profile."""

import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

THEMES = {
    "dark": dict(bg="#0b0e14", border="#26303c", text="#e6edf3", muted="#98a6b6",
                 accent="#67e8f9", base="#17222e", colors=["#1d2b39", "#155e75", "#0e7490", "#06b6d4", "#a5f3fc"]),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#57606a",
                  accent="#0e7490", base="#e7eef3", colors=["#dce7ed", "#a5f3fc", "#22d3ee", "#0891b2", "#155e75"]),
}
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    payload = json.dumps({"query": QUERY, "variables": {"login": PROFILE["username"]}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "nbach-hoang-profile-animation"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"]))
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def points(coords):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)


def shade(hex_color, factor):
    parts = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(v * factor):02x}" for v in parts)


def render(calendar, theme):
    color = THEMES[theme]
    days = [(week_index, day["weekday"], day["contributionCount"],
             LEVELS[day["contributionLevel"]], day["date"])
            for week_index, week in enumerate(calendar["weeks"])
            for day in week["contributionDays"]]
    if not days:
        raise ValueError("GitHub returned an empty contribution calendar")
    weeks = len(calendar["weeks"])
    peak = max(day[2] for day in days) or 1
    width, height = 850, 480
    x_start, y_start = 38, 327
    ux, uy, vx, vy = (width - 98) / weeks, 1.8, 7.2, 5.4

    def place(w, d, h=0):
        return (x_start + w * ux + d * vx, y_start - w * uy + d * vy - h)

    def height_for(count):
        return 0 if not count else 5 + 78 * math.sqrt(count / peak)

    parts = []
    top = [place(-.4, -.4), place(weeks + .4, -.4),
           place(weeks + .4, 7.4), place(-.4, 7.4)]
    parts.append(f'<polygon points="{points(top)}" fill="{color["base"]}"/>')
    front_edge = [place(-.4, 7.4), place(weeks + .4, 7.4),
                  place(weeks + .4, 7.4, -7), place(-.4, 7.4, -7)]
    parts.append(f'<polygon points="{points(front_edge)}" fill="{shade(color["base"], .78)}"/>')
    for week, weekday, _, _, _ in days:
        a, b = week + .12, week + .88
        c, d = weekday + .12, weekday + .88
        tile = [place(a, c), place(b, c), place(b, d), place(a, d)]
        parts.append(f'<polygon points="{points(tile)}" fill="{color["colors"][0]}"/>')

    for week, weekday, count, level, _ in sorted(days, key=lambda day: (day[1], -day[0])):
        if not count:
            continue
        a, b = week + .12, week + .88
        c, d = weekday + .12, weekday + .88
        h = height_for(count)
        base = color["colors"][max(1, level)]
        faces = [
            ([place(a, c), place(b, c), place(b, d), place(a, d)],
             [place(a, c, h), place(b, c, h), place(b, d, h), place(a, d, h)], base),
            ([place(a, d), place(b, d), place(b, d), place(a, d)],
             [place(a, d), place(b, d), place(b, d, h), place(a, d, h)], shade(base, .64)),
            ([place(b, c), place(b, d), place(b, d), place(b, c)],
             [place(b, c), place(b, d), place(b, d, h), place(b, c, h)], shade(base, .78)),
        ]
        delay = 400 + week * 25 + weekday * 15
        for flat, raised, fill in faces:
            parts.append(
                f'<polygon points="{points(raised)}" fill="{fill}">'
                f'<animate attributeName="points" values="{points(flat)};{points(flat)};{points(raised)}" '
                f'keyTimes="0;{delay / (delay + 650):.3f};1" dur="{(delay + 650) / 1000:.2f}s" '
                'calcMode="spline" keySplines="0 0 1 1;.2 .8 .3 1" fill="freeze"/>'
                '</polygon>'
            )

    name = html.escape(PROFILE["name"])
    handle = html.escape(PROFILE["username"])
    tagline = html.escape(PROFILE["tagline"])
    about = PROFILE["about"]
    text = [f'<text class="over" x="34" y="43" fill="{color["muted"]}">@{handle}</text>',
            f'<text class="name" x="34" y="82" fill="{color["text"]}">{name.upper()}</text>',
            f'<text class="tag" x="34" y="108" fill="{color["accent"]}">{tagline}</text>']
    for index, line in enumerate(about):
        text.append(f'<text class="about" x="34" y="{140 + index * 23}" fill="{color["muted"]}">'
                    f'◆  {html.escape(line)}</text>')
    text.append(f'<text class="count" x="34" y="218" fill="{color["text"]}">'
                f'{calendar["totalContributions"]:,}'
                f'<tspan class="detail" fill="{color["muted"]}" dx="9">contributions in the last year</tspan></text>')
    first = dt.date.fromisoformat(days[0][4]).strftime("%b %Y")
    last = dt.date.fromisoformat(days[-1][4]).strftime("%b %Y")
    text += [f'<text class="detail" x="38" y="444" fill="{color["muted"]}">{first}</text>',
             f'<text class="detail" x="816" y="444" text-anchor="end" fill="{color["muted"]}">{last}</text>']
    label = html.escape(f'{PROFILE["name"]}: {calendar["totalContributions"]} GitHub contributions in the last year, {first} to {last}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">\n'
            f'<title>{name} — GitHub contribution skyline</title>\n'
            '<style>text{font-family:Arial,Helvetica,sans-serif}.over{font-size:12px;letter-spacing:.08em}'
            '.name{font-size:30px;font-weight:800;letter-spacing:.04em}.tag{font-size:15px;font-weight:600}'
            '.about{font-size:13px}.count{font-size:25px;font-weight:700}.detail{font-size:12px;font-weight:400}'
            'text{opacity:0;animation:appear .6s ease-out forwards}@keyframes appear{to{opacity:1}}'
            '@media(prefers-reduced-motion:reduce){text{animation:none;opacity:1}}</style>\n'
            f'<rect x=".5" y=".5" width="849" height="479" rx="14" fill="{color["bg"]}" '
            f'stroke="{color["border"]}"/>\n'
            + '\n'.join(parts + text) + '\n</svg>\n')


def main():
    calendar = fetch_calendar()
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme in THEMES:
        (assets / f"profile-{theme}.svg").write_text(render(calendar, theme), encoding="utf-8")
    print(f'Generated {calendar["totalContributions"]} contributions for @{PROFILE["username"]}')


if __name__ == "__main__":
    main()
