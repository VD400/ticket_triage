# Ticket Triage: development setup and first merge

The project has three application processes: the FastAPI backend, the ARQ agent
worker, and the Vite frontend. PostgreSQL (with pgvector) and Redis support them.
The API and frontend can be checked offline; actual agent responses require Groq
and Cohere credentials.

## 1. Understand the three places involved

- **GitHub** stores your code. A branch is a version of the code; a pull request
  lets you review and merge the feature branch into `main`.
- **The Codex cloud environment** is a separate development machine. Its variables
  are available to backend and frontend processes on that machine.
- **Vercel, Render, and Supabase** are your deployment/database providers. Their
  settings do not automatically populate the Codex machine or GitHub Actions.

CI means automatic checks of a code change. The workflow in
`.github/workflows/ci.yml` tests the backend and builds the frontend. It contains
no deployment job. Existing Vercel/Render integrations control their own automatic
deployments; check those providers' branch settings separately.

## 2. Add the only two provider credentials needed for cloud development

1. Open the settings for the Codex environment associated with this chat.
2. Find the secure secret requirements named `GROQ_API_KEY` and `COHERE_API_KEY`.
3. Obtain a key from each provider account and enter its value securely there:
   - Groq: https://console.groq.com/keys
   - Cohere: https://dashboard.cohere.com/api-keys
4. Keep the exact variable names. Do not paste values into chat or commit `.env`.
5. Save the settings and tell the agent that the keys have been added. The agent
   can then verify provider access and the live worker without printing values.

The cloud draft allows the API destinations `api.groq.com` and `api.cohere.com`.
Saving a draft does not itself inject values into a running process or publish
the prepared environment. Recheck access after saving the settings. Once setup
and live checks are complete, review/save the prepared draft and publish through
the environment UI.

The development setup provides local database and Redis URLs and generates a
local JWT signing key. You do not need to connect your Supabase database for this
workflow. All frontend/backend names are configured in the same environment;
`VITE_*` values are public browser configuration, never secrets.

## 3. Variable reference

| Name | Used by | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | API, migrations, agent tools | SQLAlchemy PostgreSQL URL; `postgresql+psycopg://...` |
| `ASYNC_DATABASE_URL` | Worker and checkpoint setup | Plain psycopg URL; `postgresql://...` to the application database |
| `READONLY_DB_URL` | Agent SQL tool | SQLAlchemy URL using a dedicated read-only database role |
| `TEST_DATABASE_URL` | Tests | Dedicated PostgreSQL database; tests create and drop tables |
| `REDIS_URL` | API, worker, WebSockets | Redis connection URL |
| `JWT_SECRET_KEY` | API authentication | Private signing key; generated for local cloud development |
| `GROQ_API_KEY` | Agent | Private provider credential |
| `COHERE_API_KEY` | Embeddings and retrieval | Private provider credential |
| `VITE_API_URL` | Frontend | Public backend HTTP base address; WebSocket URLs derive from it |

`backend/.env.example` and `frontend/.env.example` document the names. Actual
`.env` files are ignored. Production connection strings and credentials belong
in the corresponding hosting provider's secure settings, not these examples.
Never use the application or production database as the test database.

## 4. Cloud startup and checks

The saved installation script creates local helpers under
`/workspace/.setup/ticket-triage`. Keep using the existing checkout at
`/workspace/ticket_triage`; cloud tasks are already isolated and do not require
an additional Git worktree.

An agent can start each component in its own long-running tool session:

```bash
bash /workspace/.setup/ticket-triage/start.sh services
bash /workspace/.setup/ticket-triage/start.sh api
bash /workspace/.setup/ticket-triage/start.sh worker
bash /workspace/.setup/ticket-triage/start.sh frontend
```

The API/worker commands require the relevant real provider keys. Processes must
restart in a new task; a filesystem snapshot does not preserve running servers.
If containers are absent, local startup creates fresh development databases.

To check the backend without sending AI requests:

```bash
cd /workspace/ticket_triage/backend
source /workspace/.setup/ticket-triage/env.sh
GROQ_API_KEY=test-key COHERE_API_KEY=test-key uv run --frozen pytest -q
uv run --frozen alembic current
```

`test-key` is only an offline test value. It must never be used to run actual
agent jobs. The expected migration head is `4327922f0820`.

To build the frontend:

```bash
cd /workspace/ticket_triage/frontend
source /workspace/.setup/ticket-triage/env.sh
npm run build
```

## 5. Get the prepared changes onto your feature branch

The changes prepared in the cloud checkout are not automatically on your laptop
or GitHub. If you receive the `ticket-triage-setup.patch` file, download it to the
root of your local repository, next to the `backend` and `frontend` folders.
Open a terminal in that directory. First check for uncommitted work:

```bash
git status
```

Leave the downloaded patch file untracked; it does not count as existing
application work. If there are other existing changes, commit or preserve them
before switching branches or applying the patch. Do not discard them. Once that
work is preserved:

```bash
git switch feature/agent-supervisor
git pull --ff-only origin feature/agent-supervisor
git apply --check ticket-triage-setup.patch
git apply ticket-triage-setup.patch
git diff --check
git diff
git add .github/workflows/ci.yml backend/agent/setup_checkpointer.py backend/agent/worker.py backend/tests/test_json_safety.py backend/.env.example frontend/.env.example README.md
git commit -m "Prepare development environment and CI checks"
git push origin feature/agent-supervisor
```

Run one command at a time. If a command fails, stop there and share the error
(without credentials); do not continue or force-push. The downloaded patch is
not application code and is not included in the explicit `git add` list.

Alternatively, if an agent commits/pushes these exact changes for you, do not
apply the same patch a second time. The cloud checkout already contains them.

## 6. Create and merge your first pull request

1. Open https://github.com/VD400/ticket_triage/compare/main...feature/agent-supervisor
2. Confirm **base** is `main`, and **compare** is `feature/agent-supervisor`.
   This means "put the feature branch changes into main."
3. Click **Create pull request**. Suggested title: `Add agent supervisor and frontend`.
4. In the description, mention the agent/frontend work and the automated backend
   tests and frontend build. Click **Create pull request** to submit it.
5. Wait for the CI **backend** and **frontend** jobs to pass. You can view their
   logs in the PR's checks or the repository's **Actions** tab.
6. If a check fails, open the failing step and fix it on the feature branch.
   New commits to that branch update the same PR and rerun the checks.
7. Once both pass and you have reviewed the changes, click **Merge pull request**,
   then **Confirm merge**. You can keep the feature branch for now.
8. To update your local main branch afterward, first ensure your working directory
   is clean, then run:

```bash
git switch main
git pull --ff-only origin main
```

The CI checks use temporary PostgreSQL and Redis services and offline test keys.
You do not need to add real Groq/Cohere keys as GitHub Actions secrets for these
checks. The first hosted GitHub Actions result is available only after a push/PR.

## 7. Deployment is a separate next step

Merging puts code on `main`; it does not configure new runtime services by itself.
An actual deployment needs the API, a separate ARQ worker, PostgreSQL with
pgvector/checkpoint tables, Redis, and the frontend. Configure real URLs and keys
on Render/Vercel separately. The API currently allows only the frontend origin
`http://localhost:5173` and prints mock email verification links using that origin;
those settings need adjustment before a Vercel frontend can use it.

Finish the cloud development setup and merge checks first. Deployment can then
be configured against the actual provider URLs and existing project settings.
