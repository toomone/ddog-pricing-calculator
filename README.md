# Datadog Pricing Calculator

A full-stack web application for calculating Datadog pricing with quote sharing capabilities.

![Datadog Pricing Calculator](https://img.shields.io/badge/Datadog-632CA6?style=for-the-badge&logo=datadog&logoColor=white)

## Features

- 🔍 **Searchable Product List** - Quickly find Datadog products from a searchable dropdown
- 📊 **Multiple Billing Options** - Toggle between Annual, Monthly, and On-Demand pricing
- ➕ **Dynamic Line Items** - Add multiple products with custom quantities
- 💰 **Real-time Calculations** - See totals update as you build your quote
- 🔗 **Shareable Quotes** - Generate unique URLs to share quotes with others
- 🔄 **Pricing Sync** - Fetch latest pricing data from Datadog's website

## Tech Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Pandas** - Data manipulation for web scraping
- **BeautifulSoup4** - HTML parsing for pricing data extraction
- **Pydantic** - Data validation

### Frontend
- **SvelteKit** - Fast, modern frontend framework
- **shadcn-svelte** - Beautiful, accessible UI components
- **Tailwind CSS** - Utility-first CSS framework
- **TypeScript** - Type-safe JavaScript

## Project Structure

```
ddog-pricing-calculator/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── models.py        # Pydantic models
│   │   ├── scraper.py       # Pricing data scraper
│   │   └── quotes.py        # Quote management
│   ├── data/                # JSON data storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/  # UI components
│   │   │   ├── api.ts       # API client
│   │   │   └── utils.ts     # Utility functions
│   │   └── routes/          # SvelteKit pages
│   ├── static/
│   ├── package.json
│   └── ...config files
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- pnpm (recommended) or npm

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install  # or npm install

# Run development server
pnpm dev  # or npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

1. **Sync Pricing Data**: Click the "Sync Pricing" button to fetch the latest pricing from Datadog
2. **Select Billing Type**: Choose between Annual (best savings), Monthly, or On-Demand
3. **Add Products**: Search and select products, then specify quantities
4. **Add More Lines**: Click "Add Product" to include additional items
5. **Save & Share**: Click "Save & Share Quote" to generate a shareable URL

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | Get list of all products |
| GET | `/api/pricing` | Get full pricing data |
| POST | `/api/pricing/sync` | Sync pricing from Datadog |
| POST | `/api/quotes` | Create a new quote |
| GET | `/api/quotes/{id}` | Get quote by ID |
| PUT | `/api/quotes/{id}` | Update a quote |
| DELETE | `/api/quotes/{id}` | Delete a quote |

## Data Storage

Pricing and quote data are stored as JSON files in the `backend/data/` directory:
- `pricing.json` - Cached pricing data from Datadog
- `quotes.json` - Saved user quotes

## License

MIT

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or sponsored by Datadog, Inc. Pricing data is scraped from Datadog's public pricing page and may not reflect the most current or accurate pricing. Always verify pricing directly with Datadog for official quotes.

