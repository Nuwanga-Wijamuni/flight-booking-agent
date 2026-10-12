<div align="center">

![Skyward — Your next journey, one conversation away.](assets/readme-banner.svg)

**A conversational flight discovery app with a booking simulation you can run locally.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](backend/app/main.py)
[![Groq](https://img.shields.io/badge/Groq-GPT--OSS_120B-F55036?style=flat-square)](https://console.groq.com/docs/model/openai/gpt-oss-120b)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square)](backend/app/agent.py)
[![React](https://img.shields.io/badge/React-19-149ECA?style=flat-square&logo=react&logoColor=white)](frontend/package.json)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)](frontend/src/App.tsx)
[![Mode](https://img.shields.io/badge/Mode-Demo_%26_Sandbox-A7E5CD?style=flat-square&labelColor=183E36)](#choose-your-mode)

[Quick start](#quick-start) · [Features](#what-you-can-do) · [Architecture](#how-it-works) · [Configuration](#configuration) · [Roadmap](#roadmap)

</div>

---

## Meet Skyward

Turn a travel request into flight options, inspect an itinerary, and walk through a simulated booking—all in one interface. Start with the built-in demo, then connect Groq for natural-language extraction or Duffel for sandbox searches.

> **Demo & sandbox project**
>
> Every booking is simulated. No payment is collected and no airline ticket is issued. Demo airlines, prices, schedules, and baggage allowances are illustrative; Duffel test mode uses sandbox data.

## What you can do

| | Feature | What’s implemented |
| :---: | --- | --- |
| 💬 | **Describe your trip** | Use a chat-style request or enter airports, a date, and a USD budget in the search form. |
| ✈️ | **Compare flights** | Inspect carriers, departure and arrival times, stops, and totals. |
| 🔎 | **Review before confirming** | Retrieve the selected offer again in Duffel test mode and review a time-limited quote. |
| ✅ | **Try a booking** | Confirm the itinerary and total to create a clearly labeled local simulation. |
| 🛡️ | **Handle repeat requests** | Database uniqueness and idempotency keys protect against duplicate simulation records. |
| 💾 | **Keep your results** | Persist offers, quotes, and simulated bookings with SQLite or PostgreSQL. |
| 🧑‍💻 | **Develop in VS Code** | Open the included workspace and start both services with prepared tasks. |

**Current scope:** one way · one adult · economy in the search form. The offline parser also recognizes business; Groq can extract additional supported cabins. USD budgets filter USD offers only—there is no exchange-rate conversion.

## Quick start

**You’ll need:** Python **3.11+**, Node.js **20.19+** (22+ recommended), and Git. API keys and Docker are optional for the default demo.

### 1. Get the project

```bash
git clone https://github.com/Nuwanga-Wijamuni/flight-booking-agent.git
cd flight-booking-agent
code flight-agent.code-workspace
```

If the `code` command is unavailable, open `flight-agent.code-workspace` from VS Code. Already cloned the repository? Pull the latest changes instead.

### 2. Start the backend

In a terminal at the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

<details>
<summary><strong>Windows PowerShell instructions</strong></summary>

```powershell
cd backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Use the frontend commands below in a second terminal. The included VS Code tasks use macOS/Linux paths; Windows users can start the services manually.

</details>

### 3. Start the frontend

In a **second terminal** at the project root:

```bash
cd frontend
npm ci
npm run dev
```

| Open | Address |
| --- | --- |
| **Flight app** | [localhost:5173](http://localhost:5173) |
| **Interactive API docs** | [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |

Once dependencies are installed on macOS/Linux, you can also use **Terminal → Run Task → Start flight agent** in VS Code.

### 4. Take the demo for a spin

Use a future departure date in a request such as:

> Find flights from Colombo to Singapore on YYYY-MM-DD under $400

Replace `YYYY-MM-DD` with your date. The assistant’s default prompt already includes a future date.

1. Select **Find my flight**, or use the search form.
2. Choose **Review flight** on a result.
3. Review the itinerary and total, then check the confirmation box.
4. Select **Simulate booking** to see your local simulation reference.

<details>
<summary><strong>What the offline assistant understands</strong></summary>

The default assistant uses a deterministic parser with LangGraph. It recognizes `from CITY to CITY`, an ISO date (`YYYY-MM-DD`), an optional USD budget, and economy/business requests.

City aliases: **Colombo, Singapore, Dubai, London, Paris, Bangkok, Tokyo, Sydney, Amsterdam, Frankfurt**. Three-letter IATA airport codes also work.

It asks for clarification when required details are missing or it detects unsupported trip types. Requests are stateless: each message should contain the complete trip. Enable Groq for more flexible language extraction.

</details>

## Record your portfolio demo

1. Configure Groq as above; optionally enable Duffel sandbox below.
2. Start the backend and frontend, and open the app.
3. Enter a full one-way request for one adult with a future date.
4. Compare results, review an offer, and confirm the simulated booking.
5. Keep the sandbox/simulation notice visible. A `SIM-` reference is a local record, not a Duffel order or airline ticket.

This version is stateless: include the complete trip in each message. It does not yet handle conversational follow-ups, real payments, or Duffel order creation.

## How it works

```mermaid
flowchart TD
    UI["React interface"] --> Chat["Chat request"]
    UI --> Form["Search form"]
    Chat --> Extract["LangGraph: extract trip"]
    Extract --> Validate["Validate search parameters"]
    Form --> Validate
    Validate --> Provider{"Flight provider"}
    Provider --> Demo["Illustrative demo inventory"]
    Provider --> Duffel["Duffel test API"]
    Demo --> Offers["Compare offers"]
    Duffel --> Offers
    Offers --> Review["Review offer and expiring quote"]
    Review --> Confirm["User confirmation"]
    Confirm --> Booking["Store simulated booking"]
    Booking --> DB[("SQLite / PostgreSQL")]
```

Groq, when enabled, extracts structured search parameters. LangGraph routes the request into a provider search. Backend code validates requests and controls quote expiry, confirmation, and simulation records. The model has no payment or booking tool.

### Technology stack

| Layer | Technologies |
| --- | --- |
| **Interface** | React 19 · TypeScript · Vite · CSS |
| **API & validation** | Python · FastAPI · Pydantic · HTTPX |
| **Agent workflow** | LangGraph · Groq GPT-OSS 120B · strict structured output |
| **Flight provider** | Built-in demo inventory · optional Duffel test API |
| **Persistence** | SQLAlchemy · SQLite by default · optional PostgreSQL |
| **Developer tools** | pytest · VS Code workspace/tasks · Docker Compose for PostgreSQL |

## Choose your mode

The AI and flight provider are configured independently. You can use Groq with demo flights, or the offline parser with Duffel sandbox searches.

| Setting | Default | Optional integration |
| --- | --- | --- |
| **Trip extraction** | Offline parser; no key needed | Groq with `GROQ_API_KEY` |
| **Flight search** | Illustrative demo flights | Duffel sandbox with a test token |
| **Storage** | Local SQLite | PostgreSQL |
| **Booking outcome** | Local simulation | Remains a local simulation in every mode |

## Configuration

For an existing Gemini setup, replace the `GEMINI_API_KEY` / `GEMINI_MODEL` entries with the Groq variables below. Old Gemini variables are ignored.

Create `backend/.env` from [`.env.example`](backend/.env.example). Restart the backend after changing it. Keep API keys in `.env`; that file is excluded from Git.

| Variable | Default / purpose |
| --- | --- |
| `FLIGHT_PROVIDER` | `demo`; change to `duffel_test` for sandbox searches |
| `DUFFEL_ACCESS_TOKEN` | Empty; a Duffel **test** token is required for sandbox mode |
| `GROQ_API_KEY` | Empty; setting it enables Groq extraction |
| `GROQ_MODEL` | `openai/gpt-oss-120b`; use a model supporting structured output |
| `DATABASE_URL` | `sqlite:///./flight_agent.db` |
| `CORS_ORIGIN` | `http://localhost:5173` |

<details>
<summary><strong>Enable Groq</strong></summary>

Set these values in `backend/.env` and restart the backend:

```dotenv
GROQ_API_KEY=your_new_groq_key_here
GROQ_MODEL=openai/gpt-oss-120b
FLIGHT_PROVIDER=demo
```

The UI will show **GPT-OSS-120B · Groq + LangGraph**. The badge indicates configuration; a successful chat request verifies that the key works. No OpenAI API key or additional Groq SDK is needed: the backend uses HTTPX. Leave `GROQ_API_KEY` empty for the offline parser. Never put secrets in `VITE_` variables, screenshots, recordings, or commits.

If Groq fails, the app displays an error and you can still use the flight search form. It does not silently substitute the offline parser. HTTP 429 means wait and retry; access errors mean check your Groq key and model permissions. Request text is sent to Groq for extraction; use invented travel requests during testing and avoid entering passport or payment information.

See [Groq structured output documentation](https://console.groq.com/docs/structured-outputs).

</details>

<details>
<summary><strong>Enable Duffel sandbox</strong></summary>

Obtain a test token from your Duffel account, then update `backend/.env`:

```dotenv
FLIGHT_PROVIDER=duffel_test
DUFFEL_ACCESS_TOKEN=duffel_test_your_token_here
```

The adapter calls `POST /air/offer_requests` for search and `GET /air/offers/{id}` for offer review. Live tokens are rejected. Order creation and ticket issuance are not implemented.

See the official [offer request](https://duffel.com/docs/api/v2/offer-requests) and [offer](https://duffel.com/docs/api/v2/offers) references.

</details>

<details>
<summary><strong>Use PostgreSQL</strong></summary>

From the project root:

```bash
docker compose up -d postgres
```

Then set the following in `backend/.env` and restart:

```dotenv
DATABASE_URL=postgresql+psycopg://flight:flight@localhost:5432/flight
```

The supplied credentials are for local development. Tables are created on startup; add migrations before evolving a production schema.

</details>

## Project map

| Path | Responsibility |
| --- | --- |
| [`backend/app/agent.py`](backend/app/agent.py) | LangGraph extraction and search flow |
| [`backend/app/llm.py`](backend/app/llm.py) | Groq structured extraction, validation, and API errors |
| [`backend/app/providers.py`](backend/app/providers.py) | Demo offers and Duffel sandbox adapter |
| [`backend/app/main.py`](backend/app/main.py) | Search, quotes, confirmation, and simulations |
| [`backend/app/models.py`](backend/app/models.py) | Validated requests and response models |
| [`backend/app/database.py`](backend/app/database.py) | Persistent records and database setup |
| [`frontend/src/App.tsx`](frontend/src/App.tsx) | Assistant, search, flight cards, and review dialog |
| [`frontend/src/styles.css`](frontend/src/styles.css) | Responsive interface styling |
| [`backend/tests/test_flow.py`](backend/tests/test_flow.py) | Core workflow and validation tests |
| [`flight-agent.code-workspace`](flight-agent.code-workspace) | VS Code project workspace |

## Checks & validation

**Backend** — from `backend/` with the virtual environment active:

```bash
python -m pytest -q
```

**Frontend** — from `frontend/`:

```bash
npm run build
```

**Verified for this upgrade:** 24 backend tests pass and the TypeScript/Vite production build succeeds.

Tests cover search and budget filtering, confirmation, duplicate protection, quote expiry, clarification, invalid trips, and live-token rejection. Groq contract tests use mocked HTTP responses and cover strict request schemas, extraction through booking simulation, invalid output, rate limits, access errors, and network failures.

Groq and Duffel integrations have not been tested against a provider account. PostgreSQL and a full browser walkthrough have not been verified. Mocked tests verify application behavior; they do not prove account credentials or provider availability.

## Roadmap

- [x] React interface with chat and structured search
- [x] LangGraph extraction → search workflow
- [x] Groq GPT-OSS 120B with strict structured output and sanitized errors
- [x] Demo inventory and Duffel sandbox adapter
- [x] Expiring quotes and booking simulation
- [x] Database-backed duplicate protection
- [ ] Verify Groq, Duffel, and PostgreSQL with configured services
- [ ] Add browser end-to-end tests
- [ ] Support return trips, multiple passengers, and passenger forms
- [ ] Add user authentication and per-user record access
- [ ] Implement secure checkout, ticket issuance, and order reconciliation
- [ ] Add verified webhooks, cancellations, and refunds
- [ ] Add deployment, rate limits, monitoring, and retention controls

### Development boundaries

Run this starter locally until authentication and record ownership checks exist. Quotes currently use opaque IDs without user accounts. Conversation history is not persisted; only offers, quotes, and booking simulations are stored.

Real bookings require approved provider access and payment arrangements, passenger validation, secure checkout, and confirmation from the airline/provider. A successful payment alone does not confirm a ticket. There is no cloud deployment, vector database, or paid tracing service in this starter.

---

<div align="center">

**Built by [Nuwanga Wijamuni](https://github.com/Nuwanga-Wijamuni)**

Exploring practical AI workflows through a flight discovery experience.

[Back to top](#)

</div>
