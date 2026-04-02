# 📈 Tech Pulse

> **B2B Tech News Intelligence Platform — Automated deep-scraping, cleaning, and delivery of actionable industry intelligence.**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Problem Statement

**The Problem:** Business leaders, market researchers, and go-to-market teams spend countless hours manually monitoring disparate industry news sites, blogs, and PR feeds. The noise-to-signal ratio is heavily skewed by ads, clickbait, and formatting inconsistencies, resulting in lost productivity and delayed market insights.

**The Solution:** *Tech Pulse* solves this by implementing an end-to-end data pipeline that systematically monitors key tech news sources. Our platform extracts raw HTML, rigorously cleans it of boilerplate and advertisements using AI-assisted heuristics and Trafilatura, and structures the core insights into a centralized PostgreSQL database. This transformed data is then surfaced via a sleek internal dashboard and a RESTful API, enabling B2B users to consume high-fidelity intelligence in real-time.

---

## 🚀 Live Demo

[**Access the Live Production Dashboard Here**](https://example-tech-pulse-demo.up.railway.app) (Placeholder Link)

![Tech Pulse Dashboard](https://via.placeholder.com/1000x500?text=Tech+Pulse+Dashboard+Screenshot)

---

## 🏗 Architecture Diagram

```mermaid
flowchart TB
    subgraph Data Sources
        S1["Hacker News"]
        S2["TechCrunch"]
        S3["VentureBeat"]
    end

    subgraph Data Engineering Pipeline & Automation
        SCHED(("APScheduler\nTrigger")) -->|"Hourly Cron"| Scraper
        
        Scraper["Trafilatura + BeautifulSoup\nDeep Scraper"] -->|"Raw HTML"| RawStorage[("Temp File Storage")]
        RawStorage --> Cleaner["Data Cleaning Engine\nPandas + RegEx"]
        Cleaner --> Structuring["Metadata Extraction"]
    end

    subgraph Storage Layer
        Structuring --> DB[("Neon PostgreSQL\nCloud Database")]
    end

    subgraph Serving Layer
        DB <--> API{"FastAPI Server"}
        API <--> UI["Web Dashboard\nJinja2 + Tailwind"]
    end

    subgraph Consumers
        UI --> EndUser(("B2B User / Analyst"))
        API --> B2BSystem["Enterprise CRM / Alerting"]
    end

    S1 --> Scraper
    S2 --> Scraper
    S3 --> Scraper
```

---

## 🔄 Pipeline Flow Diagram

```mermaid
flowchart TD
    Start["Scheduler Triggers Pipeline"] --> Init["Initialize Sources List"]
    Init --> Fetch["HTTP GET Request to Source URLs"]
    Fetch --> Check1{"Status 200?"}
    Check1 -- No --> Retry["Exponential Backoff Retry"]
    Retry --> Check2{"Max Retries Exceeded?"}
    Check2 -- Yes --> LogError["Log Failure & Skip"]
    Check2 -- No --> Fetch
    
    Check1 -- Yes --> Extract["Extract Article Links (Pagination)"]
    Extract --> Parse["Parse HTML Content"]
    Parse --> Clean{"Has Missing Critical Fields?"}
    Clean -- Yes --> Skip["Mark as Invalid & Skip"]
    Clean -- No --> RemoveNoise["Trafilatura: Strip Menus, Ads, JS"]
    RemoveNoise --> Sanitize["Sanitize Text & Normalize Dates"]
    
    Sanitize --> Upsert["Upsert to Neon PostgreSQL"]
    Upsert --> Success["Pipeline Run Complete"]
    LogError --> Success
```

---

## 🛠 Tech Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| **Language** | Python 3.9+ | Core logic and data manipulation |
| **Extraction** | BeautifulSoup4, Trafilatura | HTML parsing and high-fidelity text extraction |
| **Processing** | Pandas, Regex | Data structuring, cleaning, and normalization |
| **Database** | PostgreSQL (Neon) | Relational cloud storage for scraped articles |
| **ORM** | SQLAlchemy | Database schema mapping and safe parameterized queries |
| **API/Backend** | FastAPI, Uvicorn | High-performance async REST API and dashboard serving |
| **Scheduling** | APScheduler | Background cron-job execution for data ingestion |
| **Logging** | Loguru | Beautiful, structured production logging |

---

## 📂 Project Structure

```text
tech-pulse/
├── .env.example              # Environment variables template
├── pyproject.toml            # Project metadata and configuration
├── requirements.txt          # Python dependencies
├── main.py                   # Application entry point and server setup
├── Dockerfile                # Containerization instructions
├── Procfile                  # Production deployment command configuration
├── docs/                     # Additional project documentation
├── data/                     # Local data storage (caching/temporary files)
├── static/                   # CSS, JS, and image assets for the dashboard
├── templates/                # Jinja2 HTML templates for the UI
├── tests/                    # Pytest test suite for unit and integration testing
│   └── test_endpoint.py
└── src/                      # Source code
    ├── __init__.py           
    ├── config.py             # Pydantic configuration loader
    ├── database/             # SQLAlchemy models, sessions, and DB migrations
    ├── scrapers/             # Domain-specific web scraping logic and base classes
    ├── cleaning/             # Data sanitization, HTML stripping, and text formatting
    ├── scheduler/            # APScheduler definitions for pipeline automation 
    └── api/                  # FastAPI routers and HTTP endpoint definitions
```

---

## 🏁 Getting Started

### Prerequisites
- Python 3.9+ 
- Neon PostgreSQL Account (or local Postgres server)
- `pip` or `uv` package manager

### 1. Installation

Clone the repository and set up your virtual environment:

```bash
git clone https://github.com/yourusername/tech-pulse.git
cd tech-pulse

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Copy the example environment file and configure your database URI:

```bash
cp .env.example .env
```

Update your `.env` file:
```env
# Server
API_HOST="0.0.0.0"
API_PORT="8000"
LOG_LEVEL="INFO"

# Database
DATABASE_URL="postgresql://user:password@ep-cool-butterfly-1234.us-east-2.aws.neon.tech/tech_pulse?sslmode=require"

# Pipeline Settings
SCRAPE_INTERVAL_HOURS="1"
```

### 3. Running Locally

Start the entire system (FastAPI server + Background Scheduler) with one command:

```bash
python main.py
```

*The dashboard will be available at `http://localhost:8000`.*
*Swagger API Docs available at `http://localhost:8000/docs`.*

---

## ⚙️ Pipeline Stages Explained

### 1. Scraper Design (Ingestion)
The ingestion layer utilizes HTTP requests to fetch target portals (e.g., tech news listings). We implemented:
- **Pagination Logic:** Scrapers dynamically infer the number of pages available and use parameterized query strings to fetch subsequent pages until a designated freshness threshold (e.g., articles older than 48 hours) is reached.
- **Resilience & Politeness:** Built-in connection pooling, random user-agent rotation, and linear backoff error handling to prevent IP bans and navigate temporary 50x errors.

### 2. Cleaning & Sanitization Engine
Raw HTML requires rigorous processing before it is business-ready.
- **Noise Reduction:** We utilize `Trafilatura`, a state-of-the-art NLP scraping library, to differentiate between the core article content and boilerplate (navigation bars, footers, ad blocks).
- **Text Normalization:** `Pandas` is used to drop duplicates, enforce consistent UTF-8 encoding, and standardize publish date formats (ISO 8601) to support robust time-series querying.

### 3. Database Schema
We rely on a structured relational model via Neon PostgreSQL to ensure ACID compliance:
- **`Article` Table:**
  - `id` (UUID, Primary Key)
  - `source_url` (String, Unique Index)
  - `title` (String, Indexed for Search)
  - `authors` (Array of Strings)
  - `publish_date` (DateTime)
  - `content_clean` (Text)
  - `scraped_at` (DateTime, Default: NOW())

### 4. Scheduler & Automation
A background task orchestrated by `APScheduler` serves as the pipeline trigger. It runs asynchronously within the FastAPI lifecycle, activating the scraping routines on an hourly interval (`settings.scrape_interval_hours`). Conflicts are avoided via database-level deduplication (upsert queries based on `source_url`).

---

## 🔌 API Documentation

### HTTP GET `/api/v1/articles`
Fetches a list of the latest scraped tech articles.

**Parameters:**
- `skip` (int, default: 0) — Pagination offset.
- `limit` (int, default: 20) — Maximum results per page.
- `source` (str, optional) — Filter by specific domain (e.g., "techcrunch").

**Sample Request:**
```http
GET /api/v1/articles?limit=2&source=techcrunch HTTP/1.1
Host: localhost:8000
```

**Sample JSON Response:**
```json
{
  "total": 142,
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "Anthropic releases new Claude 3.5 Sonnet model",
      "source_url": "https://techcrunch.com/article/123",
      "publish_date": "2026-04-02T14:30:00Z",
      "summary": "Anthropic has unveiled its latest foundational AI model aimed at enterprise coding workflows..."
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "title": "Vercel acquires startup to improve caching infrastructure",
      "source_url": "https://techcrunch.com/article/124",
      "publish_date": "2026-04-01T09:15:00Z",
      "summary": "In an effort to expand its edge network capabilities, Vercel announced..."
    }
  ],
  "page_context": {
    "skip": 0,
    "limit": 2
  }
}
```

---

## 🧠 AI/ML Layer

*(Future Roadmap Context)*
Currently, the extraction layer leverages advanced heuristic algorithms (`Trafilatura`). In the next major release (v2.0), we are integrating a lightweight, local NLP model (e.g., `spacy` or minimal transformers) to execute:
- **Zero-shot Categorization:** Automatically tagging articles (e.g., "Cybersecurity", "GenAI", "Layoffs").
- **Abstractive Summarization:** Generating brief, 3-bullet TL;DRs using an external LLM SDK to further reduce the reading time for our B2B users.

---

## ⚖️ Design Decisions & Trade-offs

- **Neon PostgreSQL over NoSQL:** While scraping unstructured data often leans towards MongoDB, our B2B consumers run strict analytical queries (dates, sources, joins). PostgreSQL was chosen for its strong querying capabilities, while Neon's serverless architecture keeps costs near-zero during idle hours.
- **FastAPI Threading vs Process Multiprocessing:** For network IO-bound tasks like web scraping, FastAPI's `asyncio` loop combined with multithreaded workers is used instead of multiprocessing pools. This saves memory overhead while still outperforming synchronous blocking code.
- **Local APScheduler vs Airflow/Prefect:** To keep deployment simple and encapsulated within a single container on platforms like Render/Railway, `APScheduler` is embedded within the FastAPI app. Full enterprise orchestration (Airflow) was eschewed as overkill for the current project scope.

---

## 🔭 Future Improvements

With an expanded timeline, these are the immediate roadmap priorities:
1. **Proxy Rotation & IP Shuffling:** Integrated cloud proxies (e.g., BrightData, ScrapingBee) to circumvent strict anti-bot measures on high-value industry sites.
2. **Text Embeddings & Vector Search:** Embedding article contents with `sentence-transformers` and saving to `pgvector` to enable semantic search on the frontend ("Find me articles about edge compute latency").
3. **Kafka Event Bus:** As usage grows, decouple the scraping layer from the web API layer using an event broker like Kafka or RabbitMQ instead of the embedded scheduler.
4. **Automated Alerting:** Email/Slack integrations for specific tracked keywords (e.g., triggering a Slack webhook whenever a direct competitor is mentioned).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
