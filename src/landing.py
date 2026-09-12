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

LAYER_NOTE = {
    "T-Shirt": "It layers under a hoodie or a jacket once the temperature drops, which is most of "
               "the second half of the season.",
    "Hoodie": "It is the outer layer for cold kickoffs and the only layer for indoor watch parties.",
    "Sweatshirt": "A crewneck sits between a tee and a jacket, which makes it the most-worn piece "
                  "in most fans' rotations.",
    "Long Sleeve Shirt": "Long sleeves cover the shoulder season - the weeks when a tee is not "
                         "enough and a hoodie is too much.",
    "Beanie": "It works from the first cold road game to the last week of the season.",
    "Mug": "It lives on a desk all week and comes out again on Sunday morning.",
    "Phone Case": "It is the fan detail that goes everywhere the rest of your gear does not.",
}

COL_VOICE = {
    "cleveland-browns": {
        "weather": "Cleveland football weather is Lake Erie weather - grey, loud, and not interested in fair-weather kits.",
        "place": "The Dawg Pound has always been cheaper seats and a bigger mouth, which is the culture this collection draws from.",
        "mark": "Orange and brown is an awkward combination until it is yours, and then it is the whole personality.",
        "sunday": "Cleveland fans measure the year in Sundays, not months.",
    },
    "green-bay-packers": {
        "weather": "Green Bay football is cold air, louder cheese, and a public team that still feels like it belongs to the town.",
        "place": "Lambeau weather is the filter: if a graphic cannot be read with a hoodie up, it is not finished.",
        "mark": "Green and gold is a winter colourway. It looks right with snow on the sideline.",
        "sunday": "Sunday in Cheesehead Nation is less a hobby than a municipal calendar.",
    },
    "dallas-cowboys": {
        "weather": "Dallas football style sits halfway between a stadium concourse and a Texas highway - stars, silver, and a little country.",
        "place": "The city mark matters here as much as the scoreboard. Texas pride travels.",
        "mark": "Silver and navy reads as vintage the second you wash it twice.",
        "sunday": "Sunday night in Dallas is a bigger stage, and the graphics are drawn to match.",
    },
    "michigan": {
        "weather": "Ann Arbor Saturdays are maize, navy, and a crowd that treats a grudge as climate.",
        "place": "Michigan vs Everybody is less a slogan than a weather report in this town.",
        "mark": "Block lettering and a winged helmet silhouette do more work than a paragraph ever will.",
        "sunday": "A Big Ten November is crewneck weather, and the graphic has to survive it.",
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
    srange = f"{sizes[0]}-{sizes[-1]}" if len(sizes) > 1 else sizes[0]
    stylecount = len(styles)
    art_bit = title_case_art(art or name)
    if len(art_bit) > 42:
        art_bit = art_bit[:40].rsplit(" ", 1)[0]
    variants = [
        (f"{name} - fan-made {g} for {team} fans, built around {art_bit}. "
         f"Printed on demand from ${price}"
         f"{f', on {stylecount} garment styles' if stylecount > 1 else ''}, sizes {srange}. "
         f"Shop the design on {P}."),
        (f"Fan-made {g} for {city} football supporters: {name}. Artwork: {art_bit}. "
         f"From ${price}, sizes {srange}"
         f"{f', {colours} garment colourways in the campaign mockups' if colours > 1 else ''}. "
         f"Story on Gridiron Locker; checkout on {P}."),
        (f"{name} from Gridiron Locker - unofficial, fan-made {team} football {g} "
         f"featuring {art_bit}. From ${price}, sizes {srange}, printed after you order. "
         f"Style, colour and size are chosen on {P}."),
        (f"The {name}: independent {team} fan apparel printed on demand. {g.capitalize()} from "
         f"${price} in sizes {srange}, artwork {art_bit}. Design story here, checkout on {P}."),
    ]
    out = sentence(pick(variants, slug, "meta"))
    if len(out) > 158:
        fallbacks = [
            f"{name} - fan-made {g} for {team} fans, from ${price}, sizes {srange}. "
            f"Printed on demand; style, colour and size are chosen on {P}.",
            f"{name}: independent {city} football apparel from ${price}, sizes {srange}. "
            f"Printed to order, shipped worldwide. Shop the design on {P}.",
            f"Fan-made {team} {g}: {name}. From ${price} in sizes {srange}, printed on demand "
            f"and shipped worldwide. Design story on Gridiron Locker.",
        ]
        out = sentence(pick(fallbacks, slug, "metafb"))
    if len(out) > 158:
        out = sentence(f"{name} - independent fan-made {g}, from ${price}, sizes {srange}. "
                       f"Printed on demand and shipped worldwide.")
    if len(out) > 158:
        out = out[:155].rsplit(" ", 1)[0].rstrip(" ,.-") + "..."
    return out


# ---------------------------------------------------------------- short description (50-90 words)
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
    """50-90 word unique short description under the H1. Never a pride cliché."""
    p = profile(slug, name, art, col, garment, theme)
    P = partner_of(col.get("key"))
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
            f"A replica jersey names a roster. This {g} names a feeling: {phrase}.",
            f"From {city}, this independent {g} puts {art_t} on the chest for {p['nick'] or team} people.",
            f"{name} is built around one idea printed large: {art_t}.",
            f"Nothing on this {g} is trying to look official. {art_t} is a fan mark, and that is the job.",
            f"{art_t} is the shirt. Everything else - spacing, weight, contrast - exists to keep that line alive in bad light.",
        ]

    middles = [
        f"It is fan-made {team} apparel, printed on demand on a {g}, for people who want the culture without the licensed costume.",
        f"Independent artwork means the line can be the thing supporters actually shout, not the thing a brand is allowed to print.",
        f"{voice['mark']} This piece stays on that side of the argument.",
        f"The {g} is meant to be {p['v']} on Sundays and on the six ordinary days around them.",
        f"It reads as {an(THEME_LABEL.get(p['theme'], 'fan'))} {THEME_LABEL.get(p['theme'], 'fan')} design, not a reprint of a shop wall.",
    ]
    closes = [
        f"Browse the story, the verified garment styles and the colourway mockups here, then continue to {P} to choose style, colour and size.",
        f"Gridiron Locker is where you decide if the design is yours; garment style, colour and size are confirmed on {P}.",
        f"If the graphic is the reason you stopped scrolling, the rest of the page is the proof - then SHOP NOW hands you to {P}.",
        f"Printed after you order, shipped with tracking, and never pretending this site is the checkout.",
    ]
    extras = [
        person,
        motif,
        f"The printed line stays {phrase} - that is the brief, not a moodboard.",
        f"{voice['sunday']}",
        f"It is made for {city} football culture rather than a generic league aisle.",
    ]

    chunks = [openings[v], pick(middles, slug, "sdm"), pick(closes, slug, "sdc")]
    # fold in extras until we are inside 50-90
    for extra in extras:
        if extra and extra not in chunks:
            chunks.append(extra)
    text = _fit_plain(chunks, 50, 90)
    w = word_count(text)
    if w < 50:
        pad = (f" The {g} is printed to order for {team} fans, with the artwork held at "
               f"{art_t} so the piece stays specific.")
        text = sentence(text + pad)
    if word_count(text) > 90:
        words = re.findall(r"\S+", text)
        text = " ".join(words[:90]).rstrip(".,;:") + "."
    return sentence(text)


def hero_line(slug, name, art, col, garment):
    """Back-compat alias: the short description is the hero deck now."""
    return short_description(slug, name, art, col, garment)


def image_alt(name, art, garment, team, n=None):
    art_bit = title_case_art(art)
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
    if p["slogan"]:
        opts = [
            f"{name} starts with a line {p['team']} fans already know how to shout: "
            f"<em>{phrase}</em>. The {g} is not a poster with sleeves. It is that phrase, set "
            f"heavy enough to survive a parking-lot glance, with everything else in the layout "
            f"told to get out of the way.",
            f"The brief for {name} was the phrase itself. <em>{phrase}</em> is short enough to "
            f"print large on {an(g)} {g}, which is why it works as apparel instead of a caption "
            f"under a photograph.",
            f"Every piece in this locker begins with something a {p['team']} supporter would "
            f"actually say. Here the line is <em>{phrase}</em>, and the drawing exists to keep "
            f"it readable at a walk, in bad light, with a drink in the other hand.",
            f"<em>{phrase}</em> is the entire origin story of {name}. Nobody asked for a second "
            f"idea. The {g} is the first idea, held still long enough to print.",
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
    opts = [
        f"Fan merchandise has a practical constraint poster art does not: it is seen in passing, "
        f"often in bad light, usually for about two seconds. The artwork is drawn for those two "
        f"seconds - heavy shapes, generous spacing, no thin strokes that disappear on a dark "
        f"{g}.",
        f"A design like this has to work at arm's length and across a room. That rules out fine "
        f"line work and busy backgrounds, so the composition stays blunt on purpose: one message, "
        f"strong contrast, and enough space around it that the fabric colour does the rest.",
        f"The print process shapes the drawing too. Everything is printed to order rather than "
        f"screen-printed in bulk, so the artwork is prepared to hold its edges on the actual "
        f"{g} and to keep its contrast across light and dark options.",
        f"On a {g} the type has to survive motion. That is why {p['art_title']} is treated as a "
        f"mark, not a paragraph - weight, spacing and contrast, in that order.",
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
        f"{voice['sunday']} A piece carrying <em>{p['phrase']}</em> is meant to sit in that weekly "
        f"habit, not in a one-weekend costume.",
        f"{lore} {voice['mark']} That is the football connection for this design - culture first, "
        f"scoreboard second.",
    ]
    text = pick(opts, slug, "st3")
    if chant and chant.lower() not in text.lower():
        text += f' The crowd already has a chant for it: "{chant}".'
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
                 f"without a briefing."),
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
        f"without borrowing a mark it has no right to. You are buying the sentiment, not a "
        f"replica.",
        f"The difference from a team-shop reprint is simple: this {g} is one idea, {p['art_title']}, "
        f"drawn for {team} supporters instead of a catalogue of approved icons.",
    ]
    return pick([o for o in opts if o], slug, "st4")


def _story_close(p, slug, col=None):
    P = partner_of((col or {}).get("key"))
    g = p["g"]
    opts = [
        f"What you end up with is {an(g)} {g} that says something specific about being a "
        f"{p['team']} fan, rather than something generic about liking football. If that is the "
        f"read you wanted, the rest is logistics: verified styles on this page, then {P} "
        f"for the size and colour you actually wear.",
        f"It is a small idea executed cleanly, which is generally what makes fan apparel get "
        f"{p['v']} more than once a season. {p['name']} is that kind of piece.",
        f"The result belongs to {p['city']} without needing a licence to prove it. Wear it, or "
        f"give it, or leave it on a shelf until Sunday - the graphic will still be {p['phrase']}.",
        f"If you already talk like this on Sundays, the {g} is just the public version. "
        f"{p['art_title']} does not need a caption once it is on your chest.",
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
            lead = (f"{p['name']} stands out as a {person['name']} fan shirt - {person['role']} - "
                    f"built around {p['phrase']} instead of a knock-off jersey. The relevance is "
                    f"the name supporters are already searching; the graphic is how they wear it.")
        else:
            lead = (f"{p['name']} stands out as a player tribute: {person['name']} rendered as "
                    f"{p['art_title']}, a fan mark rather than official kit.")
    elif angle == "funny":
        lead = (f"What makes {p['name']} different is the joke. {p['phrase']} is a punchline "
                f"{team} fans will get without a briefing, printed at the size a tailgate needs. "
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
                f"fan art can say the line the crowd already uses.")

    extra = pick([
        f"You will not find this exact graphic in a league shop, and that is the point of an "
        f"unofficial {g}.",
        f"The search is for a {team} fan {g}; the reason to pick this one is {p['phrase']}.",
        f"Plenty of shirts mention {city}. Fewer of them are actually about {p['phrase']}.",
        f"If you wanted a replica, you would already have one. This is the other kind of {g}.",
    ], slug, "whyx")
    return paras(lead, extra)


# ---------------------------------------------------------------- who / game day
def who_its_for(slug, col, theme, garment, price, name="", art=""):
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
            f"As a gift it is straightforward: no size to get wrong, a design that does not "
            f"depend on knowing a roster, and a price that starts at ${price}.",
            f"It also works as a present. There is nothing in the design that expires with a "
            f"transfer, and it starts at ${price}.",
            f"Buying it for someone else is low risk - there is no sizing decision, the artwork "
            f"is not tied to a single week of the season, and pricing starts at ${price}.",
        ], slug, "who2")
    else:
        gift = pick([
            f"As a gift it is straightforward: unisex sizing, a design that does not depend on "
            f"knowing a roster, and a price that starts at ${price}. If you are buying for someone "
            f"else, their usual t-shirt size is the safest choice.",
            f"It also works as a present. There is nothing in the design that expires with a "
            f"transfer, sizing is unisex, and it starts at ${price}.",
            f"Buying it for someone else is low risk - the {g} is unisex, the artwork is not "
            f"tied to a single week of the season, and pricing starts at ${price}.",
        ], slug, "who2")
    return f"<p>{sentence(lead)}</p><p>{sentence(gift)}</p>"


def gameday_wear(slug, col, garment, art):
    ctx = pick_n(WEAR_CONTEXT, slug, "ctx", 3)
    layer = LAYER_NOTE.get(garment, LAYER_NOTE["T-Shirt"])
    g = garment.lower()
    v = wear_verb(garment)
    art_t = title_case_art(art)
    closers = [
        f"Because {art_t} is a fan statement rather than a licensed team mark, it does not "
        f"look out of place away from the stadium either - which is the difference between a piece "
        f"{v} seventeen Sundays a year and one {v} most weeks.",
        f"It also survives the rest of the week. A fan-made graphic reads as a graphic first, so "
        f"{art_t} works on a commute or a Saturday errand in a way a replica jersey does not.",
        f"The {g} is made for normal use rather than a stadium costume, which is why most of the "
        f"fans who buy one end up using it well outside {col['city'].split(',')[0]} and well "
        f"outside football season.",
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


def colour_copy(colours, col=None):
    P = partner_of((col or {}).get("key"))
    """AVAILABLE COLOURS - never invent names, never fake a picker."""
    if colours > 1:
        return (f"<p>This design is available in multiple garment colourways. The mockups below "
                f"are taken from the live campaign - <strong>{colours} colour variations</strong> "
                f"were published for this design. They are previews, not selectors: choose your "
                f"colour, garment style and size on the {P} product page.</p>"
                f"<p>Colour previews are shown to help you choose your look. Final colour "
                f"selection is made on {P}.</p>")
    return (f"<p>Multiple colour options may be available for this design. Garment colours are set "
            f"per campaign, so the current list is shown on the {P} product page.</p>")


def size_copy(slug, sizes, garment, col=None):
    P = partner_of((col or {}).get("key"))
    if garment in ("Mug", "Phone Case"):
        return (f"<p>This is not an apparel item, so there is no size to choose. Any model or "
                f"capacity options are shown on the {P} product page.</p>")
    if garment == "Beanie":
        return ("<p>One size fits most adults - a stretch knit body with a folded cuff.</p>")
    rng = f"{sizes[0]} to {sizes[-1]}"
    return (f"<p>This campaign is offered in <strong>{len(sizes)} sizes: {rng}</strong> "
            f"({', '.join(sizes)}). Sizing is unisex unless the design name says otherwise. "
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
    out.append(f"Pricing starts at ${price}; each garment style is priced individually on {P}")
    out.append("Worldwide shipping with tracking issued at dispatch")
    verified = parse_features(features)
    if verified:
        out.extend(verified[:4])
    else:
        out.extend(g["bullets"][:3])
    return out


def shipping_copy(delivery_time, ship_from, col=None):
    P = partner_of((col or {}).get("key"))
    return (f"<p>Every item is printed after the order is placed - there is no warehouse stock to "
            f"ship from, which is why the catalogue can stay this wide without anything selling "
            f"out. Production takes a few business days, then the parcel moves.</p>"
            f"<p><strong>United States:</strong> standard shipping from ${ship_from}, typically "
            f"{delivery_time} from order to doorstep including production. "
            f"<strong>International:</strong> worldwide delivery is available; the exact rate and "
            f"estimate for your address is calculated at checkout on {P}.</p>"
            f"<p>If an item arrives misprinted, damaged or defective it is replaced within 30 days. "
            f"Delivery estimates are estimates - if you need a piece for a specific game, order "
            f"early in the week rather than the night before.</p>")


def disclosure():
    return ("Gridiron Locker is an independent fan-made store. These designs are not officially "
            "licensed by any team, league, university or player.")


def faqs(slug, facts, col, garment, price, colours, styles, sizes):
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
                    f"Sizing is unisex; the measurement chart on this page shows chest width and "
                    f"body length in inches. You pick your size on the {P} product page."))

    out.append(("Where do I choose my shirt colour, style and size?",
                f"On {P}. Gridiron Locker is where you see the design and the details; "
                f"garment style, colour and size are selected on the {P} product page for "
                "this campaign, immediately before checkout."))

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

    out.append(("How much does it cost?",
                f"Pricing for this design starts at ${price}. Different garment styles carry "
                f"different prices, and the price you pay is the one shown on {P} for the "
                f"style, colour and size you select."))

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
