"""Generates unique, keyword-rich commercial copy for every product."""
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
    ("Tank Top", ["tank top", "tank"]),
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
    "V-Neck": dict(
        blurb="a preshrunk ring-spun cotton tee cut with a clean V neckline, tubular body and a tear-away label",
        care="Machine wash warm inside out with like colours, tumble dry medium, do not iron directly on the print.",
        fit="Unisex sizing from S to 3XL with a semi-fitted body. Between sizes? Size up one.",
        bullets=["Preshrunk 100% combed ring-spun cotton (heather colours are a cotton/poly blend)",
                 "Clean V neckline that keeps its shape instead of stretching out",
                 "4.5 oz, 30 singles - light, breathable and easy to layer",
                 "Semi-fitted unisex cut with double-needle sleeve and bottom hems",
                 "Tear-away label for tag-free comfort"],
    ),
    "Tank Top": dict(
        blurb="a sleeveless cotton tank with a scooped armhole, tubular construction and a tear-away label",
        care="Machine wash warm inside out with like colours, tumble dry medium, do not iron directly on the print.",
        fit="Unisex sizing from S to 3XL. Tanks run close to the body - size up for a relaxed fit.",
        bullets=["Preshrunk 100% combed ring-spun cotton (heather colours are a cotton/poly blend)",
                 "Sleeveless cut with a scooped armhole that stays put",
                 "Lightweight enough for August two-a-days and tailgates in the sun",
                 "Tubular construction with double-needle bottom hem",
                 "Tear-away label for tag-free comfort"],
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
        fit="Choose your exact phone model on the checkout page before adding to your bag.",
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

def meta_description(name, col, garment, price, colours):
    tmpl = [
        "{name} - fan-made {g} printed on demand in up to {c} colourways. Sizes S-3XL, from ${p}. Ships worldwide from the USA.",
        "Shop the {name}. Soft {g} for {team} fans, {c} colour options, S-3XL, from ${p}. Fast printing, worldwide shipping.",
        "{name} for {city} fans. Premium {g}, {c} colourways, sizes S-3XL, from ${p}. Secure checkout, printed and shipped to order.",
    ]
    t = tmpl[len(name) % len(tmpl)]
    out = t.format(name=name, g=garment.lower(), c=colours, p=price,
                   team=col["team"], city=col["city"].split(",")[0])
    if len(out) > 160:
        out = (f"{name} - fan-made {garment.lower()}, {colours} colourways, S-3XL, "
               f"from ${price}. Printed to order, ships worldwide.")
    return out

def long_description(slug, facts, col, garment, styles, colours, price):
    art = facts["art"]
    theme = facts.get("theme", "classic")
    if theme not in THEME_HOOK:
        theme = "classic"
    g = GARMENT_COPY.get(garment, GARMENT_COPY["T-Shirt"])
    hook = pick(THEME_HOOK[theme], slug, "hook")
    lore = pick(col["lore"], slug, "lore")
    aud = audience(theme, col)
    occ1 = pick(OCCASIONS, slug, "o1")
    occ2 = pick(OCCASIONS, slug, "o2")
    city = col["city"].split(",")[0]

    p1_variants = [
        f"<p><strong>{facts['name']}</strong> puts <em>{art}</em> front and centre. {hook} "
        f"The graphic is printed on {g['blurb']}, so the design sits flat on the fabric instead of "
        f"cracking off it after three washes.</p>",
        f"<p>This is the <strong>{facts['name']}</strong>: <em>{art}</em>, printed clean and bold. {hook} "
        f"It comes on {g['blurb']} - the kind of piece that survives a full season in the rotation.</p>",
        f"<p><strong>{facts['name']}</strong> - artwork reading <em>{art}</em>. {hook} "
        f"Printed on {g['blurb']} using a direct-to-garment process that keeps fine detail sharp.</p>",
    ]
    p1 = pick(p1_variants, slug, "p1")

    p2_variants = [
        f"<p>{lore} That is the energy behind this {garment.lower()}. It is made for {aud[0]} and "
        f"{aud[1]} around {city} and anywhere else {col['team']} fans end up - and it works just as "
        f"well for {occ1} as it does for {occ2}.</p>",
        f"<p>{lore} This piece is aimed squarely at {aud[0]}, {aud[1]} and anyone who has ever "
        f"shouted \"{col['chant']}\" at a television. Wear it for {occ1}, {occ2}, or a regular "
        f"Tuesday in {city}.</p>",
        f"<p>{lore} If you are shopping for {aud[2]}, this is a low-risk pick: the design reads from "
        f"across the room, the fit is unisex, and it is equally at home at {occ1} and {occ2}.</p>",
    ]
    p2 = pick(p2_variants, slug, "p2")

    style_line = ""
    if styles:
        shown = ", ".join(styles[:6])
        style_line = (f"<p><strong>Available styles:</strong> {shown}"
                      + (" and more" if len(styles) > 6 else "")
                      + f". Every style is printed to order after you check out, which is why the "
                        f"catalogue can stay this wide without anything going out of stock.</p>")

    colour_line = (f"<p><strong>Colourways:</strong> up to {colours} garment colours are available on "
                   f"the checkout page. Pick the colour first, then your size, then your quantity.</p>"
                   ) if colours > 1 else ""

    p3 = (f"<p><strong>Fit and sizing.</strong> {g['fit']} {g['care']}</p>")

    p4_variants = [
        f"<p><strong>Why buy this one?</strong> It starts at <strong>${price}</strong>, it is printed "
        f"on demand in the USA, and it ships worldwide. There is no minimum order and no waiting for a "
        f"restock - the campaign prints as soon as you order.</p>",
        f"<p><strong>Ordering.</strong> From <strong>${price}</strong>. Printed and shipped on demand, "
        f"so you are never buying old warehouse stock. Secure checkout, worldwide delivery, and "
        f"tracked dispatch once the print run completes.</p>",
        f"<p><strong>The short version.</strong> ${price} to start, {colours} colourways, sizes S to "
        f"3XL, printed after you order and shipped worldwide. If you want it for a specific Sunday, "
        f"order early in the week.</p>",
    ]
    p4 = pick(p4_variants, slug, "p4")

    return p1 + p2 + style_line + colour_line + p3 + p4, g["bullets"]

def faqs(slug, facts, col, garment, price, colours, styles):
    g = GARMENT_COPY[garment]
    out = [
        (f"Is the {facts['name']} officially licensed?",
         "No. This is an independent, fan-made design created by an independent artist. It is not "
         "affiliated with, endorsed by, sponsored by or licensed by any professional or collegiate "
         "team, league or player. Team names and city names are used only to describe who the "
         "artwork is for."),
        ("What sizes are available?",
         g["fit"]),
        ("How much does it cost and where do I buy it?",
         f"Pricing starts at ${price}. Tap any Buy button on this page and you will land on the "
         f"official product page where you choose your style, colour and size and complete a secure "
         f"checkout."),
        ("How is it printed?",
         "Everything is printed on demand once the order is placed - no warehouse stock, no dead "
         "inventory. That keeps the design range wide and the print fresh."),
        ("How long does shipping take?",
         "Production usually takes a few business days once the print run closes, then standard "
         "delivery follows. Worldwide shipping is available and tracking is issued at dispatch."),
    ]
    if colours > 1:
        out.append((f"What colours does the {garment.lower()} come in?",
                    f"Up to {colours} garment colours are offered for this design. The full swatch "
                    f"list, including any limited colourways, is shown on the checkout page."))
    if styles:
        out.append(("Can I get this design on a hoodie or sweatshirt instead?",
                    "Yes - this artwork is available on several garment styles including "
                    + ", ".join(styles[:5]) + ". Select your preferred style at checkout."))
    out += [(q, a) for q, a in col.get("faq_extra", [])]
    return out[:7]

def keywords(facts, col, garment):
    base = list(facts.get("kw", []))
    n = facts["name"].lower()
    base += [n, f"{n} {garment.lower()}", f"{col['team'].lower()} fan gear",
             f"{col['city'].split(',')[0].lower()} football apparel"]
    seen, out = set(), []
    for k in base:
        k = re.sub(r"\s+", " ", k.strip().lower())
        if k and k not in seen:
            seen.add(k); out.append(k)
    return out[:12]
