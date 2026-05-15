# Formant Annotation Tool

A lightweight local web app for validating pre-generated formant candidate spectrograms.

---

# Requirements

Install the following before starting:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

# Clone the Repository

```bash
git clone https://github.com/iangif/formant-annotation-tool
cd formant-annotation-tool
```

---

# Initial Setup

## 1. Create a local `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Then edit `.env` if needed:

```text
ANNOTATOR_ID=ian
FORMANT_DB_URL=sqlite:///./data/ian.sqlite
```

Each annotator shold use their own SQLite database file. For now, since token assignments are limited, don't edit `.env`.

## 2. Install dependencies

```bash
uv sync
```

---

## 3. Initialize the local database

Run:

```bash
./scripts/setup_local_db.sh
```

This will:

- create the SQLite database
- initialize the database tables
- import tokens (pilot for now)
- import token assignments (pilot for now)

---

# Start the App

Run:

```bash
./scripts/start_app.sh
```

Then open:

```text
https://127.0.0.1:8000
```

in your browser.

---

# Annotation Controls

| Action | Input |
|---|---|
| Auto-accept winner | `Space` |
| Save current F1–F4 fields | `Enter` |
| Bad token | `B` |
| Needs correction | `X` |
| Select panel | Click panel |
| Select and immediately save panel | `Shift + Click` |

---

# Development Notes

The app currently uses:

- FastAPI
- SQLAlchemy
- SQLite
- Jinja2
- Vanilla JavaScript
- Bootstrap

Each annotator uses a separate local SQLite database.

---

# Useful Commands

## Rebuild the database

```bash
rm data/*.sqlite
./scripts/setup_local_db.sh
```