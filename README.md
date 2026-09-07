# DecalVault

Internal tool for Hunter Engineering Company. Lets techs and staff look up
equipment decals by part number, model, or category instead of digging
through PDFs on the documentation portal.

Equipment hierarchy is Category → Model → Decal, with decals applying to
multiple models as the normal case (e.g. one warning decal shared across a
whole tire changer line). A decal can also carry subcategory qualifiers
(e.g. "Adapter", "Sensor"), each scoped to a single category for decals
that span more than one. Both a card grid and a sortable table view are
available for browsing.

The search box is a single free-text field, not one field per column: it
looks across part number, model, description, category, language, and
notes at once, normalizes punctuation/spacing so `175-1042-2`, `175 1042
2`, and `17510422` all match, tolerates typos in descriptive text (never in
part/model numbers), and ranks results by relevance rather than database
order. A multi-word search requires every word to match somewhere (so
`tcx50 shock` narrows to decals that are both TCX50 and about a shock
hazard), with a bonus when the words also appear together as a phrase.
Scoring rules live in `app/search.py`. Existing filters (model, category,
language, status) still compose with a search.

## Stack

- Flask + Flask-SQLAlchemy + SQLite
- Jinja2 templates, Bulma 1.x compiled from Sass with Hunter brand colors
- No JS framework - vanilla JS for the small amount of interactivity needed

## Local setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app creates its SQLite database and upload folder on first run under
`instance/` and `app/static/uploads/`. Visit `http://127.0.0.1:5000`, and
log in at `/login` with the staff password (defaults to `hunter-decals`
locally - see `.env.example` to set a real one).

## Environment variables

See `.env.example` for the full list with descriptions. At minimum, set
`SECRET_KEY` and `DECAL_VAULT_STAFF_PASSWORD` before this runs anywhere
other than your own machine.

## Rebuilding CSS

Bulma is compiled from Sass with Hunter's brand colors, not pulled from a
CDN. After editing `app/static/css/custom.scss`, rebuild with:

```
brew install dart-sass   # first time only
python build_css.py
```

Don't hand-edit `app/static/css/bulma-hunter.css` - it's generated.

## Deployment notes

The app runs under gunicorn (see `Procfile`) behind a reverse proxy or
tunnel of your choice. Before this is reachable anywhere beyond a single
machine, set:

- `SECRET_KEY` - a real random value
- `DECAL_VAULT_STAFF_PASSWORD` - a real password
- `SESSION_COOKIE_SECURE=1` - once served over HTTPS

The SQLite database and uploaded images are stored on local disk
(`instance/` and `UPLOAD_FOLDER`), so wherever this runs, that storage
needs to persist across restarts and redeploys - most free-tier hosting
platforms don't keep local disk around by default, so plan accordingly
(a persistent volume, or a managed database for the former).

## Scope

This is a proof-of-concept covering decals only - no bulk import, no
multi-user auth (a single shared staff password gates upload/edit/delete),
no linking to full manuals. The data model lives in `app/models.py`:
`EquipmentModel` (category + name) and `Decal` are many-to-many, with
`DecalSubcategory` holding the per-category qualifiers.
