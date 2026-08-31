<div align="center">

# AutoPost — Autonomous Publishing Agent

**Discover trending GitHub repos. Generate dev content. Publish everywhere. Zero humans required.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Firebase-orange?style=for-the-badge&logo=firebase)](https://autopost-9c37c.web.app/#/)
[![Backend API](https://img.shields.io/badge/Backend%20API-Render-46E3B7?style=for-the-badge&logo=render)](https://autopost-c54s.onrender.com/)
[![Built for](https://img.shields.io/badge/Built%20for-Google%20Agentic%20Hackathon-4285F4?style=for-the-badge&logo=google)](https://github.com/Qisanxi/Google_agentic_hackathon)

</div>

---

## 🎥 Demo

> 📹 **Video walkthrough coming soon** — recording in progress.

**Live links:**
- 🌐 Frontend: [https://autopost-9c37c.web.app/#/](https://autopost-9c37c.web.app/#/)
- ⚙️ Backend API / Swagger: [https://autopost-c54s.onrender.com/docs](https://autopost-c54s.onrender.com/docs)

---

## What is AutoPost?

AutoPost is a fully autonomous DevRel content agent. You point it at GitHub, it finds what is worth talking about, writes the post, and ships it — on LinkedIn and Dev.to — without you touching a keyboard after setup.

```
GitHub Trending  ──▶  Gemini Analysis  ──▶  Content Generation  ──▶  LinkedIn / Dev.to
                              │                                              │
                         Firestore                                      Discord alert
                         (per-session)
```

### What it does

1. **Discovers** trending GitHub repos from the last 7 days filtered by language and star count
2. **Analyzes** each repo with Gemini — extracting problem statement, tech stack, novelty score, and a one-liner hook
3. **Curates** — only repos scoring ≥ 7.5 / 10 on novelty get approved
4. **Generates** platform-tailored content:
   - LinkedIn: 3–4 paragraphs, professional tone, ends with a question
   - Dev.to: 800–1200 word markdown article with code snippets
5. **Publishes** directly to your LinkedIn profile and Dev.to account
6. **Notifies** your Discord channel on every publish

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  LandingPage  ──▶  Dashboard  ──▶  Session-scoped API calls     │
│                     (Vite + Firebase Hosting)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS + X-Session-ID header
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│                      Deployed on Render                          │
│                                                                  │
│  /agent/discover  ──▶  GitHubClient  ──▶  Firestore             │
│  /agent/analyze   ──▶  Gemini API    ──▶  Firestore             │
│  /agent/publish   ──▶  LinkedIn API  ──▶  Firestore             │
│                   ──▶  Dev.to API    ──▶  Firestore             │
│                   ──▶  Discord Webhook                          │
│                                                                  │
│  Google ADK Agent  (devrel_agent.py — autonomous runner)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Firebase Firestore                           │
│  sessions/{sessionId}/discovered_repos/{repoId}                 │
│  sessions/{sessionId}/posts/{postId}                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, React Router 7 |
| Backend | FastAPI, Python 3.11+ |
| AI / Agent | Google Gemini 2.5 Flash, Google ADK 2.8 |
| Database | Firebase Firestore |
| Hosting | Firebase Hosting (frontend), Render (backend) |
| Publishing | LinkedIn REST API, Dev.to API |
| Notifications | Discord Webhooks |
| Auth | Session-scoped UUID (localStorage) |
| Testing | pytest, unittest.mock |
| Code Quality | mypy, bandit, structlog |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Firebase project (free Spark plan works)
- A GitHub fine-grained token
- A Google Gemini API key
- LinkedIn and Dev.to API keys (see setup guides below)

---

### 1. Clone the repo

```bash
git clone https://github.com/Qisanxi/Google_agentic_hackathon.git
cd Google_agentic_hackathon
```

---

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

**Environment variables explained:**

| Variable | Description | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL` | Model to use | Leave as `gemini-2.5-flash` |
| `GITHUB_TOKEN` | Fine-grained PAT | GitHub → Settings → Developer settings → Fine-grained tokens |
| `GITHUB_MAX_REPOS_PER_RUN` | Max repos to fetch per discovery run | Recommended: `10` |
| `DEVTO_API_KEY` | Dev.to API key | dev.to → Settings → Extensions → API Keys |
| `DISCORD_WEBHOOK_URL` | Webhook URL for notifications | Discord channel → Edit → Integrations → Webhooks |
| `LINKEDIN_CLIENT_ID` | OAuth app client ID | LinkedIn Developer Portal |
| `LINKEDIN_CLIENT_SECRET` | OAuth app client secret | LinkedIn Developer Portal |
| `LINKEDIN_ACCESS_TOKEN` | Your personal access token | Run the token script below |
| `LINKEDIN_PERSON_URN` | Your LinkedIn person URN | Printed by the token script |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase service account JSON | Firebase → Project Settings → Service Accounts |
| `AGENT_MAX_STEPS_PER_RUN` | Max agent reasoning steps | Recommended: `20` |
| `AGENT_CURATION_THRESHOLD` | Minimum novelty score to approve a repo | Recommended: `7.5` |
| `AGENT_DAILY_POST_LIMIT` | Max posts per agent run | Recommended: `3` |

**GitHub token permissions:**

When creating a fine-grained token, set:
- Repository access → **All repositories** ← critical, not just selected repos
- Permissions → Contents: **Read-only**
- Permissions → Metadata: **Read-only** (auto-granted)

Everything else → No access.

**Generate LinkedIn access token:**

```bash
# Fill in CLIENT_ID and CLIENT_SECRET inside the script first
python scripts/Linkedin_token_generation.py
```

This opens a browser, completes OAuth, and prints your `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` directly to the terminal.

**Firebase setup:**

1. Go to [console.firebase.google.com](https://console.firebase.google.com) → Create project
2. Enable Firestore Database (start in production mode)
3. Go to Project Settings → Service Accounts → Generate new private key
4. Save the downloaded JSON as `backend/serviceAccountKey.json`
5. Set `GOOGLE_APPLICATION_CREDENTIALS=serviceAccountKey.json` in `.env`
6. Deploy Firestore indexes: `firebase deploy --only firestore:indexes`

**Start the backend:**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000
npm run dev
```

Frontend runs at [http://localhost:5173](http://localhost:5173)

---

## Project Structure

```
Google_agentic_hackathon/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── devrel_agent.py          # Google ADK agent definition
│   │   │   ├── prompts/                 # Gemini prompt templates
│   │   │   └── tools/
│   │   │       ├── analysis_tools.py    # Gemini-powered repo analysis
│   │   │       ├── discovery_tools.py   # GitHub + HN fetchers
│   │   │       ├── generation_tools.py  # Per-platform content generation
│   │   │       ├── memory_tools.py      # Firestore state persistence
│   │   │       └── publishing_tools.py  # LinkedIn / Dev.to / Discord
│   │   ├── db/
│   │   │   └── firestore_client.py      # Safe Firestore wrapper
│   │   ├── models/
│   │   │   ├── post.py                  # Post data models
│   │   │   └── repo.py                  # Repo data models
│   │   ├── services/
│   │   │   ├── devto_client.py          # Dev.to API client
│   │   │   ├── discord_client.py        # Discord webhook client
│   │   │   ├── github_client.py         # GitHub REST API client
│   │   │   └── linkedin_client.py       # LinkedIn REST API client
│   │   ├── config.py                    # Env-based configuration
│   │   ├── exceptions.py                # Safe exception hierarchy
│   │   ├── main.py                      # FastAPI app + all endpoints
│   │   └── security.py                  # Input validation + sanitization
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_security.py
│   │   └── test_tools.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx            # Main dashboard (session-scoped)
│   │   │   └── LandingPage.jsx          # Marketing landing page
│   │   ├── utils/
│   │   │   └── session.js               # Session UUID management
│   │   └── styles/
│   │       └── index.css
│   └── package.json
├── scripts/
│   └── Linkedin_token_generation.py     # OAuth helper script
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
└── README.md
```

---

## Deployment

### Backend → Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New Web Service → connect your repo
3. Set:
   - **Build command**: `pip install -r backend/requirements.txt`
   - **Start command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root directory**: *(leave blank)*
4. Add all environment variables from `.env` in the Render dashboard
5. Set `ENVIRONMENT=production` to enable config validation on startup

### Frontend → Firebase Hosting

```bash
npm install -g firebase-tools
firebase login
firebase init hosting    # select your project, public dir = frontend/dist
cd frontend && npm run build
firebase deploy --only hosting
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/health` | Database connectivity check |
| `POST` | `/agent/discover` | Discover trending repos (requires `X-Session-ID` header) |
| `POST` | `/agent/analyze/{repo_id}` | Analyze a repo with Gemini |
| `POST` | `/agent/publish/linkedin/{repo_id}` | Generate + publish LinkedIn post |
| `POST` | `/agent/publish/devto/{repo_id}` | Generate + publish Dev.to article |
| `GET` | `/agent/repos` | List session repos |
| `GET` | `/agent/posts` | List session posts |
| `GET` | `/agent/stats` | Session statistics |

All endpoints that interact with user data require the `X-Session-ID` header containing the session UUID.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🚀 Future Roadmap

AutoPost is built for a single operator today. Here is what is coming next:

### Multi-user accounts
Right now the LinkedIn and Dev.to API keys are configured at the server level — meaning the agent publishes to the repo owner's accounts. The next major milestone is a proper account system where **any user can connect their own LinkedIn, Dev.to, and Discord** through OAuth flows, and the agent publishes to their personal profiles and channels. No shared credentials, full isolation.

### Additional publishing platforms
Beyond LinkedIn and Dev.to, the roadmap includes:
- **X / Twitter** — threads and single posts
- **Bluesky** — via the AT Protocol API
- **Reddit** — posting to relevant subreddits (r/programming, language-specific subs)
- **Hashnode** — technical blogging platform
- **Threads** — Instagram's text platform

### Web trending topics scraping
The current agent only looks at GitHub trending repos. The next discovery source is **web trending topics** — scraping Google Trends, Hacker News front page, Reddit hot posts, and tech newsletters to generate posts from what developers are actually talking about today, not just what was open-sourced.

### Scheduled autonomous runs
Instead of clicking "Run discovery" manually, users will set a schedule (daily at 9 AM, weekdays only, etc.) and the agent runs itself via a cron job — fully hands-off publishing.

### Engagement analytics
After publishing, pull engagement data back from each platform (LinkedIn reactions, Dev.to reactions and views) and surface it in the dashboard, closing the feedback loop so the agent can learn which content performs best.

### Voice and tone customization
Let users upload their best existing posts and tweets so the agent learns their specific writing style — not just a generic "professional" tone, but their actual voice.

### Team workspaces
Shared dashboards where multiple people can review, approve, or reject agent-generated drafts before they go live — keeping a human in the loop for teams that want oversight.

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

```bash
# Run linting
cd backend && mypy app/ && bandit -r app/

# Run tests
pytest tests/ -v

# Run frontend lint
cd frontend && npm run lint
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built for the **Google Agentic Hackathon** · Powered by **Gemini 2.5 Flash** + **Google ADK**

</div>
