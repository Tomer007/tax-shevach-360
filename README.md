# מס שבח 360 | Tax Shevach 360

מחשבון מס שבח מקרקעין ישראלי — מדויק, מודרני, ומלא.

Israeli Capital Gains Tax (Mas Shevach) Calculator — accurate, modern, and comprehensive.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-blue?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue?logo=typescript)
![Coverage](https://img.shields.io/badge/Coverage-99%25-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

### Tax Calculation Engine
- **Per-acquisition CPI indexation** — each acquisition event indexed from its own date
- **Per-deduction indexation** — each expense indexed independently
- **Linear Mutav (ליניארי מוטב)** — with qualification check for residential property
- **Regular route** — period-based rates (pre-2001, 2001-2012, post-2012)
- **Prisa (פריסה)** — spreading over 1-4 years with auto-optimization
- **Mas Yesaf (מס יסף)** — surtax with other income stacking
- **Section 48a(d)** — 10% inflationary tax on pre-1994 acquisitions
- **Partial exemption** — linear formula when sale exceeds 49b(2) ceiling
- **Non-resident tax** — flat 25% for foreign sellers
- **Building rights (49ז)** — negligible, double exemption, above ceiling
- **Multi-seller support** — per-seller breakdown with separate prisa optimization
- **Currency conversion** — ILP, ILR (historical), USD, EUR, GBP
- **Depreciation** — manual or auto-calculated from rental periods
- **Betterment levy** — hetel hashbacha deduction

### Frontend
- Dark hi-tech UI with RTL Hebrew support
- 5-step guided wizard (Sale → Sellers → Acquisition → Deductions → Exemptions)
- Route comparison with recommended path
- Downloadable HTML report (self-contained, dark theme)
- JSON export
- Triple-click title for demo mode
- Responsive mobile design

---

## 🏗️ Architecture

```
tax-shevach-360/
├── backend/           Python FastAPI
│   ├── app/
│   │   ├── main.py          FastAPI app + SPA serving
│   │   ├── routes.py        API endpoints
│   │   ├── models.py        Pydantic models
│   │   ├── calculator.py    Core calculation engine
│   │   ├── tax_rates.py     Tax brackets, rates, constants
│   │   ├── cpi_data.py      CPI historical data (1950-2026)
│   │   ├── depreciation.py  Depreciation calculation
│   │   └── boi_api.py       Bank of Israel exchange rates
│   └── tests/               185 tests, 99%+ coverage
├── frontend/          React + TypeScript + Vite
│   └── src/
│       ├── App.tsx           Multi-step form orchestrator
│       ├── components/       Step components + Results
│       ├── types.ts          TypeScript API types
│       ├── api.ts            Axios API client
│       └── mockData.ts       Demo data
├── build.sh           Production build script
├── render.yaml        Render.com deployment config
└── dev.sh             Local development script
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+

### Development

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Production Build (single service)

```bash
bash build.sh
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 📡 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/calculate` | Full tax calculation |
| GET | `/api/cpi/{year}` | CPI value for year |
| GET | `/api/indexation` | CPI ratio between years |
| GET | `/api/exchange-rate` | BOI exchange rate |
| POST | `/api/convert-currency` | Currency to ILS conversion |
| POST | `/api/check-49z` | Building rights exemption check |
| POST | `/api/prisa-comparison` | Compare 1-4 year prisa options |
| GET | `/health` | Health check |

### Example: Calculate Tax

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "sale_date": "2025-03-15",
    "sale_amount": 3500000,
    "sale_currency": "ILS",
    "sellers": [{
      "name": "ישראל ישראלי",
      "id_number": "012345678",
      "birth_date": "1970-05-12",
      "share_percent": 100,
      "is_israeli_resident": true,
      "annual_incomes": {"2025": 180000}
    }],
    "acquisitions": [{
      "acquisition_date": "2005-06-01",
      "amount": 1200000,
      "currency": "ILS",
      "share_percent": 100
    }],
    "deductions": [],
    "is_residential": true,
    "betterment_levy": 0,
    "prisa_years": 0
  }'
```

---

## 🧪 Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v --cov=app
```

**185 tests** | **99.3% coverage** | All business logic at 100%

---

## 🌐 Deployment (Render)

Single web service deployment via `render.yaml`:

```yaml
services:
  - type: web
    name: mas-shevach-360
    runtime: python
    buildCommand: bash build.sh
    startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The build script installs backend deps, builds the frontend, and copies static files into the backend for SPA serving.

---

## 📋 Tax Law References

| Feature | Section | Description |
|---------|---------|-------------|
| Linear Mutav | Chapter 5, Section 48A(b2) | Exempt pre-2014 portion for residential |
| Mas Yesaf | Section 121B | 3% surtax above threshold (+2% from 2025) |
| Inflationary Tax | Section 48A(d) | 10% on pre-1994 inflationary gain |
| Single Apartment | Section 49B(2) | Full/partial exemption up to ceiling |
| Building Rights | Section 49Z | Negligible/double exemption |
| Prisa | Section 48A(h) | Spreading gain over up to 4 years |
| Depreciation | 1989/1941 Regulations | Reduce cost basis for rental property |
| Non-resident | Section 48A | Flat 25% without linear benefit |

---

## 📄 License

MIT

---

<p align="center">
  Built with ❤️ for Israeli tax professionals
</p>
