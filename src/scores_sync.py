#!/usr/bin/env python3
"""Season freshness sync - the missing automation from audit 2026-09-20 (M1).

src/collections_data.py SEASON is hand-edited prose about the latest/next game.
It goes stale the moment a game kicks off. This script - run by refresh.yml
BEFORE the build, inside GitHub Actions where the network exists - pulls the
final score of each team's most recent completed game and the kickoff of the
next one from ESPN's public scoreboard API, and writes data/season_override.json.
build.py applies that file over SEASON when present; on any failure the file is
left untouched and the hand-edited values stand (fail-open by design).

Field paths are read defensively throughout: an API shape change must never
crash the refresh or write a wrong score - it degrades to the hand-edited copy.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "season_override.json")

TEAMS = {
    "nfl": {
        "cleveland-browns": {"abbr": "CLE", "city": "Cleveland", "name": "Browns"},
        "green-bay-packers": {"abbr": "GB", "city": "Green Bay", "name": "Packers"},
        "dallas-cowboys": {"abbr": "DAL", "city": "Dallas", "name": "Cowboys"},
    },
    "college-football": {
        "michigan": {"abbr": "MICH", "city": "Michigan", "name": "Wolverines"},
    },
}


def fetch(league, yyyymmdd=None):
    url = (f"https://site.api.espn.com/apis/site/v2/sports/football/{league}/scoreboard")
    if yyyymmdd:
        url += f"?dates={yyyymmdd}"
    req = urllib.request.Request(url, headers={"User-Agent": "gridironlocker-season-sync/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def team_game(data, abbr):
    """(finished_game, next_event) for one team abbreviation, defensively."""
    finished, upcoming = None, None
    for ev in data.get("events", []) or []:
        comp = (ev.get("competitions") or [{}])[0]
        competitors = comp.get("competitors") or []
        mine = [c for c in competitors if (c.get("team") or {}).get("abbreviation") == abbr]
        if not mine:
            continue
        me = mine[0]
        status = (ev.get("status") or {}).get("type") or {}
        row = {
            "kickoff": ev.get("date"),
            "completed": bool(status.get("completed")),
            "detail": status.get("detail") or "",
            "my_score": me.get("score"),
            "opp": (([c for c in competitors if c is not me] or [{}])[0].get("team") or {}),
            "opp_score": (([c for c in competitors if c is not me] or [{}])[0].get("score")),
            "home_away": me.get("homeAway") or "",
        }
        if row["completed"] and finished is None:
            finished = row
        elif not row["completed"] and upcoming is None:
            upcoming = row
    return finished, upcoming


def outcome_words(home_away):
    return "at" if home_away == "away" else "vs"


def main():
    overrides = {}
    for league, teams in TEAMS.items():
        try:
            data = fetch(league)
        except Exception as e:
            print(f"scores_sync: {league} fetch failed ({e}); keeping hand-edited season")
            continue
        for ckey, t in teams.items():
            finished, upcoming = team_game(data, t["abbr"])
            ov = {}
            if finished and finished["my_score"] is not None:
                try:
                    mine, theirs = int(finished["my_score"]), int(finished["opp_score"])
                except (TypeError, ValueError):
                    mine = theirs = None
                if mine is not None:
                    opp_name = finished["opp"].get("displayName") or "the opponent"
                    preposition = outcome_words(finished["home_away"])
                    if mine > theirs:
                        ov["headline"] = f"{t['city']} beat {opp_name} {mine}-{theirs}."
                        ov["result"] = (f"{t['city']} beat {opp_name} {mine}-{theirs} "
                                        f"({finished['detail']}).")
                    elif mine < theirs:
                        ov["headline"] = f"{t['city']} lost {mine}-{theirs} {preposition} {opp_name}."
                        ov["result"] = (f"{t['city']} lost {mine}-{theirs} {preposition} "
                                        f"{opp_name} ({finished['detail']}).")
                    else:
                        ov["headline"] = f"{t['city']} tied {opp_name} {mine}-{theirs}."
                        ov["result"] = f"{t['city']} tied {opp_name} {mine}-{theirs}."
            if upcoming and upcoming.get("kickoff"):
                ov["kickoff"] = upcoming["kickoff"]
                opp_name = upcoming["opp"].get("displayName") or "their next opponent"
                preposition = outcome_words(upcoming["home_away"])
                verb = "hosts" if preposition == "vs" else "travels to"
                ov["status"] = f"{t['city']} {verb} {opp_name} next."
            if ov:
                overrides[ckey] = ov
    if not overrides:
        print("scores_sync: nothing to write; keeping hand-edited season")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_doc": "Written by src/scores_sync.py from ESPN public scoreboards. "
                           "Applied over src/collections_data.py SEASON by build.py. "
                           "Delete to fall back to the hand-edited values.",
                   "overrides": overrides}, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    print(f"scores_sync: wrote {len(overrides)} team override(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
