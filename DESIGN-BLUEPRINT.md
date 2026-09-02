# Gridiron Locker — Design Blueprint

> The graphic rules every shirt in this locker has to pass before it is
> printed, published or promoted. Last updated 2026-09-02.
>
> Companion docs: `BLUEPRINT.md` (the business), `SITE-BLUEPRINT.md` (the
> storefront), `HOW-TO-ADD-A-DESIGN.md` (the mechanical handoff).

**One-line version:** we print identity slogans, not player faces.

---

## 1. The one law

A Gridiron Locker design says who you are, not who you are wearing a jersey
of. The graphic is the fan's voice — a chant, a city, a grudge, a joke — never
a portrait of somebody else's employee.

That single rule does three jobs at once:

1. **It ages well.** Rosters turn over every off-season. A slogan does not.
2. **It is defensible.** No face, no name, no number, no mark = far less
   exposure than the licensed-merch pattern that got the Instagram account
   disabled (see `BLUEPRINT.md` §9).
3. **It is printable.** Flat vector lettering survives DTG, screen print and
   embroidery. Photographs do not.

---

## 2. Never print this

Applies to the artwork, the mockups, the product title, the alt text and the
ad copy.

| Never | Why | Use instead |
|---|---|---|
| A player's face, silhouette or photo | Likeness + trademark exposure | Type-only slogan |
| A player's surname on the chest | Same, plus it dates the shirt | City, chant or era slogan |
| A jersey number | Reads as a name-by-another-means | EST year, EST city, no numerals |
| Team logos, wordmarks, helmet marks | Directly claimed IP | Original geometry + colour |
| Press/action photography | Copyright + likeness | Hand-drawn line art |
| "Officially licensed" or any claim of it | False statement | "Independent, fan-made" |
| A slot that is still empty | "No design yet" kills a page | Ship the live sibling (§5c) |

**The Watson rule (current, non-negotiable).** The Cleveland quarterback slot
is **slogan only**: `LET IT RIP` and `NEW ERA`. No face. No `WATSON`. No `#4`.
No number of any kind. If art lands with any of those on it, it does not ship —
not to the store, not to social, not to the board's live column.

---

## 3. Type and layout

| Rule | Value |
|---|---|
| Front print area | 12 in wide × 16 in tall, centred |
| Safe margins | 1 in below the collar, 0.75 in from each side seam |
| Master file | 4500 × 5400 px, 300 dpi, transparent PNG, sRGB |
| Working file | Vector (SVG/AI) — never rasterise before export |
| Max colours, screen print | 2 spot colours |
| Max colours, DTG | Unlimited, but keep the palette to §4 |
| Min cap height | 0.35 in (anything smaller fills in on fleece) |
| Min stroke weight | 0.02 in at 300 dpi (≈ 3 px at master size) |
| Tracking | −1% to +2% on display caps; never below −2% |
| Line count | 3 lines maximum on the chest, 1 line on the sleeve |
| Composition | One hero line, one support line, one rule/device. Nothing else. |

Layout archetypes (pick one per design, do not mix):

- **Stack** — hero line over support line, left-aligned, hard edge.
- **Arch** — hero line curved over a device (helmet shape, state outline, star).
- **Stencil** — cut-out caps on a plate, athletic department energy.
- **Outline** — state or city silhouette filled with the slogan.

---

## 4. Colour

Palette is per collection; the accent comes from `src/collections_data.py`
`COLLECTIONS[...]["accent"]` and is the source of truth.

| Collection | Accent | Deep | Ink | Garment base |
|---|---|---|---|---|
| Cleveland | `#FF6A13` | `#311D00` | `#FFFFFF` | black, orange, brown, heather grey |
| Green Bay | `#2BAE66` | `#0C2B20` | `#FFFFFF` | forest, gold, heather grey, cream |
| Dallas | `#8FA0B8` | `#0B1B33` | `#FFFFFF` | heather navy, silver, vintage white |
| Michigan | `#FFCB05` | `#00274C` | `#FFFFFF` | navy, maize, heather grey |

Rules:

1. One accent + one ink per design. Two accent colours only for vintage washes.
2. Never print accent-on-accent — legibility beats enthusiasm.
3. On dark garments, knock the ink out of the accent block; do not print white
   underlay on fleece.
4. Every design must survive being printed on the lightest and the darkest
   garment in its range. If it only works on one, it is two designs, not one.

---

## 5. Slogan system

### 5a — Standing slogan bank

Evergreen, printed year-round, safe to rerun.

| Collection | Bank |
|---|---|
| Cleveland | Dawg Pound · Under Dawgs · Find A Way By Any Means · Sundays Are For The Dawgs · 19 Degrees And Sleeting · Est 1946 |
| Green Bay | Go Pack Go · Cheesehead Nation · Sunday Funday · The Future Is Green · Est 1919 · Frozen Tundra |
| Dallas | Star City · Doomsday · Texas Pride · Est 1960 · How 'Bout Them · Y'all Can Kiss My Longhorn |
| Michigan | Go Blue · Michigan Vs Everybody · Bet · Revenge Tour · Est 1879 · Big Ten November |

### 5b — Week 1 drop (Sept 5–13, 2026)

Eight slots, two per collection. Statuses are **internal only** — see §5c.

| Slot | Collection | Kickoff | Slogan | Garment | Palette | Status |
|---|---|---|---|---|---|---|
| W1-01 | Cleveland | Sept 13 @ Jacksonville | **LET IT RIP** | Tee + hoodie | `#FF6A13` on ink black | art |
| W1-02 | Cleveland | Sept 13 @ Jacksonville | **NEW ERA** | Crewneck + tee | bone on `#311D00` | art |
| W1-03 | Green Bay | Sept 13 @ Minnesota | **GO PACK GO** | Tee | `#2BAE66` + gold | live |
| W1-04 | Green Bay | Sept 13 @ Minnesota | **SUNDAY FUNDAY** | Crewneck | cream on forest | art |
| W1-05 | Dallas | Sept 13 @ NY Giants (SNF) | **STAR CITY** | Tee | `#8FA0B8` on `#0B1B33` | brief |
| W1-06 | Dallas | Sept 13 @ NY Giants (SNF) | **DOOMSDAY** | Vintage tee | washed silver | live |
| W1-07 | Michigan | Sept 5 vs Western Michigan | **MICHIGAN VS EVERYBODY** | Sweatshirt | `#FFCB05` on `#00274C` | live |
| W1-08 | Michigan | Sept 5 vs Western Michigan | **BET** | Tee | maize on navy | art |

Slot rules:

- **W1-01 / W1-02 are the Cleveland quarterback slots.** Slogan only —
  `LET IT RIP` / `NEW ERA`. No face, no `WATSON`, no `#4`, no number.
- **W1-07 / W1-08** are the earliest kickoff in the locker (Sept 5), so they
  are the first slots that must be finished. Michigan leads the Week 1 page.
- **W1-06** already exists as *Doomsday Defense Dallas Football Shirt*; the new
  art is a cleaner single-word redraw, not a replacement of the live listing.
- Status ladder: `brief` → `art` → `upload` → `live`. Nothing promotes without
  passing §7.

### 5c — No slot is ever empty in public

A slot can be `brief` internally, but a shopper never sees that. Every Week 1
slot carries a **live sibling**: a real, buyable, slogan-led design from the
same collection that is shown on the public page until the new art lands.

Selection order for a sibling, applied by `week1_picks()` in `src/build.py`:

1. Slogan-led themes first — `playoff`, `city`, `retro`, `classic`, `funny`.
2. Never a player theme while a slogan-led design is available.
3. Fewer than four available? Fill from the rest of the collection.
4. Still empty? Fall back to the collection's top designs.

The public page therefore always renders a full grid, and the strings
"no design yet", "coming soon" and "TBD" are banned from every page under
`site/`. They are fine in `ops/` — that is what the operator board is for.

---

## 6. Naming and handoff

**Slug** — `let-it-rip-tee`, `new-era-crewneck`. Lowercase, hyphenated, no
numbers, no surnames, no team name (the collection page carries the team).

**Title** — `{Slogan} {Garment}` + collection word. e.g. *Let It Rip Cleveland
Football Shirt*. Title case, no all-caps beyond the slogan itself, ≤ 60 chars
so it survives the SERP clip.

**Copy facts** — one entry in `src/catalog.py` with `name`, `art` (one sentence,
what the graphic says and who it is for), `kw` (keywords), `theme`.

**Then:**

```bash
python3 scrape_products.py      # pull the new listing
python3 dl.py                   # download the imagery
python3 src/build.py            # regenerate every page + sitemap + llms.txt
```

Full walkthrough: `HOW-TO-ADD-A-DESIGN.md`.

---

## 7. QA before a design goes live

- [ ] No face, no surname, no number, no team mark (§2)
- [ ] Watson slot: slogan only, `LET IT RIP` or `NEW ERA` (§2)
- [ ] Master file 4500 × 5400, 300 dpi, transparent PNG (§3)
- [ ] Legible on the lightest *and* darkest garment in range (§4)
- [ ] Palette uses only that collection's accent + ink (§4)
- [ ] Slogan is in the bank (§5a) or the Week 1 slate (§5b)
- [ ] Slug, title and alt text follow §6
- [ ] `src/catalog.py` entry added; `theme` is slogan-led where possible
- [ ] Rebuild is clean; page appears in `sitemap.xml`
- [ ] Public pages show a live sibling, never an empty slot (§5c)

---

## 8. Compliance guardrails

Independent and fan-made. Every page carries the disclaimer; every new design
should make the disclaimer easy to believe.

- Team and city names are used **descriptively**, to say who a design is for.
- Player names are not used on new art at all (§2). Legacy catalogue pages keep
  their historical copy but are flagged throwback by the trend pipeline
  (`data/people.json`) and must not be promoted.
- Nothing in this doc authorises a claim of licence, affiliation or
  endorsement. If a design needs one of those to work, the design is wrong.
