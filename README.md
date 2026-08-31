<p align="center">
  <b>AutoPost</b><br>
  <span>The autonomous publishing agent for developer relations</span>
</p>

---

## What is AutoPost?

AutoPost is an end-to-end autonomous agent that discovers trending open-source repositories on GitHub, analyzes them using Google Gemini, generates high-quality content, and publishes it to LinkedIn and Dev.to — all without human intervention.

Each user session is fully isolated. The frontend generates a unique session ID stored in <code>localStorage</code>, and every API call sends it as an <code>X-Session-ID</code> header. The backend namespaces all Firestore writes under <code>sessions/{sessionId}/</code>, so every device gets its own isolated view of discovered repos and published posts — no auth system required.

**Key features:**

- GitHub trending repo discovery (language-filtered, star-gated, date-bounded)
- README fetching via GitHub Contents API (auto-detects branch and filename)
- Gemini-powered analysis: problem solved, tech stack, domain tags, novelty score, complexity, target audience, one-liner hook
- AI-generated LinkedIn posts and Dev.to articles with proper tag sanitization
- Discord webhook notifications on every publish
- Session-scoped data isolation (no login required)
- Paper-ink editorial UI with live activity console

---

## Architecture

```

                         Firebase Hosting
                       (frontend SPA)
                              ◄
                              ▼
                ┌──────────────┐
                │  React Frontend  │  Vite + React Router v7
                │  (Paper-ink UI) │  X-Session-ID header
                └─┐              └┬─────────────┤
                   │               │
                   ▼               │
              Render (Backend)        │
              FastAPI + Uvicorn        │
                    │               │
        ┌────────┐              │
        │  Endpoints   │              │
        │             │              │
        │ POST /agent/discover  ─────┐
        │ POST /agent/analyze/{id}───┓
        │ POST /agent/publish/   ──┓
        │   {platform}/{id}       │
        │ GET  /agent/repos       │
        │ GET  /agent/posts       │
        │ GET  /agent/stats       │
        └─────┤────────────┤
                   │               │
                   ▼               ▼
     ┌──────┐  ┌───────┐  ┌───────┐  ┌──────┐
     │GitHub  │  │Gemini │  │LinkedIn│  │Dev.to │
     │API     │  │API     │  │API    │  │API   │
     │(README)│  │(Analysis│  │(Posts) │  │(Articles)│
     │(Search)│  │+ Gen)  │  │        │  │        │
     └──────┘  └───────┘  └───────┘  └──────┘
                              │
                              │
                              ▼
                     ┌───────────────────┐
                     │  Firestore (Firebase)   │
                     │  sessions/{sid}/repos   │
                     │  sessions/{sid}/posts   │
                     │  tag_performance        │
                     │  agent_sessions         │
                     └───────────────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │  Discord Webhook       │
                     │  (publish notifications) │
                     └───────────────────┘

```

### Pipeline Flow

```
1. DISCOVER     GitHub Search API  →  trending repos (filtered by language, stars, date)
2. SAVE         Write to Firestore  →  sessions/{sid}/discovered_repos
3. ANALYZE      Fetch README via Contents API  →  Gemini generates structured analysis JSON
4. GENERATE     Gemini writes LinkedIn post or Dev.to article (Markdown)
5. PUBLISH      POST to LinkedIn/Dev.to API  →  save result to sessions/{sid}/posts
6. NOTIFY       Discord webhook  →  confirmation with published URL
```

---

## Tech Stack

| Layer       | Technology                                      |
|-------------|--------------------------------------------------|
| Frontend    | React 19, Vite 6, React Router v7 (HashRouter)   |
| Styling     | CSS custom properties, Fraunces + IBM Plex Mono  |
| Backend     | Python 3.12, FastAPI 0.141, Uvicorn              |
| AI          | Google Gemini 2.5 Flash (via google-genai SDK)    |
| Database    | Cloud Firestore (via firebase-admin + service account) |
| Hosting     | Firebase Hosting (frontend), Render (backend)    |
| Monitoring  | Structured logging (structlog), Discord webhooks  |

---

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- A Firebase project with Firestore enabled
- API keys for Gemini, GitHub, Dev.to, LinkedIn, and a Discord webhook

### 1. Clone and install

```bash
git clone https://github.com/Qisanxi/Google_agentic_hackathon.git
cd Google_agentic_hackathon
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your actual keys (see Environment Variables section below)
```

### 3. Firebase setup

1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a project (or select an existing one).
2. Enable **Cloud Firestore** in the Firebase console (start in test mode for development).
3. Go to **Project Settings → Service Accounts** and click **Generate New Private Key**. Download the JSON file.
4. Place the service account JSON file in the <code>backend/</code> directory (or anywhere accessible) and set the path in your <code>.env</code>:

```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your-service-account-key.json
```

5. (Optional) Deploy Firestore rules and indexes:

```bash
npm install -g firebase-tools
firebase login
firebase deploy --only firestore:rules,firestore:indexes
```

### 4. Frontend setup

```bash
cd frontend
npm install
```

### 5. Run locally

Terminal 1 — backend:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:
```bash
cd frontend
npm run dev
```

The frontend runs at <code>http://localhost:5173</code> and proxies API calls to the backend.

---

## Environment Variables

All variables are set in <code>backend/.env</code> (see <code>backend/.env.example</code> for a template).

### Gemini

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| <code>GEMINI_API_KEY</code>      | Yes      | Google AI Studio API key for Gemini model access   |
| <code>GEMINI_MODEL</code>       | No       | Model name (default: <code>gemini-2.5-flash</code>)               |

### GitHub

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| <code>GITHUB_TOKEN</code>       | Yes      | GitHub Personal Access Token with <code>repo</code> scope (for search + README fetch) |
| <code>GITHUB_MAX_REPOS_PER_RUN</code> | No  | Max repos per discovery run, 1–50 (default: 10)      |

### LinkedIn

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| <code>LINKEDIN_CLIENT_ID</code>     | Yes      | LinkedIn App Client ID from the developer portal  |
| <code>LINKEDIN_CLIENT_SECRET</code> | Yes      | LinkedIn App Client Secret                        |
| <code>LINKEDIN_ACCESS_TOKEN</code>  | Yes      | OAuth 2.0 access token with <code>w_member_social</code> scope  |
| <code>LINKEDIN_PERSON_URN</code>    | Yes      | Your LinkedIn person URN (e.g. <code>urn:li:person:abc123</code>)     |

### Dev.to

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| <code>DEVTO_API_KEY</code>       | Yes      | Dev.to API key (from Settings → Extensions → DEV Community API Keys) |

### Discord

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| <code>DISCORD_WEBHOOK_URL</code> | Yes      | Full Discord webhook URL for publish notifications  |

### Firebase

| Variable                      | Required | Description                                          |
|-------------------------------|----------|------------------------------------------------------|
| <code>GOOGLE_APPLICATION_CREDENTIALS</code> | Yes      | Path to Firebase service account JSON key file      |

### Agent Behavior

| Variable                    | Required | Description                                        |
|-----------------------------|----------|----------------------------------------------------|
| <code>AGENT_MAX_STEPS_PER_RUN</code>  | No       | Max tool calls per agent run (default: 20)          |
| <code>AGENT_CURATION_THRESHOLD</code> | No       | Minimum novelty score to auto-approve (default: 7.5) |
| <code>AGENT_DAILY_POST_LIMIT</code>   | No       | Max posts per day (default: 3)                     |

---

## How to Get LinkedIn Tokens

A helper script is provided at <code>scripts/Linkedin_token_generation.py</code>. Here’s the full process:

### Step 1: Create a LinkedIn App

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/) and sign in.
2. Click **Create App** and fill in the details.
3. Under the **Auth** tab, add <code>http://localhost:8000/callback</code> as a **Redirect URL**.
4. Note your **Client ID** and **Client Secret**.

### Step 2: Request the w_member_social Scope

The app needs the <code>w_member_social</code> scope to create posts on your behalf. This requires LinkedIn approval. In the developer portal, go to the **Products** tab and request access to "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect".

### Step 3: Run the Token Generation Script

Edit <code>scripts/Linkedin_token_generation.py</code> and replace the placeholder values:

```python
CLIENT_ID = "your_actual_client_id"
CLIENT_SECRET = "your_actual_client_secret"
```

Then run:

```bash
pip install requests
python scripts/Linkedin_token_generation.py
```

This will:
1. Open your browser to the LinkedIn OAuth consent screen
2. Start a local server at <code>localhost:8000</code> to catch the redirect
3. Exchange the auth code for an access token
4. Fetch your profile and print your **Person URN**

Copy both the **access token** and **person URN** into your <code>backend/.env</code>:

```
LINKEDIN_ACCESS_TOKEN=AQV...
LINKEDIN_PERSON_URN=urn:li:person:abc123
```

> **Note:** LinkedIn access tokens expire. You will need to regenerate them periodically (typically every 60 days).

---

## Deployment

### Frontend: Firebase Hosting

```bash
cd frontend
npm run build
```

The build output goes to <code>frontend/dist/</code>, which is configured as the Firebase Hosting public directory in <code>firebase.json</code>.

Deploy:

```bash
firebase deploy --only hosting
```

Firebase is configured with:
- SPA rewrites (<code>** → /index.html</code>) for client-side routing
- Security headers (CSP, HSTS, X-Frame-Options, etc.)

### Backend: Render

1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect your GitHub repo and set:
   - **Root Directory:** <code>backend</code>
   - **Build Command:** <code>pip install -r requirements.txt</code>
   - **Start Command:** <code>uvicorn app.main:app --host 0.0.0.0 --port $PORT</code>
3. Add all environment variables from your <code>.env</code> file in the Render environment settings.
4. Upload your Firebase service account key as a file (or base64-encode it and decode at startup).

Render will auto-deploy on every push to the connected branch.

---

## API Endpoints

| Method | Endpoint                              | Description                          |
|--------|---------------------------------------|--------------------------------------|
| POST   | <code>/agent/discover</code>               | Discover trending GitHub repos       |
| POST   | <code>/agent/analyze/{repo_id}</code>      | Analyze a repo with Gemini           |
| POST   | <code>/agent/publish/linkedin/{repo_id}</code> | Generate and publish to LinkedIn  |
| POST   | <code>/agent/publish/devto/{repo_id}</code>   | Generate and publish to Dev.to    |
| GET    | <code>/agent/repos</code>                  | List discovered repos (session-scoped) |
| GET    | <code>/agent/posts</code>                  | List published posts (session-scoped)  |
| GET    | <code>/agent/stats</code>                  | Get session statistics                |

All endpoints (except health) accept an optional <code>X-Session-ID</code> header (UUID v4 format). When provided, all data is isolated to that session.

---

## Project Structure

```
Google_agentic_hackathon/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, all route handlers
│   │   ├── config.py            # Environment variable loading
│   │   ├── security.py          # Input validation, sanitization
│   │   ├── exceptions.py        # Custom exception classes
│   │   ├── db/
│   │   │   └── firestore_client.py  # Firestore wrapper with session scoping
│   │   ├── models/
│   │   │   ├── repo.py             # Pydantic model for repo analysis
│   │   │   └── post.py             # Pydantic model for posts
│   │   ├── services/
│   │   │   ├── github_client.py    # GitHub API (search + README fetch)
│   │   │   ├── linkedin_client.py  # LinkedIn posting via w_member_social
│   │   │   ├── devto_client.py     # Dev.to API with tag sanitization
│   │   │   └── discord_client.py   # Discord webhook notifications
│   │   ├── agents/               # Agent framework (tools, prompts)
│   │   └── __init__.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx    # Editorial landing page
│   │   │   └── Dashboard.jsx      # Agent dashboard with pagination
│   │   ├── styles/
│   │   │   └── index.css          # Paper-ink design system
│   │   ├── App.jsx               # Route provider (HashRouter)
│   │   └── main.jsx              # Entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── scripts/
│   └── Linkedin_token_generation.py
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
└── README.md
```