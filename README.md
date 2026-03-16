# ScholarScope

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

AI-powered scholarship discovery and application management platform. ScholarScope combines an LLM-assisted scraping pipeline, a Chrome extension, and a distributed task queue to surface relevant scholarships and generate personalised application essays from a student's profile.

> 🎥 **[Watch the Demo](https://tinyurl.com/scholarscope)** 🌐 **[Live App →](#)**

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Services](#running-the-services)
- [Chrome Extension](#chrome-extension)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Roadmap](#roadmap)

---

## Overview

Finding scholarships is fragmented — opportunities are scattered across institutional websites, buried in PDFs, or locked behind dead pages with outdated deadlines. ScholarScope solves this at every layer of the stack:

1. **Automated ingestion** — a Scrapy + Gemini pipeline crawls scholarship pages, validates and quality-scores extracted data, and rejects or recovers malformed content before it reaches the database.
2. **Browser-native discovery** — a Chrome extension detects scholarship pages while a student browses and triggers background extraction via a Celery task queue, without interrupting their session.
3. **AI essay drafting** — a RAG pipeline retrieves relevant profile data and past essays, then generates contextualised first drafts for each application prompt.
4. **Application tracking** — a unified dashboard tracks every application's status, deadline, and watch/bookmark state across both platform-scraped and user-submitted scholarships.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                                   │
│  ┌─────────────────────┐   ┌──────────────────────────────────┐ │
│  │  React Web App      │   │  Chrome Extension (React)        │ │
│  │  - Homepage (∞ scroll│   │  - Page detection                │ │
│  │  - Application dashboard│  - Auto-extract trigger           │ │
│  │  - Essay review modal│   │  - Real-time polling UI          │ │
│  └──────────┬──────────┘   └───────────────┬──────────────────┘ │
└─────────────┼─────────────────────────────┼───────────────────┘
              │  REST (JWT)                 │  REST (JWT)
┌─────────────▼─────────────────────────────▼───────────────────┐
│  API LAYER  —  Django REST Framework                           │
│  Cursor-paginated listings · Full-text search · JWT auth       │
│  Submission status polling · Per-user bookmark/watch state     │
└──────────────┬────────────────────────────────────────────────┘
               │  Task dispatch (Redis broker)
┌──────────────▼────────────────────────────────────────────────┐
│  WORKER LAYER  —  Celery                                       │
│                                                                │
│  [celery queue]              [llm queue]                       │
│  ├─ Scrapy spider            ├─ Gemini extraction              │
│  ├─ Submission processing    ├─ Quality scoring & validation   │
│  ├─ Deadline reminders       ├─ RAG essay drafting             │
│  └─ Renewal notifications    └─ Fallback field recovery        │
└──────────────┬────────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────────┐
│  DATA LAYER                                                    │
│  PostgreSQL (scholarships, applications, profiles, essays)     │
│  Redis      (Celery broker + result backend)                   │
└───────────────────────────────────────────────────────────────┘
```

### Scraping Pipeline

```
URL submitted
    │
    ▼
ScholarshipExtractor (Scrapy + parsel)
    │  CSS/semantic section parsing
    │  Navigation-poisoning detection
    ▼
QualityCheck
    │  Field completeness scoring
    │  Nav-item ratio threshold (≥40% → reject)
    │  Critical failure detection
    ▼
LLM Engine (Gemini)          ← only fires when QualityCheck flags issues
    │  Nav/sidebar stripped from HTML before prompt
    │  Structured JSON output with field-level validation
    │  Fallback: recover_specific_fields for partial failures
    ▼
Scholarship saved to PostgreSQL
    │
    ▼
Submission status → APPROVED / REJECTED
Frontend polling resolves → data_quality: "full" | "sparse" | "none"
```

---

## Features

### Intelligent Scraping Pipeline
- Multi-stage extraction: CSS selectors → semantic heading search → LLM fallback
- Navigation-poisoning detection — sidebar nav content (`"undergraduate scholarships"`, `"phd scholarships"`) is detected and blocked before it reaches the database via a 40% nav-item ratio threshold
- LLM extraction strips `<nav>`, `<aside>`, and sidebar elements from HTML before sending to Gemini, preventing prompt contamination
- `data_quality` response field tells the frontend whether extracted data is `full`, `sparse`, or `none` — triggering appropriate user notices

### Chrome Extension
- Detects scholarship pages during normal browsing via URL and DOM heuristics
- Submits the page for background extraction without blocking the user's session
- Polls `/submissions/<id>/submission_status/` every 2 seconds and surfaces real-time feedback: processing → approved/rejected, with specific missing fields listed for sparse results
- Auto-extract notification system: amber warning for non-scholarship pages, blue info notice for sparse fields

### AI Essay Drafting (RAG)
- Retrieves relevant user profile sections (leadership, financial need, academic background) based on the scholarship's requirements
- Constructs structured prompts combining scholarship context + profile data to prevent hallucination
- Interactive review modal: read, edit, regenerate with quick-prompts, or approve and inject back into the application portal
- Regeneration preserves context across multiple drafts

### Application Management
- Cursor-based infinite scroll pagination — constant-speed queries regardless of dataset size, no page drift on new insertions
- Per-user bookmark and watch state resolved via single-query `Exists` annotations, eliminating N+1 queries
- Full-text search with PostgreSQL `SearchVector` across title, description, and tags with rank-based ordering
- Optimistic UI updates for bookmark/watch toggles with automatic revert on failure

### Notification System
- Celery Beat schedules: 7-day deadline reminder, 3-day urgent reminder, weekly digest, weekly renewal check
- One digest email per user — all pending applications batched into a single send regardless of how many scholarships are approaching deadline
- Annual renewal notifications for watched scholarships: marks `notified_for_year` only after successful delivery to prevent silent skips on retry
- HTML + plain-text email templates with urgency-coloured deadline countdowns (green → amber → red)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Browser Extension | Chrome Extension Manifest V3, React |
| Backend | Python 3.12, Django 5.x, Django REST Framework |
| Task Queue | Celery 5.x (threads pool), Redis |
| Scraping | Scrapy, scrapy-playwright, parsel, trafilatura |
| AI | Google Gemini 2.0 Flash, LangChain (RAG) |
| Database | PostgreSQL 15 |
| Cache / Broker | Redis 7 |
| Auth | JWT (djangorestframework-simplejwt, dj-rest-auth) |
| Email | Django `EmailMultiAlternatives`, Django templates |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- PostgreSQL 15+
- Redis 7+ (running locally or via Docker)

### Quick start with Docker

```bash
git clone https://github.com/your-username/scholarscope.git
cd scholarscope
cp .env.example .env          # fill in credentials — see Environment Variables
docker compose up --build
```

The compose file starts Django, Celery worker (celery queue), Celery worker (llm queue), Celery Beat, Redis, and PostgreSQL in one command.

### Manual setup

```bash
# 1. Clone
git clone https://github.com/your-username/scholarscope.git
cd scholar_scope

# 2. Backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install                # Chromium for scrapy-playwright

# 3. Database
cp .env.example .env              # fill in DB credentials
python manage.py migrate
python manage.py createsuperuser

# 4. Frontend
cd scholarscope-frontend
npm install
npm run dev                       # Vite dev server on http://localhost:5173
```

---

## Environment Variables

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_URL=http://localhost:5173

# Database
DB_NAME=scholarscope
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# AI
GOOGLE_API_KEY=your-gemini-api-key

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=ScholarScope <noreply@scholarscope.com>

# App
ORGANIZATION_NAME=ScholarScope
ORGANIZATION_ADDRESS=
```

---

## Running the Services

Each service runs in a separate terminal (or as a Docker service).

```bash
# Terminal 1 — Django API server
python manage.py runserver

# Terminal 2 — Celery worker: scraping + submission processing
celery -A scholarscope worker \
  --pool=threads -c 4 \
  --queues=celery \
  --loglevel=info

# Terminal 3 — Celery worker: LLM tasks (separate queue to isolate latency)
celery -A scholarscope worker \
  --pool=threads -c 4 \
  --queues=llm \
  --loglevel=info

# Terminal 4 — Celery Beat: scheduled tasks (reminders, renewal checks)
celery -A scholarscope beat --loglevel=info

# Terminal 5 — Frontend dev server
cd frontend && npm run dev
```

### Scheduled tasks (Celery Beat)

| Task | Schedule | Description |
|---|---|---|
| `send_deadline_reminders` (7d) | Daily 8:00 AM | Remind users of scholarships due in 7 days |
| `send_deadline_reminders` (3d) | Daily 9:00 AM | Urgent reminder for scholarships due in 3 days |
| `send_bulk_reminders` | Monday 8:00 AM | Weekly digest of all pending applications |
| `send_renewal_notifications` | Monday 7:00 AM | Notify watchers when recurring scholarships reopen |

---

## Chrome Extension

The extension lives in `extension/` and is built separately.

```bash
cd scholarscope-extension
npm install
npm run build          # outputs to extension/dist/
```

**Loading in Chrome:**
1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select `extension/dist/`

**How it works:**

The content script detects scholarship-related pages based on URL patterns and DOM signals. When triggered, it sends the page URL and title to the Django API (`POST /api/submissions/`). The background script polls `/api/submissions/<id>/submission_status/` every 2 seconds. The popup renders real-time extraction status and, once approved, shows the scholarship data with a one-click link to the dashboard.

---

## Project Structure

```
scholarscope/
├── backend/
│   ├── scholarscope/          # Django project settings
│   ├── scholarships/
│   │   ├── models.py          # Scholarship, Application, WatchedScholarship, Bookmark
│   │   ├── views.py           # ScholarshipViewset, ScrapeSubmissionViewset
│   │   ├── serializers.py     # Per-user is_bookmarked/is_watched annotations
│   │   ├── pagination.py      # ScholarshipCursorPagination
│   │   ├── tasks.py           # Celery tasks (reminders, renewal, submission processing)
│   │   ├── services.py        # ScholarshipEmailService
│   │   ├── scraper/
│   │   │   ├── scholarship_batch_spider.py
│   │   │   ├── scholarship_extractor.py   # CSS + semantic extraction
│   │   │   ├── quality.py                 # QualityCheck, nav-poisoning detection
│   │   │   └── llm_engine.py              # Gemini extraction + recovery
│   │   └── templates/
│   │       └── emails/
│   │           ├── scholarship_reminder.html
│   │           ├── scholarship_reminder.txt
│   │           ├── scholarship_renewal.html
│   │           └── scholarship_renewal.txt
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx      
│   │   │   └── ScholarshipDetail.jsx
│   │   ├── components/
│   │   │   ├── ScholarshipCard.jsx
│   │   │   ├── Navbar.jsx
│   │   │   └── ReviewModal.jsx
│   │   └── api.js             # Axios instance with JWT interceptors
│   └── package.json
│
├── extension/
│   ├── src/
│   │   ├── popup/             # React popup UI
│   │   ├── content/           # DOM detection script
│   │   └── background/        # Service worker, polling logic
│   └── manifest.json
│
└── docker-compose.yml
```

---

## API Reference

### Scholarships

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/scholarships/` | Optional | List scholarships (cursor-paginated). Supports `?q=`, `?level=`, `?tag=` |
| `GET` | `/api/scholarships/<id>/` | Optional | Retrieve a scholarship |
| `GET` | `/api/scholarships/<id>/details/` | Optional | Detail view with similar scholarships |
| `POST` | `/api/scholarships/<id>/bookmark_scholarship/` | Required | Bookmark a scholarship |
| `POST` | `/api/scholarships/<id>/unbookmark/` | Required | Remove bookmark |
| `POST` | `/api/scholarships/<id>/toggle_watch_scholarship/` | Required | Toggle watch state |
| `POST` | `/api/scholarships/<id>/apply/` | Required | Record application + return link |

### Submissions (Chrome Extension)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/submissions/` | Required | Submit a URL for extraction. Returns `data_quality: "full" \| "sparse" \| "processing"` |
| `GET` | `/api/submissions/<id>/submission_status/` | Required | Poll extraction status |

### Essays

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/essays/draft/` | Required | Generate essay draft for a scholarship |
| `POST` | `/api/essays/regenerate/` | Required | Regenerate with a quick-prompt modifier |

---

## Roadmap

- [ ] Vector similarity search for scholarship recommendations based on user profile
- [ ] Application document upload and storage
- [ ] Browser extension Firefox port
- [ ] Public scholarship submission (community-sourced additions with moderation queue)
- [ ] Analytics dashboard — application success rates, deadline hit/miss tracking
- [ ] Scholarship renewal cycle prediction for un-dated recurring awards

---

## License

MIT License — see [LICENSE](LICENSE) for details.
