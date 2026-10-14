# Deployment

The backend image runs `alembic upgrade head` before starting uvicorn and honours the `PORT`
variable, so it works on most container platforms (Railway, Render, Fly.io) without changes.

## Backend

1. Provision PostgreSQL and note its connection string.
2. Deploy `backend/` as a Docker service with these variables:

   | Variable | Required | Notes |
   |---|---|---|
   | `DATABASE_URL` | yes | `postgresql://USER:PASS@HOST:5432/DB` |
   | `SECRET_KEY` | yes | ≥ 32 random characters (`openssl rand -base64 32`) |
   | `ALLOWED_ORIGINS` | yes | URL of the deployed dashboard, comma-separated if several |
   | `ENVIRONMENT` | yes | `production` (enables `Secure` / `SameSite=None` cookies) |
   | `GROQ_API_KEY` | no | enables LLM summaries |
   | `SENDGRID_API_KEY` | no | enables the e-mail channel |
   | `SENDGRID_FROM_EMAIL` | with SendGrid | sender address verified in your SendGrid account |

3. Add a second service from the same image for the scheduler with the start command
   `python -m app.scheduler --loop`, or trigger `python -m app.scheduler` from the platform's
   cron feature every minute.
4. Check `GET /api/health` returns `{"status": "ok"}`.

## Frontend

Deploy `frontend/` to Vercel (or as the provided Docker image) with:

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | public URL of the backend; baked in at build time |
| `NEXTAUTH_URL` | public URL of the dashboard |
| `NEXTAUTH_SECRET` | random secret (`openssl rand -base64 32`) |

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic check   # must report "No new upgrade operations detected"
```
