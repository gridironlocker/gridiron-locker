"""Shared garment vocabulary used by the product landing pages.

The page copy itself lives in landing.py. What survives here is the factual
garment layer - which garment a design is printed on, what that garment is
made of, how it fits, how to wash it - plus the audience vocabulary. The old
mini-checkout copy generators (long_description / faqs / meta_description /
keywords) were retired with the style-size-colourway picker they were written
for; landing.py replaces them.
"""
import hashlib, re

def h(slug, salt=""):
    return int(hashlib.md5((slug + salt).encode()).hexdigest(), 16)

def pick(lst, slug, salt=""):
    return lst[h(slug, salt) % len(lst)]

GARMENT_MAP = [
    ("Beanie", ["beanie", "winter hat"]),
    ("Mug", ["mug"]),
    ("Phone Case", ["phone case", "case"]),
    ("Hoodie", ["hoodie"]),
    ("Sweatshirt", ["sweatshirt", "crewneck"]),
    ("Long Sleeve Shirt", ["long sleeve"]),
    ("T-Shirt", ["shirt", "tee", "t-shirt"]),
]

def garment_of(facts, name, styles):
    if facts.get("type"):
        return facts["type"]
    low = name.lower()
    for label, keys in GARMENT_MAP:
        if any(k in low for k in keys):
            return label
    return "T-Shirt"

GARMENT_COPY = {
    "T-Shirt": dict(
        blurb="a preshrunk, ring-spun cotton tee with a semi-fitted body, tubular construction and a tear-away label so nothing scratches your neck",
        care="Machine wash warm inside out with like colours, tumble dry medium, do not iron directly on the print.",
        fit="Unisex sizing from S to 3XL. If you are between sizes or want a relaxed drape, size up one.",
        bullets=["Preshrunk 100% combed ring-spun cotton (heather colours are a cotton/poly blend)",
                 "4.5 oz, 30 singles - light enough for September, solid enough to last",
                 "Semi-fitted unisex cut with shoulder-to-shoulder taping",
                 "Double-needle sleeve and bottom hems",
                 "Tear-away label for tag-free comfort"],
    ),
    "Hoodie": dict(
        blurb="a heavyweight pullover hoodie with a double-lined hood, ribbed cuffs and a roomy front pouch pocket",
        care="Machine wash cold, tumble dry low, do not bleach. Turn inside out to protect the print.",
        fit="Unisex sizing from S to 3XL, cut generously. Keep your normal size for a classic hoodie fit.",
        bullets=["Heavyweight cotton/polyester fleece blend with a brushed inner face",
                 "Double-lined hood with matching drawcord",
                 "Front pouch pocket and ribbed cuffs and waistband",
                 "Set-in sleeves with double-needle stitching",
                 "Holds colour and shape wash after wash"],
    ),
    "Sweatshirt": dict(
        blurb="a classic crew neck sweatshirt in soft air-jet spun fleece that stays pill-resistant after repeated washes",
        care="Machine wash cold with like colours, tumble dry low, no fabric softener on the print.",
        fit="Unisex crewneck sizing S to 3XL with a roomy body. Size down for a slimmer look.",
        bullets=["Air-jet spun yarn for a softer feel and reduced pilling",
                 "Ribbed collar, cuffs and waistband with spandex for shape retention",
                 "Double-needle stitched neckline and armholes",
                 "No itchy side seams - tubular body",
                 "Warm mid-weight fleece for game day and everyday"],
    ),
    "Long Sleeve Shirt": dict(
        blurb="a full-print long sleeve made from a smooth, lightweight polyester knit that keeps the artwork edge to edge",
        care="Machine wash cold, hang dry for best results. The print will not crack or peel because it is dyed into the fabric.",
        fit="Unisex sizing S to 3XL with a standard body length.",
        bullets=["All-over sublimation print - the design runs across the sleeves and body",
                 "Lightweight breathable polyester knit",
                 "Print will never crack, peel or fade",
                 "Every piece is cut and sewn to order",
                 "Vivid, high-resolution colour reproduction"],
    ),
    "Beanie": dict(
        blurb="a knit cuffed beanie with a raised, high-contrast graphic across the fold",
        care="Hand wash cold and lay flat to dry to keep the knit tight.",
        fit="One size fits most adults, with a stretch knit body and a folded cuff.",
        bullets=["Soft acrylic knit that keeps its shape",
                 "Folded cuff with a bold front graphic",
                 "One size fits most adults",
                 "Warm enough for a December kickoff",
                 "Unisex - works over short or long hair"],
    ),
    "Mug": dict(
        blurb="an 11 oz ceramic mug with a wraparound print that survives the dishwasher and the microwave",
        care="Dishwasher and microwave safe. The print is fused into the coating, not stuck on top.",
        fit="Standard 11 oz ceramic mug, C-handle, glossy finish.",
        bullets=["11 oz ceramic with a glossy white or black finish",
                 "Dishwasher safe and microwave safe",
                 "Wraparound sublimation print - visible from both sides",
                 "Comfortable C-handle",
                 "Ships in protective packaging"],
    ),
    "Phone Case": dict(
        blurb="a slim, impact-absorbing phone case with the artwork printed edge to edge on the back shell",
        care="Wipe clean with a damp cloth. The print sits under a protective coating.",
        fit="Choose your exact phone model on the product page.",
        bullets=["Slim profile that still fits in a pocket",
                 "Raised lip protects the camera and screen",
                 "Precise cutouts for ports, buttons and speakers",
                 "Impact-absorbing flexible sides",
                 "Full-bleed printed back panel"],
    ),
}

THEME_HOOK = {
    "player": ["Wear the name, wear the number.", "A player tribute that does not need a jersey budget.",
               "Built for the fans who yell at the screen on third and long."],
    "funny": ["The kind of shirt that starts conversations in the tailgate lot.",
              "Funny first, but the print quality is serious.",
              "If your group chat would laugh at it, it belongs in your rotation."],
    "playoff": ["Playoff season only comes around so often. Dress like you believe.",
                "For the January cold and the noise that comes with it.",
                "A statement piece for the run."],
    "classic": ["A clean, everyday piece you will reach for all season.",
                "Simple, bold and impossible to get wrong.",
                "The safe pick that still looks sharp in the stands."],
    "retro": ["Washed-out, throwback styling with a modern print process.",
              "Vintage on the outside, brand new on the inside.",
              "Retro lettering, no thrift-store smell."],
    "city": ["Rep the city, not just the scoreboard.",
             "Hometown pride you can wear on a Tuesday.",
             "For the people who never left and the ones who moved away."],
    "family": ["An easy gift for the fan in your family.",
               "Made for the people who watch every snap together.",
               "A soft, wearable gift that actually gets worn."],
    "halloween": ["An all-over print built to be noticed across a crowded room.",
                  "Loud on purpose - this one is a costume and a fan piece at once.",
                  "Full-bleed artwork, no half measures."],
}

OCCASIONS = ["game day", "tailgates", "watch parties", "birthdays", "Father's Day",
             "Christmas stocking stuffers", "draft night", "season openers", "road trips"]

def audience(theme, col):
    base = {
        "player": ["fantasy managers", "jersey collectors", "diehard supporters"],
        "funny": ["group chat comedians", "tailgate hosts", "fans with a sense of humour"],
        "playoff": ["season ticket holders", "January diehards", "playoff-run believers"],
        "classic": ["everyday fans", "first-time buyers", "people who hate loud graphics"],
        "retro": ["vintage tee collectors", "throwback fans", "thrift-style dressers"],
        "city": ["hometown fans", "expats who moved away", "locals"],
        "family": ["moms, dads and partners", "gift buyers", "families who watch together"],
        "halloween": ["costume party regulars", "all-over-print fans", "attention-grabbers"],
    }
    return base.get(theme, base["classic"])
