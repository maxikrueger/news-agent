# News Agent – Backend

FastAPI service with a background scheduler. See the [project README](../README.md) for setup
and [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the design.

```bash
pip install -e ".[dev]"
cp .env.example .env          # DATABASE_URL, SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload # API + docs at http://localhost:8000/docs
python -m app.scheduler --loop

ruff check . && ruff format --check . && mypy app && pytest
```
