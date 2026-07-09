# U.S. Housing Market Explorer

Interactive map-based dashboard exploring housing statistics across 377 U.S. metro areas.

**Live:** [keelp2.github.io/housing-market-explorer](https://keelp2.github.io/housing-market-explorer)

## Features

- Full-screen interactive map with metro bubbles and state choropleth
- Click any metro for detailed stats (affordability, market, economy, quality of life)
- Side-by-side metro comparison
- Color by any metric with auto-scaling legend

## Data Sources

| Source | Data | API Key? |
|--------|------|----------|
| [Zillow Research](https://www.zillow.com/research/data/) | Home values, rents, inventory | No |
| [Redfin Data Center](https://www.redfin.com/news/data-center/) | Sales, DOM, price drops | No |
| [Census ACS](https://data.census.gov/) | Income, demographics, housing | Yes (free) |
| [FRED](https://fred.stlouisfed.org/) | Mortgage rates, economic indicators | Yes (free) |
| [BEA](https://www.bea.gov/) | Regional GDP, price parities | Yes (free) |
| [FEMA NRI](https://hazards.fema.gov/nri/) | Natural disaster risk | No |
| [County Health Rankings](https://www.countyhealthrankings.org/) | Health metrics | No |
| [Realtor.com](https://www.realtor.com/research/data/) | Listings, inventory | No |

## Repo Structure

```
index.html              ← static site (GitHub Pages)
assets/
  css/styles.css        ← styling
  js/app.js             ← all client-side logic
  data.json             ← 377 metros, 78 columns (auto-updated weekly)
  us-states.json        ← GeoJSON state boundaries
scripts/
  refresh_data.py       ← weekly data pull (runs via GitHub Actions)
  requirements.txt      ← Python deps for refresh script
.github/workflows/
  refresh.yml           ← weekly cron to update data.json
```

## Data Refresh

Data is automatically updated weekly via GitHub Actions. API keys are stored as GitHub Secrets:
- `FRED_API_KEY`
- `CENSUS_API_KEY`
- `BEA_API_KEY`

To run manually: `python scripts/refresh_data.py`

## Run locally

```bash
python3 -m http.server 8000
# Open http://localhost:8000
```

Built by [Peter Keel](https://keelp2.github.io)
