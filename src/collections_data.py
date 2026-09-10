"""Collection-level SEO + brand data."""
import datetime as _dt
from zoneinfo import ZoneInfo as _ZoneInfo

COLLECTIONS = {
    "cleveland-browns": dict(
        slug="cleveland-browns-shirts",
        name="Cleveland Browns Fan Shirts",
        short="Cleveland",
        h1="Cleveland Browns Fan Shirts & Dawg Pound Apparel",
        title="Cleveland Browns Fan Shirts, Hoodies & Dawg Pound Gear",
        city="Cleveland, Ohio",
        team="Browns",
        nick="Dawg Pound",
        est="1946",
        accent="#C8410B",
        accent2="#3B2415",
        accent_ink="#9C3208",
        accent_tint="#FDF3EE",
        btn_hover="#A83608",
        vs_name="ORANGE AND BROWN COLLECTION",
        banner='Orange and brown Dawg Pound apparel - bulldog graphics, Cleveland skylines, playoff slogans and quarterback tributes, printed on tees, hoodies, crewnecks, beanies and mugs.',
        ink="#ffffff",
        hero="/img/hero-cleveland.jpg?v=4",
        logo="/img/browns-logo1.webp?v=1",
        store="https://viralstyle.com/store/kebystore/Cleveland-Browns/1",
        chant="Here We Go Brownies",
        # Short cultural phrase used as the headline of the homepage team card.
        phrase="Dawg Pound",
        keywords=[
            "cleveland browns shirts", "dawg pound shirt", "browns fan gear",
            "cleveland football t-shirt", "browns hoodie", "cleveland ohio apparel",
            "browns gifts for men", "cleveland browns womens shirt",
        ],
        intro=(
            "Every design in this collection is drawn, printed and shipped for the people who "
            "still show up when it is 19 degrees and sleeting off Lake Erie. This is "
            "{nick} apparel for the loyal: bulldog graphics, {city} skylines, playoff slogans, "
            "coach humour and quarterback tributes, printed on soft ring-spun cotton tees, "
            "heavyweight hoodies, crewnecks, beanies and mugs."
        ),
        lore=[
            "Orange and brown is not an easy colour combination to love, and that is exactly the point.",
            "The Dawg Pound has been the loudest cheap seats in football since the eighties.",
            "Cleveland fans measure the year in Sundays, not months.",
        ],
        faq_extra=[
            ("Do these shirts come in Dawg Pound orange and brown?",
             "Garment colourways are set per campaign, so the range differs from design to design. Each product page previews the colourways that design's campaign published; the authoritative, current list is on the Viralstyle product page, where you pick the one you want."),
        ],
    ),
    "dallas-cowboys": dict(
        slug="dallas-cowboys-shirts",
        name="Dallas Vintage Sports Tees",
        short="Dallas",
        h1="Dallas Football Vintage Tees & Texas Pride Apparel",
        title="Dallas Football Vintage T-Shirts & Texas Pride Tees",
        city="Dallas, Texas",
        team="Dallas",
        nick="America's Team faithful",
        est="1960",
        accent="#2C4A72",
        accent2="#97A6B8",
        accent_ink="#26405F",
        accent_tint="#F2F5F9",
        btn_hover="#22395A",
        vs_name="Dallas Vintage Sports Graphic Tee",
        banner='Celebrate your pride for the city with classic vintage-style designs - worn-in athletic prints, star-city lettering and Texas pride, for game days and everyday casual wear.',
        ink="#ffffff",
        hero="/img/hero-dallas.jpg?v=4",
        logo="/img/dallas-logo1.webp?v=1",
        store="https://viralstyle.com/store/kebystore/dallas-vintage-sports/1",
        chant="How 'Bout Them Cowboys",
        phrase="Star Power",
        keywords=[
            "dallas cowboys shirt", "vintage dallas football tee", "texas pride shirt",
            "doomsday defense shirt", "dallas football t-shirt", "this girl loves cowboys",
            "dallas texas graphic tee", "cowboys gifts",
        ],
        intro=(
            "Washed-out seventies athletics, longhorn skulls, star-and-lightning graphics and "
            "distressed 1960 helmets. This capsule is built around vintage {city} football style: "
            "silver, navy and heather grey garments that look like they were pulled out of a "
            "stadium locker forty years ago."
        ),
        lore=[
            "Silver and blue reads as vintage the second you wash it twice.",
            "Texas football style is half stadium, half country: helmets, stars and longhorns.",
            "Every design here is printed on demand, so nothing sits in a warehouse fading.",
        ],
        faq_extra=[
            ("Are these officially licensed Dallas Cowboys products?",
             "No. These are independent fan-made graphic tees inspired by Dallas football culture and Texas pride. They are not affiliated with, endorsed by or licensed by any professional football club."),
        ],
    ),
    "green-bay-packers": dict(
        slug="green-bay-packers-shirts",
        name="Green Bay Packers Fan Shirts",
        short="Green Bay",
        h1="Green Bay Packers Fan Shirts, Cheesehead Tees & Hoodies",
        title="Green Bay Packers Fan Shirts, Cheesehead Tees & Hoodies",
        city="Green Bay, Wisconsin",
        team="Packers",
        nick="Cheesehead Nation",
        est="1919",
        accent="#1A6B47",
        accent2="#D8A21A",
        accent_ink="#155739",
        accent_tint="#EFF6F2",
        btn_hover="#135238",
        vs_name="Welcome G Fans",
        banner='Green and gold for the frozen tundra faithful - cheesehead humour, Lambeau tributes, EST 1919 crests and Go Pack Go scripts on tees, hoodies and crewnecks.',
        ink="#ffffff",
        hero="/img/hero-greenbay.jpg?v=4",
        logo="/img/green-bay-logo1.webp?v=1",
        store="https://viralstyle.com/store/kebystore/Packss/1",
        chant="Go Pack Go",
        phrase="Go Pack Go",
        keywords=[
            "green bay packers shirt", "go pack go t-shirt", "cheesehead shirt",
            "jordan love shirt", "packers hoodie", "wisconsin football tee",
            "packers gifts for men", "green bay womens shirt",
        ],
        intro=(
            "Green, gold and a lot of cheese. This collection covers {nick} from every angle: "
            "quarterback tributes, EST {est} collegiate crests, Wisconsin state outlines, "
            "Sunday Funday scripts and the kind of retro lettering that looks right on a "
            "frozen January afternoon."
        ),
        lore=[
            "Nineteen nineteen. Publicly owned. Coldest ticket in football.",
            "A cheese wedge shaped like a heart is a whole personality in Wisconsin.",
            "Green and gold hits differently when there is snow on the sideline.",
        ],
        faq_extra=[
            ("Which Green Bay designs work as gifts?",
             "The cheese-heart mug, the EST 1919 collegiate crest and the Go Pack Go stencil tee are the three easiest gifts to buy for someone else because they are not tied to one player."),
        ],
    ),
    "michigan": dict(
        slug="michigan-wolverines-shirts",
        name="Michigan Go Blue Apparel",
        short="Michigan",
        h1="Michigan Football Shirts, Go Blue Tees & Sweatshirts",
        title="Michigan Football Shirts, Go Blue Tees & Sweatshirts",
        city="Ann Arbor, Michigan",
        team="Michigan",
        nick="Go Blue faithful",
        est="1879",
        accent="#00274C",
        accent2="#E8B800",
        accent_ink="#00274C",
        accent_tint="#F2F5F9",
        btn_hover="#001B36",
        vs_name="MAIZE & NAVY",
        banner='Vintage-inspired football gear built for Saturdays in Ann Arbor - worn-in athletic prints, block lettering, classic maize and navy, timeless gridiron energy.',
        ink="#ffffff",
        hero="/img/hero-michigan.jpg?v=4",
        logo="/img/michigan-logo1.webp?v=1",
        store="https://viralstyle.com/store/kebystore/MICHIG/1",
        chant="Go Blue",
        phrase="Go Blue",
        keywords=[
            "michigan football shirt", "go blue t-shirt", "michigan vs everybody shirt",
            "jj mccarthy shirt", "michigan sweatshirt", "ann arbor apparel",
            "michigan wolverines gifts", "maize and blue tee",
        ],
        intro=(
            "Maize and blue, block lettering and zero apologies. Heavyweight crewnecks and tees "
            "built around the phrases {short} fans actually shout: Michigan vs Everybody, "
            "Revenge Tour, Victory Sunday and Bet."
        ),
        lore=[
            "Michigan vs Everybody is less a slogan than a weather report in Ann Arbor.",
            "The winged helmet is the most recognisable silhouette in college football.",
            "Heavy navy crewnecks are the unofficial uniform of a Big Ten November.",
        ],
        faq_extra=[
            ("Do the Michigan designs run big?",
             "The crewneck sweatshirts in this collection are unisex and roomy. If you want a slim fit, order one size down; if you are layering over a hoodie, keep your normal size."),
        ],
    ),
}

ORDER = ["cleveland-browns", "green-bay-packers", "dallas-cowboys", "michigan"]

# 2026 season context. `kickoff` is each collection's 2026 opener; `opener`,
# `headline` and `status` are written in the tense that is correct TODAY (a
# game that has already been played reads "Final", one still ahead reads as
# upcoming). `result` is set once a game is complete so date-sensitive pages
# can render a recap instead of a countdown. When the next fixture happens,
# update this dict - every page reads it, so nothing else has to change.
SEASON = {'cleveland-browns': {'status': 'Todd Monken has named his captains for Week 1.', 'headline': 'Cleveland opens the season at Jacksonville with Sanders and Watson leading the QB room.', 'kickoff': '2026-09-13T13:00:00-04:00', 'opener': 'Week 1 &middot; Sept 13 at Jacksonville', 'hot': ['shedeur sanders shirt', 'sanders browns qb shirt', 'browns qb1 2026 shirt', 'sanders 2026 tee'], 'legacy_note': 'Designs for departed players and coaches - Joe Flacco, Myles Garrett and Kevin Stefanski - were retired ahead of the 2026 season; Garrett was traded in June 2026 and Todd Monken took over as head coach.', 'result': ''}, 'green-bay-packers': {'status': 'Jordan Love enters 2026 as QB1 with Josh Jacobs carrying the run game.', 'headline': 'Green Bay opens Week 1 at Minnesota with Love under centre.', 'kickoff': '2026-09-13T16:25:00-05:00', 'opener': 'Week 1 &middot; Sept 13 at Minnesota', 'hot': ['jordan love 2026 shirt', 'packers 2026 shirt', 'go pack go 2026 tee', 'packers week 1 shirt'], 'legacy_note': '', 'result': ''}, 'dallas-cowboys': {'status': 'Dallas opens in prime time on Sunday night.', 'headline': 'Dallas kicks off 2026 on Sunday night at the Giants.', 'kickoff': '2026-09-13T20:20:00-05:00', 'opener': 'Week 1 &middot; Sept 13 at NY Giants (SNF)', 'hot': ['dallas 2026 shirt', 'cowboys week 1 shirt', 'dallas football 2026 tee', 'texas football shirt 2026'], 'legacy_note': '', 'result': ''}, 'michigan': {'status': 'The Wolverines host No. 11 Oklahoma on Saturday.', 'headline': 'Michigan opened 2026 with a last-second Hail Mary win over Western Michigan.', 'kickoff': '2026-09-05T19:30:00-04:00', 'opener': 'Final &middot; Sept 5 vs Western Michigan', 'hot': ['bryce underwood shirt', 'michigan 2026 shirt', 'go blue 2026 tee', 'michigan football 2026 shirt'], 'legacy_note': 'J.J. McCarthy designs were retired - Bryce Underwood is the current QB and a 2026 team captain.', 'result': 'Michigan opened the 2026 season on Sept 5 with a Hail Mary win over Western Michigan. The Wolverines host No. 11 Oklahoma on Saturday.'}}


# ---------------------------------------------------------------- next game
# Homepage / /collections/ display order: the collection that kicks off
# soonest goes first. v1 has no real 2026 schedule yet, so each collection's
# slate is rolled forward WEEKLY from its SEASON opener date using the
# league's typical kickoff window (approximate is fine - this is ordering
# only). To swap in a real schedule later, replace _KICKOFF_WINDOW + the roll
# in next_game() with an explicit per-collection list of ISO kickoff strings
# and pick the first entry >= now - callers only read NEXT_GAME / next_game(),
# so nothing downstream changes.
# Weekly kickoff template per collection: (weekday, "HH:MM" Eastern).
# weekday: Monday=0 ... Sunday=6.
_KICKOFF_WINDOW = {
    "cleveland-browns":  (6, "13:00"),   # NFL Sunday early window
    "green-bay-packers": (6, "13:00"),   # NFL Sunday early window
    "dallas-cowboys":    (6, "13:00"),   # NFL Sunday early window
    "michigan":          (5, "19:30"),   # Saturday night under the lights
}
_ET = _ZoneInfo("America/New_York")


def next_game(ckey, now=None):
    """ISO datetime of the collection's next kickoff (>= now).

    v1: use the SEASON opener date, then roll forward weekly
    (michigan: Saturdays 19:30 ET, NFL: Sundays 13:00 ET) until >= now.
    Kickoff times approximate is fine - this is for ordering only.
    """
    weekday, hhmm = _KICKOFF_WINDOW[ckey]
    hh, mm = hhmm.split(":")
    opener_date = _dt.date.fromisoformat(SEASON[ckey]["kickoff"][:10])
    now = now or _dt.datetime.now(_dt.timezone.utc)
    # First candidate: the opener's date at the template kickoff time (ET),
    # then every 7 days after until we reach the next game still ahead.
    kick = _dt.datetime(opener_date.year, opener_date.month, opener_date.day,
                        int(hh), int(mm), tzinfo=_ET)
    while kick <= now:
        kick += _dt.timedelta(days=7)
    return kick.astimezone(_dt.timezone.utc).isoformat()


# ISO kickoff of each collection's next game, computed once at import with
# UTC now (today: 2026-09-05). Read-only for callers.
NEXT_GAME = {ckey: next_game(ckey) for ckey in ORDER}
