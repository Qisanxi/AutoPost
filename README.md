# AutoPost — Autonomous Publishing Agent

AutoPost is an AI-powered developer-relations agent that discovers trending GitHub repositories, analyzes them with Gemini, and turns promising projects into publishable content for LinkedIn and Dev.to.

## What it does

1. **Discover** — searches for trending repositories by language.
2. **Analyze** — reads repository metadata and README content, then asks Gemini to identify the problem solved, tech stack, domain tags, novelty, complexity, audience, and a content hook.
3. **Review** — shows repositories in a paginated dashboard with a detailed analysis view.
4. **Publish** — generates and publishes LinkedIn posts or Dev.to articles.
5. **Track** — stores discovered repositories and published posts in Firestore.

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
┌──────────────────────────────────────┐
│ React + Vite Dashboard               │
│ localStorage UUID                    │
│ X-Session-ID on every API request    │
└───────────────────┬──────────────────┘
                    │ HTTPS
                    ▼
┌──────────────────────────────────────┐
│ FastAPI Backend                      │
│  ├─ Discovery endpoint               │
│  ├─ Gemini analysis                  │
│  └─ Publishing orchestration         │
└───────┬───────────┬───────────┬──────┘
        │           │           │
        ▼           ▼           ▼
    GitHub API   Gemini API   Firestore
        │           │           │
        │           │     sessions/{id}/...
        │           │
        └──────┬────┘
               ▼
      LinkedIn / Dev.to / Discord
```

## Tech stack

- **Frontend:** React, Vite, React Router
- **Backend:** Python, FastAPI
- **AI:** Google Gemini API
- **Database:** Cloud Firestore via Firebase Admin SDK
- **Discovery:** GitHub API
- **Publishing:** LinkedIn API and Dev.to API
- **Notifications:** Discord webhook
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
GEMINI_MODEL=gemini-2.5-flash
```

- `GEMINI_API_KEY`: API key used for repository analysis and content generation.
- `GEMINI_MODEL`: Gemini model identifier.

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

> Video link will be added after recording.

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
