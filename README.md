# ImaraPay 🌍

WhatsApp-first payment collection for Kenyan merchants — create payment requests, check daily summaries, and manage staff access entirely from WhatsApp chat.

## Quick Start (Docker — recommended)

```bash
git clone <repo-url> ImaraPay && cd ImaraPay

# 1. Copy environment files
cp backend/.env.example backend/.env   # fill in WhatsApp credentials if needed

# 2. Boot the full stack (postgres + redis + django + vite)
docker compose up --build

# 3. Open the dashboard
open http://localhost:5173
```

The backend API is available at `http://localhost:8000`.  
Django admin: `http://localhost:8000/admin/`

---

## Quick Start (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in values

python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

All variables are documented in [`backend/.env.example`](backend/.env.example).

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ prod | Django secret key |
| `DATABASE_URL` | optional | Postgres URL (SQLite used by default) |
| `REDIS_URL` | optional | Redis URL (in-memory queue used by default) |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp | Meta Cloud API phone number ID |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp | Permanent system-user access token |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp | Webhook verify token (your choice) |
| `WHATSAPP_APP_SECRET` | WhatsApp | Used to verify `X-Hub-Signature-256` |
| `FRONTEND_URL` | optional | Base URL for magic-link emails |
| `CONFIRMATION_THRESHOLD_MINOR` | optional | KES amount above which a confirm prompt is shown (default 1000) |

---

## Running Tests

```bash
# Backend (Django TestCase — no live server required)
cd backend
python manage.py test apps --verbosity=2

# Frontend (Vitest + React Testing Library)
cd frontend
npm test
```

CI runs both test suites on every push — see `.github/workflows/ci.yml`.

---

## Project Structure

```
ImaraPay/
├── backend/               Django 4.2 API
│   ├── apps/
│   │   ├── api/           Public REST views + WhatsApp webhook
│   │   ├── conversation/  Command parser, handlers, session
│   │   ├── identity/      PhoneIdentity, OTP, magic links
│   │   ├── merchants/     Merchant profiles
│   │   ├── payments/      PaymentRequest, Transaction state machine
│   │   ├── tenants/       Multi-tenant middleware
│   │   └── whatsapp/      Inbound event model, Meta adapter
│   └── config/            Django settings, URLs
└── frontend/              React 19 + Vite + TailwindCSS v4 dashboard
    └── src/components/    Dashboard views
```

---

## WhatsApp Commands

| Command | Description |
|---|---|
| `request 2500 for INV-001` | Create a payment request |
| `today` | Daily summary (collected, pending, count) |
| `status INV-001` | Check status of a payment link |
| `last 5` | Last 5 transactions |
| `cancel INV-001` | Cancel a pending request |
| `help` | Full command menu |
