"""SEO landing-page copy for a single design.

Gridiron Locker is the discovery + SEO layer; Viralstyle is the transaction
layer. Nothing in here may pretend to configure or process an order: no style
picker, no size picker, no colour picker, no checkout. Every section exists to
answer one of five questions before the visitor taps SHOP NOW:

    What is this?  Why do I want it?  What am I getting?
    What options exist?  Where do I buy it?

Rules that are enforced by tests (tests/test_layout.py):
  * Copy is generated from the *actual* product record - name, artwork line,
    theme, garment, verified style list, verified size list and the number of
    campaign mockups. Nothing is invented.
  * Colour names are never fabricated. We only know how many garment mockups
    the campaign published, so we show those mockups as informational previews
    and say the authoritative list lives on Viralstyle.
  * No player quotes, statistics, records or historical claims.
  * Section copy varies per product (hash-selected variants + real data), so
    127 pages are not 127 copies of one paragraph.
"""
import hashlib
import re

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
    a = sentence(art)
    return a


NON_APPAREL = ("Mug", "Phone Case")


def an(word):
    """Article for a word - 'a player tribute' / 'an everyday fan'."""
    return "an" if word[:1].lower() in "aeiou" else "a"


def is_slogan(art):
    """True when the artwork line is a phrase printed on the garment rather
    than a description of a picture. The catalogue stores printed slogans in
    caps and descriptive lines in sentence case, so the casing is the signal.
    Many entries are a slogan plus a scene note ("GO PACK GO with cheesehead"),
    so only the leading clause is tested. We must not claim "the design began
    as a phrase" about a design that is really an illustration."""
    head = re.split(r"\s+with\s+|\s+on\s+|,", art, 1)[0]
    letters = [ch for ch in head if ch.isalpha()]
    if len(letters) < 3:
        return False
    return sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.7


def slogan_text(art):
    """Just the printed phrase, without the trailing scene description."""
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


# ---------------------------------------------------------------- sections
def meta_title(name, brand="Gridiron Locker"):
    """Unique, non-templated-looking title per product."""
    base = f"{name} | Fan-Made Football Apparel | {brand}"
    if len(base) <= 60:
        return base
    mid = f"{name} | Fan-Made Football Apparel"
    if len(mid) <= 60:
        return mid
    short = f"{name} | {brand}"
    if len(short) <= 60:
        return short
    return name


def meta_description(slug, name, col, garment, price, styles, colours, sizes):
    """Unique description: product, football context, apparel, fan-made, brand."""
    g = garment.lower()
    team = col["team"]
    city = col["city"].split(",")[0]
    srange = f"{sizes[0]}-{sizes[-1]}" if len(sizes) > 1 else sizes[0]
    stylecount = len(styles)
    variants = [
        (f"{name} - an independent, fan-made {g} for {team} fans. Printed on demand from ${price}"
         f"{f', on {stylecount} garment styles' if stylecount > 1 else ''}, sizes {srange}. "
         f"See the design, then shop it on Viralstyle."),
        (f"Fan-made {g} for {city} football supporters: {name}. From ${price}, sizes {srange}"
         f"{f', {colours} garment colourways in the campaign mockups' if colours > 1 else ''}. "
         f"Read the design story on Gridiron Locker and shop on Viralstyle."),
        (f"{name} from Gridiron Locker - an unofficial, fan-made {team} football {g}. "
         f"From ${price}, sizes {srange}, printed after you order. Style, colour and size are "
         f"chosen on Viralstyle."),
        (f"The {name}: independent {team} fan apparel, printed on demand. {g.capitalize()} from "
         f"${price} in sizes {srange}. Full design story, sizing and shipping details here, "
         f"checkout on Viralstyle."),
    ]
    out = sentence(pick(variants, slug, "meta"))
    if len(out) > 158:
        # Trim to the last complete sentence that still fits Google's snippet.
        fallbacks = [
            f"{name} - fan-made {g} for {team} fans, from ${price}, sizes {srange}. "
            f"Printed on demand; style, colour and size are chosen on Viralstyle.",
            f"{name}: independent {city} football apparel from ${price}, sizes {srange}. "
            f"Printed to order, shipped worldwide. Shop the design on Viralstyle.",
            f"Fan-made {team} {g}: {name}. From ${price} in sizes {srange}, printed on demand "
            f"and shipped worldwide. Design story and details on Gridiron Locker.",
        ]
        out = sentence(pick(fallbacks, slug, "metafb"))
    if len(out) > 158:
        out = sentence(f"{name} - independent fan-made {g}, from ${price}, sizes {srange}. "
                       f"Printed on demand and shipped worldwide.")
    if len(out) > 158:                      # very long product names only
        out = out[:155].rsplit(" ", 1)[0].rstrip(" ,.-") + "..."
    return out


def hero_line(slug, name, art, col, garment):
    """One-sentence hero deck, under the H1."""
    g = garment.lower()
    if garment in NON_APPAREL:
        variants = [
            f"A fan-made {col['team']} {g} carrying {title_case_art(art)} - "
            f"printed to order for supporters who want the detail, not the jersey.",
            f"An independent {col['city'].split(',')[0]} football {g}: {title_case_art(art)}, "
            f"printed on demand.",
            f"{title_case_art(art)} - a fan-made {col['team']} {g}, printed after you order.",
        ]
        return sentence(pick(variants, slug, "hero"))
    variants = [
        f"A fan-made {col['team']} {g} built around {title_case_art(art)} - made for game day and "
        f"the six days in between.",
        f"An independent {col['city'].split(',')[0]} football design: {title_case_art(art)}, "
        f"printed to order on a {g}.",
        f"{title_case_art(art)} - drawn for {col['team']} supporters and printed on demand on a {g}.",
    ]
    return sentence(pick(variants, slug, "hero"))


def about_design(slug, facts, col, garment, art, theme):
    """ABOUT THIS DESIGN - inspiration, football culture, concept, difference."""
    concept = pick(THEME_CONCEPT.get(theme, THEME_CONCEPT["classic"]), slug, "concept")
    lore = pick(col["lore"], slug, "lore")
    label = THEME_LABEL.get(theme, "fan")
    g = garment.lower()
    art_noun = "reads" if is_slogan(art) else "shows"
    opens = [
        f"<p><strong>{facts['name']}</strong> is {an(label)} {label} design for {col['team']} "
        f"supporters. "
        f"The artwork {art_noun} <em>{artline(art)}</em>, printed as the single focal point of the "
        f"{g} rather than one graphic among several.</p>",
        f"<p>This is {an(label)} {label} piece from the {col['name']} range. The {g} carries one "
        f"graphic - "
        f"<em>{artline(art)}</em> - sized so it is the first thing anyone notices.</p>",
        f"<p><strong>{facts['name']}</strong> takes a single idea, <em>{artline(art)}</em>, and "
        f"builds the whole {g} around it. It is {an(label)} {label} design, not a team-shop "
        f"reprint.</p>",
    ]
    body = [
        f"<p>{concept} {lore}</p>",
        f"<p>{lore} {concept}</p>",
    ]
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


def design_story(slug, facts, col, art, theme, garment):
    """THE IDEA BEHIND THE DESIGN - narrative, verified information only."""
    g = garment.lower()
    city = col["city"].split(",")[0]
    chant = col.get("chant", "")
    if is_slogan(art):
        phrase = slogan_text(art)
        starts = [
            f"<p>The starting point was the line itself: <em>{phrase}</em>. Everything else "
            f"in the layout exists to keep that phrase readable - weight, spacing and contrast, in "
            f"that order.</p>",
            f"<p>The design began as a phrase rather than a picture. <em>{phrase}</em> is "
            f"short enough to set large, which is why it works on {an(g)} {g} instead of a "
            f"poster.</p>",
            f"<p>Every piece in this collection starts with something a {col['team']} fan would "
            f"actually say. Here it is <em>{phrase}</em>, laid out so it survives being seen "
            f"at a distance and in motion.</p>",
        ]
    else:
        starts = [
            f"<p>The starting point was the image: <em>{artline(art)}</em>. Everything else in the "
            f"composition exists to keep that read clean - scale, contrast and negative space, in "
            f"that order.</p>",
            f"<p>This one began as a drawing rather than a slogan. <em>{artline(art)}</em> is "
            f"simple enough to hold together at {g} scale, which is more than most illustrations "
            f"manage.</p>",
            f"<p>The brief was a single graphic, not a caption: <em>{artline(art)}</em>, drawn to "
            f"be recognised before it is examined.</p>",
        ]

    middles = [
        f"<p>Fan merchandise has a practical constraint that poster art does not: it is seen in "
        f"passing, often in bad light, usually for about two seconds. The artwork is drawn for "
        f"those two seconds - heavy shapes, generous spacing, no thin strokes that disappear on a "
        f"dark background.</p>",
        f"<p>A design like this has to work at arm's length and across a room. That rules out fine "
        f"line work and busy backgrounds, so the composition stays blunt on purpose: one message, "
        f"strong contrast, and enough space around it that the fabric colour does the rest.</p>",
        f"<p>The print process shapes the drawing too. Everything is printed to order rather than "
        f"screen-printed in bulk, so the artwork is prepared to hold its edges on the actual "
        f"surface and to keep its contrast across light and dark options.</p>",
    ]
    ends = [
        f"<p>The result is a piece that belongs to {city} without needing a licence to prove it"
        + (f" - and one that fits a crowd already chanting \"{chant}\"." if chant else ".")
        + "</p>",
        f"<p>What you end up with is a {g} that says something specific about being a "
        f"{col['team']} fan, rather than something generic about liking football.</p>",
        f"<p>It is a small idea executed cleanly, which is generally what makes fan apparel get "
        f"worn more than once a season.</p>",
    ]
    return (pick(starts, slug, "story1") + pick(middles, slug, "story2")
            + pick(ends, slug, "story3"))


def who_its_for(slug, col, theme, garment, price):
    aud = _c.audience(theme, col)
    a = pick_n(aud, slug, "aud", min(3, len(aud)))
    city = col["city"].split(",")[0]
    g = garment.lower()
    lead = pick([
        f"<p>This one is aimed at {a[0]}, {a[1] if len(a) > 1 else 'lifelong supporters'} and "
        f"anyone who has spent a season explaining their team to people who do not follow it.</p>",
        f"<p>It suits {a[0]} and {a[1] if len(a) > 1 else 'everyday fans'} best - the people who "
        f"want to show allegiance without wearing a full replica kit.</p>",
        f"<p>Think {a[0]}, {a[1] if len(a) > 1 else 'gift buyers'}, and {city} supporters who "
        f"moved away and still set an alarm for kickoff.</p>",
    ], slug, "who1")
    if garment in NON_APPAREL or garment == "Beanie":
        gift = pick([
            f"<p>As a gift it is straightforward: no size to get wrong, a design that does not "
            f"depend on knowing a roster, and a price that starts at ${price}.</p>",
            f"<p>It also works as a present. There is nothing in the design that expires with a "
            f"transfer or a bad season, and it starts at ${price}.</p>",
            f"<p>Buying it for someone else is low risk - there is no sizing decision, the artwork "
            f"is not tied to a single week of the season, and pricing starts at ${price}.</p>",
        ], slug, "who2")
    else:
        gift = pick([
            f"<p>As a gift it is straightforward: unisex sizing, a design that does not depend on "
            f"knowing a roster, and a price that starts at ${price}. If you are buying for someone "
            f"else, their usual t-shirt size is the safest choice.</p>",
            f"<p>It also works as a present. There is nothing in the design that expires with a "
            f"transfer or a bad season, sizing is unisex, and it starts at ${price}.</p>",
            f"<p>Buying it for someone else is low risk - the {g} is unisex, the artwork is not "
            f"tied to a single week of the season, and pricing starts at ${price}.</p>",
        ], slug, "who2")
    return lead + gift


def gameday_wear(slug, col, garment, art):
    ctx = pick_n(WEAR_CONTEXT, slug, "ctx", 3)
    layer = LAYER_NOTE.get(garment, LAYER_NOTE["T-Shirt"])
    g = garment.lower()
    v = wear_verb(garment)
    closers = [
        f"<p>Because the graphic is a fan statement rather than a licensed team mark, it does not "
        f"look out of place away from the stadium either - which is the difference between a piece "
        f"{v} seventeen Sundays a year and one {v} most weeks.</p>",
        f"<p>It also survives the rest of the week. A fan-made graphic reads as a graphic first, so "
        f"it works on a commute or a Saturday errand in a way a replica jersey does not.</p>",
        f"<p>The {g} is made for normal use rather than a stadium costume, which is why most of the "
        f"fans who buy one end up using it well outside {col['city'].split(',')[0]} and well "
        f"outside football season.</p>",
    ]
    return (f"<p>Where this {g} actually gets {v}: {ctx[0]}, {ctx[1]}, and {ctx[2]}. "
            f"{layer}</p>" + pick(closers, slug, "wear"))


def styles_copy(slug, styles, garment):
    """AVAILABLE APPAREL - verified style list only."""
    if garment in NON_APPAREL and styles:
        return (f"<p>This artwork is published across <strong>{len(styles)} product "
                f"variations</strong> in the campaign, listed below exactly as the campaign shows "
                f"them. Pick the one you want on the Viralstyle product page, where each variation "
                f"carries its own price.</p>")
    if not styles:
        return (f"<p>This design is printed on a {garment.lower()}. The exact garment options for "
                f"this campaign are listed on the Viralstyle product page.</p>")
    n = len(styles)
    if n == 1:
        return (f"<p>This campaign prints the design on one garment: <strong>{styles[0]}</strong>. "
                f"You confirm your size on the Viralstyle product page.</p>")
    return (f"<p>The campaign for this design offers <strong>{n} garment styles</strong>. "
            f"They are listed below exactly as the campaign publishes them - pick the one you "
            f"want on the Viralstyle product page, where each style shows its own price.</p>")


def apparel_heading(garment):
    return "Available Products" if garment in NON_APPAREL else "Available Apparel"


def colour_copy(colours):
    """AVAILABLE COLOURS - never invent names, never fake a picker."""
    if colours > 1:
        return (f"<p>This design is available in multiple garment colourways. The mockups below "
                f"are taken from the live campaign - <strong>{colours} colour variations</strong> "
                f"were published for this design. They are previews, not selectors: choose your "
                f"colour, garment style and size on the Viralstyle product page.</p>")
    return ("<p>Multiple colour options may be available for this design. Garment colours are set "
            "per campaign, so the current list is shown on the Viralstyle product page.</p>")


def size_copy(slug, sizes, garment):
    if garment in ("Mug", "Phone Case"):
        return ("<p>This is not an apparel item, so there is no size to choose. Any model or "
                "capacity options are shown on the Viralstyle product page.</p>")
    if garment == "Beanie":
        return ("<p>One size fits most adults - a stretch knit body with a folded cuff.</p>")
    rng = f"{sizes[0]} to {sizes[-1]}"
    return (f"<p>This campaign is offered in <strong>{len(sizes)} sizes: {rng}</strong> "
            f"({', '.join(sizes)}). Sizing is unisex unless the design name says otherwise. "
            f"The measurement chart below is a guide - the size you select is confirmed on the "
            f"Viralstyle product page.</p>")


def details_bullets(garment, styles, sizes, colours, price):
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
    out.append(f"Pricing starts at ${price}; each garment style is priced individually on Viralstyle")
    out.append("Worldwide shipping with tracking issued at dispatch")
    return out + g["bullets"][:3]


def shipping_copy(delivery_time, ship_from):
    return (f"<p>Every item is printed after the order is placed - there is no warehouse stock to "
            f"ship from, which is why the catalogue can stay this wide without anything selling "
            f"out. Production takes a few business days, then the parcel moves.</p>"
            f"<p><strong>United States:</strong> standard shipping from ${ship_from}, typically "
            f"{delivery_time} from order to doorstep including production. "
            f"<strong>International:</strong> worldwide delivery is available; the exact rate and "
            f"estimate for your address is calculated at checkout on Viralstyle.</p>"
            f"<p>If an item arrives misprinted, damaged or defective it is replaced within 30 days. "
            f"Delivery estimates are estimates - if you need a piece for a specific game, order "
            f"early in the week rather than the night before.</p>")


def faqs(slug, facts, col, garment, price, colours, styles, sizes):
    """Product FAQ - answers the handoff questions explicitly."""
    name = facts["name"]
    g = garment.lower()
    out = []

    if colours > 1:
        out.append((f"What colours does the {name} come in?",
                    f"This campaign published {colours} garment colour variations, previewed on "
                    f"this page as campaign mockups. Colour availability is set per campaign and "
                    f"can change, so the current, authoritative list is on the Viralstyle product "
                    f"page - that is also where you select the one you want."))
    else:
        out.append((f"What colours does the {name} come in?",
                    "Colour options vary by campaign. Visit the Viralstyle product page for this "
                    "design to see the colours currently offered."))

    if garment in ("Mug", "Phone Case"):
        out.append(("What sizes or models are available?",
                    "This is not an apparel item, so there is no garment size. Any model or "
                    "capacity choice is made on the Viralstyle product page."))
    elif garment == "Beanie":
        out.append(("What sizes are available?",
                    "One size fits most adults - a stretch knit body with a folded cuff."))
    else:
        out.append(("What sizes are available?",
                    f"Sizes {sizes[0]} to {sizes[-1]} ({', '.join(sizes)}) for this campaign. "
                    f"Sizing is unisex; the measurement chart on this page shows chest width and "
                    f"body length in inches. You pick your size on the Viralstyle product page."))

    out.append(("Where do I choose my shirt colour, style and size?",
                "On Viralstyle. Gridiron Locker is where you see the design and the details; "
                "garment style, colour and size are selected on the Viralstyle product page for "
                "this campaign, immediately before checkout."))

    out.append(("Where is checkout completed?",
                "Orders are placed and paid for on Viralstyle, the print-on-demand partner that "
                "runs this campaign. Gridiron Locker never takes payment or handles your card "
                "details - the SHOP NOW button hands you over to the campaign page."))

    out.append((f"Is the {name} official team merchandise?",
                "No. This is an independent, fan-made design. It is not affiliated with, endorsed "
                "by, sponsored by or licensed by any professional or collegiate team, league or "
                "player. Team and city names are used only to describe who the artwork is for."))

    out.append(("How is the product made?",
                f"It is printed on demand. Once your order is placed on Viralstyle the {g} is "
                f"printed and finished, then shipped with tracking. Nothing is pre-printed, so "
                f"there is no dead stock and no 'sold out' on a design that is still live."))

    if styles and len(styles) > 1:
        out.append(("Can I get this design on a hoodie or sweatshirt instead?",
                    "The campaign offers " + ", ".join(styles[:6])
                    + (" and more. " if len(styles) > 6 else ". ")
                    + "Each style is priced separately and selected on the Viralstyle product page."))

    out.append(("How much does it cost?",
                f"Pricing for this design starts at ${price}. Different garment styles carry "
                f"different prices, and the price you pay is the one shown on Viralstyle for the "
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
    seen, out = set(), []
    for k in base:
        k = re.sub(r"\s+", " ", k.strip().lower())
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out[:12]
