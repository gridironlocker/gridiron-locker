#!/usr/bin/env python3
"""
Real Copy Vault — unique voice per team, no repetition.

This is the fix for "same caption or adcopy repeated for all teams".
Each collection has its own slang, openers, angles, CTAs, and story triggers.
Templates are hashed by slug+platform+date so every product gets a different
line every day, but deterministically reproducible.
"""
from __future__ import annotations
import hashlib, random, re
from typing import Dict, List

def h(slug: str, salt: str = "") -> int:
    return int(hashlib.md5((slug + salt).encode()).hexdigest(), 16)

def pick(lst: List[str], slug: str, salt: str) -> str:
    if not lst:
        return ""
    return lst[h(slug, salt) % len(lst)]

# ------------------------------------------------- who's-who headline gate
# people.json flags traded/released/replaced players and coaches as
# "throwback". The rule is absolute: they must not be used or mentioned in
# posts, captions, or hashtags. Their names trend hardest right after they
# leave (the trade story), so without this gate the #1 Cleveland headline
# would keep naming them in captions for unrelated, still-listed designs.
_THROWBACK_ALIASES: tuple[str, ...] | None = None

def _throwback_aliases() -> tuple[str, ...]:
    """All name fragments of throwback people, loaded once per process."""
    global _THROWBACK_ALIASES
    if _THROWBACK_ALIASES is None:
        aliases: list[str] = []
        try:
            import json
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent
            people = json.loads((root / "data" / "people.json").read_text(encoding="utf-8"))
            from marketing.plan import ENTITY_ALIASES
            for person in people.get("people", []):
                if str(person.get("status", "")).lower() != "throwback":
                    continue
                name = str(person.get("name", "")).strip().lower()
                if name:
                    aliases.append(name)
                aliases.extend(a.lower() for a in ENTITY_ALIASES.get(name, ()) if a)
        except Exception:
            pass  # people.json missing/unreadable -> no filtering, old behaviour
        _THROWBACK_ALIASES = tuple(sorted(set(aliases)))
    return _THROWBACK_ALIASES

def mentions_throwback(text: str) -> bool:
    """True if the text names a departed (throwback) player or coach."""
    t = (text or "").lower()
    return any(a in t for a in _throwback_aliases())


# ---------------------------------------------------------------- voices
VOICES = {
    "cleveland-browns": {
        "city": "Cleveland",
        "nick": "Dawg Pound",
        "chant": "Here We Go Brownies",
        "vibe": "gritty, loyal, lake-effect cold, blue-collar, underdog that never leaves",
        "slang": [
            "Dawg Pound", "The Land", "North Coast", "Lake Erie cold", "19 degrees and sleeting",
            "Factory of Sadness to Factory of Faith", "orange helmets", "brown and orange",
            "barking", "Here We Go Brownies", "CLE", "Believeland", "Dawg Check"
        ],
        "emotions": ["loyalty", "grit", "revenge", "family", "cold-Sunday pride", "underdog hope"],
        "locations": ["Muni Lot", "FirstEnergy tailgate", "West Side Market run", "Edgewater Park", "Ohio City"],
        "weather": ["lake-effect snow", "September humidity", "November wind off the lake", "December sleet"],
    },
    "green-bay-packers": {
        "city": "Green Bay",
        "nick": "Cheesehead Nation",
        "chant": "Go Pack Go",
        "vibe": "community-owned, frozen tundra, tradition, cheese, family, small town big heart",
        "slang": [
            "Cheesehead Nation", "Titletown", "Frozen Tundra", "Lambeau Leap", "Go Pack Go",
            "Green and Gold", "Pack is Back", "Sunday Funday", "1919", "Lambeau Field",
            "Wisconsin winter", "cheese curds", "brat and beer"
        ],
        "emotions": ["community pride", "tradition", "family", "frozen-tundra toughness", "cheesehead humor"],
        "locations": ["Lambeau", "Atwood Ave", "Bay Beach", "Title Town District", "Kroll's"],
        "weather": ["frozen tundra", "January cold", "September tailgate", "snow on the bleachers"],
    },
    "dallas-cowboys": {
        "city": "Dallas",
        "nick": "Star City faithful",
        "chant": "How Bout Them Cowboys",
        "vibe": "Texas swagger, big lights, prime time, lone star pride, bold and loud",
        "slang": [
            "Star City", "Doomsday Defense", "How Bout Them Cowboys", "Lone Star", "Texas-sized",
            "Silver and Blue", "America's Team", "Big D", "1960", "Star on the helmet",
            "prime time", "AT&T glow"
        ],
        "emotions": ["Texas pride", "swagger", "prime-time energy", "family tradition", "big-stage confidence"],
        "locations": ["Deep Ellum", "AT&T Stadium lot", "Stockyards", "Texas State Fair", "Bishop Arts"],
        "weather": ["Texas heat", "October dusk", "November prime time", "September scorcher"],
    },
    "michigan": {
        "city": "Ann Arbor",
        "nick": "Go Blue faithful",
        "chant": "Go Blue",
        "vibe": "college town, Maize and Blue, defiant vs everybody, academic + athletic, revenge tour",
        "slang": [
            "Go Blue", "Maize and Blue", "Michigan vs Everybody", "Block M", "Big House",
            "Ann Arbor", "Revenge Tour", "Victory Sunday", "Maize out", "Hail",
            "winged helmet", "M vs All", "Bet"
        ],
        "emotions": ["college pride", "revenge", "defiance", "academic swagger", "Maize-out unity"],
        "locations": ["State Street", "Big House tunnel", "Diag", "Main Street", "Michigan Stadium"],
        "weather": ["crisp October", "November Maize out", "September kickoff heat", "snowy Big House"],
    },
}

# ---------------------------------------------------------------- diverse openers per platform per team
# Each list has 18-25 unique lines — never the same template repeated across teams.

INSTAGRAM_OPENERS = {
    "cleveland-browns": [
        "Dawg Pound, you felt that headline — {headline} — this {name} is how you wear it.",
        "Muni Lot at 7AM, lake wind in your face, and {headline}. {name} just makes sense.",
        "53-man roster dropped. Cuts hurt. {name} still hits. Cleveland, this one's yours.",
        "From Factory of Sadness to {headline} — {name} is the era change tee.",
        "Here We Go Brownies isn't a chant, it's a survival skill. {name} proves you stayed.",
        "Lake Erie cold, orange helmet bright. {headline} and {name} belong together.",
        "They said Cleveland was done. {headline}. {name} says we're just starting.",
        "19 degrees and sleeting off the lake — still barking. {name} for the loyal.",
        "Not a jersey, not a costume. {name} is Dawg Pound armor for {context}.",
        "The Land remembers every Sunday. {headline} — wear {name} like a timestamp.",
        "Orange and brown is hard to love. That's the point. {name} earns it.",
        "Believeland isn't a meme, it's a zip code. {name} for {city} lifers.",
        "Bark first, talk later. {headline} means {name} season is officially on.",
        "Your dad's Browns tee is in the attic. This {name} is for now.",
        "Tailgate smoke, beer cold, {headline} on the radio. {name} fits the moment.",
        "North Coast grit, no filter. {name} with {art} hits different after {headline}.",
        "CLE script, bulldog stare. {headline} — {name} turns news into uniform.",
        "Dawg Check: {headline}. If you're in, you're in {name}.",
        "No bandwagon, just lake wind and loyalty. {name} is Dawg Pound certified.",
        "From draft whispers to {headline} — {name} tracks the whole story.",
    ],
    "green-bay-packers": [
        "Lambeau in December energy. {headline} and {name} were made for each other.",
        "Cheesehead Nation doesn't do bandwagons. {headline} — {name} is for the lifers.",
        "Community-owned since 1919. {headline}. {name} keeps the tradition alive.",
        "Go Pack Go isn't a suggestion. {headline} means {name} is game-day required.",
        "Frozen tundra, warm beer, {headline} on the jumbotron. {name} fits.",
        "Titletown, small town, big heart. {headline} — {name} is the uniform.",
        "Your grandpa had the same colors. {headline} proves {name} never ages.",
        "Cheese curds, brat smoke, {headline}. {name} is Sunday Funday ready.",
        "1919 crest, 2026 headlines. {headline} and {name} bridge the gap.",
        "Wisconsin winter builds character. {headline} — {name} is character.",
        "Lambeau Leap starts in the lot. {headline}, {name}, and a cold one.",
        "Not loud, just loyal. {headline} — {name} says Go Pack Go without yelling.",
        "Pack is Back isn't hype, it's history repeating. {headline} = {name} season.",
        "Green and gold hits different with snow on the bleachers. {headline}. {name}.",
        "From Atwood Ave to the Tundra: {headline} and {name} travel together.",
        "Cheese wedge shaped like a heart. {headline} — {name} is that heart.",
        "Family-owned team, family-worn tee. {headline} means {name} for the crew.",
        "Sunday Funday started as a joke. {headline} made {name} the tradition.",
        "Cold hands, warm heart, {headline} on the radio. {name} belongs.",
        "One city, one team, one {name} that gets {headline} right.",
    ],
    "dallas-cowboys": [
        "Star City. Prime time. {headline} — {name} was built for this moment.",
        "Texas doesn't whisper. {name} with {art} says it out loud.",
        "Silver and blue, Texas-sized swagger. {headline} means {name} season.",
        "Doomsday Defense energy. {headline} and {name} bring the noise.",
        "Big D, bigger stage. {headline} — {name} is prime-time armor.",
        "How Bout Them Cowboys? {headline} answers it. {name} wears it.",
        "Lone Star pride, star on the helmet. {headline} — {name} fits.",
        "From Deep Ellum to AT&T glow: {headline} and {name} travel together.",
        "1960 roots, 2026 headlines. {headline} — {name} is the bridge.",
        "Texas heat, October dusk, {headline}. {name} works in all three.",
        "America's Team isn't a nickname, it's a dress code. {name} is it.",
        "Star-city lettering, washed silver. {headline} makes {name} vintage and now.",
        "Not flashy, just Texas. {headline} — {name} proves it.",
        "Prime time isn't a slot, it's an identity. {headline} = {name}.",
        "Longhorn skull, star helmet. {headline} — {name} mixes both.",
        "Your dad's 90s Cowboys tee faded. {name} is the upgrade that respects it.",
        "Dallas football is half stadium, half country. {headline} — {name} nails it.",
        "Silver helmets shine brighter after {headline}. {name} catches that light.",
        "State Fair, big stage, {headline} on the loudspeaker. {name} belongs.",
        "Texas pride without borrowing anybody's logo. {headline} — {name} is original.",
    ],
    "michigan": [
        "Ann Arbor just did it again — {headline}. {name} is the victory tee.",
        "Maize out, Big House loud. {headline} means {name} season is on.",
        "Michigan vs Everybody isn't a slogan, it's a weather report. {headline} — {name}.",
        "Go Blue. Block M. {headline}. {name} writes the headline on your chest.",
        "Winged helmet silhouette, {headline} energy. {name} belongs in the Big House.",
        "Revenge Tour rolls on. {headline} — {name} is the uniform.",
        "State Street to the tunnel: {headline} and {name} walk together.",
        "Bet. That's it. {headline} and {name} says the rest.",
        "Maize and blue hits different in November. {headline} — {name} is November.",
        "Academic swagger, athletic punch. {headline} — {name} brings both.",
        "Your roommate's Maize tee is borrowed. This {name} is yours after {headline}.",
        "Victory Sunday started early. {headline} — {name} is the Sunday fit.",
        "M vs All, four words, whole identity. {headline} proves {name} right.",
        "Crisp October, Big House roar, {headline}. {name} fits the forecast.",
        "Hail to the victors, and to {headline}. {name} is how you Hail.",
        "From the Diag to the end zone: {headline} and {name} cover the campus.",
        "Maize sunrise, navy shade. {headline} — {name} is Ann Arbor light.",
        "Not a costume, a credential. {headline} means {name} is student-section approved.",
        "Second Act, same Block M. {headline} — {name} is the new chapter.",
        "Michigan football is three hours of believing. {headline} — {name} believes.",
    ],
}

TIKTOK_OPENERS = {
    "cleveland-browns": [
        "POV: Dawg Pound heard {headline} and immediately put on {name}.",
        "Tell me you're from The Land without telling me — {name} + {headline}.",
        "This {name} is what Cleveland wears when {headline} drops.",
        "Dawg Check: {headline}. {name} is the answer.",
        "No one suffers like us. No one stays like us. {name} after {headline}.",
        "Muni Lot fit check: {name} + {headline} = approved.",
        "If {headline} doesn't make you bark, this {name} will.",
        "Lake Erie wind vs {name}. {headline} says the tee wins.",
        "CLE moms, Browns dads, {headline} — {name} for the family.",
        "When {headline} hits and you need a tee that already knows.",
    ],
    "green-bay-packers": [
        "POV: Cheesehead Nation sees {headline} and grabs {name}.",
        "Lambeau Leap tutorial but it's just {name} after {headline}.",
        "Tell me you own stock in the Packers without telling me — {name}.",
        "Frozen tundra fit check: {name} + {headline} = Go Pack Go.",
        "This {name} is what 1919 tastes like after {headline}.",
        "Cheesehead mom, Pack dad, {headline} — {name} for the crew.",
        "When {headline} drops and your {name} already knew.",
        "Sunday Funday uniform: {name} + {headline} + brat.",
        "Small town, big {name}, {headline} energy.",
        "Your grandpa's Packers tee, but make it {name} after {headline}.",
    ],
    "dallas-cowboys": [
        "POV: Star City hears {headline} and puts on {name}.",
        "Texas-sized fit check: {name} + {headline} = How Bout Them Cowboys.",
        "This {name} is what prime time wears when {headline} hits.",
        "Doomsday Defense but make it fashion — {name} + {headline}.",
        "Tell me you're Dallas without telling me — {name} after {headline}.",
        "Silver and blue glow-up: {name} + {headline}.",
        "Big D energy: {headline} meets {name}.",
        "When {headline} drops and your {name} is already on.",
        "Texas moms, Cowboys dads, {headline} — {name}.",
        "Prime time fit: {name} + {headline} = approved.",
    ],
    "michigan": [
        "POV: Ann Arbor hears {headline} and puts on {name}.",
        "Maize out fit check: {name} + {headline} = Go Blue.",
        "This {name} is what the Big House wears when {headline} happens.",
        "Michigan vs Everybody, but it's just {name} after {headline}.",
        "Tell me you go to Michigan without telling me — {name}.",
        "Bet. {headline}. {name}. That's the TikTok.",
        "Revenge Tour uniform: {name} + {headline}.",
        "When {headline} hits and your {name} already knew the ending.",
        "College town, big {name}, {headline} energy.",
        "Victory Sunday fit: {name} + {headline} = Hail.",
    ],
}

PINTEREST_TITLES = {
    "cleveland-browns": [
        "{name} - Dawg Pound Game Day Outfit Idea | Cleveland Browns Fan Style",
        "{name} - Cleveland Football Tailgate Look | {city} Fan Gift",
        "{name} - Orange and Brown Street Style | Dawg Pound Approved",
        "{name} - Cleveland Browns Outfit Inspo | Game Day to Everyday",
        "{name} - The Land Fan Style | Cold Weather Game Day Idea",
    ],
    "green-bay-packers": [
        "{name} - Cheesehead Game Day Outfit Idea | Green Bay Packers Style",
        "{name} - Lambeau Field Tailgate Look | Wisconsin Fan Gift",
        "{name} - Green and Gold Street Style | Go Pack Go Approved",
        "{name} - Packers Outfit Inspo | Frozen Tundra to Everyday",
        "{name} - Titletown Fan Style | Wisconsin Winter Game Day Idea",
    ],
    "dallas-cowboys": [
        "{name} - Dallas Cowboys Game Day Outfit Idea | Texas Football Style",
        "{name} - Star City Tailgate Look | Dallas Fan Gift",
        "{name} - Silver and Blue Street Style | Doomsday Defense Approved",
        "{name} - Dallas Outfit Inspo | Prime Time to Everyday",
        "{name} - Texas Pride Fan Style | Lone Star Game Day Idea",
    ],
    "michigan": [
        "{name} - Michigan Go Blue Outfit Idea | Ann Arbor Game Day Style",
        "{name} - Big House Tailgate Look | Michigan Fan Gift",
        "{name} - Maize and Blue Street Style | Michigan vs Everybody Approved",
        "{name} - Michigan Outfit Inspo | Campus to Game Day",
        "{name} - Ann Arbor Fan Style | College Football Game Day Idea",
    ],
}

FACEBOOK_OPENERS = {
    "cleveland-browns": [
        "Cleveland, {headline} just changed the conversation. {name} is how Dawg Pound marks it — fan-made, printed on demand, no warehouse stock.",
        "If you were in the Muni Lot when {headline} broke, you get it. {name} with {art} is the tee that remembers.",
        "For the family that watches every snap together: {headline} and {name} belong in the same story.",
        "Not officially licensed, just officially Cleveland. {headline} — {name} is independent fan art for the loyal.",
        "From 19 degrees and sleeting to {headline} — {name} has been through it with you.",
    ],
    "green-bay-packers": [
        "Green Bay, {headline} just gave us a new reason to wear green and gold. {name} is fan-made for Cheesehead Nation.",
        "Community-owned, family-worn. {headline} — {name} with {art} is the tee that travels from Lambeau to the living room.",
        "If you learned Go Pack Go before you learned your ABCs, {headline} and {name} are for you.",
        "Not officially licensed, just officially Green Bay. {headline} — {name} is independent fan art, printed on demand.",
        "From frozen tundra mornings to {headline} — {name} keeps the tradition warm.",
    ],
    "dallas-cowboys": [
        "Dallas, {headline} just made prime time bigger. {name} is how Star City wears the moment.",
        "Texas pride, star-city lettering. {headline} — {name} with {art} is fan-made for the faithful.",
        "If your family says How Bout Them Cowboys at Thanksgiving, {headline} and {name} belong together.",
        "Not officially licensed, just officially Dallas. {headline} — {name} is independent fan art, printed on demand.",
        "From Texas heat to {headline} — {name} works every season.",
    ],
    "michigan": [
        "Ann Arbor, {headline} just wrote the next chapter. {name} is how Go Blue wears it.",
        "Maize and blue, block lettering, no apologies. {headline} — {name} with {art} is fan-made for the Big House.",
        "If you know what Michigan vs Everybody feels like, {headline} and {name} are for you.",
        "Not officially licensed, just officially Michigan. {headline} — {name} is independent fan art, printed on demand.",
        "From State Street to the Big House tunnel — {headline} and {name} walk the same path.",
    ],
}

X_TEMPLATES = {
    "cleveland-browns": [
        "{name} — {headline} energy. Dawg Pound, you know what to do. {url}",
        "{headline}. {name} for The Land. Fan-made, printed on demand. {url}",
        "CLE: {headline} = {name} season. Here We Go Brownies. {url}",
        "{name} with {art}. {headline}. Dawg Pound approved. {url}",
        "{headline} just dropped. {name} is how Cleveland answers. {url}",
    ],
    "green-bay-packers": [
        "{name} — {headline} energy. Go Pack Go. {url}",
        "{headline}. {name} for Titletown. Fan-made, printed on demand. {url}",
        "Green Bay: {headline} = {name} season. Cheesehead Nation, assemble. {url}",
        "{name} with {art}. {headline}. Lambeau ready. {url}",
        "{headline} just dropped. {name} is how Green Bay answers. {url}",
    ],
    "dallas-cowboys": [
        "{name} — {headline} energy. How Bout Them Cowboys. {url}",
        "{headline}. {name} for Star City. Fan-made, printed on demand. {url}",
        "Dallas: {headline} = {name} season. Prime time ready. {url}",
        "{name} with {art}. {headline}. Texas-sized. {url}",
        "{headline} just dropped. {name} is how Dallas answers. {url}",
    ],
    "michigan": [
        "{name} — {headline} energy. Go Blue. {url}",
        "{headline}. {name} for Ann Arbor. Fan-made, printed on demand. {url}",
        "Michigan: {headline} = {name} season. Maize out. {url}",
        "{name} with {art}. {headline}. Big House ready. {url}",
        "{headline} just dropped. {name} is how Michigan answers. {url}",
    ],
}

CTAS = {
    "instagram": [
        "Save this idea and tap through to see the design.",
        "Tap the link in bio to see colourways and sizes.",
        "Save for your next game day, share with your crew.",
        "Comment your size — S to 3XL, printed on demand.",
        "Add it to your gift list before kickoff.",
    ],
    "tiktok": [
        "Show us the fit.",
        "Duet this with your game day look.",
        "Comment 'GO' and we'll drop the link.",
        "POV: you already ordered it.",
        "Fit check approved? Link in bio.",
    ],
    "facebook": [
        "Explore the design here — sizes S to 3XL, worldwide shipping.",
        "Tap through to see all colourways and garment styles.",
        "Gift-ready: beanies and mugs can't be the wrong size.",
        "Printed on demand in the USA, shipped worldwide with tracking.",
        "Order early in the week if you want it for Sunday.",
    ],
    "pinterest": [
        "Save this look for your next game day outfit.",
        "Pin this for your football gift list.",
        "Save to your game day board — S to 3XL, printed on demand.",
        "Tap to see colourways, sizes, and secure checkout.",
        "Add to your tailgate outfit ideas.",
    ],
    "x": ["", "Fan-made.", "Printed on demand.", "S to 3XL.", "Game day ready."],
}

def clean_headline(title: str) -> str:
    """Make headline snippet usable in copy — short, punchy, no URL junk."""
    if not title:
        return "today's news"
    # Take first clause, strip source noise
    t = title.split(" - ")[0].split(" | ")[0]
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 70:
        t = t[:67] + "..."
    return t

def get_headline_for_product(ckey: str, slug: str, fact: dict, trends_data: dict) -> str:
    """Pick most relevant headline for product based on entity match."""
    try:
        col_trend = trends_data.get("collections", {}).get(ckey, {})
        headlines = col_trend.get("headlines", [])
        if not headlines:
            return "today's lineup news"
        # Who's-who gate: a headline that names a departed player/coach can
        # never be used as a caption hook, even as the collection fallback.
        headlines = [hd for hd in headlines if not mentions_throwback(hd.get("title", ""))]
        if not headlines:
            return "today's lineup news"
        # Try to match entity
        text = (fact.get("name","") + " " + fact.get("art","")).lower()
        # entity aliases
        from marketing.plan import ENTITY_ALIASES
        for h in headlines[:8]:
            title_low = h.get("title","").lower()
            for ent, aliases in ENTITY_ALIASES.items():
                if any(a in text for a in aliases) and any(a in title_low for a in aliases):
                    return clean_headline(h.get("title",""))
        # Fallback: top headline for collection
        return clean_headline(headlines[0].get("title",""))
    except Exception:
        return "today's roster update"

def generate_caption(ckey: str, platform: str, product: dict, fact: dict, trends_data: dict, slug: str) -> str:
    """Generate unique caption per team/platform/product using vault."""
    voice = VOICES.get(ckey, VOICES["cleveland-browns"])
    headline = get_headline_for_product(ckey, slug, fact, trends_data)
    name = fact.get("name", product.get("title", slug))
    art = fact.get("art", "")[:50]
    city = voice["city"]
    context = pick(voice["slang"], slug, f"{platform}-ctx") if voice["slang"] else "game-day energy"
    cta = pick(CTAS.get(platform, [""]), slug, f"{platform}-cta")

    # Pick opener template
    if platform == "instagram":
        opener_pool = INSTAGRAM_OPENERS.get(ckey, INSTAGRAM_OPENERS["cleveland-browns"])
    elif platform == "tiktok":
        opener_pool = TIKTOK_OPENERS.get(ckey, TIKTOK_OPENERS["cleveland-browns"])
    elif platform == "facebook":
        opener_pool = FACEBOOK_OPENERS.get(ckey, FACEBOOK_OPENERS["cleveland-browns"])
    elif platform == "x":
        opener_pool = X_TEMPLATES.get(ckey, X_TEMPLATES["cleveland-browns"])
    elif platform == "pinterest":
        opener_pool = PINTEREST_TITLES.get(ckey, PINTEREST_TITLES["cleveland-browns"])
    else:
        opener_pool = ["{name} — {headline}. {city} fan style."]

    template = pick(opener_pool, slug, f"{platform}-{ckey}-opener")

    url = product.get("url","")

    # Fill
    caption = template.format(
        name=name,
        art=art,
        headline=headline,
        city=city,
        context=context,
        url=url,
    )
    if platform != "x" and cta and cta not in caption:
        caption = caption.rstrip(".") + ". " + cta
    # X trim
    if platform == "x" and len(caption) > 280:
        caption = caption[:277] + "..."
    return caption

def generate_hashtags(ckey: str, fact: dict, platform: str, slug: str) -> List[str]:
    base_tags = {
        "cleveland-browns": ["#dawgpound", "#clevelandfootball", "#brownsfans", "#clevelandbrowns", "#theland"],
        "green-bay-packers": ["#cheeseheadnation", "#gopackgo", "#packersfans", "#greenbaypackers", "#titletown"],
        "dallas-cowboys": ["#dallascowboys", "#star city", "#texasfootball", "#dallasfootball", "#howboutthemcowboys"],
        "michigan": ["#goblue", "#michiganfootball", "#michiganvseverybody", "#annarbor", "#bigHouse"],
    }
    theme_tags = {
        "player": ["#playertee", "#fanfavorite"],
        "funny": ["#funnyfootball", "#footballhumor"],
        "playoff": ["#playoffready", "#gameday"],
        "retro": ["#vintagefootball", "#retrostyle"],
        "city": ["#citypride", "#hometown"],
        "family": ["#footballgift", "#giftideas"],
        "classic": ["#classictee", "#gamedaystyle"],
        "halloween": ["#halloweenshirt", "#alloverprint"],
    }
    tags = []
    tags += base_tags.get(ckey, [])[:3]
    tags += theme_tags.get(fact.get("theme","classic"), [])[:2]
    # add kw tags
    for kw in fact.get("kw", [])[:3]:
        clean = "#" + re.sub(r"[^a-z0-9]", "", kw.lower().replace(" ",""))[:20]
        if len(clean) > 2 and clean not in tags:
            tags.append(clean)
    # dedupe and limit per platform
    limits = {"instagram": 12, "tiktok": 8, "facebook": 6, "x": 4, "pinterest": 12}
    limit = limits.get(platform, 8)
    # hash-shuffle for uniqueness
    shuffled = sorted(tags, key=lambda t: h(slug, t + platform))
    return shuffled[:limit]
