# Deploy Ticket Triage on Vercel, Render, and Supabase

The browser app runs on Vercel. Render runs **two** processes: the API and the
ARQ background worker. Supabase stores records and processing checkpoints.
Render Key Value (Redis) connects the API, worker, and live dashboard.

Codex environment settings do not copy to these providers. Enter real credentials
in Render's secure Environment settings. Do not copy the Codex localhost database
URLs, proxy secret placeholders, or test keys. Never upload `.env` to GitHub.

Use a small paid, always-on API and background worker for a reliable shared demo.
Check the current Render prices before creating services. A sleeping API cannot
keep a live connection open. A free Redis instance may lose jobs on restart;
PostgreSQL keeps ticket history, and the retry feature can recover interrupted work.

## 1. Put this deployment change on main

Merge the deployment pull request after its checks pass. Both providers should
deploy `main`, which already contains the dashboard and interrupted-ticket fixes.
No terminal download or patch application is required.

These files add configurable CORS, real verification email, private employee
provisioning, Docker startup, database initialization, and Vercel route rewrites.
Production `/auth/register` is disabled. Local public registration can create
viewers only; create administrator/agent accounts with the private CLI below.

## 2. Create the Vercel project and get its public address

Since you currently only have Supabase, first create your frontend project:

1. Sign in at https://vercel.com and choose **Add New → Project**.
2. Import `VD400/ticket_triage` from GitHub, granting access to this repository.
3. Set **Root Directory** to `frontend`, **Framework Preset** to `Vite`,
   **Install Command** to `npm ci`, **Build Command** to `npm run build`,
   **Output Directory** to `dist`, and Node version to `24.x`.
4. Deploy `main`. We will add the API URL and redeploy in step 9. At this point
   the landing page can load, but login and complaints are not connected yet.
5. Copy the stable production URL from the project, for example:

```text
https://your-project.vercel.app
```

Use the stable production address, not a temporary preview deployment URL.
Your Render API will get an address such as:

```text
https://ticket-triage-api.onrender.com
```

The examples below are placeholders. Substitute your actual addresses. Do not
include a trailing slash or `/docs` in either environment value.

## 3. Configure Supabase

1. Open your existing Supabase project. Use the project containing the tickets you
   want to keep, or a separate project for a demo. Do not reset it or rerun the seed
   scripts: `seed_data.py` deletes existing application records.
2. Open **Connect** and select the **Session pooler** connection string. Copy the
   current project host, username, port (normally 5432), database, and password.
   Avoid the transaction pooler (normally 6543): the checkpoint connection uses
   prepared statements and needs session/direct connections.
3. Enter the real database password. This is not a Supabase API key or account
   password. URL-encode special characters in the password before putting it in a
   connection string; for example, `@` becomes `%40` and `#` becomes `%23`.
4. Create two versions of the same application connection:

   ```text
   DATABASE_URL=postgresql+psycopg://USER:ENCODED_PASSWORD@SESSION_HOST:5432/postgres?sslmode=require
   ASYNC_DATABASE_URL=postgresql://USER:ENCODED_PASSWORD@SESSION_HOST:5432/postgres?sslmode=require
   ```

   For the admin session-pooler URI, `USER` is usually `postgres.PROJECT_REF`.
   Copy the exact current values from Connect; do not reuse an old project reference
   or guess the regional host. These two URLs point to the **same** database.
5. The API startup creates the pgvector extension, runs `alembic upgrade head`, and
   initializes LangGraph checkpoint tables. It does not insert sample records.

If migrations report that tables already exist or that a revision is missing,
stop and share the error without credentials. Do not drop tables or run
`alembic stamp head` as a workaround.

## 4. Create Redis on Render

1. In Render choose **New → Key Value** (Redis).
2. Name it `ticket-triage-redis` and select a region near your Supabase project.
3. Use that same Render region for your API and worker.
4. Set its eviction policy to **noeviction** so Redis does not silently evict jobs.
5. Copy the **Internal Redis URL**. Use it as `REDIS_URL` on both Render services.
   Do not use an HTTP/REST Redis URL. Leave external access disabled unless needed.

## 5. Choose how to send verification email

The project supports either Resend over HTTPS or SMTP. Configure one option.
Resend avoids outbound SMTP port restrictions on hosting providers.

### Option A: Resend with a domain you own

1. Create a Resend account at https://resend.com.
2. Add your domain and apply the DNS records Resend supplies at your domain provider.
3. Wait until the domain is verified. A `vercel.app` address is not a domain you
   own and cannot be used as your sending domain.
4. Create a Resend API key and choose a sender on the verified domain.
5. Add these **to the Render API service**:

   | Variable | Value |
   | --- | --- |
   | `EMAIL_BACKEND` | `resend` |
   | `RESEND_API_KEY` | Your real Resend key |
   | `EMAIL_FROM` | For example, `support@your-domain.com` |

Resend's test sender can be used only within its testing restrictions. It is not
enough to email arbitrary visitors. Verify your domain before inviting others.

### Option B: SMTP if you do not own a domain

Use an email provider that permits authenticated SMTP. For a personal Gmail
account, enable two-step verification, then generate a Google **App Password**
(if your account supports it). Use that app password, not your normal password.

Add these to the **Render API service** instead of the Resend settings:

| Variable | Gmail example |
| --- | --- |
| `EMAIL_BACKEND` | `smtp` |
| `EMAIL_FROM` | Your Gmail address |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USERNAME` | Your Gmail address |
| `SMTP_PASSWORD` | Your Google App Password |

Port 465 uses SSL; port 587 uses STARTTLS. Both verify TLS certificates.
Check that your Render plan permits outbound SMTP. If the host blocks it,
use the HTTPS Resend option or another HTTPS email provider integration.

These settings currently send **verification emails only**. Resolution emails
are not implemented; agents review and resolve tickets in the dashboard.

## 6. Create the Render API

1. Choose **New → Web Service** and connect `VD400/ticket_triage`.
2. Use the following settings (labels may vary slightly):

   | Setting | Value |
   | --- | --- |
   | Name | `ticket-triage-api` |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime / Language | `Docker` |
   | Dockerfile Path | `./Dockerfile` |
   | Docker Build Context | `.` (relative to `backend`) |
   | Docker Command | Leave empty; the Dockerfile starts the API |
   | Region | Same as Redis |
   | Health Check Path | `/health` |

   Do not enter a Python build/start command in Docker mode. The image installs
   the pinned Python/dependencies; it starts with `bash deployment/start.sh api`.
   The process listens on `0.0.0.0` and Render's `PORT`, without `--reload`.

3. Open **Environment** and add:

   | Variable | What to put there |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `FRONTEND_URL` | Your stable `https://...vercel.app` URL |
   | `CORS_ORIGINS` | The same Vercel URL; comma-separated origins if you also have a custom domain |
   | `DATABASE_URL` | SQLAlchemy Supabase session-pooler URI from step 3 |
   | `ASYNC_DATABASE_URL` | Plain PostgreSQL version of that same URI |
   | `REDIS_URL` | Render's Internal Redis URL |
   | `JWT_SECRET_KEY` | A new, long random signing secret |
   | `GROQ_API_KEY` | Your real Groq key |
   | `COHERE_API_KEY` | Your real Cohere key |
   | `READONLY_DB_URL` | Dedicated read-only-role URI from step 7 |

   Add your chosen email variables from step 5 too. Some API imports initialize
   agent modules, so both provider keys and the read-only URI must be present
   on the API as well as the worker.

   Generate the JWT secret on your laptop:

   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```

   If your system uses `python3`, substitute that command. Copy the output directly
   into Render's secure settings, not chat or GitHub. Keep the value stable across
   redeploys; changing it invalidates existing logins.

4. Create/deploy the service. If you have not created the read-only role yet, follow
   step 7 after its database migrations finish, then save that URI and redeploy.
5. Wait for the service to be live and visit:

   ```text
   https://YOUR-API.onrender.com/health
   ```

   Expect `{"status":"ok"}`. Also open `/docs`. A passing health check confirms
   API/database/Redis connectivity; it does not prove the worker or email works.

Do not set `TEST_DATABASE_URL` on production services and do not run pytest there.
The tests create/drop database tables. No `SUPABASE_ANON_KEY`, Supabase service-role
key, `OPENAI_API_KEY`, or frontend `VITE_*` variable is required on Render.

## 7. Create the agent's read-only database role

If you already have a dedicated read-only role, keep using it. Otherwise, after
the API migrations create the tables, open Supabase **SQL Editor** and run:

```sql
CREATE ROLE ticket_triage_reader LOGIN PASSWORD 'REPLACE_WITH_A_NEW_RANDOM_PASSWORD';
ALTER ROLE ticket_triage_reader SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE postgres TO ticket_triage_reader;
GRANT USAGE ON SCHEMA public TO ticket_triage_reader;
GRANT SELECT ON public.customers, public.transactions, public.tickets TO ticket_triage_reader;
```

Choose the password privately and replace the placeholder before running. Run
`CREATE ROLE` only once. This does not grant access to password hashes or
verification tokens. The AI SQL tool only needs the three listed tables.

Use the same session-pooler host/database from step 3, with the custom-role
username in Supabase's pooler format:

```text
READONLY_DB_URL=postgresql+psycopg://ticket_triage_reader.PROJECT_REF:ENCODED_READER_PASSWORD@SESSION_HOST:5432/postgres?sslmode=require
```

The `PROJECT_REF` is the same reference used in `postgres.PROJECT_REF` in your
Connect URI. If custom-role pooling is unavailable for your project, use its
supported direct connection and networking option; do not substitute the admin
URI as the agent's read-only connection.

The API migrations run before agent imports need this role. You can enter its
planned URI when creating the API, then create the role after migrations finish.
Alternatively, create it before deploying and apply the SELECT grants afterward.

## 8. Create the Render worker

1. Choose **New → Background Worker**, connecting the same GitHub repository.
2. Set:

   | Setting | Value |
   | --- | --- |
   | Name | `ticket-triage-worker` |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime | `Docker` |
   | Dockerfile Path | `./Dockerfile` |
   | Docker Build Context | `.` |
   | Docker Command | `bash deployment/start.sh worker` |
   | Region | Same as API and Redis |
   | Instance count | `1` to start |

3. Add the exact same values as the API for:

   ```text
   DATABASE_URL
   ASYNC_DATABASE_URL
   READONLY_DB_URL
   REDIS_URL
   GROQ_API_KEY
   COHERE_API_KEY
   APP_ENV=production
   ```

   The worker does not need the JWT secret or email variables for current code.
   An environment group can share the common values with the API.
4. Deploy after the API's migrations/checkpoint setup and read-only grants have
   completed. Check its logs for ARQ startup with `process_ticket` and
   `resume_ticket`. A worker has no public URL and needs no HTTP health-check path.

Do not use a cron job: this process must stay running to consume tickets.

## 9. Configure Vercel

1. Open your project → **Settings**.
2. Connect `VD400/ticket_triage` if needed, and use these settings:

   | Setting | Value |
   | --- | --- |
   | Production Branch | `main` |
   | Root Directory | `frontend` |
   | Framework Preset | `Vite` |
   | Install Command | `npm ci` |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |
   | Node.js Version | `24.x` |

3. Under **Environment Variables**, add this one application variable for
   **Production**:

   ```text
   VITE_API_URL=https://YOUR-API.onrender.com
   ```

4. Save it and **redeploy**. Vite embeds this value during the build; changing
   Vercel settings does not update an already-built deployment.
5. The included `frontend/vercel.json` lets direct visits to `/login`,
   `/customerComplaint`, and dashboard routes load the React app.

Do not add database passwords, JWT secrets, or Groq/Cohere/email keys to Vercel.
Everything in a `VITE_*` value is visible to visitors. If using preview deployments,
configure their backend/CORS separately; production settings allow the stable URL.

## 10. Create your employee login privately

If your existing Supabase database already contains your working employee account,
use it. Otherwise open the Render **API service → Shell** and run:

```bash
python -m deployment.create_user --username vishesh --email YOUR_EMAIL --role admin
```

Replace `YOUR_EMAIL`. Enter a strong password twice when prompted; characters are
hidden. The script refuses to overwrite an existing username/email. It never
resets or seeds the database.

For a trusted teammate, use a unique username/email and `--role agent` (can review
and resolve) or `--role viewer` (can view the dashboard). Employee accounts can see
shared complaint information, so customers should use the complaint page instead.
There is currently no working Team account-management page.

If Shell is unavailable on your plan, run the same module from your laptop's
`backend` folder using `uv run python -m deployment.create_user ...`, with your
ignored backend `.env` connected to this Supabase database. Do not run seed scripts.

## 11. Verify the whole deployment

1. Open your Vercel URL in an incognito/private browser.
2. Click the complaint action, enter an email address you control, and check the
   inbox (and spam). The verification link must point to your Vercel URL.
3. Open the link and submit a test complaint without personal or financial details.
4. In another browser/session, sign in with your employee account.
5. Confirm the ticket appears in Unprocessed Queue and Live Trace, then progresses
   to Awaiting Review or Needs Attention. Review/approve a draft and check Resolved.
6. Refresh a dashboard URL directly; it should load instead of showing Vercel 404.
7. Close your laptop's local API/worker/frontend terminals and repeat. The public
   workflow must still run; this proves it is using the hosted services.

If a ticket stays queued, check the Render worker and that both services use the
same Redis/database. If email fails, inspect the provider dashboard and sender
verification/SMTP access. If you see a browser CORS error, compare the exact
browser origin against API `CORS_ORIGINS`, then redeploy the API.

Both providers can auto-deploy after pushes to `main`; GitHub CI itself only runs
tests. Where Render supports it, choose deployment after checks pass. This initial
setup uses one API and one worker; coordinate releases with schema changes by
deploying the API migrations before a worker that needs the new schema.

## Scope of this deployment

This guide sets up a shared demonstration and real verification email. Complaint
submission requires the verified customer's unexpired email token. It does not
establish readiness for sensitive customer data: public endpoints still need
abuse/rate limits and a broader security review. Resolution-email delivery is
also a separate feature. Use synthetic complaints for the initial deployment test.
