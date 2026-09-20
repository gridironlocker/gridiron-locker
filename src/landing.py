"""SEO landing-page copy for a single design.

Gridiron Locker is the discovery + SEO layer; the fulfilment partner
layer. Nothing in here may pretend to configure or process an order: no style
picker, no size picker, no colour picker, no checkout.

Copy is composed from the actual product record (name, artwork line, theme,
garment, collection) plus verified campaign facts. Colour names are never
invented. No player quotes, statistics, records or historical claims.
"""
import hashlib
import re

from collections_data import partner_of

import seocopy as _c


# ---------------------------------------------------------------- helpers
def h(slug, salt=""):
    return int(hashlib.md5((slug + salt).encode()).hexdigest(), 16)


def pick(lst, slug, salt=""):
    return lst[h(slug, salt) % len(lst)]


def pick_n(lst, slug, salt, n):
    """Deterministic sample of n items, order varied per slug."""
    items = list(lst)
    out = []
    i = h(slug, salt)
    while items and len(out) < n:
        out.append(items.pop(i % len(items)))
        i //= max(2, len(items) + 1) or 2
        i = i or h(slug, salt + str(len(out)))
    return out


def sentence(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s


def artline(art):
    """The artwork text as a readable phrase (the scraper stores it shouted)."""
    return sentence(art)


def word_count(text):
    return len(re.findall(r"[A-Za-z0-9']+", re.sub(r"<[^>]+>", " ", text or "")))


def paras(*chunks):
    return "".join(f"<p>{sentence(c)}</p>" for c in chunks if sentence(c or ""))


NON_APPAREL = ("Mug", "Phone Case")


def an(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def is_slogan(art):
    """True when the artwork line is a phrase printed on the garment rather
    than a description of a picture."""
    head = re.split(r"\s+with\s+|\s+on\s+|,", art, 1)[0]
    letters = [ch for ch in head if ch.isalpha()]
    if len(letters) < 3:
        return False
    return sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.7


def slogan_text(art):
    return sentence(re.split(r"\s+with\s+|\s+on\s+", art, 1)[0].rstrip(" ,-"))


def wear_verb(garment):
    return "used" if garment in NON_APPAREL else "worn"


def title_case_art(art):
    a = artline(art)
    if a.isupper():
        return a.title()
    return a


# ---------------------------------------------------------------- vocabulary
THEME_LABEL = {
    "player": "player tribute",
    "funny": "humour",
    "playoff": "playoff-run",
    "classic": "everyday fan",
    "retro": "throwback",
    "city": "hometown",
    "family": "gift",
    "halloween": "all-over-print",
}

THEME_CONCEPT = {
    "player": [
        "It is a name-and-number tribute done as typography rather than a knock-off jersey, "
        "so it reads as a fan statement instead of a costume.",
        "The layout borrows from locker-room nameplates: heavy lettering, a numeral, and nothing "
        "competing with it.",
        "It celebrates one player the way supporters actually talk about him - a phrase and a "
        "number, not a stat sheet.",
    ],
    "funny": [
        "The joke lands from across a tailgate lot, which is the only test a funny shirt has to pass.",
        "It is built around one punchline and a clean layout, so the humour is legible before "
        "anyone gets close enough to read the small print.",
        "The gag is short, the type is big, and the graphic does not try to explain itself.",
    ],
    "playoff": [
        "It is deliberately loud: postseason graphics are worn in cold stadiums and crowded bars, "
        "so contrast matters more than detail.",
        "The design is built for the weeks when the season narrows - bold slogan, heavy weight, "
        "no clutter.",
        "Everything about the layout is aimed at the January stretch, when fans want a shirt that "
        "says exactly where they stand.",
    ],
    "classic": [
        "There is nothing fussy about it: one idea, balanced spacing, and colours that survive a "
        "wash cycle.",
        "It is the low-risk pick in the collection - simple enough for a Tuesday, still clearly "
        "football on a Sunday.",
        "The restraint is the point. It is a design you can wear when you are not trying to make "
        "a statement.",
    ],
    "retro": [
        "The lettering leans on worn-in athletics styling - the kind of type that looks like it "
        "has been through fifteen seasons already.",
        "It is drawn to look like a shirt found at the back of a closet, printed with a process "
        "that will not crack like one.",
        "Faded-era styling, modern print: throwback shapes without the thrift-store smell.",
    ],
    "city": [
        "The artwork puts the city first and the scoreboard second, which is how most lifelong "
        "supporters actually think about it.",
        "It is a hometown mark more than a team mark - wearable in the stands and at the airport.",
        "Place comes before players here: the design is about where the football is played.",
    ],
    "family": [
        "It is designed to be easy to give: no player-specific reference to get wrong, no size-"
        "specific joke, nothing that dates in a month.",
        "The graphic is friendly rather than aggressive, which is what makes it a safe gift for a "
        "fan you do not shop for often.",
        "It reads as a present rather than merch - a clean idea printed on something soft.",
    ],
    "halloween": [
        "The artwork runs edge to edge instead of sitting in a chest-sized box, so the whole "
        "garment is the graphic.",
        "It is a full-bleed print built to be seen across a crowded room.",
        "Nothing about it is subtle - the design covers the piece rather than decorating it.",
    ],
}

WEAR_CONTEXT = [
    "kickoff at home with the game on and the phone face down",
    "a tailgate where you are standing outside for three hours before anyone throws a ball",
    "a sports bar two time zones from the stadium",
    "a watch party where half the room supports the other side",
    "the walk from the parking lot to the gate in November",
    "a Sunday on the sofa when the weather makes the trip a bad idea",
    "a draft-night group chat that has been arguing since May",
    "the first cold road game of the year",
    "a family living room that turns into a stadium for three hours",
]

# One line per garment about when it actually gets worn. Each entry holds
# several variants and gameday_wear() picks one per slug: a single fixed
# sentence repeated on all 81 t-shirt pages is a duplicate-content signal
# (2026-09-18 audit, F16), and it reads like a template to a human too.
LAYER_NOTE = {
    # T-shirts are 81 of the 84 live designs, so this entry is composed from
    # leads x tails (16 distinct sentences) instead of a fixed line - one
    # sentence repeated on every tee page was the single biggest
    # duplicate-content signal on the site (2026-09-18 audit, F16).
    "T-Shirt": None,   # filled in below, after _TEE_LEADS/_TEE_TAILS exist
    "Hoodie": [
        "It is the outer layer for cold kickoffs and the only layer for indoor watch parties.",
        "Cold-weather piece first: hood up in the stands, sleeves pushed back in the living room.",
        "The one you reach for on a December game day and keep wearing through the offseason.",
    ],
    "Sweatshirt": [
        "A crewneck sits between a tee and a jacket, which makes it the most-worn piece "
        "in most fans' rotations.",
        "No hood, no bulk - the crewneck is the layer that works indoors and out.",
        "It covers the weeks when a tee is too little and a coat is too much.",
    ],
    "Long Sleeve Shirt": [
        "Long sleeves cover the shoulder season - the weeks when a tee is not "
        "enough and a hoodie is too much.",
        "Built for those in-between autumn weeks: sleeves for the shade, no fleece for the walk back.",
        "The shoulder-season piece - warm at kickoff, still wearable by the fourth quarter.",
    ],
    "Beanie": [
        "It works from the first cold road game to the last week of the season.",
        "Late-season gear: the weeks when the wind off the lot matters more than the score.",
        "A cold-weather small - the thing you pull on before you leave the car.",
    ],
    "Mug": [
        "It lives on a desk all week and comes out again on Sunday morning.",
        "Desk all week, kitchen counter on a game-day morning.",
        "The pre-kickoff object: coffee in it, football on the screen.",
    ],
    "Phone Case": [
        "It is the fan detail that goes everywhere the rest of your gear does not.",
        "The one piece of fandom that travels with you all week, not just on game day.",
        "Small, daily and visible - the mark you carry past the stadium gates.",
    ],
}


# Each combo is a SINGLE sentence: splitting lead and tail into two sentences
# just moved the duplication from one line to two.
_TEE_LEADS = [
    "It goes under a hoodie or a jacket the moment the temperature drops,",
    "Worn alone in September, it goes under something heavier by November,",
    "It is the base layer of a football year - on its own while it is warm, "
    "under everything after,",
    "Short sleeves early in the year, a layer over it later,",
    "It is the piece that adapts: alone in the warm weeks, layered in the cold ones,",
]
_TEE_TAILS = [
    "which covers most of the second half of the season.",
    "which in these cities means most of the season.",
    "so it stays in rotation until the last cold game.",
    "and it never goes back in the drawer until spring.",
    "which is why it outlasts the novelty pieces in a fan's wardrobe.",
]
LAYER_NOTE["T-Shirt"] = [f"{a} {b}" for a in _TEE_LEADS for b in _TEE_TAILS]



def layer_note(garment, slug):
    """Deterministic per-product pick from LAYER_NOTE[garment]."""
    opts = LAYER_NOTE.get(garment) or LAYER_NOTE["T-Shirt"]
    if isinstance(opts, str):
        return opts
    return pick(list(opts), slug, "layer-" + garment)

COL_VOICE = {
    "cleveland-browns": {
        "weather": "Cleveland football weather is Lake Erie weather - grey, loud, and not interested in fair-weather kits.",
        "place": "The Dawg Pound has always been cheaper seats and a bigger mouth, which is the culture this collection draws from.",
        "mark": [
            "Orange and brown is an awkward combination until it is yours, and then it is the whole personality.",
            "Brown and orange is not a polite colourway, which is rather the point of wearing it.",
            "The colourway does the arguing; the artwork only has to stand up next to it.",
        ],
        "sunday": [
            "Cleveland fans measure the year in Sundays, not months.",
            "Around here the week is just the run-up to Sunday.",
            "Sundays are the fixed point; everything else moves around them.",
        ],
    },
    "green-bay-packers": {
        "weather": "Green Bay football is cold air, louder cheese, and a public team that still feels like it belongs to the town.",
        "place": "Lambeau weather is the filter: if a graphic cannot be read with a hoodie up, it is not finished.",
        "mark": [
            "Green and gold is a winter colourway, and it looks right with snow on the sideline.",
            "Green and gold only really makes sense in cold weather, which is most of a Packers year.",
            "The palette is a December palette: deep green, flat gold, no bright finishes.",
        ],
        "sunday": [
            "Sunday in Cheesehead Nation is less a hobby than a municipal calendar.",
            "In Green Bay the Sunday schedule comes first and the week is fitted around it.",
            "A Packers Sunday is a town-wide appointment, not a viewing preference.",
        ],
    },
    "dallas-cowboys": {
        "weather": "Dallas football style sits halfway between a stadium concourse and a Texas highway - stars, silver, and a little country.",
        "place": "The city mark matters here as much as the scoreboard. Texas pride travels.",
        "mark": [
            "Silver and navy reads as vintage the second you wash it twice.",
            "Silver, navy and a little white is a colourway that ages into a throwback on its own.",
            "The palette is stadium-concourse silver and navy - sharp new, better worn in.",
        ],
        "sunday": [
            "Sunday night in Dallas is a bigger stage, and the graphics are drawn to match.",
            "Dallas treats a Sunday game as an occasion, so the artwork is drawn to be seen.",
            "A Cowboys Sunday has an audience well past the stands - the art has to hold up.",
        ],
    },
    "michigan": {
        "weather": "Ann Arbor Saturdays are maize, navy, and a crowd that treats a grudge as climate.",
        "place": "Michigan vs Everybody is less a slogan than a weather report in this town.",
        "mark": [
            "Block lettering and a winged-helmet silhouette carry more weight here than any paragraph could.",
            "Maize and navy with block lettering is a look that needs no explanation in this town.",
            "The visual language is big letters and flat colour - the oldest trick in college football, still the loudest.",
        ],
        "sunday": [
            "A Big Ten November is crewneck weather, and the graphic has to survive it.",
            "Michigan football arrives in the cold half of the year, so nothing here is delicate.",
            "Ann Arbor Saturdays in November are cold enough that a graphic has to read through a scarf.",
        ],
    },
}

# Named people only when the artwork or product name actually says so.
# Status is taken from data/people.json (current vs throwback). No stats.
_PERSON_KEYS = [
    ("shedeur sanders", "Shedeur Sanders", "current", "Cleveland quarterback"),
    ("shedeur", "Shedeur Sanders", "current", "Cleveland quarterback"),
    ("sanders", "Shedeur Sanders", "current", "Cleveland quarterback"),
    ("denzel ward", "Denzel Ward", "current", "Cleveland cornerback"),
    ("denzel", "Denzel Ward", "current", "Cleveland cornerback"),
    ("mason graham", "Mason Graham", "current", None),
    ("jordan freaking love", "Jordan Love", "current", "Green Bay quarterback"),
    ("jordan love", "Jordan Love", "current", "Green Bay quarterback"),
    ("joe flacco", "Joe Flacco", "throwback", None),
    ("flacco", "Joe Flacco", "throwback", None),
    ("myles garrett", "Myles Garrett", "throwback", None),
    ("garrett 95", "Myles Garrett", "throwback", None),
    ("garrett", "Myles Garrett", "throwback", None),
    ("stefanski", "Kevin Stefanski", "throwback", None),
    ("coach kevin", "Kevin Stefanski", "throwback", None),
    ("j.j. mccarthy", "J.J. McCarthy", "throwback", None),
    ("jj mccarthy", "J.J. McCarthy", "throwback", None),
    ("mccarthy", "J.J. McCarthy", "throwback", None),
    ("robert tonyan", "Robert Tonyan", None, None),
    ("tonyan", "Robert Tonyan", None, None),
    ("bryce underwood", "Bryce Underwood", "current", "Michigan quarterback"),
    ("underwood", "Bryce Underwood", "current", "Michigan quarterback"),
]

_MOTIF_KEYS = [
    ("bulldog", ("bulldog", "dawg pound", "beware of dawg", "angry bulldog", "armored bulldog",
                 "vintage bulldog", "cheese mascot")),
    ("skyline", ("skyline",)),
    ("helmet", ("helmet", "winged helmet")),
    ("cheese", ("cheese", "cheesehead", "cheese wedge")),
    ("heart", ("heart", "(heart)", "heartbeat", "hearts")),
    ("skull", ("skull", "sugar skull", "longhorn skull")),
    ("flag", ("flag", "stars and stripes", "american flag")),
    ("map", ("state map", "state outline", "wisconsin state", "inside ohio")),
    ("signature", ("signature",)),
    ("crown", ("crown",)),
    ("star", ("lightning", "stars")),
    ("crest", ("crest", "est.", "est ")),
    ("script", ("script",)),
    ("photo", ("player photo", "with player")),
    ("beer", ("beer", "drink", "cup of joe")),
    ("football", ("football",)),
]


def find_person(name, art):
    blob = f"{name} {art}".lower()
    for key, pname, status, role in sorted(_PERSON_KEYS, key=lambda x: -len(x[0])):
        if key in blob:
            return {"name": pname, "status": status, "role": role}
    # Love number marks that never print the surname.
    if "10ve" in blob or "love 10" in blob or "10 love" in blob:
        return {"name": "Jordan Love", "status": "current", "role": "Green Bay quarterback"}
    return None


def find_motifs(art, name):
    blob = f"{name} {art}".lower()
    found = []
    for label, keys in _MOTIF_KEYS:
        if any(k in blob for k in keys):
            found.append(label)
    return found


def find_number(art, name):
    blob = f"{name} {art}"
    nums = re.findall(r"\b(\d{1,2})\b", blob)
    skip = {"0", "01", "1841", "1879", "1919", "1946", "1960", "2023", "2024", "2025", "2026"}
    for n in nums:
        if n not in skip and not n.startswith("0"):
            return n
    return None


def seo_angle(theme, art, name, col):
    blob = f"{art} {name}".lower()
    if any(x in blob for x in ("vs everybody", "vs everyone", "-vs-", "revenge", "haters",
                               "ain't for sissies", "not that bad")):
        return "rivalry"
    if theme == "player" or find_person(name, art):
        return "player"
    if theme == "funny":
        return "funny"
    if theme == "retro":
        return "vintage"
    if theme == "family":
        return "gift"
    if theme == "playoff" or "playoff" in blob or "game day" in blob or "sunday" in blob:
        return "gameday"
    if theme == "city":
        return "city"
    if theme == "halloween":
        return "statement"
    if any(x in blob for x in ("new era", "second act", "the future is")):
        return "new-season"
    return "culture"


def profile(slug, name, art, col, garment, theme):
    person = find_person(name, art)
    motifs = find_motifs(art, name)
    angle = seo_angle(theme, art, name, col)
    city = col["city"].split(",")[0]
    return {
        "slug": slug,
        "name": name,
        "art": artline(art),
        "art_title": title_case_art(art),
        "phrase": slogan_text(art) if is_slogan(art) else title_case_art(art),
        "slogan": is_slogan(art),
        "team": col["team"],
        "short": col["short"],
        "city": city,
        "nick": col.get("nick") or "",
        "chant": col.get("chant") or "",
        "est": col.get("est") or "",
        "ckey": col.get("key") or "",
        "garment": garment,
        "g": garment.lower(),
        "theme": theme if theme in THEME_CONCEPT else "classic",
        "angle": angle,
        "motifs": motifs,
        "person": person,
        "number": find_number(art, name),
        "voice": h(slug) % 8,
        "v": wear_verb(garment),
    }


def _voice_of(col):
    return COL_VOICE.get(col.get("key"), COL_VOICE.get(
        next((k for k in COL_VOICE if col.get("short", "").lower() in k), "cleveland-browns")
    ))


def _col_voice(col):
    # collections_data keys: cleveland-browns, green-bay-packers, dallas-cowboys, michigan
    team = (col.get("team") or "").lower()
    short = (col.get("short") or "").lower()
    if "brown" in team or short == "cleveland":
        return COL_VOICE["cleveland-browns"]
    if "pack" in team or short == "green bay":
        return COL_VOICE["green-bay-packers"]
    if "dallas" in team or short == "dallas":
        return COL_VOICE["dallas-cowboys"]
    return COL_VOICE["michigan"]


def _voice_line(voice, key, slug):
    """A COL_VOICE entry is either one string or a list of variants. Picking a
    variant per slug keeps the collection's voice without printing the same
    sentence on every page of that collection."""
    v = voice.get(key, "")
    if isinstance(v, (list, tuple)):
        return pick(list(v), slug, "voice-" + key)
    return v


# ---------------------------------------------------------------- titles / meta
def search_intent(p):
    """Short search-intent phrase unique enough to sit beside the product name."""
    short, city, g = p["short"], p["city"], p["g"]
    person = p["person"]
    angle = p["angle"]
    opts = []
    if person:
        opts += [f"{person['name']} fan shirt", f"{person['name']} {g}"]
    if angle == "funny":
        opts += [f"funny {short} shirt", f"{short} humour tee"]
    elif angle == "vintage":
        opts += [f"vintage {short} tee", f"{short} throwback shirt"]
    elif angle == "rivalry":
        opts += [f"{short} rivalry shirt", f"{short} vs everybody tee"]
    elif angle == "gameday":
        opts += [f"game day {short} shirt", f"{short} Sunday tee"]
    elif angle == "gift":
        opts += [f"{short} fan gift", f"{short} football gift"]
    elif angle == "city":
        opts += [f"{city} football shirt", f"{short} city pride tee"]
    elif angle == "new-season":
        opts += [f"{short} new era {g}", f"{short} 2026 shirt"]
    elif angle == "statement":
        opts += [f"{short} all-over print", f"{short} statement {g}"]
    elif angle == "player":
        opts += [f"{short} player tribute", f"{short} fan {g}"]
    opts += [f"{short} fan shirt", f"fan-made {short} {g}", f"{city} football {g}",
             f"{short} football apparel"]
    # de-dupe preserving order
    seen, clean = set(), []
    for o in opts:
        k = o.lower()
        if k not in seen:
            seen.add(k)
            clean.append(o)
    return pick(clean, p["slug"], "intent")


def meta_title(name, brand="Gridiron Locker", slug="", col=None, garment="T-Shirt",
               theme="classic", art=""):
    """[Product] | [search intent] | Gridiron Locker - shortened to the SERP budget."""
    if col:
        p = profile(slug or name, name, art or name, col, garment, theme)
        intent = search_intent(p)
    else:
        intent = "Fan-Made Football Apparel"
    full = f"{name} | {intent} | {brand}"
    if len(full) <= 60:
        return full
    mid = f"{name} | {intent}"
    if len(mid) <= 60:
        return mid
    short = f"{name} | {brand}"
    if len(short) <= 60:
        return short
    return name


def meta_description(slug, name, col, garment, price, styles, colours, sizes, art=""):
    """Unique description: product, football context, apparel, fan-made, brand."""
    g = garment.lower()
    P = partner_of(col.get("key"))
    team = col["team"]
    city = col["city"].split(",")[0]
    srange = f"{sizes[0]}-{sizes[-1]}" if len(sizes) > 1 else (sizes[0] if sizes else "")
    if garment == "Beanie":
        size_phrase = "one size"
    elif garment == "Mug":
        size_phrase = "11 oz"
    elif garment == "Phone Case":
        size_phrase = "device-specific models"
    else:
        size_phrase = f"sizes {srange}"
    stylecount = len(styles)
    fixed_campaign = P == "Mayzing" and stylecount == 1 and colours == 1
    price_phrase = f"priced at ${price}" if fixed_campaign else f"from ${price}"
    if fixed_campaign:
        option_phrase = "Confirm your size on Mayzing"
    elif garment == "Beanie":
        option_phrase = f"Confirm colour and finish on {P}"
    elif garment == "Mug":
        option_phrase = f"Confirm the mug option on {P}"
    elif garment == "Phone Case":
        option_phrase = f"Choose your device model on {P}"
    else:
        option_phrase = f"Style, colour and size are chosen on {P}"
    art_bit = title_case_art(art or name)
    if len(art_bit) > 42:
        art_bit = art_bit[:40].rsplit(" ", 1)[0]
    variants = [
        (f"{name} - fan-made {g} for {team} fans, built around {art_bit}. "
         f"Printed on demand, {price_phrase}"
         f"{f', on {stylecount} garment styles' if stylecount > 1 else ''}, {size_phrase}. "
         f"Shop the design on {P}."),
        (f"Fan-made {g} for {city} football supporters: {name}. Artwork: {art_bit}. "
         f"{price_phrase.capitalize()}, {size_phrase}"
         f"{f', {colours} garment colourways in the campaign mockups' if colours > 1 else ''}. "
         f"Story on Gridiron Locker; checkout on {P}."),
        (f"{name} from Gridiron Locker - unofficial, fan-made {team} football {g} "
         f"featuring {art_bit}. {price_phrase.capitalize()}, {size_phrase}, printed after you order. "
         f"{option_phrase}."),
        (f"The {name}: independent {team} fan apparel printed on demand. {g.capitalize()} "
         f"{price_phrase}, {size_phrase}, artwork {art_bit}. Design story here, checkout on {P}."),
    ]
    out = sentence(pick(variants, slug, "meta"))
    if len(out) > 158:
        fallbacks = [
            f"{name} - fan-made {g} for {team} fans, {price_phrase}, {size_phrase}. "
            f"Printed on demand; {option_phrase.lower()}.",
            f"{name}: independent {city} football apparel {price_phrase}, {size_phrase}. "
            f"Printed to order, shipped worldwide. Shop the design on {P}.",
            f"Fan-made {team} {g}: {name}. {price_phrase.capitalize()} in {size_phrase}, printed on demand "
            f"and shipped worldwide. Design story on Gridiron Locker.",
        ]
        out = sentence(pick(fallbacks, slug, "metafb"))
    if len(out) > 158:
        out = sentence(f"{name} - independent fan-made {g}, {price_phrase}, {size_phrase}. "
                       f"Printed on demand and shipped worldwide.")
    if len(out) > 158:
        out = out[:155].rsplit(" ", 1)[0].rstrip(" ,.-") + "..."
    return out


# ---------------------------------------------------------------- value line
# One short fan-focused line under the H1: WHY a fan would wear this, in one
# glance. Not a description (that is the herodeck below), not a claim (no
# stats, no "best"), and never a re-print of the artwork line - for long
# slogans the H1 already carries the words, and the value line carries the
# moment. Two independent banks are hashed per slug, so combinations stay
# specific across the catalogue without a sales feed to rank by.
VALUE_MOMENT = {
    "player": [
        "{person}, the way {short} fans actually say it.",
        "Name-and-number energy - a fan mark, not a replica jersey.",
        "The tribute a {short} fan would print if the shop never would.",
        "For the fans who talk about {person} at every table.",
    ],
    "funny": [
        "The joke lands from across a tailgate lot.",
        "Short joke, big type - funny the way fan shirts should be.",
        "The shirt that gets the laugh before anyone can read it.",
    ],
    "vintage": [
        "Worn-in look, straight off the press.",
        "Throwback styling for people who remember the old way.",
        "The back-of-the-closet feel, without the cracked print.",
    ],
    "rivalry": [
        "A side, taken in public. {short} fans know exactly what it says.",
        "Worn on the days the grudge matters most.",
        "The take, printed loud enough to skip the argument.",
    ],
    "gameday": [
        "Built for {city} game day - loud enough to read from the lot.",
        "Sunday gear for {short} fans who show up in the cold too.",
        "The shirt you reach for when it's {short} football.",
    ],
    "gift": [
        "Easy to give - no roster to keep up with.",
        "A present a {short} fan can wear on Sunday and on Tuesday.",
        "Safe to buy for a fan you only shop for twice a year.",
    ],
    "city": [
        "{city} first, scoreboard second.",
        "Hometown gear that still works at the airport.",
        "The city is the graphic - players come and go.",
    ],
    "new-season": [
        "The 2026 mood, printed before anyone earns a parade.",
        "New-season energy for the {short} faithful.",
        "First weeks of the year, captured in one line.",
    ],
    "statement": [
        "The whole garment is the graphic.",
        "Loud on purpose - made to be seen across a crowded bar.",
        "Not a chest logo. The statement is the shirt.",
    ],
    "culture": [
        "The line {short} fans already say out loud.",
        "Fan-made {short} culture, not a team-shop reprint.",
        "The one idea, printed big enough to stand on.",
    ],
}


def value_line(slug, name, art, col, garment, theme="classic"):
    """Short fan-focused value line (<= ~12 words) under the PDP H1."""
    p = profile(slug, name, art, col, garment, theme)
    # A player-angle design without a recognised person has no name to hang
    # the line on - a generic fan line reads better than an invented one.
    if p["angle"] == "player" and not p["person"]:
        bank = VALUE_MOMENT["culture"]
    else:
        bank = VALUE_MOMENT.get(p["angle"], VALUE_MOMENT["culture"])
    line = pick(bank, slug, "value")
    person = (p["person"] or {}).get("name", "")
    return sentence(line.format(
        person=person,
        short=p["short"], city=p["city"]))


# ---------------------------------------------------------------- short description (30-70 words)
def _fit_plain(chunks, lo, hi):
    acc = []
    for ch in chunks:
        ch = sentence(ch)
        if not ch:
            continue
        nxt = (" ".join(acc + [ch])).strip()
        if word_count(nxt) > hi:
            if not acc:
                words = re.findall(r"\S+", ch)
                acc = [" ".join(words[:hi]).rstrip(".,;:") + "."]
            break
        acc.append(ch)
        if word_count(" ".join(acc)) >= lo and word_count(nxt) > hi - 8:
            break
    text = " ".join(acc)
    # pad if still short
    return text


def _person_line(p):
    person = p["person"]
    if not person:
        return ""
    if person.get("status") == "throwback":
        return (f"It is a fan tribute to {person['name']} - a name-and-number mark, not a "
                f"licensed jersey and not a claim about the current roster.")
    if person.get("role"):
        return (f"The graphic is built around {person['name']}, {person['role']}, the way "
                f"supporters actually talk about him rather than a replica kit.")
    return (f"The graphic is built around {person['name']} as a fan tribute, printed as a "
            f"statement instead of a knock-off jersey.")


def _motif_line(p):
    motifs = p["motifs"]
    art = p["art_title"]
    banks = {
        "bulldog": f"The bulldog is drawn as a character, so {art} still reads from across a tailgate table.",
        "skyline": f"The skyline keeps {p['city']} in the picture, which is the point of a hometown mark.",
        "helmet": f"The helmet silhouette does the recognition work so the lettering can stay blunt.",
        "cheese": f"The cheese graphic is a Wisconsin personality, not a garnish - it is the whole joke.",
        "heart": f"The heart mark is the soft version of a football shirt - still clearly {p['short']}.",
        "skull": f"The skull drawing gives the lettering a harder edge without turning it into a costume.",
        "flag": f"The flag texture is a backdrop, not a claim - the words on top are the fan statement.",
        "map": f"The state outline makes the geography the graphic, which is how hometown shirts earn their keep.",
        "signature": f"The signature treatment is there to feel personal, not to impersonate an autograph session.",
        "crown": f"The crown is a punchline, not a coronation - it is meant to get a laugh in the room.",
        "star": f"Stars and bolts are the Dallas athletics shorthand: loud, simple, readable in motion.",
        "crest": f"The crest layout borrows collegiate weight so the year mark sits like a school seal, not a sticker.",
        "script": f"The script lettering is the whole personality of the piece - one word, drawn to be recognised.",
        "photo": f"The figure is a fan illustration, not a licensed portrait - the type still has to carry the shirt.",
        "beer": f"The drink joke is the kind of line that only works if it is huge and unapologetic.",
        "football": f"The football shape is a frame, not decoration - it holds the words in one glance.",
    }
    for m in motifs:
        if m in banks:
            return banks[m]
    return ""


def short_description(slug, name, art, col, garment, theme="classic"):
    """30-70 word unique short description under the H1. Never a pride cliché.

    The partner hand-off is NOT in the deck: the value line above it sells
    the moment, and the hand-off note, badges, FAQ and schema all state
    where style/colour/size are chosen. A deck that spends half its words
    on logistics teaches the visitor to read the deck as fine print."""
    p = profile(slug, name, art, col, garment, theme)
    g, team, city = p["g"], p["team"], p["city"]
    art_t, phrase = p["art_title"], p["phrase"]
    v = p["voice"]
    person = _person_line(p)
    motif = _motif_line(p)
    voice = _col_voice(col)

    if garment in NON_APPAREL:
        openings = [
            f"{name} puts {art_t} on a {g} for {team} supporters who want the detail without buying another jersey.",
            f"This {g} carries one graphic - {art_t} - printed on demand for {city} football people.",
            f"{phrase} is the whole brief on this {g}: independent {team} fan art, made after you order.",
            f"A small {city} football object: {name}, with {art_t} wrapping the {g}.",
            f"Not apparel - a {g} that still talks like a fan. The artwork is {art_t}.",
            f"{art_t} lands on this {g} as a desk-and-Sunday object for {p['nick'] or team} people.",
            f"Independent {team} fan art, printed on a {g}: {name} is built around {phrase}.",
            f"The {g} exists so {art_t} can live somewhere other than a t-shirt drawer.",
        ]
    else:
        openings = [
            f"{phrase} sits on this {g} as a single readable mark for {team} fans who already say it out loud.",
            f"The graphic is {art_t} - one idea, printed large, drawn for {city} football rather than a replica aisle.",
            f"This {g} belongs at a watch party more than it belongs in a team shop. The artwork, {art_t}, is the whole argument.",
            f"A replica jersey lists a roster. This {g} carries a feeling instead: {phrase}.",
            f"From {city}, this independent {g} puts {art_t} on the chest for {p['nick'] or team} people.",
            f"{name} is built around one idea printed large: {art_t}.",
            f"Nothing on this {g} is trying to look official. {art_t} is a fan mark, and that is the job.",
            f"{art_t} is the shirt. Everything else - spacing, weight, contrast - exists to keep that line alive in bad light.",
        ]

    # Widened and de-templated: every one of these used to be a single fixed
    # sentence, so the same line landed on dozens of product pages (audit F16).
    mark = _voice_line(voice, "mark", slug)
    theme_label = THEME_LABEL.get(p["theme"], "fan")
    middles = [
        f"It is fan-made {team} apparel, printed on demand on a {g}, for people who want the culture without the licensed costume.",
        f"Independent artwork means the line can be the thing supporters actually shout, not the thing a brand is allowed to print.",
        f"{mark} That is the whole idea behind it.",
        f"The {g} is meant to be {p['v']} on Sundays and on the six ordinary days around them.",
        f"It reads as {an(theme_label)} {theme_label} design, not a reprint of a shop wall.",
        f"Nothing here is licensed, which is exactly why {phrase} is allowed to be this blunt.",
        f"Drawn by fans for {city} fans, printed one at a time rather than in a warehouse run.",
        f"Because it is made after you order, the artwork never ends up in a clearance bin.",
    ]
    # The collection's "sunday" voice line is garment-specific flavour -
    # Michigan's says "crewneck weather", so a t-shirt must not inherit it.
    # It is folded in only on the layers it describes.
    layer_only = garment in ("Hoodie", "Sweatshirt", "Long Sleeve Shirt")
    # The tail used to be the same three sentences on every page ("that is the
    # brief, not a moodboard" appeared on 54 of them, in agency jargon no
    # customer uses). Now one line is drawn per slug from a wide pool, and each
    # variant is built from this product's own phrase, artwork or city.
    tails = [
        f"The printed line stays {phrase}, so the piece says one thing clearly.",
        f"{art_t} is the only graphic on it - nothing competes for the read.",
        f"It is made for {city} football culture rather than a generic league aisle.",
        f"Read it from across a room and you still get {phrase}.",
        f"Fan-drawn rather than licensed: {art_t} is ours, and it stays that way.",
        f"Printed after you order it, so {phrase} is never out of stock.",
        f"One mark, one colour story: {art_t} and the space kept around it.",
        f"{p['nick'] or team} people already say {phrase}; this just prints it.",
        f"Made to order in the colours {city} football actually wears.",
        f"The artwork holds up at the size it is printed, not just in a thumbnail.",
        f"No seasonal roster to date it - {art_t} outlasts a depth chart.",
        f"{phrase} is printed at the size the room can read it.",
    ]
    if garment not in NON_APPAREL:
        tails += [
            f"The {g} is cut for a crowd, not for a photo shoot.",
            f"Wear it to the game, to the bar, or to the six days in between.",
        ]
    extras = [person, motif, pick(tails, slug, "tail")]
    if layer_only:
        extras.append(_voice_line(voice, "sunday", slug))

    chunks = [openings[v], pick(middles, slug, "sdm")]
    # fold in extras until we are inside 30-70
    for extra in extras:
        if extra and extra not in chunks:
            chunks.append(extra)
    text = _fit_plain(chunks, 30, 70)
    w = word_count(text)
    if w < 30:
        pad = (f" The {g} is printed to order for {team} fans, with the artwork held at "
               f"{art_t} so the piece stays specific.")
        text = sentence(text + pad)
    if word_count(text) > 70:
        words = re.findall(r"\S+", text)
        text = " ".join(words[:70]).rstrip(".,;:") + "."
    return sentence(text)


def hero_line(slug, name, art, col, garment):
    """Back-compat alias: the short description is the hero deck now."""
    return short_description(slug, name, art, col, garment)


def _lev(a, b):
    """Small Levenshtein: alt strings are short, and this keeps a crawl typo
    out of screen-reader text (see typo_variant)."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def typo_variant(name, art):
    """True when `art` is the same phrase as `name` mangled by the crawl.

    The Mayzing/Viralstyle crawls delivered a few artwork strings that are the
    product name with a transposition or a dropped letter ("DAWG" -> "DWAG",
    "Beware Of Dawg" -> "BE AWAR OF DAWG"). Whether the typo is also printed on
    the garment is unknowable from the crawl, but alt text is a description for
    assistive tech and image search, not a transcription: it should carry the
    curated name. Card alts that printed both strings read as a visible typo on
    the homepage, /collections/, /search/ and the team pages.
    """
    n = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    x = re.sub(r"[^a-z0-9]", "", (art or "").lower())
    if not n or not x:
        return False
    return x == n or sorted(x) == sorted(n) or _lev(n, x) <= 2


def image_alt(name, art, garment, team, n=None):
    art_bit = title_case_art(name if typo_variant(name, art) else art)
    if len(art_bit) > 64:
        art_bit = art_bit[:62].rsplit(" ", 1)[0]
    base = f"Fan-made {team} {garment.lower()} with {art_bit} graphic"
    if n:
        return f"{base}, view {n}"
    return base


# ---------------------------------------------------------------- about (kept for callers; PDP uses story + short desc)
def about_design(slug, facts, col, garment, art, theme):
    """ABOUT THIS DESIGN - kept for compatibility; PDP no longer renders it."""
    p = profile(slug, facts["name"], art, col, garment, theme)
    concept = pick(THEME_CONCEPT.get(theme, THEME_CONCEPT["classic"]), slug, "concept")
    lore = pick(col["lore"], slug, "lore")
    label = THEME_LABEL.get(theme, "fan")
    g = garment.lower()
    art_noun = "reads" if is_slogan(art) else "shows"
    opens = [
        f"<p><strong>{facts['name']}</strong> is {an(label)} {label} design for {col['team']} "
        f"supporters. The artwork {art_noun} <em>{artline(art)}</em>, printed as the single "
        f"focal point of the {g} rather than one graphic among several.</p>",
        f"<p>This is {an(label)} {label} piece from the {col['name']} range. The {g} carries one "
        f"graphic - <em>{artline(art)}</em> - sized so it is the first thing anyone notices.</p>",
        f"<p><strong>{facts['name']}</strong> takes a single idea, <em>{artline(art)}</em>, and "
        f"builds the whole {g} around it. It is {an(label)} {label} design, not a team-shop "
        f"reprint.</p>",
    ]
    body = [f"<p>{concept} {lore}</p>", f"<p>{lore} {concept}</p>"]
    close = [
        f"<p>It is an independent design, which is the point: you are not going to see it on four "
        f"other people in the same section, and it does not carry a licensed logo it has no right "
        f"to. What it carries is the sentiment {col['team']} fans already say out loud.</p>",
        f"<p>Because it is fan-made rather than licensed, the design can say the thing supporters "
        f"actually shout instead of the thing a brand is allowed to print. That is usually the "
        f"difference between a shirt that gets worn and one that stays folded.</p>",
        f"<p>Independent artwork gives it a different job from a replica jersey. A jersey says who "
        f"is playing; this says who you are in the room - which is why it works well outside the "
        f"stadium too.</p>",
    ]
    return (pick(opens, slug, "about1") + pick(body, slug, "about2")
            + pick(close, slug, "about3"))


# ---------------------------------------------------------------- story (150-300 words)
def _story_origin(p, slug):
    g, phrase, art = p["g"], p["phrase"], p["art"]
    name = p["name"]
    # The "readable where" clause used to be one fixed sentence ("...with a
    # drink in the other hand") printed on 20 pages; it is now drawn from a
    # pool per slug so the story does not rhyme across the catalogue.
    readable = pick([
        "at a walk, in bad light, with a drink in the other hand",
        "from ten feet away in a room that is already loud",
        "while the crowd is still finding its seat",
        "across a bar, at speed, in a jacket",
        "on a concourse with three seconds of attention",
    ], slug, "read")
    if p["slogan"]:
        opts = [
            f"{name} starts with a line {p['team']} fans already know how to shout: "
            f"<em>{phrase}</em>. The {g} is not a poster with sleeves. It is that phrase, set "
            f"heavy enough to survive a parking-lot glance, with everything else in the layout "
            f"told to get out of the way.",
            f"The starting point for {name} was the phrase itself. <em>{phrase}</em> is short enough to "
            f"print large on {an(g)} {g}, which is why it works as apparel instead of a caption "
            f"under a photograph.",
            f"Every piece in this locker begins with something a {p['team']} supporter would "
            f"actually say. Here the line is <em>{phrase}</em>, and the drawing exists to keep "
            f"it readable {readable}.",
            f"<em>{phrase}</em> is the entire origin story of {name}. Nobody asked for a second "
            f"idea. The {g} is the first idea, held still long enough to print.",
            f"There is no second concept on {name}. <em>{phrase}</em> was written first and the "
            f"layout was built to carry it {readable.split(',')[0]} - heavy type, generous space, "
            f"nothing else asking to be read.",
            f"{name} began as a phrase rather than an illustration: <em>{phrase}</em>. Once it "
            f"was set large enough to read {readable}, the {g} needed nothing added to it.",
        ]
    else:
        opts = [
            f"{name} starts as a drawing, not a caption. The artwork is <em>{art}</em>, composed "
            f"so it is recognised before it is examined - scale first, detail second, nothing "
            f"competing with the read.",
            f"The starting point was the image: <em>{art}</em>. On {an(g)} {g} that means thick "
            f"shapes, generous space, and a composition that still holds when someone is moving "
            f"past you in a concourse.",
            f"This one began as a picture. <em>{art}</em> is simple enough to hold together at "
            f"{g} scale, which is more than most illustrations manage once they leave a screen.",
            f"{name} is built around one graphic - <em>{art}</em> - drawn to be the first thing "
            f"in the room, not the tenth thing on a busy print.",
        ]
    return pick(opts, slug, "st1")


def _story_craft(p, slug):
    g = p["g"]
    motif = _motif_line(p)
    person = _person_line(p)
    # Every sentence names this design (its title, phrase or artwork). Pools of
    # four fixed sentences put the same line on 20+ of the 84 product pages,
    # which reads as template filler to a human and as thin content to a
    # crawler (2026-09-18 audit, F16).
    opts = [
        f"{p['name']} faces a constraint poster art never does: it is seen in passing, in bad "
        f"light, for about two seconds. {p['art_title']} is drawn for those two seconds - heavy "
        f"shapes, generous spacing, no thin strokes that vanish on a dark {g}.",
        f"A mark like {p['art_title']} has to work at arm's length and across a room, which "
        f"rules out fine line work and busy backgrounds. The composition stays blunt on "
        f"purpose: {p['phrase']}, strong contrast, and enough space around it that the fabric "
        f"colour does the rest.",
        f"The print process shapes {p['art_title']} as much as the idea does. Everything is "
        f"printed to order rather than screen-printed in bulk, so {p['name']} is prepared to "
        f"hold its edges on the actual {g} and to keep contrast across the light and dark "
        f"options.",
        f"On a {g}, the type behind {p['phrase']} has to survive motion - which is why "
        f"{p['art_title']} is treated as a mark rather than a paragraph: weight, spacing and "
        f"contrast, in that order.",
    ]
    body = pick(opts, slug, "st2")
    extra = person or motif
    if extra:
        return f"{body} {extra}"
    return body


def _story_football(p, col, slug):
    voice = _col_voice(col)
    lore = pick(col["lore"], slug, "lore")
    chant = p["chant"]
    opts = [
        f"{voice['place']} {lore} The graphic belongs to that room: {p['city']} football, not a "
        f"generic league aisle.",
        f"{voice['weather']} {p['art_title']} is drawn for that climate, which is why it does not "
        f"need a licensed logo to feel local.",
        f"{_voice_line(voice, 'sunday', slug)} A piece carrying <em>{p['phrase']}</em> is meant to sit in that weekly "
        f"habit, not in a one-weekend costume.",
        f"{lore} {_voice_line(voice, 'mark', slug)} The football connection here is "
        f"{p['art_title']}: culture first, scoreboard second.",
    ]
    text = pick(opts, slug, "st3")
    if chant and chant.lower() not in text.lower():
        text += pick([
            f' The crowd already has a chant for it: "{chant}", which is why '
            f'{p["phrase"]} needs no introduction in this collection.',
            f' It is also a chant town - "{chant}" - so a line as short as '
            f'{p["phrase"]} lands without any setup.',
            f' And there is a chant for it: "{chant}", the nearest thing this '
            f'fanbase has to a house style, which {p["art_title"]} sits inside comfortably.',
            f' The stands already supply the soundtrack ("{chant}"); '
            f'{p["art_title"]} only has to hold its own against that noise.',
        ], slug, "chant")
    return text


def _story_difference(p, slug):
    g, team = p["g"], p["team"]
    angle = p["angle"]
    angle_line = {
        "player": (f"A licensed jersey says who is playing. This {g} says who you stood with. "
                   f"That is a different job, and it is why a name-and-number fan mark still "
                   f"works when it is not embroidered by a league shop."),
        "funny": (f"Funny football shirts fail when they need a paragraph. This one does not. "
                  f"{p['phrase']} is the joke, printed at the size a tailgate requires."),
        "vintage": (f"Throwback styling is easy to fake and easy to cheapen. Here the lettering "
                    f"is the era cue; the print itself is modern, so the {g} looks lived-in "
                    f"without arriving already cracked."),
        "rivalry": (f"Rivalry graphics are not subtle, and they should not be. {p['phrase']} is "
                    f"a side, taken in public, which is the whole point of wearing it out of "
                    f"the house."),
        "gameday": (f"Game-day graphics have one job: be readable when the room is already loud. "
                    f"{p['art_title']} is built for that noise, not for a lookbook."),
        "gift": (f"Gift designs fail when they require a roster update. This one is a feeling "
                 f"someone already has about {team} football, printed cleanly enough to give "
                 f"with no explanation needed."),
        "city": (f"City designs outlast depth charts. {p['city']} stays put. That is why "
                 f"{p['art_title']} is a safer long-term mark than a single season's hero."),
        "new-season": (f"A new-season graphic is a temperature check, not a prediction. "
                       f"{p['phrase']} is the mood of the locker, printed before anyone has "
                       f"earned a parade."),
        "statement": (f"All-over prints are supposed to be too much. The {g} is the canvas; "
                      f"{p['art_title']} is allowed to use all of it."),
        "culture": (f"Independent artwork lets the {g} say the thing {team} fans already say. "
                    f"That is usually the difference between a piece that gets worn and one "
                    f"that stays folded."),
    }.get(angle)
    opts = [
        angle_line,
        f"Because it is fan-made rather than licensed, {p['name']} can carry {p['phrase']} "
        f"without borrowing a mark it has no right to. "
        + pick([
            f"You are buying the sentiment behind {p['phrase']}, not a replica.",
            f"What is on offer is the feeling {p['art_title']} carries, not a club badge.",
            f"Nobody is selling you a copy of {team} kit here - just the line "
            f"{p['phrase']} the way fans already say it.",
            f"So the thing you take home is {p['phrase']}, not a licence number.",
        ], slug, "std-buy"),
        f"The difference from a team-shop reprint is simple: this {g} is one idea, {p['art_title']}, "
        f"drawn for {team} supporters instead of a catalogue of approved icons.",
    ]
    return pick([o for o in opts if o], slug, "st4")


def _story_close(p, slug, col=None):
    P = partner_of((col or {}).get("key"))
    g = p["g"]
    opts = [
        f"What you end up with is {an(g)} {g} that says something specific about being a "
f"{p['team']} fan, rather than something generic about liking football. If "
f"{p['phrase']} is the read you wanted, the rest is logistics: verified styles on "
        f"this page, then {P} for the size and colour you actually wear.",
        f"{p['name']} is a small idea executed cleanly, which is generally what makes fan "
        f"apparel get {p['v']} more than once a season. Nothing about {p['art_title']} needs "
        f"a second look to land.",
        f"{p['name']} belongs to {p['city']} without needing a licence to prove it. Wear it, or "
        f"give it, or leave it on a shelf until Sunday - the graphic will still be {p['phrase']}.",
        f"If you already talk like this on Sundays, the {g} is just the public version of "
        f"{p['phrase']}. "
        + pick([
            f"{p['art_title']} does not need a caption once it is on your chest.",
            f"{p['art_title']} carries it without an explanation attached.",
            f"The artwork says {p['phrase']} and leaves it at that.",
            f"Once it is printed at that size, {p['art_title']} explains itself.",
        ], slug, "stc-cap"),
    ]
    return pick(opts, slug, "st5")


def design_story(slug, facts, col, art, theme, garment):
    """THE STORY BEHIND THE DESIGN - 150-300 words, unique to this artwork."""
    p = profile(slug, facts["name"], art, col, garment, theme)
    chunks = [
        _story_origin(p, slug),
        _story_craft(p, slug),
        _story_football(p, col, slug),
        _story_difference(p, slug),
        _story_close(p, slug, col),
    ]
    html = paras(*chunks)
    w = word_count(html)
    if w < 150:
        html += paras(
            f"{p['name']} stays specific because the artwork stays <em>{p['art']}</em> - not a "
            f"template with the city name swapped. That is the whole reason it gets its own page."
        )
    if word_count(html) > 300:
        # drop the last paragraph if we overshot
        parts = re.findall(r"<p>.*?</p>", html)
        while len(parts) > 3 and word_count("".join(parts)) > 300:
            parts.pop()
        html = "".join(parts)
    return html


# ---------------------------------------------------------------- why it stands out
def why_it_stands_out(slug, facts, col, art, theme, garment):
    """WHY THIS DESIGN STANDS OUT - SEO angle, unique to this design."""
    p = profile(slug, facts["name"], art, col, garment, theme)
    g, team, city = p["g"], p["team"], p["city"]
    angle = p["angle"]
    person = p["person"]

    if angle == "player" and person:
        if person.get("status") == "throwback":
            lead = (f"{p['name']} stands out because it is a fan tribute to {person['name']}, "
                    f"printed as {p['art_title']} rather than a licensed replica. It is about the "
                    f"way supporters remember a player, not a claim about who is taking snaps now.")
        elif person.get("role"):
            lead = (f"{p['name']} stands out as a {person['name']} fan {g} - {person['role']} - "
                    f"built around {p['phrase']} instead of a knock-off jersey. The relevance is "
                    f"the name supporters are already searching; the graphic is how they wear it.")
        else:
            lead = (f"{p['name']} stands out as a player tribute: {person['name']} rendered as "
                    f"{p['art_title']}, a fan mark rather than official kit.")
    elif angle == "funny":
        lead = (f"What makes {p['name']} different is the joke. {p['phrase']} is a punchline "
                f"{team} fans will get with no explanation needed, printed at the size a tailgate needs. "
                f"Funny football shirts only work when they do not explain themselves.")
    elif angle == "vintage":
        lead = (f"{p['name']} stands out as vintage {city} football styling: worn-in athletics "
                f"lettering and {p['art_title']}, printed with a modern process so the throwback "
                f"look does not arrive already cracked.")
    elif angle == "rivalry":
        lead = (f"This is a rivalry piece. {p['phrase']} picks a side in public, which is the "
                f"whole job of a {team} fan {g}. It is not trying to be polite, and it is not "
                f"trying to look licensed.")
    elif angle == "gameday":
        lead = (f"{p['name']} is built for game day: {p['art_title']} set loud enough to read "
                f"when the room is already shouting. It is a Sunday {g}, not a quiet graphic.")
    elif angle == "gift":
        lead = (f"{p['name']} stands out as a gift because the artwork - {p['art_title']} - is "
                f"not tied to a single roster move. It is the feeling someone already has about "
                f"{team} football, printed cleanly enough to wrap.")
    elif angle == "city":
        lead = (f"Hometown first. {p['name']} puts {city} on the {g} through {p['art_title']}, "
                f"which is why it still makes sense on a Tuesday and at an airport, not only "
                f"in the stands.")
    elif angle == "new-season":
        lead = (f"{p['name']} is a new-season mark: {p['phrase']} as a temperature check for "
                f"{team} fans, printed before anyone has a parade to sell. It is mood, not a "
                f"prediction.")
    elif angle == "statement":
        lead = (f"The {g} is the canvas. {p['art_title']} runs as a full-bleed statement, which "
                f"is a different job from a chest-sized box of type.")
    else:
        lead = (f"{p['name']} stands out because the artwork stays specific: {p['art_title']}, "
                f"drawn for {team} supporters instead of a generic football aisle. Independent "
                f"fan art can say {p['phrase']} exactly the way the crowd says it.")

    extra = pick([
        f"You will not find {p['art_title']} in a league shop, and that is the point of an "
        f"unofficial {g}.",
        f"The search is for a {team} fan {g}; the reason to pick this one is {p['phrase']}.",
        f"Plenty of fan pieces mention {city}. Fewer of them are actually about {p['phrase']}.",
        f"If you wanted a replica you would already own one - this is the other kind of "
        f"{g}, the one built around {p['phrase']}.",
    ], slug, "whyx")
    return paras(lead, extra)


# ---------------------------------------------------------------- who / game day
def who_its_for(slug, col, theme, garment, price, name="", art="", styles=None):
    aud = _c.audience(theme, col)
    a = pick_n(aud, slug, "aud", min(3, len(aud)))
    city = col["city"].split(",")[0]
    g = garment.lower()
    art_t = title_case_art(art) if art else ""
    lead_name = name if name else "This design"
    art_bit = f" The artwork, {art_t}," if art_t else " It"
    lead = pick([
        f"{lead_name} is aimed at {a[0]}, {a[1] if len(a) > 1 else 'lifelong supporters'} and "
        f"anyone who has spent a season explaining {col['team']} football to people who do not follow it."
        f"{art_bit} is the public version of that explanation.",
        f"It suits {a[0]} and {a[1] if len(a) > 1 else 'everyday fans'} best - the people who "
        f"want allegiance without a full replica kit.{art_bit} keeps the statement on the {g} "
        f"instead of on a numbered jersey.",
        f"Think {a[0]}, {a[1] if len(a) > 1 else 'gift buyers'}, and {city} supporters who "
        f"moved away and still set an alarm for kickoff.{art_bit} travels because the idea is "
        f"the city and the club, not a seating chart.",
    ], slug, "who1")
    if garment in NON_APPAREL or garment == "Beanie":
        gift = pick([
            f"As a gift, {name or 'this piece'} is straightforward: no size to get wrong, a "
            f"design that does not depend on knowing a roster, and a price that starts at "
            f"${price}.",
            f"{name or 'It'} also works as a present - nothing in the design expires with a "
            f"transfer, and it starts at ${price}.",
            f"Buying {name or 'one'} for someone else is low risk: there is no sizing decision, "
            f"the artwork is not tied to a single week of the season, and pricing starts at "
            f"${price}.",
        ], slug, "who2")
    else:
        fit = fit_note(styles)
        gift = pick([
            f"As a gift, {name or 'this piece'} is straightforward: {fit.lower()} Nothing in "
            f"{name or 'the design'} depends on knowing a roster, and pricing starts at "
            f"${price}.",
            f"{name or 'It'} also works as a present: nothing in the design expires with a "
            f"transfer, {fit.lower()} and it starts at ${price}.",
            f"Buying {name or 'one'} for someone else is low risk - {fit.lower()} "
            f"{name or 'The artwork'} is not tied to a single week of the season, and pricing "
            f"starts at ${price}.",
        ], slug, "who2")
    return f"<p>{sentence(lead)}</p><p>{sentence(gift)}</p>"


def gameday_wear(slug, col, garment, art):
    ctx = pick_n(WEAR_CONTEXT, slug, "ctx", 3)
    layer = layer_note(garment, slug)
    g = garment.lower()
    v = wear_verb(garment)
    art_t = title_case_art(art)
    closers = [
        f"Because {art_t} is a fan statement rather than a licensed team mark, it does not look "
        f"out of place away from the stadium either - the difference between a piece "
        f"{v} seventeen Sundays a year and one {v} most weeks.",
        f"It also survives the rest of the week, because a fan-made graphic like {art_t} reads "
        f"as a graphic first - it works on a commute or a Saturday errand in a way a replica "
        f"jersey does not.",
        f"This {g} is made for normal use rather than a stadium costume, which is why most of "
        f"the fans who buy {art_t} end up wearing it well outside "
        f"{col['city'].split(',')[0]} and well outside football season.",
    ]
    return (f"<p>Where this {g} actually gets {v}: {ctx[0]}, {ctx[1]}, and {ctx[2]}. "
            f"{layer} The graphic stays {art_t} in all of those rooms.</p>"
            + f"<p>{pick(closers, slug, 'wear')}</p>")


def styles_copy(slug, styles, garment, col=None):
    P = partner_of((col or {}).get("key"))
    """AVAILABLE APPAREL - verified style list only."""
    if garment in NON_APPAREL and styles:
        return (f"<p>This artwork is published across <strong>{len(styles)} product "
                f"variations</strong> in the campaign, listed below exactly as the campaign shows "
                f"them. Pick the one you want on the {P} product page, where each variation "
                f"carries its own price.</p>")
    if not styles:
        return (f"<p>This design is printed on a {garment.lower()}. The exact garment options for "
                f"this campaign are listed on the {P} product page.</p>")
    n = len(styles)
    if n == 1:
        return (f"<p>This campaign prints the design on one garment: <strong>{styles[0]}</strong>. "
                f"You confirm your size on the {P} product page.</p>")
    return (f"<p>The campaign for this design offers <strong>{n} garment styles</strong>. "
            f"They are listed below exactly as the campaign publishes them - pick the one you "
            f"want on the {P} product page, where each style shows its own price.</p>")


def apparel_heading(garment):
    return "Available Products" if garment in NON_APPAREL else "Available Apparel"


def colour_copy(colours, col=None, name=None, garment=None):
    P = partner_of((col or {}).get("key"))
    """AVAILABLE COLOURS - never invent names, never fake a picker."""
    if colours > 1:
        if garment == "Beanie":
            choice = "colour and finish"
        elif garment == "Mug":
            choice = "mug option"
        elif garment == "Phone Case":
            choice = "device model"
        else:
            choice = "garment style, colour and size"
        return (f"<p>This design is available in multiple garment colourways. The mockups below "
                f"are taken from the live campaign - <strong>{colours} colour variations</strong> "
                f"were published for this design. They are previews, not selectors: choose your "
                f"{choice} on the {P} product page.</p>"
                f"<p>Colour previews are shown to help you choose your look. Final colour "
                f"selection is made on {P}.</p>")
    if name:
        # A Mayzing product is published in exactly one colourway and
        # data/mayzing_products.json carries its verified name off the
        # storefront - state it instead of the crawled-campaign hedge below.
        if garment == "Beanie":
            handoff = "confirm the available colour and finish"
        elif garment == "Mug":
            handoff = "confirm the available mug option"
        elif garment == "Phone Case":
            handoff = "choose your device model"
        else:
            handoff = "confirm your size"
        return (f"<p>This product is sold in <strong>one colourway: {name}</strong>. The mockup "
                f"above shows it exactly as {P} prints it, and the {P} product page is where you "
                f"{handoff} before checkout.</p>")
    return (f"<p>Multiple colour options may be available for this design. Garment colours are set "
            f"per campaign, so the current list is shown on the {P} product page.</p>")


def fit_note(styles):
    """Describe the cut actually listed by a campaign, without guessing."""
    text = " ".join(styles or []).lower()
    women = "women" in text or "ladies" in text
    men = re.search(r"\bmen'?s\b", text) is not None
    unisex = "unisex" in text
    if women and not men and not unisex:
        return "This campaign lists a women's cut."
    if men and not women and not unisex:
        return "This campaign lists a men's cut."
    return "Sizing is unisex for the listed apparel styles."


def size_copy(slug, sizes, garment, col=None, styles=None):
    P = partner_of((col or {}).get("key"))
    if garment in ("Mug", "Phone Case"):
        return (f"<p>This is not an apparel item, so there is no size to choose. Any model or "
                f"capacity options are shown on the {P} product page.</p>")
    if garment == "Beanie":
        return ("<p>One size fits most adults - a stretch knit body with a folded cuff.</p>")
    rng = f"{sizes[0]} to {sizes[-1]}"
    return (f"<p>This campaign is offered in <strong>{len(sizes)} sizes: {rng}</strong> "
            f"({', '.join(sizes)}). {fit_note(styles)} "
            f"The measurement chart below is a guide - the size you select is confirmed on the "
            f"{P} product page.</p>")


def parse_features(feat):
    if not feat:
        return []
    parts = re.split(r"\s+-\s+", str(feat))
    out = []
    for p in parts:
        p = p.strip(" -\t")
        if p and len(p) > 2:
            out.append(p)
    return out


def details_bullets(garment, styles, sizes, colours, price, features="", col=None):
    P = partner_of((col or {}).get("key"))
    g = _c.GARMENT_COPY.get(garment, _c.GARMENT_COPY["T-Shirt"])
    out = ["Independent, fan-made design - not official or licensed team merchandise",
           "Printed on demand after the order is placed, so nothing is warehouse stock"]
    if styles:
        out.append(f"{len(styles)} garment style{'s' if len(styles) != 1 else ''} offered by this "
                   f"campaign" if len(styles) > 1 else f"Printed on the {styles[0]}")
    if garment not in ("Mug", "Phone Case", "Beanie"):
        out.append(f"Sizes {sizes[0]}-{sizes[-1]} ({len(sizes)} sizes)")
    if colours > 1:
        out.append(f"{colours} garment colourways published in the campaign mockups")
    if P == "Mayzing" and len(styles) == 1 and colours == 1:
        out.append(f"One garment style and one colourway at ${price} on Mayzing")
    elif styles:
        out.append(f"Pricing starts at ${price}; each garment style is priced individually on {P}")
    else:
        out.append(f"Campaign pricing starts at ${price}; the final option price is shown on {P}")
    out.append("Worldwide shipping with tracking issued at dispatch")
    verified = parse_features(features)
    if verified:
        out.extend(verified[:4])
    else:
        out.extend(g["bullets"][:3])
    return out


def shipping_copy(delivery_time, ship_from, col=None):
    """Shipping block for a product page.

    ``delivery_time`` / ``ship_from`` are Viralstyle's published figures, so
    they are only ever printed on a Viralstyle product. A Mayzing product
    publishes no rate and no window - its page says only that delivery times
    vary by location, and its cart calculates the live rate - so quoting
    Viralstyle's numbers there would be a false shipping claim.
    """
    P = partner_of((col or {}).get("key"))
    head = (f"<p>Every item is printed after the order is placed - there is no warehouse stock "
            f"to ship from, which is why the catalogue can stay this wide without anything "
            f"selling out. Production takes a few business days, then the parcel moves.</p>")
    if P == "Viralstyle":
        return (head +
                f"<p><strong>United States:</strong> standard shipping from ${ship_from}, "
                f"typically {delivery_time} from order to doorstep including production. "
                f"<strong>International:</strong> worldwide delivery is available; the exact "
                f"rate and estimate for your address is calculated at checkout on {P}.</p>"
                f"<p>If an item arrives misprinted, damaged or defective it is replaced within "
                f"30 days. Delivery estimates are estimates - if you need a piece for a specific "
                f"game, order early in the week rather than the night before.</p>")
    return (head +
            f"<p><strong>Shipping:</strong> this design is printed and shipped by {P}, which "
            f"calculates the live rate for your address in its cart. Production and delivery "
            f"times vary by product and destination, so the current figures are shown at "
            f"checkout rather than quoted here.</p>"
            f"<p>If an item arrives misprinted, damaged or defective, contact support with a "
            f"photo and your order number and it is handled under {P}'s return policy, shown at "
            f"checkout. Allow extra time if you need a piece for a specific game - order early "
            f"in the week rather than the night before.</p>")


def disclosure():
    return ("Gridiron Locker is an independent fan-made store. These designs are not officially "
            "licensed by any team, league, university or player.")


def faqs(slug, facts, col, garment, price, colours, styles, sizes, colour=None):
    """Product FAQ - answers the handoff questions explicitly."""
    name = facts["name"]
    P = partner_of(col.get("key"))
    g = garment.lower()
    art = facts.get("art") or name
    out = []

    out.append((f"What is printed on the {name}?",
                f"The artwork is {artline(art)}. It is an independent, fan-made graphic for "
                f"{col['team']} supporters, not official team merchandise."))

    if colours > 1:
        out.append((f"What colours does the {name} come in?",
                    f"This campaign published {colours} garment colour variations, previewed on "
                    f"this page as campaign mockups. Colour availability is set per campaign and "
                    f"can change, so the current, authoritative list is on the {P} product "
                    f"page - that is also where you select the one you want."))
    else:
        if colour:
            out.append((f"What colours does the {name} come in?",
                        f"This product is sold in one colourway: {colour}. Colour availability "
                        f"is set by the campaign; if more are ever published they appear on the "
                        f"{P} product page first."))
        else:
            out.append((f"What colours does the {name} come in?",
                        f"Colour options vary by campaign. Visit the {P} product page for this "
                        "design to see the colours currently offered."))

    if garment in ("Mug", "Phone Case"):
        out.append(("What sizes or models are available?",
                    "This is not an apparel item, so there is no garment size. Any model or "
                    f"capacity choice is made on the {P} product page."))
    elif garment == "Beanie":
        out.append(("What sizes are available?",
                    "One size fits most adults - a stretch knit body with a folded cuff."))
    else:
        out.append(("What sizes are available?",
                    f"Sizes {sizes[0]} to {sizes[-1]} ({', '.join(sizes)}) for this campaign. "
                    f"{fit_note(styles)} The measurement chart on this page shows chest width and "
                    f"body length in inches. You pick your size on the {P} product page."))

    if garment == "Beanie":
        handoff_q = "Where do I choose my beanie colour and finish?"
        handoff_a = (f"On {P}. Gridiron Locker is where you see the design and the details; "
                     f"the available colour and finish are confirmed on the {P} product page "
                     "immediately before checkout.")
    elif garment == "Mug":
        handoff_q = "Where do I choose my mug option?"
        handoff_a = (f"On {P}. Gridiron Locker is where you see the design and the details; "
                     f"the available mug option is confirmed on the {P} product page "
                     "immediately before checkout.")
    elif garment == "Phone Case":
        handoff_q = "Where do I choose my phone-case model?"
        handoff_a = (f"On {P}. Gridiron Locker is where you see the design and the details; "
                     f"your device model is selected on the {P} product page immediately "
                     "before checkout.")
    else:
        handoff_q = "Where do I choose my shirt colour, style and size?"
        handoff_a = (f"On {P}. Gridiron Locker is where you see the design and the details; "
                     f"garment style, colour and size are selected on the {P} product page for "
                     "this campaign, immediately before checkout.")
    out.append((handoff_q, handoff_a))

    out.append(("Where is checkout completed?",
                f"Orders are placed and paid for on {P}, the print-on-demand partner that "
                "runs this campaign. Gridiron Locker never takes payment or handles your card "
                "details - the SHOP NOW button hands you over to the campaign page."))

    out.append((f"Is the {name} official team merchandise?",
                "No. This is an independent, fan-made design. It is not affiliated with, endorsed "
                "by, sponsored by or licensed by any professional or collegiate team, league or "
                "player. Team and city names are used only to describe who the artwork is for."))

    out.append(("How is the product made?",
                f"It is printed on demand. Once your order is placed on {P} the {g} is "
                f"printed and finished, then shipped with tracking. Nothing is pre-printed, so "
                f"there is no dead stock and no 'sold out' on a design that is still live."))

    if styles and len(styles) > 1:
        out.append(("Can I get this design on a hoodie or sweatshirt instead?",
                    "The campaign offers " + ", ".join(styles[:6])
                    + (" and more. " if len(styles) > 6 else ". ")
                    + f"Each style is priced separately and selected on the {P} product page."))

    if styles and len(styles) == 1:
        out.append(("How much does it cost?",
                    f"This design is ${price} on {P}: one garment style at one flat price. The "
                    f"final total - including any size surcharge for extended sizes - is the one "
                    f"shown on {P} before you pay."))
    else:
        out.append(("How much does it cost?",
                    f"Pricing for this design starts at ${price}. The final total for the "
                    f"campaign option you choose is the amount shown on {P} before you pay."))

    out += [(q, a) for q, a in col.get("faq_extra", [])]
    return out[:9]


def keywords(facts, col, garment, name):
    """Search-intent keyword set: design name, team, apparel, fan-made, game day."""
    base = list(facts.get("kw", []))
    n = name.lower()
    team = col["team"].lower()
    city = col["city"].split(",")[0].lower()
    g = garment.lower()
    base += [n, f"{n} {g}", f"{team} fan shirt", f"{team} football apparel",
             f"{city} football {g}", "fan-made football shirt", "game day shirt"]
    person = find_person(name, facts.get("art") or "")
    if person:
        base.append(f"{person['name'].lower()} shirt")
    seen, out = set(), []
    for k in base:
        k = re.sub(r"\s+", " ", k.strip().lower())
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out[:12]
