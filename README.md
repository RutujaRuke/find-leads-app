# Find Leads App

A small browser app that searches the Google Places API, optionally checks business websites for publicly listed email addresses, displays the results, and downloads them as an Excel workbook.

## Requirements

- Python 3.10 or newer
- A Google Cloud project with billing enabled and the Places API (New) enabled
- An API key restricted to the Places API

Google Places does not return email addresses. Email discovery is best-effort: the tool checks a business homepage and up to two same-site contact/about pages, and many sites will not publish an email.

## Setup

From this folder, create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your API key in `.env`:

```env
GOOGLE_MAPS_API_KEY=your_real_api_key
```

Keep `.env` private. Do not commit or share it.

## Start the app

```bash
streamlit run app.py
```

Streamlit opens the app in your browser, usually at `http://localhost:8501`. Enter a search such as `hotels in Nashik`, provide the API key in the sidebar (or in `.env`), and press **Search**. Results appear in the page; use **Download Excel** to export them.

To stop the app, press `Ctrl+C` in the terminal running Streamlit.

For coworkers on the same office network, start it with `streamlit run app.py --server.address 0.0.0.0`, then have them open `http://<this-computer's-local-IP>:8501`. Keep the computer running and ensure its firewall allows the connection.

The default limit is 20 businesses; the maximum is 60. Each search may incur Google API charges. If Google reports `API_KEY_INVALID`, verify the key is copied correctly, belongs to the expected project, Places API (New) is enabled, billing is attached, and key restrictions allow Places API. Review current Google Maps Platform pricing and Places API policies before use. Google Places content has restrictions on caching, storage, and redistribution; confirm that exporting returned fields to Excel is permitted for your intended use. Website email checks only access public pages and use request timeouts and a small delay.