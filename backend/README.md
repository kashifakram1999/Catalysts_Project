# Backend Service (Django)

This directory hosts the Django 5 project that exposes the CARB catalytic converter API and blog CMS used by the frontend app. It ships with a SQLite database by default, but any Django-supported database can be configured through the standard `DATABASES` setting.

## Features

- REST API (Django REST Framework) for manufacturers, converters, and published blog posts
- Rich-text blog management from the Django admin (CKEditor-powered) with hero image uploads
- Media hosting for uploaded blog images (`MEDIA_ROOT = backend/media`)
- Search/filter helpers for makes, models, years, and database statistics
- Management commands for scraping and loading converter data (see `converters/management/commands/`)

## Tech Stack

- Python 3.12+
- Django 5.0.1
- Django REST Framework 3.14
- django-ckeditor 6.7
- SQLite (development default)

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

3. **Apply migrations**:

   ```bash
   python manage.py migrate
   ```

4. **Create a superuser** so you can access the Django admin and publish blogs:

   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server**:

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

## Environment Settings

Key settings live in `carb_backend/settings.py`:

- `ALLOWED_HOSTS` – update for production domains.
- `CORS_ALLOWED_ORIGINS` – extend to any additional frontend origins.
- `REST_FRAMEWORK` – pagination defaults (`PAGE_SIZE = 25`).
- `MEDIA_URL` / `MEDIA_ROOT` – adjust when serving media via CDN or S3.

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
