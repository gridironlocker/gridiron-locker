#!/usr/bin/env python3
"""Hunter intelligence — the layer underneath ops/hq.

The old HQ turned every Google News headline into a "TRENDING" card and told the
operator to "post your Browns shirt with angle: <headline>". That is a headline,
not demand. One published story is not a trend, and a trend without a product and
a commercial intent is not something to post.

This module defines the ladder the board reports against:

    HEADLINE    something was published                       (filtered out)
    SIGNAL      fans/coverage are reacting - volume + sources
    TREND       that reaction is accelerating
    OPPORTUNITY trend + a design that matches + commercial intent
    ACTION      opportunity we should post now (confidence + timing)

Only SIGNAL and above reach the board. HEADLINE is counted and named as filtered,
never shown as an opportunity.

Evidence comes from three files only, and nothing is invented:

    data/trends.json            headlines, entity_mentions, fan_trend_index
    marketing/social-signals.json   reddit / google_news / x (if configured)
    data/products_live.json     commercial match pool (+ data/catalogue-live.json
                                marks which of those designs are actually sellable)

When a fan connector is not configured (X_BEARER_TOKEN missing, Reddit 403) the
evidence grid says so instead of pretending a disconnected platform was observed.
That cap is also reflected in the confidence score, so a headline-only signal can
never score its way onto the action list.

Import-safe: stdlib only, no network, no writes. src/hq.py renders the payload
returned by hunt_opportunities().
"""
from __future__ import annotations

import datetime as dt
import email.utils
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # season context is data, not a hard dependency: the hunt still runs without it
    from collections_data import COLLECTIONS as _COLLECTIONS, NEXT_GAME as _NEXT_GAME, SEASON as _SEASON
except Exception:  # pragma: no cover - defensive, keeps ops dashboards alive
    _COLLECTIONS, _NEXT_GAME, _SEASON = {}, {}, {}

# ------------------------------------------------------------------ the ladder
LEVELS = ("HEADLINE", "SIGNAL", "TREND", "OPPORTUNITY", "ACTION")
LEVEL_RANK = {name: i for i, name in enumerate(LEVELS)}
SHOWN_FROM = "SIGNAL"          # everything below this is filtered off the board
ACTION_MIN = 75                # confidence floor for ACTION
OPPORTUNITY_MIN = 60           # confidence floor for OPPORTUNITY
SIGNAL_MIN_ITEMS = 3           # >= 3 reaction items from >= 2 sources = a reaction
SIGNAL_MIN_SOURCES = 2         # one outlet repeating itself is still one headline
SIGNAL_MIN_WEIGHT = 3.0        # weighted demand floor - utility copy cannot buy one
TREND_MIN_VELOCITY = 25.0      # %/window acceleration that upgrades SIGNAL -> TREND
TREND_MIN_FAN_POSTS = 5        # ...or this many real fan posts in the window
STALE_HOURS = 24               # newest evidence older than this -> 🔴 STALE
MAX_ARTICLES = 9               # 3 per opportunity, capped

# Confidence weights (they sum to 100 so the number on the card is a real share).
WEIGHTS = {
    "volume": 16,          # how much demand the topic actually has
    "sources": 10,         # how many independent outlets
    "fan_reaction": 18,    # real fan posts (capped hard when no fan connector)
    "recency": 18,         # age of the newest evidence - the board answers "right now"
    "velocity": 14,        # is it accelerating
    "sentiment": 8,        # is there an emotion to sell into
    "game_state": 8,       # is there a posting window
    "commercial": 8,       # do we own a design that matches
}
# What a topic scores with no fan connector attached. The cap is the honest part:
# without X/Reddit we are reading journalism, not fans, so fan_reaction can never
# carry a headline-only topic into ACTION.
FAN_REACTION_CAPPED = 6

VELOCITY_WINDOWS = (60, 240, 1440)   # minutes, finest first

# ---------------------------------------------------------------- team brains
# Four separate brains. Same shape, different language, different players,
# different culture, different commercial hooks and different posting playbook.
# `topics` are the things fans actually demand product for; `patterns` are what
# that topic looks like in a headline or a fan post.
TEAM_BRAINS = {
    "cleveland-browns": {
        "label": "Cleveland Browns",
        "short": "BROWNS",
        "nick": "Dawg Pound",
        "subreddits": ["r/Browns", "r/DawgPoundByNature", "r/nfl"],
        "quora": "Cleveland Browns / NFL fandom",
        "medium": "NFL fan culture (Dawg Pound / Cleveland sports)",
        "voice": ("Browns fans do not need convincing, they need backup. Speak like the "
                  "Dawg Pound: short, defiant, a little gallows humour, never corporate. "
                  "Defence and identity sell; QB debates get argued, not bought."),
        "sentiment": {
            "defiant": ["counted out", "counting", "count them out", "prove them wrong",
                        "they forgot", "forgot who i am", "nobody believes", "underdog",
                        "under dawgs", "doubt", "disrespect", "us against", "haters",
                        "make them know", "believe"],
            "anxious": ["watson", "interception", "intercepts", "turnover", "injury",
                        "surgery", "ir", "bench", "struggle", "rebuild", "concern",
                        "worried", "questions", "why are the browns", "controversy",
                        "impact draft", "trade suitor"],
            "hype": ["touchdown", "pick six", "sack", "win", "beats", "stuns", "upset",
                     "dominant", "clutch", "record", "breakout", "milestone", "pay off"],
            "proud": ["dawg pound", "dawg life", "cleveland", "ohio", "est 1946", "1946",
                      "here we go", "orange and brown", "factory", "loyal", "family"],
        },
        "players": {
            "deshaun watson": {"patterns": ["deshaun watson", "watson"], "jersey": "", "note": "veteran starter, most-covered name in the window"},
            "shedeur sanders": {"patterns": ["shedeur sanders", "shedeur", "qb 12", "qb12"], "jersey": "12", "note": "rookie QB, the belief design"},
            "denzel ward": {"patterns": ["denzel ward", "denzel", "no fly zone"], "jersey": "21", "note": "shutdown corner, No Fly Zone"},
            "myles garrett": {"patterns": ["myles garrett", "garrett"], "jersey": "95", "note": "edge rusher - legacy designs retired"},
            "todd monken": {"patterns": ["todd monken", "monken"], "jersey": "", "note": "first season as HC"},
            "joe flacco": {"patterns": ["joe flacco", "flacco"], "jersey": "15", "note": "legacy design, retired"},
        },
        "topics": [
            {
                "key": "qb-room",
                "title": "QB room: who is QB1 in Cleveland",
                "kind": "player",
                "patterns": ["deshaun watson", "watson", "shedeur", "sanders", "qb",
                             "quarterback", "4 qb", "4 qbs", "flacco", "starting"],
                "why": "The whole fanbase is arguing one question: who starts. That is a "
                       "belief argument, and belief is what a QB tee sells.",
                "commercial": ["sanders", "they forgot who i am", "qb 12", "qb12", "12",
                               "next level", "second act", "make them know"],
                "campaign": "THEY FORGOT WHO I AM — QB1 belief",
                "angle": "Post the belief, not the debate: 'QB1 wears 12' with the Sanders "
                         "design. Never take a side on Watson - that thread eats the post.",
            },
            {
                "key": "no-fly-zone",
                "title": "No Fly Zone: the secondary wins the argument",
                "kind": "moment",
                "patterns": ["no fly zone", "denzel", "denzel ward", "interception",
                             "intercepts", "pick six", "pass breakup", "cornerback",
                             "secondary", "the wall", "three-and-out"],
                "why": "Every live pick or three-and-out turns straight into defence pride "
                       "in the Dawg Pound replies.",
                "commercial": ["no fly zone", "denzel", "the wall", "rock out"],
                "campaign": "NO FLY ZONE — Denzel Ward 21",
                "angle": "Clip the moment, caption it 'No Fly Zone', link the Denzel design "
                         "in the first reply. Defence posts out-reach QB posts every week.",
            },
            {
                "key": "dawg-pound",
                "title": "Dawg Pound identity: orange, brown and 1946",
                "kind": "culture",
                "patterns": ["dawg pound", "dawg life", "dawgs", "here we go brownies",
                             "est 1946", "orange and brown", "new era", "north coast",
                             "factory of sadness"],
                "why": "Evergreen identity demand - the fans who buy because it says "
                       "Cleveland, not because of a player.",
                "commercial": ["dawg", "cle", "cleveland", "1946", "ohio", "go browns", "dwag"],
                "campaign": "DAWG POUND IDENTITY — CLE since 1946",
                "angle": "Identity post: skyline + 'EST 1946'. Works on any day, sells on "
                         "gameday, and never dates.",
            },
            {
                "key": "prove-them-wrong",
                "title": "Counted out: the prove-them-wrong window",
                "kind": "phrase",
                "patterns": ["counted out", "counting", "count them out", "underdog",
                             "under dawgs", "prove them wrong", "they forgot", "nobody",
                             "doubt", "disrespect", "why are the browns", "watchability"],
                "why": "National media writing Cleveland off is the single highest-"
                       "converting emotion in this fanbase.",
                "commercial": ["playoffs", "all we want", "all we got", "make them know",
                               "they forgot"],
                "campaign": "PROVE THEM WRONG",
                "angle": "Quote the dismissive take, answer with the design. 'They're "
                         "counting Cleveland out' → PLAYOFFS tee. Do not argue the record.",
            },
            {
                "key": "gameday-cleveland",
                "title": "Gameday in Cleveland: kickoff to final",
                "kind": "moment",
                "context": True,
                "patterns": ["how to watch", "live updates", "inactives", "kickoff",
                             "opening drive", "touchdown", "field goal", "1st quarter",
                             "halftime", "final", "jaguars", "week 1", "stream",
                             "tv channel", "odds", "predictions"],
                "why": "Watch-party traffic peaks 90 minutes before kickoff and again at "
                       "halftime - the two windows a gameday post actually lands.",
                "commercial": ["sundays", "sunday", "let it rip", "go browns", "gameday"],
                "campaign": "SUNDAYS IN CLEVELAND",
                "angle": "Two posts, not one: pre-kickoff 'where you watching from' and a "
                         "halftime reaction. Product goes in the reply, never the opener.",
            },
            {
                "key": "coach-room",
                "title": "Coaching: Monken's first season",
                "kind": "player",
                "patterns": ["monken", "todd monken", "stefanski", "coach", "captains",
                             "offensive coordinator", "staff"],
                "why": "New-coach hope and captain announcements are low-volume but very "
                       "shareable inside the fanbase.",
                "commercial": ["coach", "this girl loves", "she love coach", "dawg"],
                "campaign": "COACH LOYALTY",
                "angle": "Captain names and sideline moments, framed as 'this is our coach "
                         "now'. Skip the schematic takes - fans do not buy those.",
            },
        ],
        "platforms": [
            {"key": "x", "label": "X (@gridironlocker1 first)", "play": "conversation post now",
             "when": "now", "detail": "Fan-voice account leads. Question, not a pitch."},
            {"key": "threads", "label": "Threads", "play": "alternate angle", "when": "+20 min",
             "detail": "Same moment, different cut - never the same caption twice."},
            {"key": "instagram", "label": "Instagram", "play": "product creative after engagement confirms the angle",
             "when": "gate", "detail": "Only once the X post has real replies. Story + feed."},
            {"key": "pinterest", "label": "Pinterest", "play": "keyword pin of the matched design",
             "when": "+2 h", "detail": "Evergreen - it outlives the game."},
        ],
    },

    "green-bay-packers": {
        "label": "Green Bay Packers",
        "short": "PACKERS",
        "nick": "Cheesehead Nation",
        "subreddits": ["r/GreenBayPackers", "r/nfl"],
        "quora": "Green Bay Packers / NFC North",
        "medium": "Packers fan culture (Cheesehead Nation)",
        "voice": ("Packers fans are owners, not customers - they talk in decades, not "
                  "takes. Lead with Love and Lambeau, treat roster news as bookkeeping, "
                  "and never punch down at the division."),
        "sentiment": {
            "optimistic": ["love", "jacobs", "kraft", "extension", "pack is back",
                           "future", "dynasty", "elite", "beat", "win", "rise", "bold"],
            "anxious": ["suspension", "suspends", "injury", "injuries", "ir", "miss",
                        "missing", "release", "released", "practice squad", "roster move",
                        "contract", "holdout", "questions", "struggle", "torches",
                        "shut out", "concern"],
            "hype": ["touchdown", "pick", "sack", "stuns", "dominant", "clutch",
                     "breakout", "milestone", "feat", "record"],
            "proud": ["cheesehead", "lambeau", "titletown", "1919", "green bay wisconsin",
                      "tundra", "packers packers", "property of", "civic institution",
                      "dynasty"],
        },
        "players": {
            "jordan love": {"patterns": ["jordan love", "love", "no. 10", "number 10"], "jersey": "10", "note": "franchise QB, biggest design cluster"},
            "josh jacobs": {"patterns": ["josh jacobs", "jacobs"], "jersey": "8", "note": "run game, suspension watch"},
            "tucker kraft": {"patterns": ["tucker kraft", "kraft"], "jersey": "85", "note": "fresh 4-year extension"},
            "micah parsons": {"patterns": ["micah parsons", "parsons"], "jersey": "1", "note": "now in Green Bay"},
            "matt lafleur": {"patterns": ["matt lafleur", "lafleur"], "jersey": "", "note": "HC"},
            "bo melton": {"patterns": ["bo melton", "melton"], "jersey": "", "note": "practice squad churn"},
        },
        "topics": [
            {
                "key": "love-era",
                "title": "Jordan Love era: 10 is the number",
                "kind": "player",
                "patterns": ["jordan love", "10ve", "no. 10", "qb1", "starting qb",
                             "what would jordan"],
                "why": "Love is the only Packers name with a design cluster behind it - "
                       "when he is in the news, the shelf matches the moment.",
                "commercial": ["jordan love", "love 10", "10ve", "what would jordan",
                               "jordan freaking love", "all you need is", "love"],
                "campaign": "WHAT WOULD JORDAN DO — Love 10",
                "angle": "Love highlight → 'WDJD' caption. The retro What Would Jordan Do "
                         "design carries the joke; the Love 10 jersey-back carries the fan.",
            },
            {
                "key": "jacobs-run",
                "title": "Josh Jacobs and the run game",
                "kind": "player",
                "patterns": ["josh jacobs", "jacobs", "running back", "run game",
                             "suspension", "suspends", "miss games", "carry", "touches"],
                "why": "Jacobs is the most-mentioned Packer in the window and every mention "
                       "is about availability - that is a nervous fan, and nervous fans buy "
                       "identity, not player tees.",
                "commercial": ["go pack go", "packers", "green bay", "cheesehead",
                               "pack is back"],
                "campaign": "GO PACK GO — identity over one back",
                "angle": "Do not print a Jacobs shirt on suspension news. Post the "
                       "identity design with a 'the run game is deeper than one name' line.",
            },
            {
                "key": "kraft-extension",
                "title": "Kraft extension: the front office pays its own",
                "kind": "moment",
                "patterns": ["tucker kraft", "kraft", "extension", "4-year", "75m",
                             "agrees to", "contract extension"],
                "why": "An extension signed the week of the opener is the one roster story "
                       "Packers fans treat as good news - it is a 'we are building' moment, "
                       "not bookkeeping.",
                "commercial": ["pack is back", "go pack go", "packers", "green bay",
                               "future is green"],
                "campaign": "PACK IS BACK / THE FUTURE IS GREEN",
                "angle": "One post: the number, the years, and 'the future is green'. "
                         "No player tee exists for Kraft - sell the identity, not the name.",
            },
            {
                "key": "cheesehead-nation",
                "title": "Cheesehead Nation: Lambeau and the tundra",
                "kind": "culture",
                "patterns": ["cheesehead", "lambeau", "frozen tundra", "tundra",
                             "titletown", "1919", "green bay wisconsin", "wisconsin",
                             "dynasty", "civic institution", "packers packers",
                             "property of green bay"],
                "why": "The culture topic is the one that sells 52 weeks a year, and it is "
                       "the only Packers angle with mugs and hoodies behind it.",
                "commercial": ["cheese", "wisconsin", "green bay", "packers", "1919",
                               "home", "property of"],
                "campaign": "CHEESEHEAD NATION — Sundays are better here",
                "angle": "Lambeau photo + 'Sundays are better in Cheesehead Nation'. "
                         "Cheese-heart tee and mug are the natural attach.",
            },
            {
                "key": "nfc-north",
                "title": "NFC North week: Vikings, Lions, Bears",
                "kind": "moment",
                "context": True,
                "patterns": ["nfc north", "vikings", "lions", "bears", "division",
                             "standings", "jefferson"],
                "why": "Division weeks drive the loudest fan traffic of the season and the "
                       "cheapest reach.",
                "commercial": ["green bay vs everyone", "packers", "green bay football"],
                "campaign": "GREEN BAY VS EVERYONE",
                "angle": "Division-week banter post using Green Bay Vs Everyone. Keep it "
                         "light - the rivalry sells, the insult does not.",
            },
            {
                "key": "roster-room",
                "title": "Roster moves, releases and injuries",
                "kind": "moment",
                "context": True,
                "patterns": ["extension", "contract", "signs", "sign", "release",
                             "released", "practice squad", "roster move", "roster moves",
                             "injury report", "injuries", "ir", "kraft", "melton",
                             "hiestand", "waiver"],
                "why": "Low emotion, high volume. It tells you what the fanbase is reading "
                       "but it is not a product moment on its own.",
                "commercial": ["packers", "green bay", "go pack go"],
                "campaign": "PACK IS BACK — depth-chart pride",
                "angle": "News-adjacent only. One post that names the move and pivots to "
                       "the Pack Is Back design; no carousel, no product push.",
            },
            {
                "key": "gameday-packers",
                "title": "Gameday: Lambeau kickoff windows",
                "kind": "moment",
                "context": True,
                "patterns": ["how to watch", "what channel", "live blog", "stream",
                             "kickoff", "inactives", "week 1", "odds", "predictions",
                             "picks", "radio", "tv"],
                "why": "Watch-party and stream questions spike 2 hours before kickoff - "
                       "the highest-intent Packers traffic of the week.",
                "commercial": ["sunday funday", "sunday", "go pack go", "packers"],
                "campaign": "SUNDAY FUNDAY — Green Bay",
                "angle": "Sunday Funday design + 'where are you watching from'. Post at "
                         "kickoff minus 30, again at halftime.",
            },
        ],
        "platforms": [
            {"key": "x", "label": "X (@gridironlocker1 first)", "play": "conversation post now",
             "when": "now", "detail": "Fan-voice account. Owners-talk, not hot takes."},
            {"key": "threads", "label": "Threads", "play": "alternate angle", "when": "+20 min",
             "detail": "Culture cut of the same moment."},
            {"key": "instagram", "label": "Instagram", "play": "product creative after engagement confirms the angle",
             "when": "gate", "detail": "Cheese/Lambeau visual. Story first, feed if it lands."},
            {"key": "pinterest", "label": "Pinterest", "play": "keyword pin of the matched design",
             "when": "+2 h", "detail": "'green bay shirt' / 'cheesehead gift' keywords."},
        ],
    },

    "dallas-cowboys": {
        "label": "Dallas Cowboys",
        "short": "COWBOYS",
        "nick": "America's Team faithful",
        "subreddits": ["r/cowboys", "r/Dallas_Cowboys", "r/nfl"],
        "quora": "Dallas Cowboys / NFC East",
        "medium": "Cowboys fan culture (Texas football)",
        "voice": ("Cowboys fans live in a permanent argument between the star on the helmet "
                  "and 30 years without a ring. Texas pride sells; the drought joke sells "
                  "only when we tell it, never when we repeat it back at them."),
        "sentiment": {
            "hopeful": ["confidence", "new culture", "debut", "smile is back", "update",
                        "lands", "opening", "favorite", "win", "beat", "storylines",
                        "milestone", "key stats"],
            "skeptical": ["sorrow", "worst moments", "last super bowl", "30 years",
                          "drought", "injury", "ir", "surgery", "hip", "trade rumor",
                          "filling in", "questions", "struggle", "loyalty", "valuing"],
            "hype": ["touchdown", "pick", "sack", "prime time", "sunday night", "snf",
                     "debut", "breakout", "record", "milestone"],
            "proud": ["texas", "dallas", "america's team", "star", "est 1841", "1841",
                      "flag", "longhorn", "cowboys nation", "how 'bout them cowboys",
                      "superfan", "legend"],
        },
        "players": {
            "dak prescott": {"patterns": ["dak prescott", "dak", "prescott"], "jersey": "4", "note": "QB1"},
            "ceedee lamb": {"patterns": ["ceedee lamb", "ceedee", "lamb"], "jersey": "88", "note": "WR1"},
            "george pickens": {"patterns": ["george pickens", "pickens"], "jersey": "", "note": "new weapon, news-driven"},
            "micah parsons": {"patterns": ["micah parsons", "parsons"], "jersey": "11", "note": "Doomsday memory - he is in Green Bay now"},
            "tyler smith": {"patterns": ["tyler smith", "t.j. bass", "bass"], "jersey": "73", "note": "line injury watch"},
            "malik davis": {"patterns": ["malik davis", "davis"], "jersey": "", "note": "hip surgery / IR"},
            "von miller": {"patterns": ["von miller", "miller"], "jersey": "40", "note": "veteran debut"},
        },
        "topics": [
            {
                "key": "snf-opener",
                "title": "Sunday night at the Giants: prime-time opener",
                "kind": "moment",
                "patterns": ["sunday night", "snf", "prime time", "primetime", "giants",
                             "tonight", "opener", "season opener", "debut", "week 1"],
                "why": "A prime-time opener is the biggest single traffic window of the "
                       "Cowboys week, and it has a fixed clock to post against.",
                "commercial": ["dallas football", "star", "dallas", "cowboys", "texas"],
                "campaign": "STAR POWER — Sunday night in Dallas",
                "angle": "Kickoff minus 30 post ('who's got the TV'), halftime reaction, "
                         "final-word post. Texas-pride tee is the visual, not the pitch.",
            },
            {
                "key": "texas-pride",
                "title": "Texas pride: flag, star and Est. 1841",
                "kind": "culture",
                "women": True,
                "patterns": ["texas", "flag", "est 1841", "1841", "longhorn",
                             "america's team", "cowboys nation", "famous", "celebrity",
                             "superfan", "cheerleaders", "fan loyalty", "star power"],
                "why": "Identity demand that does not care about the score - and the "
                       "women's cut is the one design line this collection actually has.",
                "commercial": ["texas pride", "dallas flag", "flag", "this girl loves",
                               "est 1841", "longhorn", "vintage texas", "dallas"],
                "campaign": "VINTAGE TEXAS PRIDE",
                "angle": "Flag + star creative with the women's 'This Girl Loves Cowboys' "
                         "cut called out explicitly. Gifting copy, not gameday copy.",
            },
            {
                "key": "doomsday",
                "title": "Doomsday memory: defence and the pass rush",
                "kind": "phrase",
                "patterns": ["doomsday", "defence", "defense", "pass rush", "sack",
                             "parsons", "von miller", "miller", "edge", "porter",
                             "trade rumor", "joey porter", "steelers"],
                "why": "Dallas defence talk always drifts to the Doomsday era - the one "
                       "defensive identity we own a design for.",
                "commercial": ["doomsday", "defense", "skull", "helmet"],
                "campaign": "DOOMSDAY DEFENSE",
                "angle": "Pass-rush moment → Doomsday Defense tee. Retro framing beats "
                         "current-roster framing here; Parsons is not ours to sell.",
            },
            {
                "key": "thirty-years",
                "title": "Thirty years: the drought joke we own",
                "kind": "phrase",
                "patterns": ["30 years", "thirty years", "last super bowl", "sorrow",
                             "drought", "worst moments", "championship", "super bowl",
                             "since 1995", "1995", "heartbreak"],
                "why": "The highest-engagement Cowboys topic on the internet is the drought "
                       "- and vintage designs are the only honest way to sell into it.",
                "commercial": ["vintage", "1960", "helmet", "texas", "country", "flag"],
                "campaign": "VINTAGE GLORY — 1960 helmet, 1995 ring",
                "angle": "Nostalgia post: 1960 helmet design with 'we remember what this "
                         "felt like'. Never punch the fan about the drought - join them.",
            },
            {
                "key": "roster-room-dallas",
                "title": "Roster: injuries, IR and the depth chart",
                "kind": "moment",
                "context": True,
                "patterns": ["injury", "ir", "surgery", "hip", "malik davis", "davis",
                             "tyler smith", "t.j. bass", "bass", "practice squad",
                             "signs", "signed", "pickens", "update", "inactives"],
                "why": "Volume without emotion. Useful as proof the fanbase is reading, "
                       "not as a post of its own.",
                "commercial": ["dallas", "football", "texas"],
                "campaign": "DALLAS FOOTBALL — depth-chart pride",
                "angle": "Single news-adjacent post, vintage Dallas football design, no "
                         "product push. Never monetise an injury directly.",
            },
            {
                "key": "nfc-east",
                "title": "NFC East week: Giants, Eagles, Commanders",
                "kind": "moment",
                "context": True,
                "patterns": ["nfc east", "giants", "eagles", "commanders", "division",
                             "standings", "rival", "rivalry"],
                "why": "Division weeks are the Cowboys' loudest traffic and the easiest "
                       "reach of the season.",
                "commercial": ["dallas football", "dallas", "star", "texas"],
                "campaign": "AMERICA'S TEAM — NFC East",
                "angle": "Rivalry-week banter with the star-and-lightning vintage design. "
                         "Light touch, no player names.",
            },
        ],
        "platforms": [
            {"key": "x", "label": "X (@gridironlocker1 first)", "play": "conversation post now",
             "when": "now", "detail": "Fan voice leads. Prime time = the whole night."},
            {"key": "threads", "label": "Threads", "play": "alternate angle", "when": "+20 min",
             "detail": "Texas-pride cut while the game is still live."},
            {"key": "instagram", "label": "Instagram", "play": "product creative after engagement confirms the angle",
             "when": "gate", "detail": "Flag/star creative. Women's cut if pride angle wins."},
            {"key": "pinterest", "label": "Pinterest", "play": "keyword pin of the matched design",
             "when": "+2 h", "detail": "'dallas football shirt' / 'texas pride tee'."},
        ],
    },

    "michigan": {
        "label": "Michigan Wolverines",
        "short": "MICHIGAN",
        "nick": "Go Blue faithful",
        "subreddits": ["r/MichiganWolverines", "r/CFB", "r/collegefootball"],
        "quora": "Michigan football / college football recruiting",
        "medium": "Michigan football culture (Ann Arbor)",
        "voice": ("Michigan fans talk in eras and standards, not weeks. Underwood is the "
                  "present, the Hail Mary is the folklore, and 'respond' is the house "
                  "motto. Recruiting news is treated as programme news, not gossip."),
        "sentiment": {
            "defiant": ["respond", "nothing given", "earned", "revenge", "everybody",
                        "vs everybody", "v everybody", "haters", "calls out", "doubt",
                        "work in progress", "character", "statement win", "us against"],
            "pride": ["go blue", "legacy", "big house", "ann arbor", "maize", "history",
                      "championship", "michigan michigan", "the m", "wolverines",
                      "program", "tradition"],
            "hype": ["stuns", "upset", "hail mary", "late-game", "heroics", "one second",
                     "shocker", "rises", "top 25", "coaches poll", "ap poll", "power",
                     "major win", "bounce-back", "breakout", "feat"],
            "anxious": ["injury", "offense", "offensive", "find footing", "struggle",
                       "clock controversy", "questions", "clean up", "relies on defense",
                       "concern", "drops", "loss", "portal"],
        },
        "players": {
            "bryce underwood": {"patterns": ["bryce underwood", "underwood", "qb19", "qb 19"], "jersey": "19", "note": "the era - biggest design cluster"},
            "kyle whittingham": {"patterns": ["kyle whittingham", "whittingham"], "jersey": "", "note": "first season, statement win"},
            "jj mccarthy": {"patterns": ["jj mccarthy", "mccarthy"], "jersey": "", "note": "legacy designs retired"},
            "jordan marshall": {"patterns": ["jordan marshall", "marshall"], "jersey": "", "note": "backfield"},
        },
        "topics": [
            {
                "key": "underwood-era",
                "title": "Underwood era: QB19 in Ann Arbor",
                "kind": "player",
                "patterns": ["bryce underwood", "underwood", "qb19", "qb 19",
                             "true freshman", "pff grade", "backs underwood", "quarterback"],
                "why": "Every Michigan story right now routes through Underwood - the "
                       "grade, the coach backing him, and what the era means next.",
                "commercial": ["bryce 19", "qb19", "second act", "qb 19", "19"],
                "campaign": "SECOND ACT QB19",
                "angle": "Grade/stat line → 'QB19' creative. Bryce 19 for the believer, "
                         "Second Act QB19 for the story. Recruiting news = same designs.",
            },
            {
                "key": "recruiting",
                "title": "Recruiting: the class built around QB19",
                "kind": "phrase",
                "patterns": ["recruiting", "recruit", "recruits", "five-star", "commit",
                             "commits", "flip", "transfer portal", "offer", "class of",
                             "signing day", "target"],
                "why": "Michigan fans treat recruiting as programme news. It is the one "
                       "demand that runs all year, including the weeks with no game.",
                "commercial": ["qb19", "bryce 19", "second act", "legacy", "go blue"],
                "campaign": "SECOND ACT — the class behind QB19",
                "angle": "Commit/offer news with the QB19 or Legacy design. Frame it as "
                         "'what they are building', never as a rumour post.",
            },
            {
                "key": "hail-mary",
                "title": "Late-game heroics: the Hail Mary folklore",
                "kind": "moment",
                "patterns": ["hail mary", "hail", "late-game", "heroics", "one second",
                             "last second", "final play", "clock controversy", "walkoff",
                             "stuns", "shocker", "miracle", "drama", "avoid massive upset"],
                "why": "The Hail Mary win is the story Michigan fans keep re-telling - and "
                       "we own the only design named after it.",
                "commercial": ["h a i l", "hail", "mary", "one second"],
                "campaign": "H.A.I.L. MARY — one second left",
                "angle": "Re-tell the moment (not the player): 'one second' creative. "
                         "This is the Michigan design that sells to neutral fans too.",
            },
            {
                "key": "respond",
                "title": "Respond: nothing given, everything earned",
                "kind": "phrase",
                "patterns": ["respond", "nothing given", "earned", "revenge", "bounce-back",
                             "statement", "character", "work in progress", "haters",
                             "calls out", "proves", "silence", "narrative"],
                "why": "This is the programme's own language and it is in the headlines "
                       "verbatim after the Oklahoma win - the highest-intent phrase in the "
                       "Michigan catalogue.",
                "commercial": ["respond", "nothing given", "earned", "revenge tour",
                               "legacy", "maize out"],
                "campaign": "RESPOND — Nothing Given, Everything Earned",
                "angle": "Quote the headline's own word ('respond'), pair the Revenge Tour "
                         "or Respond design. Works for wins and for losses - rare.",
            },
            {
                "key": "go-blue",
                "title": "Go Blue: The Big House identity",
                "kind": "culture",
                "patterns": ["go blue", "maize", "big house", "ann arbor", "wolverines",
                             "the m", "michigan michigan", "m vs", "m-vs", "everybody",
                             "tradition", "1919", "bet m"],
                "why": "The evergreen identity buy - Michigan fans gift Go Blue apparel "
                       "year round, and it does not depend on a result.",
                "commercial": ["go blue", "maize", "michigan", "m vs", "everybody", "bet m"],
                "campaign": "M VS EVERYBODY — Go Blue",
                "angle": "Big House crowd shot + 'M vs Everybody'. Gifting angle, not "
                         "gameday angle - it converts outside the season too.",
            },
            {
                "key": "rankings-risers",
                "title": "Rankings week: polls, upsets and the top 25",
                "kind": "moment",
                "context": True,
                "patterns": ["rankings", "top 25", "coaches poll", "ap poll", "power",
                             "rises", "falls", "poll", "no. 11", "no. 1", "projected",
                             "takeaways", "week 3"],
                "why": "Poll movement is the weekly scoreboard Michigan fans argue about - "
                       "cheap reach, low product intent.",
                "commercial": ["michigan", "go blue", "maize", "legacy"],
                "campaign": "MAIZE OUT — risers only",
                "angle": "One post with the number and the Maize Out design. No carousel, "
                         "no player names - poll posts date in four days.",
            },
            {
                "key": "gameday-michigan",
                "title": "Gameday: kickoff, TV and the watch party",
                "kind": "moment",
                "context": True,
                "patterns": ["how to watch", "what channel", "where to watch", "stream",
                             "tv schedule", "kickoff", "time", "today", "week 2", "week 3",
                             "game recap", "postgame"],
                "why": "Saturday watch-party traffic - the only college window with a fixed "
                       "posting clock in the week.",
                "commercial": ["go blue", "maize out", "michigan", "one second"],
                "campaign": "GO BLUE — Saturday in Ann Arbor",
                "angle": "Kickoff minus 30 and a postgame word. Product only in the "
                         "reply thread.",
            },
        ],
        "platforms": [
            {"key": "x", "label": "X (@gridironlocker1 first)", "play": "conversation post now",
             "when": "now", "detail": "Fan voice. Recruiting + result talk lives here."},
            {"key": "threads", "label": "Threads", "play": "alternate angle", "when": "+20 min",
             "detail": "Culture cut: Go Blue / Big House, not the box score."},
            {"key": "instagram", "label": "Instagram", "play": "product creative after engagement confirms the angle",
             "when": "gate", "detail": "QB19 or Hail Mary creative once X confirms."},
            {"key": "pinterest", "label": "Pinterest", "play": "keyword pin of the matched design",
             "when": "+2 h", "detail": "'bryce underwood shirt' / 'go blue gift'."},
        ],
    },
}

FALLBACK_BRAIN = {
    "label": "Gridiron Locker", "short": "TEAM", "nick": "the fanbase",
    "subreddits": ["r/nfl"], "quora": "football fandom", "medium": "football fan culture",
    "voice": "Neutral fan voice.", "sentiment": {}, "players": {}, "topics": [],
    "platforms": [{"key": "x", "label": "X", "play": "conversation post now", "when": "now",
                   "detail": ""}],
}


# --------------------------------------------------------------- data loading
def _read_json(rel, default=None):
    """Read a repo JSON file, returning `default` instead of raising.

    ops dashboards are generated inside the storefront build; a missing or
    half-written data file must degrade the board, not break the build.
    """
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def load_trends():
    return _read_json("data/trends.json", {}) or {}


def load_signals():
    return _read_json("marketing/social-signals.json", {}) or {}


def load_products():
    """Commercial match pool: the live crawl, as the board reports against.

    data/products_live.json is the crawl artefact (no collection field, and it
    includes designs that are no longer sellable). data/catalogue-live.json is
    the authoritative sellable list written by the storefront. We match against
    the union and mark each candidate `sellable`, so the board can show a real
    buy link for designs that still exist and label the rest as crawl artefacts
    instead of quietly recommending a dead campaign.
    """
    pool = {}
    for slug, row in (_read_json("data/products_live.json", {}) or {}).items():
        if not isinstance(row, dict):
            continue
        pool[slug] = {
            "slug": slug,
            "title": row.get("title") or slug.replace("-", " ").title(),
            "price_usd": row.get("price_usd"),
            "url": row.get("url") or "",
            "desc": row.get("desc") or "",
            "art": "",
            "collection": "",
            "sellable": False,
            "buy_url": "",
        }
    cat = _read_json("data/catalogue-live.json", {}) or {}
    for row in cat.get("products", []) or []:
        if not isinstance(row, dict) or not row.get("slug"):
            continue
        slug = row["slug"]
        entry = pool.get(slug) or {"slug": slug, "desc": "", "art": "", "url": row.get("url") or ""}
        entry.update({
            "slug": slug,
            "title": row.get("name") or entry.get("title") or slug,
            "price_usd": row.get("price_usd", entry.get("price_usd")),
            "url": entry.get("url") or row.get("url") or "",
            "collection": row.get("collection") or entry.get("collection") or "",
            "sellable": True,
            "buy_url": row.get("buy_url") or row.get("url") or "",
        })
        pool[slug] = entry
    # Printed artwork and human-verified keywords are the best matching text we
    # have - "NO FLY ZONE" on the garment matches a fan demand no title ever will.
    try:
        from catalog import CATALOG  # noqa: PLC0415 - src/ is on sys.path
    except Exception:
        CATALOG = {}
    for slug, entry in pool.items():
        facts = CATALOG.get(slug) or {}
        art = facts.get("art") or ""
        kws = facts.get("kw") or []
        entry["art"] = art
        entry["keywords"] = [k for k in kws if isinstance(k, str)]
        entry["haystack"] = _norm(" ".join([
            str(entry.get("title") or ""), art, str(entry.get("desc") or ""),
            " ".join(entry["keywords"]), slug.replace("-", " "),
        ]))
        if not entry.get("collection"):
            entry["collection"] = _guess_team(entry["haystack"])
    return pool


# ------------------------------------------------------------------- text bits
_STOP = set("""the a an and or of for to in on at is are was were be been with from by
as it its this that these those we our you your they their he she his her i not no
yes vs versus what when where why how who whom which will would can could should may
might must do does did doing have has had having more most other some such than then
there here after before into over under out up down off again about all any both each
few only own same so too very s t just don now also get got gets getting""".split())


def _norm(text):
    """Lowercase, collapse whitespace, keep apostrophes and hyphens that carry meaning."""
    text = (text or "").lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u2013", "-").replace("\u2014", " - ").replace("\u2026", " ")
    return re.sub(r"\s+", " ", text).strip()


def _words(text):
    return [w for w in re.split(r"[^a-z0-9']+", _norm(text)) if w and w not in _STOP]


def _pattern(pattern):
    """Compile a phrase pattern with boundaries only where they make sense."""
    esc = re.escape(pattern)
    left = r"\b" if re.match(r"[a-z0-9]", pattern) else ""
    right = r"\b" if re.match(r"[a-z0-9]", pattern[-1]) else ""
    return re.compile(left + esc + right)


_PAT_CACHE = {}


def _matches(pattern, text):
    rx = _PAT_CACHE.get(pattern)
    if rx is None:
        rx = _PAT_CACHE[pattern] = _pattern(pattern)
    return bool(rx.search(text))


def _any(patterns, text):
    return any(_matches(p, text) for p in patterns if p)


# Team and place names sit in the sentiment lexicons because fans say them, but
# they carry no emotion: "Dallas" in a headline is not excitement. Only the words
# that actually name a feeling get to pick the signal line.
_IDENTITY_WORDS = frozenset("""dallas cleveland texas michigan ohio green bay packers
cowboys browns wisconsin star flag love maize go blue wolverines lambeau 1919 1841
ann arbor the m big house legacy cheesehead titletown dawg pound est 1946 north coast
orange and brown factory cleveland ohio ohio cle dawgs 10ve""".split())


def _emotion_patterns(brain):
    lex = (brain or {}).get("sentiment") or {}
    return [p for pats in lex.values() for p in pats if p not in _IDENTITY_WORDS]


# Google News titles arrive as "Headline text - Publisher". The publisher is the
# only real outlet name we get (the link is a Google redirect), and counting
# outlets is what separates "one story" from "everyone is covering this".
_OUTLET_REJECT = frozenset("""with after the for from and on in as at how why what watch
live photos inside big mailbag column update updates notes recap postgame sources
nfl network 10 5 3 things things-to-watch""".split())


def _outlet(raw, source, metrics=None):
    """Split a real publisher name off the end of a headline, if there is one."""
    metrics = metrics or {}
    if source == "reddit":
        sub = metrics.get("subreddit")
        if sub:
            return "r/" + str(sub)
    if source in ("x", "twitter"):
        return "x"
    text = str(raw or "")
    if " - " in text:
        head, _, tail = text.rpartition(" - ")
        tail = tail.strip()
        if tail and head.strip() and len(tail) <= 44 and len(tail.split()) <= 6:
            first = tail.split()[0].lower().strip(".,:;'\"()[]")
            if first and first not in _OUTLET_REJECT and not first.isdigit():
                return tail
    return source or "unknown"


# Guess a team for crawl-only designs that are not in the sellable catalogue.
_TEAM_HINTS = (
    ("cleveland-browns", ["browns", "cleveland", "dawg", "dwag", "cle ", " ohio", "denzel", "sanders", "flacco", "monken"]),
    ("green-bay-packers", ["packers", "green bay", "greenbay", "grb", "cheesehead", "lambeau", "wisconsin", "jordan love"]),
    ("dallas-cowboys", ["cowboys", "dallas", "texas", "doomsday", "longhorn", "dak"]),
    ("michigan", ["michigan", "go blue", "wolverines", "maize", "ann arbor", "underwood", "hail mary"]),
)


def _guess_team(haystack):
    for team, hints in _TEAM_HINTS:
        if _any(hints, haystack):
            return team
    return ""


# ------------------------------------------------------- what counts as demand
# Not every item is evidence of fan demand. "What channel is the game on" tells us
# people are searching; it is not a reaction, and treating it as one is exactly how
# the old board turned a TV listing into "TRENDING - post your Browns shirt".
# So every item is graded, and the grade is what the confidence is built from:
#
#   fan      a real fan post (reddit/x/facebook, when a connector is attached)
#   moment   something that happened - a pick, an upset, a postgame, a stat line
#   news     roster/injury/contract/coaching journalism about the team
#   utility  how-to-watch, TV schedule, odds and picks: search intent, not demand
_UTILITY_WORDS = ["how to watch", "what channel", "where to watch", "what time",
                  "tv channel", "live stream", "stream", "radio", "odds", "picks",
                  "prediction", "predictions", "betting", "spread", "schedule",
                  "fantasy", "how & where", "time, tv"]
_MOMENT_WORDS = ["intercepts", "interception", "touchdown", "sack", "final", "beats",
                 "wins", "win ", "upset", "stuns", "heroics", "postgame", "game recap",
                 "rises in", "coaches poll", "ap poll", "top 25", "pff grade",
                 "opening drive", "halftime", "1st quarter", "live updates", "inactives",
                 "statement win", "bounce-back", "shocker", "drops", "feat", "milestone",
                 "key stats", "field goal", "pick six", "hail mary", "one second",
                 "clock controversy", "calls out", "backed by", "backs"]
ITEM_WEIGHTS = {"fan": 3.0, "moment": 2.0, "news": 1.0, "utility": 0.25}


def _demand_kind(item):
    """Grade one item: fan reaction > live moment > team news > utility listing."""
    if item.get("kind") == "fan_post":
        return "fan"
    text = item.get("text", "")
    if _any(_MOMENT_WORDS, text):
        return "moment"
    if _any(_UTILITY_WORDS, text):
        return "utility"
    return "news"


def grade_demand(items):
    """Split a topic's evidence into reaction vs utility and total the demand.

    Returns the numbers the board reports: how much of the coverage is actually
    people reacting, which outlets that reaction comes from, and how much of what
    we dropped was only a TV listing.
    """
    reaction, utility = [], []
    for it in items:
        kind = it.get("demand") or _demand_kind(it)
        it["demand"] = kind
        it["weight"] = ITEM_WEIGHTS.get(kind, 1.0)
        (utility if kind == "utility" else reaction).append(it)
    return {
        "reaction": reaction,
        "utility": utility,
        "weighted": round(sum(it["weight"] for it in items), 2),
        "reaction_weight": round(sum(it["weight"] for it in reaction), 2),
        "reaction_sources": _sources(reaction),
        "utility_count": len(utility),
    }


# ------------------------------------------------------------------ the pool
def _parse_ts(value):
    """Timestamp from RFC-822 (Google News), ISO-8601, or epoch seconds (Reddit)."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(float(value), dt.timezone.utc)
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        try:
            return dt.datetime.fromtimestamp(float(text), dt.timezone.utc)
        except Exception:
            return None
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        if parsed is not None:
            return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        pass
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def build_pool(trends=None, signals=None, now=None):
    """One flat, de-duplicated list of evidence items for all four teams.

    Every item keeps its provenance (`source`, `kind`) so the evidence grid can
    tell a fan post apart from a headline, and its parsed timestamp so velocity
    and recency are measured rather than assumed.
    """
    trends = trends if trends is not None else load_trends()
    signals = signals if signals is not None else load_signals()
    now = now or dt.datetime.now(dt.timezone.utc)
    pool, seen = [], set()

    def add(team, source, kind, text, url="", published="", metrics=None):
        outlet = _outlet(text, source, metrics)
        # Match and score on the headline itself, never on the publisher suffix -
        # "- Dallas Cowboys" at the end of a story is not a Cowboys fan saying it.
        body = str(text or "")
        if outlet and outlet != source and body.rstrip().endswith(outlet):
            body = body.rstrip()[: -len(outlet)].rstrip(" -–—").strip()
        norm = _norm(body)
        if not norm:
            return
        # Keyed on the stripped headline so the same story arriving from the live
        # feed and from the repository snapshot counts once, not twice.
        key = (team, norm[:160])
        if key in seen:
            return
        seen.add(key)
        ts = _parse_ts(published)
        entry = {
            "team": team, "source": source, "outlet": outlet, "kind": kind, "text": norm,
            "display": body.strip(),
            "raw": str(text or "").strip(), "url": url or "", "published": published or "",
            "ts": ts, "age_min": (round((now - ts).total_seconds() / 60) if ts else None),
            "metrics": metrics or {},
        }
        entry["demand"] = _demand_kind(entry)
        entry["weight"] = ITEM_WEIGHTS.get(entry["demand"], 1.0)
        pool.append(entry)

    for team, col in (trends.get("collections") or {}).items():
        for row in col.get("headlines", []) or []:
            if isinstance(row, dict):
                add(team, row.get("source") or "google_news", "headline",
                    row.get("title", ""), row.get("url", ""), row.get("pub", ""))
    srcs = signals.get("sources") or {}
    for row in signals.get("items", []) or []:
        if not isinstance(row, dict):
            continue
        source = row.get("source") or "unknown"
        kind = "fan_post" if source in ("reddit", "x", "twitter", "facebook") else "news"
        if source == "repository_trend_snapshot":
            kind = "snapshot"
        add(row.get("team", ""), source, kind, row.get("text", ""),
            row.get("url", ""), row.get("published", ""), row.get("metrics"))

    connectors = {}
    for name, meta in srcs.items():
        if isinstance(meta, dict):
            connectors[name] = {
                "status": meta.get("status") or "unknown",
                "reason": meta.get("reason") or "",
                "items": len(meta.get("items") or []),
                "fan": name in ("reddit", "x", "twitter", "facebook"),
            }
    return {
        "items": pool,
        "now": now,
        "signals_generated": signals.get("generated_at") or "",
        "trends_generated": trends.get("generated") or "",
        "connectors": connectors,
        "entity_mentions": {t: (c.get("entity_mentions") or {}) for t, c in (trends.get("collections") or {}).items()},
        "fti": trends.get("fan_trend_index") or {},
    }


def fan_connector_state(pool):
    """What we can honestly claim about fan-sourced evidence.

    Returns (fan_sources_live, note). When no fan connector is attached, the note
    names the reason straight from marketing/social-signals.json.
    """
    conns = pool.get("connectors") or {}
    fan = [n for n, meta in conns.items() if meta.get("fan")]
    live = [n for n in fan if conns[n]["status"] == "connected" and conns[n]["items"] > 0]
    if live:
        return live, "fan sources connected: " + ", ".join(sorted(live))
    reasons = []
    for n in fan:
        meta = conns.get(n) or {}
        reasons.append(f"{n} {meta.get('status', 'unknown')}" + (f" ({meta['reason']})" if meta.get("reason") else ""))
    if not fan:
        return [], "no fan connector configured in marketing/social-signals.json"
    return [], "no fan posts observed - " + "; ".join(reasons)


def _topic_items(pool, team, patterns):
    """Evidence for one topic inside one team - strongest demand first, then newest."""
    hits = []
    for item in pool["items"]:
        if item["team"] != team:
            continue
        if _any(patterns, item["text"]):
            hits.append(item)
    hits.sort(key=lambda it: (it.get("weight", 1.0),
                              it["ts"] is not None,
                              it["ts"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
              reverse=True)
    return hits


def _sources(items):
    """Distinct outlets carrying this story - not distinct connectors."""
    return sorted({it.get("outlet") or it.get("source") or "unknown" for it in items})


# -------------------------------------------------------------------- velocity
def compute_velocity(items, now=None, windows=VELOCITY_WINDOWS):
    """Rate of the newest window vs the window before it.

    We only report a percentage when a real baseline exists. With no items in the
    prior window the answer is "new", not infinity, and the caller decides how
    much a brand-new burst is worth. Windows are tried finest-first and the first
    one that actually contains evidence wins, so a sparse college topic is
    reported over 24 h instead of pretending a 60-minute measurement.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    dated = [it for it in items if it.get("ts")]
    out = {"pct": None, "window_minutes": None, "recent": 0, "baseline": 0,
           "label": "no timestamped evidence", "accelerating": False, "note": ""}
    if not dated:
        return out
    chosen = None
    for minutes in windows:
        span = dt.timedelta(minutes=minutes)
        recent = [it for it in dated if now - span <= it["ts"] <= now]
        baseline = [it for it in dated if now - 2 * span <= it["ts"] < now - span]
        if recent:
            chosen = (minutes, len(recent), len(baseline))
            break
    if chosen is None:
        span = dt.timedelta(minutes=windows[-1])
        recent = [it for it in dated if now - span <= it["ts"]]
        chosen = (windows[-1], len(recent), 0)
    minutes, recent, baseline = chosen
    arrow, label, note = "→", "", ""
    if baseline == 0:
        label = f"new - {recent} item{'s' if recent != 1 else ''} in last {minutes} min, none in the window before"
        note = "no baseline in the prior window; treated as a burst, not a percentage"
        accelerating = recent >= 2
    else:
        pct = (recent - baseline) / baseline * 100.0
        arrow = "↑" if pct > 0 else ("↓" if pct < 0 else "→")
        label = f"{arrow} {abs(pct):.0f}% / {minutes} min ({recent} vs {baseline})"
        note = f"{recent} item(s) in the last {minutes} min vs {baseline} in the prior {minutes} min"
        out["pct"] = round(pct, 1)
        accelerating = pct >= TREND_MIN_VELOCITY
    out.update({"window_minutes": minutes, "recent": recent, "baseline": baseline,
                "label": label, "accelerating": accelerating, "note": note})
    return out


# ------------------------------------------------------------------- sentiment
def analyze_sentiment(texts, brain=None):
    """Label the emotion behind the evidence, using the team's own words.

    The lexicons are per brain on purpose: "watson" is anxiety in Cleveland and
    means nothing in Ann Arbor, "respond" is Michigan's house motto and noise
    everywhere else. Returns the winning label, its share of the evidence, and
    the words that produced it so the board can show its working.
    """
    if isinstance(texts, str):
        texts = [texts]
    corpus = [_norm(t) for t in texts if t]
    lex = (brain or {}).get("sentiment") or {}
    if not corpus or not lex:
        return {"label": "neutral", "strength": 0.0, "hits": {}, "note": "no sentiment evidence"}
    hits = {}
    for label, patterns in lex.items():
        found = []
        for pat in patterns:
            count = sum(1 for text in corpus if _matches(pat, text))
            if count:
                found.append((pat, count))
        if found:
            found.sort(key=lambda pair: pair[1], reverse=True)
            hits[label] = found
    if not hits:
        return {"label": "neutral", "strength": 0.0, "hits": {},
                "note": f"{len(corpus)} item(s), none matched the {brain.get('short','team')} lexicon"}
    scored = {label: sum(c for _, c in found) for label, found in hits.items()}
    total = sum(scored.values()) or 1
    best = max(scored.items(), key=lambda kv: kv[1])
    label, score = best
    strength = min(1.0, score / max(3.0, len(corpus) * 0.35))
    return {
        "label": label,
        "strength": round(strength, 2),
        "hits": {k: v[:3] for k, v in hits.items()},
        "share": round(score / total, 2),
        "note": f"'{label}' on {score}/{total} lexicon hits across {len(corpus)} item(s)",
        "top_words": [w for w, _ in hits[label][:4]],
    }


# ------------------------------------------------------------------ game state
_LIVE_MIN = 4 * 60          # kickoff -> 4 h later still counts as live coverage
_RECENT_RESULT_HOURS = 30   # a finished game is still a posting window for this long
_RESULT_WORDS = ["final", "beats", "wins", "win ", "upset", "stuns", "defeat", "loses",
                 "drops", "postgame", "game recap", "rises in", "bounce-back", "shocker",
                 "intercepts", "touchdown"]


def get_game_state(team, pool=None, now=None, brain=None):
    """Where this team is in its week: live, just played, today, this week, off.

    Kickoff comes from src/collections_data.SEASON (the same data the storefront
    uses), never from a guess. `recent-result` is detected from evidence text so a
    team whose season data is a week old - Michigan after Saturday - still gets
    credit for a result the fanbase is reacting to right now.
    """
    now = now or (pool or {}).get("now") or dt.datetime.now(dt.timezone.utc)
    season = (_SEASON or {}).get(team) or {}
    kickoff = _parse_ts(season.get("kickoff", ""))
    nxt = _parse_ts((_NEXT_GAME or {}).get(team, ""))
    label, state, evidence = "no scheduled game in season data", "off-week", []
    minutes = None
    items = [it for it in (pool or {}).get("items", []) if it.get("team") == team]
    fresh = [it for it in items if it.get("ts") and (now - it["ts"]).total_seconds() <= _RECENT_RESULT_HOURS * 3600]
    result_hits = [it for it in fresh if _any(_RESULT_WORDS, it["text"])]

    if kickoff and -30 * 60 <= (now - kickoff).total_seconds() <= _LIVE_MIN * 60:
        minutes = round((now - kickoff).total_seconds() / 60)
        state = "live"
        label = f"game live - kickoff {kickoff.strftime('%H:%M UTC')}, ~{minutes} min in"
        evidence = [it["text"] for it in fresh if _any(
            ["live updates", "intercepts", "interception", "touchdown", "1st quarter",
             "halftime", "opening drive", "inactives", "field goal", "sack"], it["text"])][:3]
    elif result_hits:
        state = "recent-result"
        label = f"result coverage in the last {_RECENT_RESULT_HOURS} h ({len(result_hits)} item(s))"
        evidence = [it["text"] for it in result_hits[:3]]
    elif kickoff and 0 < (kickoff - now).total_seconds() <= 12 * 3600:
        state = "today"
        minutes = round((kickoff - now).total_seconds() / 60)
        label = f"kickoff in ~{minutes} min"
    elif kickoff and 0 < (kickoff - now).total_seconds() <= 72 * 3600:
        state = "this-week"
        minutes = round((kickoff - now).total_seconds() / 60)
        label = f"kickoff in ~{round(minutes / 60)} h"
    elif nxt and 0 < (nxt - now).total_seconds() <= 7 * 86400:
        state = "this-week"
        minutes = round((nxt - now).total_seconds() / 60)
        label = f"next game in ~{round(minutes / 1440)} day(s)"
    elif nxt:
        label = f"next game {nxt.strftime('%Y-%m-%d')}"
    elif kickoff:
        label = f"last kickoff {kickoff.strftime('%Y-%m-%d')}, no next game in data"
    return {
        "state": state, "label": label, "kickoff": kickoff.isoformat() if kickoff else None,
        "next_game": nxt.isoformat() if nxt else None, "minutes": minutes,
        "evidence": evidence,
        "timing_open": state in ("live", "recent-result", "today", "this-week"),
        "season_note": (season.get("headline") or season.get("status") or "").replace("&middot;", "·"),
    }


# ------------------------------------------------------------ commercial match
def _money(value):
    """Price as the storefront writes it: 21 -> $21.00, '21.99' -> $21.99."""
    if value in (None, ""):
        return ""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


# Generic per-team hooks used only when no topic-specific design matches, so a
# team is never left without a shelf to point at - but never scored as a match.
_TEAM_GENERIC = {
    "cleveland-browns": ["browns", "cleveland", "dawg", "dwag", "go browns", "cle", "ohio"],
    "green-bay-packers": ["packers", "green bay", "go pack go", "cheesehead", "pack"],
    "dallas-cowboys": ["dallas", "cowboys", "texas", "star"],
    "michigan": ["michigan", "go blue", "maize", "wolverines"],
}


def find_commercial_match(team, topic, pool=None):
    """Which design on the shelf answers this demand, and how well.

    Match quality is graded, because "we own a Browns shirt" is not the same
    claim as "we own the design this exact fan phrase is asking for":

      exact    the printed artwork or verified keywords name the demand
      campaign a design that carries the same commercial angle
      team     a generic team design - shelf filler, not a match
      none     nothing on the shelf answers it (that is a design gap, and the
               board says so instead of recommending an unrelated tee)

    Sellable designs (data/catalogue-live.json) always outrank crawl artefacts so
    the recommended link is one a customer can actually buy.
    """
    pool = pool if pool is not None else load_products()
    hooks = [h for h in (topic.get("commercial") or []) if h]
    generic = _TEAM_GENERIC.get(team, [])
    candidates = [p for p in pool.values() if p.get("collection") == team]
    if not candidates:
        candidates = [p for p in pool.values() if _guess_team(p.get("haystack", "")) == team]

    women_wanted = bool(topic.get("women"))

    def score(product, terms):
        hay = product.get("haystack", "")
        art = _norm(product.get("art") or "")
        title = _norm(product.get("title") or "")
        total, hits = 0, []
        for term in terms:
            needle = _norm(term)
            if not needle:
                continue
            specific = len(needle.split()) >= 2 or len(needle) >= 8
            if art and needle in art:
                total += 4 if specific else 3
                hits.append((term, "printed artwork"))
            elif _matches(needle, title) or any(needle in _norm(k) for k in product.get("keywords") or []):
                total += 2
                hits.append((term, "design name/keywords"))
            elif needle in hay:
                total += 1
                hits.append((term, "listing text"))
        # A women's cut is the right answer when the topic asks for it (Texas pride)
        # and the wrong answer for a prime-time gameday post, so it is penalised
        # rather than allowed to win on keyword stacking.
        if not women_wanted and _any(["this girl", "women", "girly", "mom", "milf", "she love"], title + " " + art):
            total -= 3
        return total, hits

    ranked = []
    art_hit = False
    for product in candidates:
        total, hits = score(product, hooks)
        if total > 0:
            ranked.append((total, hits, product))
    kind = "none"
    if ranked:
        # "exact" means the garment itself says the phrase the fans are using.
        # A match that only appears in listing copy is a campaign fit, not proof.
        art_hit = any(where == "printed artwork" for _t, hits, _p in ranked for _term, where in hits)
        if art_hit and ranked[0][0] >= 3:
            kind = "exact"
        elif ranked[0][0] >= 2:
            kind = "campaign"
        else:
            kind = "team"
    else:
        for product in candidates:
            total, hits = score(product, generic)
            if total > 0:
                ranked.append((total, hits, product))
        kind = "team" if ranked else "none"

    ranked.sort(key=lambda row: (row[2].get("sellable", False), row[0]), reverse=True)
    if not ranked:
        return {"type": "none", "design": None, "score": 0, "alternates": [],
                "reason": "no design on the shelf answers this demand - that is a gap, not a post",
                "campaign": topic.get("campaign", "")}

    best_total, best_hits, best = ranked[0]
    where = best_hits[0][1] if best_hits else "listing text"
    alternates = [{"slug": p["slug"], "title": p["title"], "score": t, "sellable": p.get("sellable", False)}
                  for t, _h, p in ranked[1:4]]
    reason = f"'{best_hits[0][0]}' in {where}" if best_hits else "team-level design"
    if not best.get("sellable"):
        reason += " - crawl artefact, not in the sellable catalogue"
    return {
        "type": kind,
        "design": {
            "slug": best["slug"], "title": best["title"],
            "price": _money(best.get("price_usd")),
            "url": best.get("buy_url") or best.get("url") or "",
            "front": best.get("front") or "",
            "art": best.get("art") or "",
            "sellable": bool(best.get("sellable")),
        },
        "score": best_total, "alternates": alternates,
        "reason": reason, "campaign": topic.get("campaign", ""),
        "angle": topic.get("angle", ""),
    }


# ----------------------------------------------------------------- confidence
def compute_confidence(evidence):
    """0-100 with the arithmetic visible.

    Every component is capped and named, and the fan-reaction component is capped
    at FAN_REACTION_CAPPED when no fan connector is attached - so a story with no
    observed fan reaction cannot buy its way into the action list.
    """
    items = evidence.get("items", 0)
    sources = evidence.get("sources", 0)
    fan_posts = evidence.get("fan_posts", 0)
    weighted = evidence.get("weighted")
    if weighted is None:
        weighted = float(items)
    velocity = evidence.get("velocity") or {}
    sentiment = evidence.get("sentiment") or {}
    game = evidence.get("game") or {}
    commercial = evidence.get("commercial") or {}
    fresh = evidence.get("freshness_min")
    parts = []

    def add(key, label, ratio, note):
        points = round(WEIGHTS[key] * max(0.0, min(1.0, ratio)), 1)
        parts.append({"key": key, "label": label, "points": points, "max": WEIGHTS[key], "note": note})
        return points

    total = 0.0
    total += add("volume", "demand volume", weighted / 8.0,
                 f"{items} reaction item(s) = {weighted} weighted demand (utility copy excluded)")
    total += add("sources", "independent sources", sources / 4.0, f"{sources} outlet(s) carrying the reaction")

    if fan_posts:
        fan_ratio = fan_posts / 25.0
        fan_note = f"{fan_posts} fan post(s) from connected source(s)"
        points = round(WEIGHTS["fan_reaction"] * max(0.0, min(1.0, fan_ratio)), 1)
    else:
        points = round(min(FAN_REACTION_CAPPED, WEIGHTS["fan_reaction"] * min(1.0, weighted / 8.0)), 1)
        fan_note = f"capped at {FAN_REACTION_CAPPED} - no fan posts observed (X/Reddit not connected)"
    parts.append({"key": "fan_reaction", "label": "fan reaction", "points": points,
                  "max": WEIGHTS["fan_reaction"], "note": fan_note})
    total += points

    if fresh is None:
        rec_ratio, rec_note = 0.0, "no timestamped evidence"
    elif fresh <= 60:
        rec_ratio, rec_note = 1.0, f"newest evidence {fresh} min old"
    elif fresh <= 360:
        rec_ratio, rec_note = 0.79, f"newest evidence {round(fresh / 60)} h old"
    elif fresh <= 1440:
        rec_ratio, rec_note = 0.5, f"newest evidence {round(fresh / 60)} h old"
    elif fresh <= 4320:
        rec_ratio, rec_note = 0.21, f"newest evidence {round(fresh / 1440)} day(s) old"
    else:
        rec_ratio, rec_note = 0.05, f"newest evidence {round(fresh / 1440)} day(s) old"
    total += add("recency", "recency", rec_ratio, rec_note)

    pct = velocity.get("pct")
    if pct is None and velocity.get("accelerating"):
        vel_ratio, vel_note = 0.86, velocity.get("label", "new burst")
    elif pct is None:
        vel_ratio, vel_note = 0.21, velocity.get("label", "not measurable")
    elif pct >= 100:
        vel_ratio, vel_note = 1.0, velocity.get("label", "")
    elif pct >= 50:
        vel_ratio, vel_note = 0.79, velocity.get("label", "")
    elif pct >= TREND_MIN_VELOCITY:
        vel_ratio, vel_note = 0.57, velocity.get("label", "")
    elif pct >= 0:
        vel_ratio, vel_note = 0.29, velocity.get("label", "")
    else:
        vel_ratio, vel_note = 0.0, velocity.get("label", "")
    total += add("velocity", "phrase velocity", vel_ratio, vel_note)

    strength = sentiment.get("strength", 0.0)
    if strength >= 0.6:
        sen_ratio = 1.0
    elif strength >= 0.35:
        sen_ratio = 0.75
    elif strength > 0:
        sen_ratio = 0.4
    else:
        sen_ratio = 0.1
    total += add("sentiment", "sentiment", sen_ratio, sentiment.get("note", ""))

    state = game.get("state", "off-week")
    game_ratio = {"live": 1.0, "today": 1.0, "recent-result": 0.88, "this-week": 0.5}.get(state, 0.1)
    total += add("game_state", "game state", game_ratio, game.get("label", ""))

    kind = commercial.get("type", "none")
    com_ratio = {"exact": 1.0, "campaign": 0.75, "team": 0.25, "none": 0.0}.get(kind, 0.0)
    total += add("commercial", "commercial match", com_ratio,
                 commercial.get("reason", "no match"))

    return {"score": int(round(total)), "parts": parts}


# ------------------------------------------------------------------- classify
def classify_level(confidence, commercial=None, items=0, sources=0, velocity=None,
                   fan_posts=0, timing_open=True, weighted=None):
    """The ladder, checked top-down: ACTION, OPPORTUNITY, TREND, SIGNAL, HEADLINE.

    The commercial and timing gates are checked first, on purpose - they are the
    expensive claims. Only then does real evidence decide TREND vs SIGNAL, and
    anything that is really just "something got published" falls out as HEADLINE
    and is filtered off the board.

    `items` here means reaction items (fan posts, live moments, team news) - not
    raw coverage. Utility listings are counted nowhere in this decision, which is
    the whole reason "1 mention = TRENDING" cannot happen again: a single headline
    is one unweighted item from one source and lands on HEADLINE every time.
    """
    comm = commercial.get("type") in ("exact", "campaign") if isinstance(commercial, dict) else bool(commercial)
    vel = velocity or {}
    accelerating = bool(vel.get("accelerating")) or (vel.get("pct") is not None and vel["pct"] >= TREND_MIN_VELOCITY)
    volume = float(items) if weighted is None else float(weighted)
    reacting = (items >= SIGNAL_MIN_ITEMS and sources >= SIGNAL_MIN_SOURCES
                and volume >= SIGNAL_MIN_WEIGHT)

    if confidence >= ACTION_MIN and comm and timing_open and reacting:
        return "ACTION"
    # OPPORTUNITY is "trend + product + commercial intent" - the product alone is
    # not enough. Without a reaction this is still one published story about a
    # design we happen to own, which is the headline the old board called a trend.
    if confidence >= OPPORTUNITY_MIN and comm and reacting:
        return "OPPORTUNITY"
    if reacting and (accelerating or fan_posts >= TREND_MIN_FAN_POSTS):
        return "TREND"
    if reacting:
        return "SIGNAL"
    return "HEADLINE"


def opportunity_status(level, game, commercial, freshness_min, velocity):
    """🟢 READY / 🟡 PREP / ⚪ WATCH / 🔴 STALE - and why, in words."""
    stale = freshness_min is not None and freshness_min > STALE_HOURS * 60
    if stale:
        return ("STALE", "🔴", f"newest evidence is {round(freshness_min / 1440)} day(s) old")
    sellable = bool((commercial or {}).get("design", {}) and (commercial or {}).get("design", {}).get("sellable"))
    matched = (commercial or {}).get("type") in ("exact", "campaign")
    timing_open = bool((game or {}).get("timing_open"))
    if level in ("ACTION", "OPPORTUNITY"):
        if matched and timing_open and (freshness_min is None or freshness_min <= 720):
            return ("READY", "🟢", "matched design, posting window open, evidence under 12 h")
        if matched and not sellable:
            return ("PREP", "🟡", "matched design is a crawl artefact - confirm it is still sellable")
        return ("PREP", "🟡", "matched, but the posting window is closed or the evidence is ageing")
    return ("WATCH", "⚪", "fans are reacting but nothing on the shelf answers it yet")


# ------------------------------------------------------------- action + copy
def _when_text(platform, game, now):
    when = platform.get("when", "now")
    state = (game or {}).get("state")
    if when == "gate":
        return "after the X post confirms the angle"
    if when == "now" and state == "today" and game.get("minutes"):
        return f"now - kickoff in ~{game['minutes']} min"
    if when == "now" and state == "live":
        return "now - game is live"
    return when


def build_actions(opportunity, brain, game, now):
    """Platform-by-platform play, in the order it should actually go out."""
    commercial = opportunity.get("commercial") or {}
    design = commercial.get("design") or {}
    design_line = design.get("title") or "the matched design"
    actions = []
    for platform in brain.get("platforms") or []:
        detail = platform.get("detail") or ""
        if platform.get("key") == "x":
            detail = f"{detail} Lead with the fan signal, not the product.".strip()
        if platform.get("key") in ("instagram", "pinterest") and design:
            detail = f"{detail} Creative: {design_line}.".strip()
        actions.append({
            "platform": platform.get("label") or platform.get("key"),
            "key": platform.get("key"),
            "play": platform.get("play", ""),
            "when": _when_text(platform, game, now),
            "detail": detail,
        })
    return actions


def build_article_ideas(opportunity, brain):
    """Medium / Quora / Reddit drafts - OPPORTUNITY and above only.

    Article ideas are the slowest asset on the board, so they are reserved for a
    topic that already has a trend, a matched design and commercial intent. One
    headline does not earn an article.
    """
    commercial = opportunity.get("commercial") or {}
    design = commercial.get("design") or {}
    design_name = design.get("title") or "the matched design"
    design_url = design.get("url") or ""
    signal = (opportunity.get("fan_signal") or {}).get("quote") or opportunity.get("title")
    team_full = brain.get("label", "the team")
    nick = brain.get("nick", "fans")
    topic_title = opportunity.get("title")
    subs = " / ".join(brain.get("subreddits") or ["r/nfl"])
    sources = [it for it in opportunity.get("items") or [] if it.get("url")][:3]
    proof = "; ".join(f'"{str(it.get("text") or "")[:70]}" ({it.get("source", "")})' for it in sources) or "see the evidence grid"

    return [
        {
            "type": "Medium",
            "team": opportunity["team"],
            "title": f"{team_full}: what the {nick} are actually saying about {topic_title.lower()}",
            "where": brain.get("medium") or "Medium - football fan culture",
            "angle": f"Fan-demand piece built on the live signal ({signal}), not on a headline recap.",
            "outline": [
                f"Hook with the signal itself: {signal}",
                f"What changed - {opportunity['evidence']['items']} item(s) across {opportunity['evidence']['sources']} outlet(s)",
                f"How the {nick} read it - {opportunity['evidence']['sentiment'].get('label')} tone",
                f"What that makes people want to wear - {commercial.get('campaign') or design_name}",
                "Close with a question that invites their version",
            ],
            "evidence": proof,
            "link": design_url,
            "image_idea": f"{design_name} mockup next to the moment that started it.",
        },
        {
            "type": "Quora",
            "team": opportunity["team"],
            "title": f"Why are {team_full} fans so focused on {topic_title.lower()} right now?",
            "where": brain.get("quora") or "Quora - football fandom",
            "angle": "Answer the question a fan would actually type, then answer it properly.",
            "outline": [
                "Answer in the first line - no preamble",
                f"Two or three real items as proof: {proof}",
                "What it means for the fanbase this week",
                f"One useful pointer to gear if it is genuinely relevant ({design_name})",
                "No pitch in the body - the answer has to stand alone",
            ],
            "evidence": proof,
            "link": design_url,
            "image_idea": "Simple stat/quote graphic - no product shot.",
        },
        {
            "type": "Reddit",
            "team": opportunity["team"],
            "title": f"{topic_title} - be a fan first in {brain.get('subreddits', ['r/nfl'])[0]}",
            "where": subs,
            "angle": "Join the existing thread instead of starting a promo post.",
            "outline": [
                "Comment in the game/topic thread, never a new promo post",
                f"Say the thing a fan would say: {signal}",
                "Only mention gear if someone asks - profile link, not a sales pitch",
                "Read the room: no product talk in a loss thread",
            ],
            "evidence": proof,
            "link": "profile link only, if asked",
            "image_idea": "None - text comment.",
        },
    ]


# Rank ties break toward the card that is actually shippable right now.
_STATUS_RANK = {"READY": 3, "PREP": 2, "WATCH": 1, "STALE": 0}


# ---------------------------------------------------------------------- hunt
def _entity_evidence(team, texts, pool, brain):
    """Tracked names from data/trends.json that this topic is actually about.

    trends.json labels anything with a mention as "trending". That label is
    ignored here on purpose - we take the mention counts as evidence and make our
    own call, because one mention is a headline, not a trend.
    """
    blob = " ".join(texts)
    fti_rows = {r.get("name"): r for r in ((pool.get("fti") or {}).get("rows") or []) if isinstance(r, dict)}
    out = []
    for name, pats in ((brain.get("players") or {}).items()):
        if not _any(pats.get("patterns") or [name], blob):
            continue
        mentions = int((pool.get("entity_mentions", {}).get(team) or {}).get(name, 0) or 0)
        row = fti_rows.get(name) or {}
        out.append({
            "name": name, "mentions": mentions, "fti": row.get("index", 0),
            "jersey": pats.get("jersey") or "", "note": pats.get("note") or "",
            "data_status": row.get("status") or "",
            "gap": bool(row.get("gap")),
        })
    out.sort(key=lambda r: r["mentions"], reverse=True)
    return out


def _fan_signal(items, brain):
    """The line that proves fans are reacting - quoted, attributed, never invented."""
    if not items:
        return {"quote": "", "source": "", "url": "", "age_min": None, "kind": ""}
    # Prefer the line that actually carries the emotion: a fan post first, then the
    # item that says something ("my smile is back", "they're counting us out") over
    # a neutral one ("photos of the cheerleaders").
    lex = _emotion_patterns(brain)

    def rank_key(it):
        emotion = 1.0 if lex and _any(lex, it.get("text", "")) else 0.0
        return (it.get("weight", 1.0) + emotion,
                it.get("ts") or dt.datetime.min.replace(tzinfo=dt.timezone.utc))

    pick = sorted(items, key=rank_key, reverse=True)[0]
    quote = pick.get("display") or pick.get("raw") or pick.get("text") or ""
    if len(quote) > 180:
        quote = quote[:177].rsplit(" ", 1)[0] + "…"
    return {"quote": quote, "source": pick.get("source", ""), "outlet": pick.get("outlet", ""),
            "url": pick.get("url", ""), "age_min": pick.get("age_min"), "kind": pick.get("kind", ""),
            "demand": pick.get("demand", "")}


def hunt_opportunities(trends=None, signals=None, products=None, now=None):
    """The whole board: ranked opportunities, evidence, product, action, confidence.

    Returns a payload src/hq.py renders as-is. `opportunities` holds SIGNAL and
    above only; HEADLINE-level topics are counted in `filtered` and named there so
    the operator can see what was dropped and why.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    trends = trends if trends is not None else load_trends()
    signals = signals if signals is not None else load_signals()
    pool = build_pool(trends, signals, now)
    products = products if products is not None else load_products()
    fan_live, fan_note = fan_connector_state(pool)

    order = [t for t in (_COLLECTIONS and list(_COLLECTIONS.keys()) or []) if t in TEAM_BRAINS]
    order += [t for t in TEAM_BRAINS if t not in order]

    opps, filtered, per_team = [], [], {}
    for team in order:
        brain = TEAM_BRAINS[team]
        team_items = [it for it in pool["items"] if it["team"] == team]
        game = get_game_state(team, pool, now, brain)
        team_opps = []
        context = []
        for topic in brain.get("topics") or []:
            items = _topic_items(pool, team, topic.get("patterns") or [])
            if not items:
                continue
            demand = grade_demand(items)
            if topic.get("context"):
                # Watch-party listings and roster wires tell us where the fans are
                # looking, not what they want to buy. They shape timing, so they
                # are counted here and never allowed to become an opportunity.
                context.append({"title": topic.get("title", ""), "items": len(items),
                                "utility": demand["utility_count"],
                                "reaction": len(demand["reaction"])})
                continue
            reaction = demand["reaction"]
            sources = demand["reaction_sources"] or _sources(items)
            fan_posts = [it for it in reaction if it["kind"] == "fan_post"]
            # Velocity and sentiment are measured on the reaction, never on the
            # TV listings - a spike in "what channel is the game on" is not a
            # phrase accelerating.
            velocity = compute_velocity(reaction or items, now)
            sentiment = analyze_sentiment([it["text"] for it in reaction] or
                                          [it["text"] for it in items], brain)
            commercial = find_commercial_match(team, topic, products)
            ages = [it["age_min"] for it in (reaction or items) if it.get("age_min") is not None]
            freshness = min(ages) if ages else None
            evidence_in = {
                "items": len(reaction), "weighted": demand["reaction_weight"],
                "sources": len(sources), "fan_posts": len(fan_posts),
                "velocity": velocity, "sentiment": sentiment, "game": game,
                "commercial": commercial, "freshness_min": freshness,
            }
            confidence = compute_confidence(evidence_in)
            level = classify_level(confidence["score"], commercial=commercial, items=len(reaction),
                                   sources=len(sources), velocity=velocity,
                                   fan_posts=len(fan_posts), timing_open=game.get("timing_open", False),
                                   weighted=demand["reaction_weight"])
            entities = _entity_evidence(team, [it["text"] for it in items], pool, brain)
            by_source = {}
            for it in reaction:
                by_source[it["source"]] = by_source.get(it["source"], 0) + 1
            opp = {
                "team": team,
                "team_label": brain.get("short", team),
                "team_full": brain.get("label", team),
                "nick": brain.get("nick", ""),
                "topic_key": topic.get("key"),
                "title": topic.get("title", topic.get("key", "")),
                "kind": topic.get("kind", ""),
                "why": topic.get("why", ""),
                "level": level,
                "confidence": confidence["score"],
                "confidence_parts": confidence["parts"],
                "fan_signal": _fan_signal(reaction or items, brain),
                "evidence": {
                    "items": len(reaction),
                    "all_items": len(items),
                    "utility": demand["utility_count"],
                    "weighted": demand["reaction_weight"],
                    "sources": len(sources),
                    "source_names": sources,
                    "by_source": by_source,
                    "fan_posts": len(fan_posts),
                    "velocity": velocity,
                    "sentiment": sentiment,
                    "game": game,
                    "freshness_min": freshness,
                    "entities": entities,
                },
                "commercial": commercial,
                "items": [{"text": it["raw"] or it["text"], "source": it["source"], "url": it["url"],
                           "age_min": it["age_min"], "kind": it["kind"], "demand": it["demand"]}
                          for it in (reaction or items)[:6]],
            }
            opp["status"], opp["status_emoji"], opp["status_why"] = opportunity_status(
                level, game, commercial, freshness, velocity)
            opp["actions"] = build_actions(opp, brain, game, now) if level in ("ACTION", "OPPORTUNITY") else []
            team_opps.append(opp)

        team_opps.sort(key=lambda o: (LEVEL_RANK[o["level"]], o["confidence"],
                                      _STATUS_RANK.get(o["status"], 0)), reverse=True)
        per_team[team] = {
            "label": brain.get("label", team), "short": brain.get("short", team),
            "shown": sum(1 for o in team_opps if LEVEL_RANK[o["level"]] >= LEVEL_RANK[SHOWN_FROM]),
            "filtered": sum(1 for o in team_opps if o["level"] == "HEADLINE"),
            "items": len(team_items), "game": game, "context": context,
            "best": team_opps[0]["title"] if team_opps else "",
        }
        for opp in team_opps:
            (opps if LEVEL_RANK[opp["level"]] >= LEVEL_RANK[SHOWN_FROM] else filtered).append(opp)

    opps.sort(key=lambda o: (LEVEL_RANK[o["level"]], o["confidence"],
                             _STATUS_RANK.get(o["status"], 0),
                             -(o["evidence"]["freshness_min"] if o["evidence"]["freshness_min"] is not None else 10 ** 9)),
              reverse=True)
    for i, opp in enumerate(opps, start=1):
        opp["rank"] = i

    articles = []
    for opp in opps:
        if opp["level"] in ("OPPORTUNITY", "ACTION") and opp["commercial"].get("design"):
            articles.extend(build_article_ideas(opp, TEAM_BRAINS[opp["team"]]))
    articles = articles[:MAX_ARTICLES]

    board = None
    if opps:
        top = opps[0]
        design = (top["commercial"].get("design") or {})
        where = top["actions"][0]["platform"] if top["actions"] else "X"
        when = top["actions"][0]["when"] if top["actions"] else "now"
        board = {
            "answer": (f"Post the {top['title']} angle for {top['team_full']} on {where} {when}"
                       f"{' with ' + design.get('title') if design.get('title') else ''}"
                       f" - {top['confidence']}% confidence, {top['level']}."),
            "why": top["why"],
            "product": design.get("title") or "no matched design",
            "product_url": design.get("url") or "",
            "platform": where, "timing": when, "confidence": top["confidence"],
            "level": top["level"], "team": top["team_label"], "status": top["status"],
            "status_emoji": top["status_emoji"], "creative": top["commercial"].get("angle", ""),
            "campaign": top["commercial"].get("campaign", ""),
        }
    counts = {lvl: sum(1 for o in opps if o["level"] == lvl) for lvl in LEVELS if lvl != "HEADLINE"}
    counts["HEADLINE"] = len(filtered)
    return {
        "generated": pool["trends_generated"] or (now.strftime("%Y-%m-%d")),
        "as_of": now.strftime("%Y-%m-%d %H:%M UTC"),
        "signals_generated": pool["signals_generated"],
        "opportunities": opps,
        "filtered": filtered,
        "counts": counts,
        "teams": per_team,
        "articles": articles,
        "board": board,
        "connectors": pool["connectors"],
        "fan_note": fan_note,
        "fan_sources_live": fan_live,
        "ladder": [
            {"level": "HEADLINE", "rule": "something was published", "shown": False},
            {"level": "SIGNAL", "rule": f">= {SIGNAL_MIN_ITEMS} reaction items from >= {SIGNAL_MIN_SOURCES} outlets, >= {SIGNAL_MIN_WEIGHT:g} weighted demand (how-to-watch copy counts for nothing)", "shown": True},
            {"level": "TREND", "rule": f"reaction accelerating (>= {TREND_MIN_VELOCITY:.0f}% vs the prior window) or >= {TREND_MIN_FAN_POSTS} fan posts", "shown": True},
            {"level": "OPPORTUNITY", "rule": f"reaction + matched design + confidence >= {OPPORTUNITY_MIN}", "shown": True},
            {"level": "ACTION", "rule": f"opportunity + confidence >= {ACTION_MIN} + open posting window", "shown": True},
        ],
    }
