# Portable image for any container host (Fly.io, Scaleway, a VPS...).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput

RUN useradd --create-home app
USER app

EXPOSE 8000
# Run `python manage.py migrate` and `python manage.py generate_editions`
# as a release step of your host before starting new versions.
CMD gunicorn django_project.wsgi --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 30
