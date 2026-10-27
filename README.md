# Find Bananas 🍌

A daily 30-second game. Bananas appear for 5 seconds, you guess how many you
saw. Three rounds, more bananas each time. A new challenge goes live every day
at 12:00 (Paris time), the same for every player in the world.

- Play immediately, no account needed.
- Optional account (email, password and a public username) to keep your history.
- Score = total number of bananas you were off by (lower is better).
- After the game: your position among today's players, and a share button.
- In French and English: the browser's language is detected (French browsers
  get French, every other language gets English); a switch in the footer
  overrides it.

Design decisions, data model and scaling notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Before going live: [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md).

## Stack

Django 5.2 LTS · Python 3.12+ · PostgreSQL in production (SQLite locally) ·
WhiteNoise for static files · Pillow for the images · plain HTML/CSS/JS, no
front-end framework or build step.

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_DEBUG=1
python manage.py migrate
python manage.py generate_editions      # creates today's and the next 2 editions
python manage.py createsuperuser        # optional, for /admin/
python manage.py runserver
```

Open http://localhost:8000. Password-reset emails are printed in the terminal.

To replay locally, open a private window (a new guest) or delete your plays in
`/admin/`.

## Tests

```bash
DJANGO_DEBUG=1 python manage.py test
```

43 tests cover the daily schedule (including daylight-saving changes), image
generation, the server-side game rules, anti-cheat limits, ranking, accounts,
privacy of the history, rate limits and language detection.

## Translations

Every visible text goes through Django's translation system, including the
texts used by `game.js` (`find_bananas/strings.py`). French lives in
`locale/fr/LC_MESSAGES/django.po`; the compiled `django.mo` is committed so
deployment needs no extra tool.

After changing or adding a text (requires GNU gettext: `brew install gettext`
on macOS, `apt install gettext` on Linux):

```bash
DJANGO_DEBUG=1 python manage.py makemessages -l fr --ignore=".venv/*"
# edit locale/fr/LC_MESSAGES/django.po (empty msgstr = untranslated)
DJANGO_DEBUG=1 python manage.py compilemessages --ignore=".venv/*"
```

To add a language: add it to `LANGUAGES` in `django_project/settings.py`, then
run the same two commands with `-l <code>`.

## How the daily challenge is produced

`python manage.py generate_editions` creates the live edition and the next two
if they don't exist. It is safe to run any number of times. Run it at each
deploy (done by `render.yaml`) and, ideally, once a day from a scheduler.
If an edition is missing when someone opens the site, it is generated on the
spot (about 2 seconds for that one visitor), so a missed run never breaks the
game.

Change the switch time with `EDITION_HOUR` and `EDITION_TIMEZONE`.

## Configuration

All settings come from environment variables; see [.env.example](.env.example).
With `DJANGO_DEBUG=0` the app refuses to start without `DJANGO_SECRET_KEY`.

## Deploy (recommended: Render + Neon)

1. Create a free PostgreSQL database on [Neon](https://neon.com), in an EU
   region. Copy its connection string.
2. On [Render](https://render.com), create a **Blueprint** from this
   repository. It reads `render.yaml` (one web service, Frankfurt).
3. Fill the variables Render asks for: `DATABASE_URL` (Neon string), and the
   SMTP settings for password-reset emails (any provider with a free tier).
4. Deploy. Migrations and edition generation run before each release.
5. Add the custom domain `find-bananas.com` in Render, then update the DNS
   records it shows.

A `Dockerfile` is included to run the same app on any container host.

## Project layout

```
django_project/   settings (env-based), URLs
accounts/         custom user (email login), signup/login/reset/delete
find_bananas/
  editions.py     daily schedule + image generation
  game.py         game rules enforced server-side
  scoring.py      score and percentile
  players.py      guests, accounts, IP fingerprint
  ratelimit.py    per-IP rate limits
  strings.py      texts used by the JavaScript (translatable)
  views.py        pages + JSON API
  assets/         banana sprite used to draw images (not public)
  static/         CSS, JS, font (Cherry Bomb One, OFL), icons
  templates/
locale/fr/        French translations
```
