# AutoPost — Autonomous Publishing Agent

𝐀𝐮𝐭𝐨𝐏𝐨𝐬𝐭 𝐢𝐬 𝐚𝐧 𝐞𝐧𝐝-𝐭𝐨-𝐞𝐧𝐝 𝐚𝐮𝐭𝐨𝐧𝐨𝐦𝐨𝐮𝐬 𝐚𝐠𝐞𝐧𝐭 𝐭𝐡𝐚𝐭 𝐝𝐢𝐬𝐜𝐨𝐯𝐞𝐫𝐬 𝐭𝐫𝐞𝐧𝐝𝐢𝐧𝐠 𝐨𝐩𝐞𝐧-𝐬𝐨𝐮𝐫𝐜𝐞 𝐫𝐞𝐩𝐨𝐬𝐢𝐭𝐨𝐫𝐢𝐞𝐬 𝐨𝐧 𝐆𝐢𝐭𝐇𝐮𝐛, 𝐚𝐧𝐚𝐥𝐲𝐳𝐞𝐬 𝐭𝐡𝐞𝐦 𝐮𝐬𝐢𝐧𝐠 𝐆𝐨𝐨𝐠𝐥𝐞 𝐆𝐞𝐦𝐢𝐧𝐢, 𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐬 𝐡𝐢𝐠𝐡-𝐪𝐮𝐚𝐥𝐢𝐭𝐲 𝐜𝐨𝐧𝐭𝐞𝐧𝐭, 𝐚𝐧𝐝 𝐩𝐮𝐛𝐥𝐢𝐬𝐡𝐞𝐬 𝐢𝐭 𝐭𝐨 𝐋𝐢𝐧𝐤𝐞𝐝𝐈𝐧 𝐚𝐧𝐝 𝐃𝐞𝐯.𝐭𝐨 — 𝐚𝐧𝐝 𝐩𝐮𝐬𝐡𝐞𝐬 𝐚𝐥𝐞𝐫𝐭𝐬 𝐭𝐨 𝐚 𝐃𝐢𝐬𝐜𝐨𝐫𝐝 𝐬𝐞𝐫𝐯𝐞𝐫.

## 🚀 Live Links

- **Live Application:** https://autopost-9c37c.web.app/#/
- **Backend API:** https://autopost-c54s.onrender.com/
- **Demo Video:** _Coming soon — the video link will be added after recording._

## What it does

1. **Discover** — searches for trending repositories by language.
2. **Analyze** — reads repository metadata and README content, then asks Gemini to identify the problem solved, tech stack, domain tags, novelty, complexity, audience, and a content hook.
3. **Review** — shows repositories in a paginated dashboard with a detailed analysis view.
4. **Generate** — creates platform-specific content based on the repository analysis.
5. **Publish** — publishes content to LinkedIn or Dev.to and sends a notification to Discord.
6. **Track** — stores discovered repositories and published posts in Firestore.

The dashboard uses a browser-generated UUID stored in `localStorage`. Every API request sends it through `X-Session-ID`, and user-facing Firestore data is stored under that session:

```text
sessions/{sessionId}/
├── discovered_repos/{repoId}
└── posts/{postId}
```

This prevents one browser session from seeing another session's repositories or publishing history without requiring a login screen.

> Note: this is session isolation, not strong authentication. A production multi-user application with sensitive data should use Firebase Authentication and verify identity tokens on the backend.

## Architecture

```text
                         Firebase Hosting
                       (frontend SPA)
                              ▲
                              │
                ┌─────────────┴─────────────┐
                │     React Frontend         │
                │     (Paper-ink UI)         │
                │ Vite + React Router v7     │
                │ X-Session-ID header        │
                └─────────────┬─────────────┘
                              │ HTTPS
                              ▼
                  Render (Backend)
                 FastAPI + Uvicorn
                              │
                    ┌─────────┴─────────┐
                    │     Endpoints      │
                    │ POST /agent/discover
                    │ POST /agent/analyze/{id}
                    │ POST /agent/publish/
                    │   {platform}/{id}
                    │ GET  /agent/repos
                    │ GET  /agent/posts
                    │ GET  /agent/stats
                    └─────────┬─────────┘
                              │
        ┌────────────┬────────┼────────┬────────────┐
        ▼            ▼        ▼        ▼            ▼
   ┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
   │ GitHub │  │ Gemini │ │LinkedIn│ │ Dev.to │ │ Firestore│
   │  API   │  │3.5 Flash│ │  API   │ │  API   │ │ Firebase │
   │Search + │  │Analysis│ │ Posts  │ │Articles│ │sessions/ │
   │README   │  │ + Gen  │ │        │ │        │ │{sid}/... │
   └────────┘  └────────┘ └────────┘ └────────┘ └────┬─────┘
                                                       │
                                                       ▼
                                             ┌───────────────────┐
                                             │  Discord Webhook  │
                                             │publish notifications│
                                             └───────────────────┘
```

### Pipeline Flow

```text
1. DISCOVER     GitHub Search API → trending repos (filtered by language, stars, date)
2. SAVE         Write to Firestore → sessions/{sid}/discovered_repos
3. ANALYZE      Fetch README via Contents API → Gemini 3.5 Flash generates structured analysis JSON
4. GENERATE     Gemini writes a platform-specific LinkedIn post or Dev.to article (Markdown)
5. PUBLISH      POST to LinkedIn/Dev.to API → save result to sessions/{sid}/posts
6. NOTIFY       Discord webhook → confirmation with published URL
```

---

## Tech stack

- **Frontend:** React, Vite, React Router v7
- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Google Gemini 3.5 Flash
- **Database:** Cloud Firestore via Firebase Admin SDK
- **Discovery:** GitHub API
- **Publishing:** LinkedIn API and Dev.to API
- **Notifications:** Discord Webhook
- **Deployment:** Render + Firebase Hosting

## Project structure

```text
Google_agentic_hackathon/
├── backend/
│   ├── app/
│   │   ├── db/firestore_client.py
│   │   ├── services/
│   │   ├── models/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   └── components/
│   ├── package.json
│   └── .env.example
├── scripts/
│   └── Linkedin_token_generation.py
├── firebase.json
└── firestore.rules
```

## Local setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Firebase CLI
- A Google Cloud/Firebase project with Firestore enabled
- API credentials listed below

### Backend

```bash
cd backend
python -m venv .venv
```

Activate it:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
source .venv/bin/activate
```

Install dependencies and create your environment file:

```bash
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux, use:

```bash
cp .env.example .env
```

Fill in `.env`, then start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The local API will run on `http://localhost:8000` and interactive docs are available at `/docs`.

### Frontend

In another terminal:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

For macOS/Linux:

```bash
cp .env.example .env
```

Set:

```env
VITE_API_URL=http://localhost:8000
```

## Environment variables

### Gemini

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
```

- `GEMINI_API_KEY`: API key used for repository analysis and content generation.
- `GEMINI_MODEL`: Gemini 3.5 Flash model identifier used by AutoPost.

### GitHub

```env
GITHUB_TOKEN=
GITHUB_MAX_REPOS_PER_RUN=10
```

- `GITHUB_TOKEN`: GitHub personal access token used for authenticated API access and higher rate limits.
- `GITHUB_MAX_REPOS_PER_RUN`: maximum repositories considered in one agent run.

### Dev.to

```env
DEVTO_API_KEY=
```

- `DEVTO_API_KEY`: API key used to publish articles.
- AI-generated tags are sanitized to lowercase alphanumeric values before publishing.

### Discord

```env
DISCORD_WEBHOOK_URL=
```

- Optional webhook used to send publishing notifications.

### LinkedIn

```env
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_PERSON_URN=
```

- `LINKEDIN_CLIENT_ID`: application client ID.
- `LINKEDIN_CLIENT_SECRET`: application client secret.
- `LINKEDIN_ACCESS_TOKEN`: OAuth token used for publishing.
- `LINKEDIN_PERSON_URN`: authenticated LinkedIn member URN.

### Firebase / Firestore

```env
GOOGLE_APPLICATION_CREDENTIALS=serviceAccountKey.json
```

For local development, this points to the downloaded Firebase/Google service-account JSON file. Never commit that file.

### Agent configuration

```env
AGENT_MAX_STEPS_PER_RUN=20
AGENT_CURATION_THRESHOLD=7.5
AGENT_DAILY_POST_LIMIT=3
```

These configure the agent's execution limits and curation behavior.

## Getting a LinkedIn access token

The repository includes `scripts/Linkedin_token_generation.py`.

1. Create a LinkedIn application and configure the redirect URI used by the script: `http://localhost:8000/callback`.
2. Enter your LinkedIn client ID and client secret in the script.
3. Install `requests` if it is not already installed.
4. Run:

```bash
python scripts/Linkedin_token_generation.py
```

The script opens the authorization page, starts a local callback server, exchanges the authorization code for an access token, and prints both the access token and person URN.

Copy them into the backend `.env` file. Keep the token private and regenerate it when it expires.

## Firebase and Firestore setup

1. Create a Firebase project.
2. Enable **Cloud Firestore**.
3. Add your Firebase project to the Firebase CLI:

```bash
firebase login
firebase use --add
```

4. For local backend development, create/download a service-account key and set `GOOGLE_APPLICATION_CREDENTIALS` to its path.
5. Deploy Firestore rules and indexes when required:

```bash
firebase deploy --only firestore
```

The backend uses the Firebase Admin SDK, so server-side Firestore calls are authorized with the service account rather than browser Firestore rules.

## Deploy backend to Render

Create a Render Web Service connected to this repository.

Recommended settings:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Add all backend environment variables in the Render environment settings. For production Firestore access, configure Google application credentials according to your deployment secret-management approach; do not commit a service-account JSON file.

After deployment, use the Render service URL as the frontend API URL.

## Deploy frontend to Firebase Hosting

Set the production frontend environment variable:

```env
VITE_API_URL=https://your-render-service.onrender.com
```

Then build and deploy:

```bash
cd frontend
npm install
npm run build
cd ..
firebase deploy --only hosting
```

The included `firebase.json` controls Firebase Hosting configuration.

## Live demo

### Application

- Firebase Hosting: https://autopost-9c37c.web.app/#/
- Render backend: https://autopost-c54s.onrender.com/

### Demo video

> 🎥 Video link will be added after recording.

## 🚀 Future Vision & Planned Features

My goal is to scale **AutoPost** to a larger user base and expand it to more community platforms such as **Instagram, Facebook, X, Reddit, and more — all with one tap of a finger**.

Each post will be unique and tailored to the style, audience, and nuances of its destination platform, helping maximize engagement and relevance instead of publishing the exact same content everywhere.

I also plan to simplify the integration process. Currently, AutoPost requires API keys and credentials from different platforms, which the agent uses to call platform-specific publishing tools. In the future, my vision is to make AutoPost work directly with connected user accounts through a simpler authorization flow, reducing the complexity of manually managing API keys.

This will make AutoPost more accessible to students who are not from technical backgrounds, as well as a wider community of users who want **simplicity, efficiency, and scale**.

### Planned features

- 🌐 Support for more publishing platforms, including Instagram, Facebook, X, Reddit, and additional communities.
- 🎯 Platform-specific AI content generation instead of one generic post for every platform.
- 👤 User accounts and simplified account connections.
- 🔐 OAuth-based integrations to reduce manual API-key management.
- 📈 Improved analytics and engagement tracking.
- 🧠 Better content recommendations based on historical performance.
- ⚡ One-tap publishing to multiple connected platforms.
- 👥 Scalable multi-user architecture with proper authentication and user-level data isolation.

## Important behavior

- Repositories are paginated five at a time in the dashboard.
- **Open** displays the full AI analysis, including hook, tech stack, novelty score, complexity, target audience, and domain tags.
- **Analyze** remains available for repositories awaiting analysis.
- LinkedIn and Dev.to publishing controls appear in the expanded repository view.
- Dev.to errors now include the API response body when available, making publishing failures easier to debug.

## Security notes

Never commit `.env` files, API tokens, OAuth secrets, or Firebase service-account keys. Rotate any credential that is accidentally exposed in source control.

## License

Add a license file if you intend to distribute or reuse this project publicly.
