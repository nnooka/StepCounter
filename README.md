# StepCounter

A Python Flask web application that visualises **MI Fitness (Xiaomi)** step-counter data across multiple years with interactive Chart.js charts.

---

## Features

- Upload your MI Fitness ZIP export, a plain CSV, or a JSON file
- Interactive dashboard with:
  - **Stats cards** – total steps, best day, current-year steps, daily average
  - **Yearly summary** bar chart
  - **Year comparison** line chart (monthly totals for every year overlaid)
  - **Monthly breakdown** bar chart with year selector
  - Recent-entries data table
- **Demo mode** – explore the app with 3 years of realistic generated data (no file needed)
- Fully client-side charts (Chart.js fetches JSON from the Flask API)

---

## Installation

```bash
# Clone and enter the repo
git clone <repo-url>
cd StepCounter

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the app

```bash
python app.py
```

Then open <http://127.0.0.1:5000> in your browser.

---

## How to export data from MI Fitness

1. Open the **MI Fitness** app on your phone.
2. Go to **Profile** (bottom-right icon) → **Settings**.
3. Tap **Export data** and choose your date range.
4. Share the resulting `.zip` file to your computer.
5. Upload it on the **Upload** page.

The parser looks for `ACTIVITY_STAGE_DATA.csv` inside the ZIP (or any CSV containing "step" in the filename as a fallback).

### Supported upload formats

| Format | Description |
|--------|-------------|
| `.zip` | MI Fitness export archive |
| `.csv` | Plain CSV with columns `date, steps[, distance, calories]` |
| `.json` | JSON array of objects with the same keys |

Accepted date formats: `YYYY-MM-DD`, `YYYYMMDD`, `MM/DD/YYYY`.

---

## Running the tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project structure

```
StepCounter/
├── app.py                    # Flask application & routes
├── requirements.txt
├── parser/
│   ├── __init__.py
│   └── mi_fitness.py         # Data parser & aggregation helpers
├── static/
│   ├── css/style.css
│   └── js/dashboard.js       # Chart.js rendering
├── templates/
│   ├── base.html
│   ├── upload.html
│   └── dashboard.html
└── tests/
    ├── test_parser.py
    └── sample_data/steps.csv
```
