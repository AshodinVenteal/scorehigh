from datetime import datetime, timezone
from hashlib import sha256

import requests
from flask import Flask, abort, render_template
from .ranking import best_cards, player_cards
from .matchplay_api import get_tournament_data_cached
from .tournament import MAX_PER_ERA, parse_tournament

app = Flask(__name__)
TOURNAMENT_INFO = {281672: "Test Tournament"}


@app.context_processor
def site_context():
    return {"tournaments": TOURNAMENT_INFO, "max_per_era": MAX_PER_ERA,
            "static_snapshot": bool(app.config.get("SNAPSHOT_AT"))}


def score_timestamp():
    return app.config.get("SNAPSHOT_AT") or datetime.now(timezone.utc).isoformat()


def tournament_title(tournament_id):
    return TOURNAMENT_INFO.get(tournament_id, f"Tournament {tournament_id}")


@app.template_filter("commafy")
def commafy(value: int) -> str:
    "Apply thousands separator to integers"
    return "{:,d}".format(value)


@app.template_filter("card_key")
def card_key(card) -> str:
    return sha256(repr(card).encode("utf-8")).hexdigest()[:16]


@app.route("/ranking/<int:tournament_id>")
def render_ranking(tournament_id: int):
    cards = best_cards(tournament_id, use_cache=True)
    title = tournament_title(tournament_id)
    return render_template(
        "ranking.html", cards=cards, title=title, tournament_id=tournament_id,
        updated_at=score_timestamp(), active_tab="standings",
    )


@app.route("/player/<int:tournament_id>/<path:player_name>")
def render_player(tournament_id: int, player_name: str):
    cards = player_cards(tournament_id, player_name)
    if not cards and "_" in player_name:
        player_name = player_name.replace("_", " ")
        cards = player_cards(tournament_id, player_name)
    if not cards:
        abort(404)
    valid_cards = [card for card in cards if card.is_valid()]
    standings = best_cards(tournament_id, use_cache=True)
    rank = next((i for i, card in enumerate(standings, 1)
                 if card.player_name == player_name), None)
    return render_template(
        "player.html", cards=cards, player_name=player_name,
        best_card=valid_cards[0] if valid_cards else None, rank=rank,
        title=tournament_title(tournament_id), tournament_id=tournament_id,
        updated_at=score_timestamp(), active_tab="standings",
    )


@app.route("/machines/<int:tournament_id>")
def render_machines(tournament_id: int):
    tournament = parse_tournament(get_tournament_data_cached(tournament_id))
    return render_template(
        "machines.html", arenas=tournament.arenas_by_id.values(),
        title=tournament_title(tournament_id), tournament_id=tournament_id,
        active_tab="machines",
    )


@app.errorhandler(requests.RequestException)
def upstream_error(error):
    return render_template("error.html", title="Scores unavailable",
                           message="We couldn't reach Match Play. Please try again in a moment."), 503


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", title="Page not found",
                           message="This player or page couldn't be found. Choose a tournament to continue."), 404


@app.route("/")
def index():
    return render_template("index.html", tournaments=TOURNAMENT_INFO)
