<p align="center">
  <img src="frontend/static/pricehound-logo.png" alt="PriceHound Logo" width="120" height="120">
</p>

<h1 align="center">PriceHound</h1>

<p align="center">
  <strong>Get a sense of your Datadog costs before you commit.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Datadog-632CA6?style=for-the-badge&logo=datadog&logoColor=white" alt="Datadog">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SvelteKit-FF3E00?style=for-the-badge&logo=svelte&logoColor=white" alt="SvelteKit">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
</p>

---

## ✨ Features

### 📊 Build Your Quote

- **Smart Product Search** — Quickly find any Datadog product from 100+ options with instant search
- **Multi-Region Support** — Switch between US, EU, AP1, AP2 regions with accurate regional pricing
- **Flexible Billing** — Compare Annual, Monthly, and On-Demand pricing side by side
- **Real-time Calculations** — Watch totals update instantly as you build your quote
- **Allotment Tracking** — Automatically displays included allotments (e.g., containers with Infrastructure Hosts)

### 🚀 Quick Start Templates

Pre-built quote templates to jumpstart your estimates:
- **Full Stack Website** — Frontend, backend, database, RUM & logs
- **IoT Project** — Metrics, logs, incident management & on-call
- **Kubernetes on AWS** — Container monitoring, cloud costs & log management

### 🔗 Share & Protect

- **Public URLs** — Generate shareable links to collaborate on quotes
- **Password Protection** — Lock quotes with a password to prevent unauthorized edits
- **Clone & Fork** — Anyone can clone a shared quote to create their own version
- **Edit Mode** — Unlock protected quotes with the password to make changes

### 📄 Export & Print

- **PDF Export** — Print-optimized light theme for professional documents
- **Clean Output** — Buttons and UI elements hidden in print view
- **Copy to Clipboard** — Quick copy of quote URLs for easy sharing

### 📈 Log Indexing Estimator

Built-in calculator for log management costs:
- **Volume-based Estimates** — Input ingestion volume and average log size
- **Retention Options** — Compare 3, 7, 15, and 30-day retention costs
- **Indexing Presets** — Quick presets for common use cases (Minimal, Standard, Extended, Compliance)
- **Flex Logs Support** — Add Flex Logs Starter or Storage with compute pricing notes
- **Log Forwarding** — Include forwarding to custom destinations (S3, Azure, GCS)

### 🎨 User Experience

- **Dark/Light Mode** — Toggle between themes with persistent preference
- **Smooth Animations** — Fade and slide transitions throughout the interface
- **Responsive Design** — Works beautifully on desktop and mobile
- **Auto-sync Pricing** — Hourly background sync keeps pricing data fresh

---

## 🖼️ Screenshots

<details>
<summary>Click to expand</summary>

### Main Quote Builder
Build quotes with real-time pricing calculations and allotment tracking.

### Shared Quote View
Clean, read-only view for sharing with stakeholders.

### Log Indexing Estimator
Calculate log costs with visual breakdowns.

</details>

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (optional, falls back to file storage)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/toomone/ddog-pricing-calculator.git
cd ddog-pricing-calculator

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## 📖 Usage Guide

### Building a Quote

1. **Select Region** — Choose your Datadog region (US, EU, AP1, AP2)
2. **Add Products** — Search and select products, specify quantities
3. **Review Allotments** — See included resources automatically displayed
4. **Compare Pricing** — Toggle billing types to compare costs
5. **Save & Share** — Generate a public URL, optionally with password protection

### Using Templates

1. Click **"or stack example"** next to Add Product
2. Select a template (Website, IoT, Kubernetes)
3. Template items are added to your existing quote
4. Customize quantities as needed

### Protecting Your Quote

1. When saving, enter an optional password
2. Share the URL — anyone can view but not edit
3. To edit: click Unlock, enter password, make changes

---

## 🔌 API Reference

### Products & Pricing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | List all products for a region |
| GET | `/api/pricing` | Get full pricing data |
| POST | `/api/pricing/sync` | Force sync from Datadog |
| GET | `/api/regions` | List available regions |
| GET | `/api/allotments` | Get allotment mappings |

### Quotes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/quotes` | Create a new quote |
| GET | `/api/quotes/{id}` | Get quote by ID |
| PUT | `/api/quotes/{id}` | Update quote (password required if protected) |
| POST | `/api/quotes/{id}/verify-password` | Verify quote password |

### Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List all templates |
| GET | `/api/templates/{id}` | Get template by ID |
| POST | `/api/templates/seed` | Re-sync templates from files |

---

## 🏗️ Architecture

```
ddog-pricing-calculator/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application & routes
│   │   ├── models.py         # Pydantic models
│   │   ├── scraper.py        # Datadog pricing scraper
│   │   ├── quotes.py         # Quote CRUD operations
│   │   ├── templates.py      # Template management
│   │   ├── redis_client.py   # Redis connection & utilities
│   │   └── config.py         # Environment configuration
│   ├── data/
│   │   ├── pricing/          # Cached pricing by region
│   │   ├── quotes/           # Stored quotes (file fallback)
│   │   └── templates/        # Template JSON files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/   # Svelte components
│   │   │   ├── api.ts        # API client
│   │   │   └── utils.ts      # Utility functions
│   │   └── routes/           # SvelteKit pages
│   └── static/               # Static assets
└── render.yaml               # Render deployment config
```

---

## 🛠️ Tech Stack

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** — High-performance Python web framework
- **[Redis](https://redis.io/)** — In-memory data store (optional)
- **[Pydantic](https://pydantic.dev/)** — Data validation & serialization
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** — HTML parsing for price scraping
- **[APScheduler](https://apscheduler.readthedocs.io/)** — Background job scheduling

### Frontend
- **[SvelteKit](https://kit.svelte.dev/)** — Full-stack Svelte framework
- **[shadcn-svelte](https://www.shadcn-svelte.com/)** — Beautiful UI components
- **[Tailwind CSS](https://tailwindcss.com/)** — Utility-first CSS
- **[TypeScript](https://www.typescriptlang.org/)** — Type-safe JavaScript
- **[mode-watcher](https://github.com/svecosystem/mode-watcher)** — Dark mode support

### Deployment
- **[Render](https://render.com/)** — Cloud hosting platform
- Infrastructure as Code via `render.yaml`

---

## 🚢 Deployment

### Render (Recommended)

The project includes a `render.yaml` Blueprint for easy deployment:

1. Fork this repository
2. Connect to Render
3. Create a new Blueprint instance
4. Select your fork — services auto-configure

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_TYPE` | `redis` or `file` | `file` |
| `REDIS_URL` | Redis connection string | — |

---

## 📄 License

MIT

---

## ⚠️ Disclaimer

This is an **unofficial tool** and is not affiliated with, endorsed by, or sponsored by Datadog, Inc. Pricing data is scraped from Datadog's public pricing page and may not reflect the most current or accurate pricing. Always verify pricing directly with Datadog for official quotes.

---

<p align="center">
  Made with ❤️ for the Datadog community
</p>
