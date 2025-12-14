# Backend Service (Django)

This directory hosts the Django backend that exposes the CARB catalytic converter API and blog CMS used by the frontend app. It now targets PostgreSQL for all environments via `DB_*` environment variables.

## Features

- REST API (Django REST Framework) for manufacturers, converters, and published blog posts
- Rich-text blog management from the Django admin (CKEditor-powered) with hero image uploads
- Media hosting for uploaded blog images (`MEDIA_ROOT = backend/media`)
- Search/filter helpers for makes, models, years, and database statistics
- Management commands for scraping and loading converter data (see `converters/management/commands/`)

## Tech Stack

- Python 3.12+
- Django 4.2 LTS
- Django REST Framework 3.14
- django-ckeditor 6.7
- PostgreSQL (development and production)

## Getting Started

1. **Create / activate a virtualenv** (example uses `venv`):

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\\Scripts\\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure PostgreSQL** by setting the following environment variables (create a `.env` file if you use `python-decouple`):

   ```bash
   DB_NAME=carb_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

4. **Apply migrations**:

   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** so you can access the Django admin and publish blogs:

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**:

   ```bash
   python manage.py runserver
   ```

   The API is served at `http://localhost:8000/api/` and the admin panel at `http://localhost:8000/admin/`.

## Media Files

- Uploaded blog hero images are stored in `backend/media/blog_images/`.
- Ensure `MEDIA_ROOT` is writable locally; in production, configure it to point to shared storage/CDN and serve `MEDIA_URL` accordingly.

## API Overview

| Endpoint | Description |
| --- | --- |
| `GET /api/converters/` | List CARB-approved converters with filters (year, make, model, EO, etc.). |
| `GET /api/converters/<id>/` | Converter detail.
| `GET /api/converters/makes/` | Unique makes.
| `GET /api/converters/models/?make=...` | Models for a make.
| `GET /api/converters/years/` | Min/max year range.
| `GET /api/converters/stats/` | Aggregate stats (counts, latest EO date).
| `GET /api/converters/filters/` | Combined filter metadata (makes, vehicle classes, manufacturers).
| `GET /api/manufacturers/` | Manufacturer list/details.
| `GET /api/blogs/` | List published blog posts (ordered by `published_at`).
| `GET /api/blogs/latest/` | Single most recent blog post (204 if none).
| `GET /api/blogs/<slug>/` | Blog post detail using slug routing.

All blog endpoints return `excerpt`, `content` (HTML from CKEditor), hero image URL, and metadata so the frontend can render previews and full articles.

## Scraping & Data Commands

`converters/management/commands/` contains helper commands to load or refresh CARB data. Common examples:

- `python manage.py scrape_website` – scrape the CARB aftermarket catalog website.
- `python manage.py scrape_by_eo --eo=<EO_NUMBER>` – fetch data for a specific Executive Order.
- `python manage.py clear_data` – remove converter/manufacturer records (use cautiously).

Each command includes `--help` detailing available flags. Review scripts before use to ensure they align with your deployment constraints.

## Celery Workers & Beat

Celery powers both manual scrapes triggered from the admin dashboard and the scheduled scrapes defined in `CELERY_BEAT_SCHEDULE`. To run them locally:

1. Make sure Redis is available at the URL referenced by `CELERY_BROKER_URL`/`CELERY_CACHE_BACKEND` (defaults to `redis://localhost:6379/0` and `/1`).  
2. Apply the result/beat migrations if you have not already:
   ```bash
   python manage.py migrate django_celery_results django_celery_beat
   ```
3. Start a worker (add `--concurrency` as needed):
   ```bash
   celery -A carb_backend worker -l info
   ```
4. In another terminal start Celery Beat so the periodic scraping/cleanup jobs fire automatically:
   ```bash
   celery -A carb_backend beat -l info
   ```

With worker + beat running, scraping tasks launched from the admin use Celery queues, and the nightly website scrape, weekly PDF scrape, and daily cleanup tasks execute automatically. Use the Django admin “Periodic Tasks” interface (provided by `django_celery_beat`) if you need to pause or adjust the schedule without editing settings.

## Environment Settings

Key settings live in `carb_backend/settings.py`:

- `ALLOWED_HOSTS` – update for production domains.
- `CORS_ALLOWED_ORIGINS` – extend to any additional frontend origins.
- `REST_FRAMEWORK` – pagination defaults (`PAGE_SIZE = 25`).
- `MEDIA_URL` / `MEDIA_ROOT` – adjust when serving media via CDN or S3.
- `DB_*` – configure PostgreSQL connection (name, user, password, host, port).

For production, remember to set `DEBUG = False` and configure a secure secret key through environment variables.

## Testing

- Run Django tests:

  ```bash
  python manage.py test
  ```

- Additional exploratory scripts for scraping verification live in the repo (`test_*.py`, `debug_*`). They are optional utilities and are not executed automatically.

## Frontend Integration

- The Vite/React frontend consumes this API at `http://localhost:8000/api` during development (see `frontend/src/services/api.js`).
- If you change the backend host/port, update `API_BASE_URL` in that file or inject it via environment variables.

## Deployment Checklist

1. Configure a production-ready database (e.g., Postgres).
2. Set up persistent media storage and ensure the app can write to it.
3. Run migrations and create an admin user.
4. Configure CORS and ALLOWED_HOSTS for the deployed frontend.
5. Serve static files via `collectstatic` or a CDN if needed.
6. Secure the admin (strong passwords, HTTPS, optional IP allowlists).

With these steps the backend is ready to power the catalytic converter search experience and the admin-managed blog.
