# Barcelona HoReCa Dashboard

Interactive Dash dashboard for the **Barcelona: Horeca** Google Maps list.

## Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Main Dash app — run this to launch the dashboard |
| `venues_enriched2.json` | Enriched venue data (555 venues, Google Places API results cached) |
| `places_api_cache.json` | Google Places API response cache (avoids re-fetching) |
| `venue_data.json` | Photon geocoding cache (backup neighbourhood data) |
| `fetch_places_api.py` | Script to re-fetch/update venue data from Google Places API |
| `fetch_venue_data.py` | Script to re-fetch venue data via Photon geocoding (fallback) |
| `Opgeslagen plaatsen.json` | Google Takeout — general saved places |
| `takeout-20260923T190333Z-1-001.zip` | Google Takeout ZIP containing all custom lists incl. Barcelona: Horeca |

## How to run

```bash
python dashboard.py
```

Then open **http://127.0.0.1:8051** in your browser.

## Dashboard features

- **Treemap** — venue type breakdown (Bar, Restaurant, Japanese, Tapas/Vermut, etc.)
- **Neighbourhood bar chart** — which areas have the most venues
- **Heatmap map** — density map of all 555 venues across Barcelona
- **Price chart** — approximate spend per person (< €10 / €10–20 / €20–40 / > €40)
- **Avg rating by type** — which venue category rates best on Google
- **Avg rating by neighbourhood** — which area has the best spots
- **Top 10 highest-rated** — venues with ≥50 reviews sorted by rating
- **Searchable & filterable table** — filter by type, neighbourhood, price, keyword

## Data source

- **Input:** `Barcelona_ Horeca.csv` from the Google Takeout ZIP
- **Enrichment:** Google Places API (Find Place + Place Details)
  - Real price levels (1–4), ratings, review counts, coordinates, address components

## Refreshing the data

1. (Optional) Export a fresh Takeout of your saved places and update `ZIP_PATH` in `fetch_places_api.py`
2. Set the `GOOGLE_MAPS_API_KEY` environment variable (the key's Google Cloud project needs billing enabled)
3. Run `python fetch_places_api.py --refresh` to re-fetch latest ratings/prices for all venues
   (without `--refresh`, only venues missing from the cache are fetched)
4. Commit the regenerated `venues_enriched2.json`

## Dependencies

```
pip install dash plotly pandas openpyxl requests
```
