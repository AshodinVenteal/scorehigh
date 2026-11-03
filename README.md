# matchplay-score-tournament

Support code for a 90s-style card format pinball tournament, where a card includes your entire score on each pinball table you play (times a multiplier to balance different machines against each other).

## Run locally

Requires Python 3.14 and uv:

```sh
uv sync --group dev
uv run flask --app matchplay_score.web run --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765/ranking/281672 for the test tournament.
Pages fetch real scores from the public Match Play API; no API key is required.
Tournament names and IDs are configured in `src/matchplay_score/web.py`.
`TOURNAMENT_MATCHPLAY_URLS` holds placeholder event links for the prominent
Match Play buttons on the tournament desk and in tournament headers. Replace
these with URLs from tournament records when database integration is added.

## Frontend

The interface uses Flask/Jinja, local CSS, and vanilla JavaScript. No Node build
or frontend framework is needed. The framed panels, restrained era colors,
compact navigation tabs, and system fonts use a Windows 95/2000 aesthetic.
`windows.css` holds the visual treatment over the shared responsive layout.
ScoreHigh is a working display name.

- Standings show complete, unrounded totals and searchable player names.
- Each card expands into raw machine scores, multipliers, and adjusted points.
- Player pages include card history; invalid cards remain visible but do not
  become the best valid card or affect the existing ranking calculation.
- Machine pages show configured machines belonging to the selected tournament.
- How it works has a separate page with calculated game/card examples and
  an example showing why a higher-scoring invalid card is excluded.
- Tournament icons are selected from event-themed emoji using the tournament
  ID as a random seed. They remain consistent across visits and exports;
  listed tournaments avoid duplicate icons while the emoji pool allows it.
- Auto-refresh runs every 60 seconds while the page is visible. It preserves
  the search and expanded cards, skips focused card controls, and keeps the
  previous scores visible if a request fails. The API's existing cache can add
  up to 60 seconds of latency. Refresh can be paused.
- The Display menu has two independent settings. Website style offers Classic
  Windows and 2000s Portal (MSN/Yahoo-style columns, GameTrailers-era steel
  section bars, and subtle trans flag blue/pink accents).
  Color mode offers System, Light, and Dark for either style. System follows
  device appearance changes; style, color, and refresh preferences are saved
  on the device. Classic Windows is the initial style.
- Navigation and card breakdowns work without JavaScript; refresh and search
  controls are shown only when JavaScript is available.

Run checks with `uv run pytest`. Existing API integration tests need network
access; `uv run pytest tests/test_web.py tests/test_arenas.py` runs offline.

For browser checks, start the local server, then run
`uv run --with playwright python tools/check_ui.py`. This requires an installed
Playwright Chromium browser and saves mobile/desktop screenshots in `.preview/`.

## GitHub Pages

Public site: https://ashodinventeal.github.io/scorehigh/

The Pages workflow builds a complete static score snapshot from Match Play
on pushes, manual dispatch, and a five-minute schedule. GitHub may delay
scheduled runs. Snapshot times are shown explicitly; the browser checks for
new published snapshots every 60 seconds when Auto is enabled. GitHub Pages
does not run Flask, and Match Play's CORS policy prevents direct browser API
requests from the Pages domain. No credentials or third-party proxy are used.

Build locally with:

```sh
uv run python -m matchplay_score.export --output _site --base-path /scorehigh
```

The Vercel entrypoint is retained for anyone running the live Flask backend.

Original scoring code: Elia Lake / arborelia. Copyright and terms are retained
in `LICENSE.txt`. Portal visual reference:
[GameTrailers, 2004](https://www.webdesignmuseum.org/gallery/gametrailers-in-2004).

