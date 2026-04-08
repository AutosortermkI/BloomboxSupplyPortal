# BloomBox Supply Portal

**Master Wholesale Plant Supplier Command Center** for BloomBox / Second Chance Plants — a plant distribution company operating 12 retail locations across Pennsylvania and Northern Maryland.

## What This Is

A single, self-contained HTML dashboard (`index.html`) that opens in any browser with zero dependencies, no server, and no build step. Just open the file.

### Features

- **317 verified wholesale suppliers** across 35 states and Canadian provinces — every entry includes full procurement detail (MOQs, payment terms, container sizes, delivery routes, specific cultivars)
- **Side-by-side price comparison** across 13 product categories with "Best Price" flagging
- **Arbitrage engine** that surfaces the highest savings opportunities between suppliers
- **Interactive map** (Leaflet.js + OpenStreetMap) with geographic route clustering
- **Dark mode** with full theme system
- **Strategy tab** with:
  - Margin calculator (enter retail price, see profit per supplier after freight + shrinkage)
  - Vendor scorecards with letter grades (Quality / Reliability / Pricing / Variety)
  - Seasonal demand forecasting by quarter
  - 52-week procurement calendar for 12 store locations
- **Favorites & order planning** — star suppliers, add buyer notes, build draft order templates, export to CSV
- **Analytics** — Chart.js-powered breakdowns by state, type, category, wholesale status
- **CSV export** of filtered supplier data

### Supplier Coverage

| Region | Count | Highlights |
|--------|-------|------------|
| Pennsylvania | 60+ | Lancaster nursery belt, Chester County natives, York-Adams tree farms |
| Florida | 30+ | Homestead tropical corridor, Apopka foliage trail |
| New Jersey | 15+ | South Jersey nursery row (Bridgeton/Vineland) |
| Virginia | 15+ | Shenandoah Valley, Northern VA |
| Maryland | 15+ | Eastern Shore, Frederick, I-83 corridor |
| Canada (ON/BC/QC) | 14 | Ontario greenhouse belt, Niagara growers |
| North Carolina | 15+ | Western NC nursery region |
| Midwest (MI/OH/IL/WI/MN/IN) | 25+ | Proven Winners belt, Bailey Nurseries |
| Supply/Hard Goods | 15+ | Sungro, Premier Tech, Berger, ICL, HC Companies |

## Getting Started

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/BloomboxSupplyPortal.git

# Open in your browser
open BloomboxSupplyPortal/index.html
```

That's it. No `npm install`, no server, no API keys.

## Tech Stack

All in a single HTML file:

- **Chart.js 4.5.1** — bar charts, doughnut charts for analytics
- **Leaflet.js 1.9.4** — interactive supplier map with OpenStreetMap tiles
- **Vanilla JS** — Dashboard class, favorites system, margin calculator, arbitrage engine
- **CSS Custom Properties** — full light/dark theme system with smooth transitions

## Project Structure

```
BloomboxSupplyPortal/
  index.html          # The entire dashboard (self-contained, ~350KB)
  README.md           # This file
  LICENSE             # MIT License
```

## Data Sources

Supplier data was compiled from public wholesale nursery catalogs, trade directories, industry databases, and direct research as of April 2026. Pricing represents typical wholesale ranges — always confirm current pricing directly with suppliers.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built for **BloomBox / Second Chance Plants** — 12 locations across PA & Northern MD.
