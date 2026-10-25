# Mayzing store theme — making the storefront look like the locker

The creator lockers (`/crystal/`, `/amber/`, `/laquala/`, `/des/`, `/yvette/`, plus
`/michigan/joe/` and `/michigan/bella/`) are warm-parchment pages. The shop they
hand off to (`gridironlocker.shop`) runs one store-wide theme, so the moment a
client taps a design the palette, the type and the header all change. That jump is
what reads as "a different shop".

This file is the exact spec to type into the Mayzing dashboard. Everything below
is a **dashboard setting**, not a code change: no URL parameter can carry a palette,
and a Mayzing store has one theme for every creator.

Two things are already handled on our side and need no action:

- every product card opens the store's own product page, tagged (`?creator=…&utm_…`),
  so attribution survives the jump (`store_href()` in `src/build.py`);
- every creator grid says where the checkout happens before a card is tapped
  ("Secure checkout on gridironlocker.shop").

---

## 1. Palette

Theme → Colours. If a field is missing, use the nearest equivalent and leave the
rest alone; the goal is that the two pages sit in the same family, not that they
match pixel for pixel.

| Role | Hex | In a locker |
|---|---|---|
| Page background | `#F4EAD9` | body, header, nav bar |
| Card / panel surface | `#FFFAF2` | product cards, forms, social pills |
| Soft panel (alternate rows) | `#F8F1E5` | about block, "what you get" panels |
| Ink (headings, prices) | `#2C1A0F` | h1–h3, prices, primary buttons |
| Body / muted text | `#6F5C4A` | descriptions, meta lines, footnotes |
| Hairline, borders | `#E4D3B8` | card borders, dividers |
| Accent (links, hover, focus) | `#C85A1C` | underlines, hover states, rules |
| Primary button | `#C85A1C`, hover `#AD4A12` | "Shop now", "Add to cart" |
| Headline accent | `#B8480F` | collection title beside the script name |
| Announcement bar | `#2C1A0F` on `#FFF8EF`, highlight `#FFC38F` | the promo/creator-code bar |

Rules of thumb: background warm cream, **never** pure white as a page background;
text espresso, never pure black; one accent only (burnt orange) — do not add a
second brand colour; borders are hairlines in `#E4D3B8`, not shadows.

## 2. Type

| Slot | Font | Weight | Notes |
|---|---|---|---|
| Headings, collection titles, product names | **Playfair Display** (fallback Georgia) | 700 (800 for a page title) | serif, tight line-height 1.15, no letterspacing |
| Body, buttons, prices, labels | **Inter** (fallback system sans) | 400 body · 600 prices · 700 buttons | |
| Eyebrow / small caps labels | Inter | 800 | uppercase, `letter-spacing: .2em`, 11–12px, colour `#8A5326` |

Never more than these two families in the storefront. The script face (Caveat) is
reserved for the creator's signature on our pages — do not use it in the store's
UI or on the checkout.

Practical sizes: page title 34–40px, product title 20–22px, price 16px semibold,
body 16px/1.6, button 14px/700 uppercase `.06em`.

## 3. Shape and components

- Corner radius: **8px** on buttons and inputs, **14px** on product cards.
- Cards: `#FFFAF2` surface, `1px solid #E4D3B8`, no drop shadow (or 0 4px 14px
  rgba(60,35,18,.07) if your theme requires one).
- Buttons: solid `#C85A1C`, text `#FFF8EF`, no gradient, no rounded-pill; 12–14px
  vertical padding.
- Header: `#F4EAD9` with a `1px` bottom border in `#DFCBB0`; keep it light, not dark.
- Links inside copy: ink text with an accent underline, not accent-coloured text.

## 4. Assets

| Asset | File | Export |
|---|---|---|
| Store icon / favicon | `site/img/lockups/browns.svg` (256 × 256, espresso `#3B2415` + burnt orange `#C8410B`) | 512 × 512 PNG, transparent |
| Header wordmark | the existing "Gridiron Locker" lockup | 600 × 160 PNG, transparent, or set the name in Playfair Display 700, `letter-spacing .12em` |
| Banner | any locker hero, e.g. `site/img/hero-yvette.jpg` (1916 × 821) | 1920 × 600 JPG, centre-crop, ≤ 300 KB |

The store mark is already espresso and burnt orange, which is why this palette is
the one that makes both sides agree — it is the same two inks the lockups use.

## 5. Store settings checklist

- [ ] **Currency: USD.** Our pages quote `$`, and the store's product pages return
      `$23.00` — but the collection listing rendered the visitor's local currency
      in an external check (`NOK 239.00`). Pin the store to USD so the listing and
      the product page never disagree.
- [ ] **Browns collection (`P19bpeU2x_Ng`) shows all 33 designs.** The lockers
      promise "ALL 33 BROWNS DESIGNS", but the store listing currently shows 24.
      These product entries are missing from the collection; add them:
      Cle Browns Dawg, No Fly Zone, Cleveland, Dawg Life, Make Them Know Your Name,
      Browns Cle, DWAG, Let's Go Cle Copy, Go Browns, Playoffs, Ohio Cle.
      (Every one of them already has a live, buyable product page — this is only
      about the collection listing.)
- [ ] **Creator codes exist in the store.** `JOE10`, `VIP10`, `CRYSTAL`, `AMBER`,
      `LAQUALA`, `DESTINY`, `BOUGIESPORTS` — 10% off, active for the length of each
      collaboration. A code printed on a locker that fails at the store checkout is
      the one inconsistency a client *will* find.
- [ ] **Announcement bar** carries the creator code (dark `#2C1A0F` bar, cream text,
      `#FFC38F` highlight) — same message as our promo bar.
- [ ] **Store name and logo alt text**: "Gridiron Locker".
- [ ] **Product titles**: design name first, garment second ("Cleveland Victory
      Monday — Classic Unisex T-shirt"), so a card title on our side matches the
      product page title on the store's.

## 6. Verification (10 minutes, on a phone)

1. Open `/yvette/`, note the background, the heading font, the button colour.
2. Tap a design → the store product page: background, headings and the "Add to
   cart" button should read as the same family; the URL bar is the only thing that
   should look new.
3. Go back, open the store home: card background `#FFFAF2`, border `#E4D3B8`.
4. Apply `BOUGIESPORTS` at checkout — it must reduce the total by 10%.
5. Open `/p/browns` — the listing must show 33 items and prices in `$`.

## 7. What cannot be changed from our side

- **One theme per store.** Every creator locker inherits the same storefront
  palette; there is no per-creator theme, and a product URL carries no palette,
  logo or creator styling parameter (only `collectionId`, `color`, `productId`,
  plus our `creator` / `utm_*`).
- **The store's own header and footer copy** live in the dashboard, not in this
  repository.
- **Prices** are the store's: our page and the product page both read USD, so a
  localised collection listing is a store setting, not a data error here.
