"""Collection-level SEO + brand data."""

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
        accent="#FF6A13",
        accent2="#311D00",
        ink="#ffffff",
        hero="/img/hero-cleveland.jpg",
        store="https://viralstyle.com/store/kebystore/Cleveland-Browns/1",
        chant="Here We Go Brownies",
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
             "Most designs are offered on black, white, orange, brown, heather grey, navy and red garments. Pick the colourway you want on the checkout page before adding to your bag."),
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
        accent="#8FA0B8",
        accent2="#0B1B33",
        ink="#ffffff",
        hero="/img/hero-dallas.jpg",
        store="https://viralstyle.com/store/kebystore/dallas-vintage-sports/1",
        chant="How 'Bout Them Cowboys",
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
        accent="#FFB612",
        accent2="#0C2B20",
        ink="#ffffff",
        hero="/img/hero-greenbay.jpg",
        store="https://viralstyle.com/store/kebystore/Packss/1",
        chant="Go Pack Go",
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
        accent="#FFCB05",
        accent2="#00274C",
        ink="#ffffff",
        hero="/img/hero-michigan.jpg",
        store="https://viralstyle.com/store/kebystore/MICHIG/1",
        chant="Go Blue",
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

# 2026 season context (researched 24 Aug 2026)
SEASON = {'cleveland-browns': {'status': 'QB1 decision expected Monday, Aug 24', 'headline': 'Shedeur Sanders vs Deshaun Watson: Cleveland names its 2026 starter this week.', 'kickoff': '2026-09-13T13:00:00-04:00', 'opener': 'Week 1 &middot; Sept 13 at Jacksonville', 'hot': ['shedeur sanders shirt', 'sanders browns qb shirt', 'browns qb1 2026 shirt', 'sanders 2026 tee'], 'legacy_note': 'Flacco, Myles Garrett and Kevin Stefanski designs are now throwback pieces - Garrett was traded in June 2026 and Todd Monken took over as head coach.'}, 'green-bay-packers': {'status': 'Jordan Love enters 2026 as QB1, Micah Parsons on the roster', 'headline': 'Green Bay opens Week 1 at Minnesota with Love under centre.', 'kickoff': '2026-09-13T16:25:00-05:00', 'opener': 'Week 1 &middot; Sept 13 at Minnesota', 'hot': ['jordan love 2026 shirt', 'packers 2026 shirt', 'go pack go 2026 tee', 'packers week 1 shirt'], 'legacy_note': ''}, 'dallas-cowboys': {'status': 'Season opens Sunday night at the Giants', 'headline': 'Dallas kicks off 2026 in prime time on Sept 13.', 'kickoff': '2026-09-13T20:20:00-05:00', 'opener': 'Week 1 &middot; Sept 13 at NY Giants (SNF)', 'hot': ['dallas 2026 shirt', 'cowboys week 1 shirt', 'dallas football 2026 tee', 'texas football shirt 2026'], 'legacy_note': ''}, 'michigan': {'status': "Bryce Underwood named 2026 captain, Kyle Whittingham's first season", 'headline': 'Michigan opens Sept 5 vs Western Michigan under new head coach Kyle Whittingham.', 'kickoff': '2026-09-05T12:00:00-04:00', 'opener': 'Sept 5 vs Western Michigan', 'hot': ['bryce underwood shirt', 'michigan 2026 shirt', 'go blue 2026 tee', 'michigan football 2026 shirt'], 'legacy_note': 'J.J. McCarthy designs are throwback pieces now - Bryce Underwood is the current QB and a 2026 team captain.'}}
