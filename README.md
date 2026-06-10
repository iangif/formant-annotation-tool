# Formant Annotation Tool

A local application for annotating formant tracks from FastTrack candidate spectrograms.

## First-Time Setup

### 1. Install the project

Clone the repository and install dependencies:

```bash
git clone https://github.com/iangif/formant-annotation-tool
cd formant-annotation-tool
uv sync
```

### 2. Configure your annotator ID

Copy the example `.env.example` file:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
ANNOTATOR_ID=name
REMOTE_USER_HOST=username@oka

# Optional, for opening Praat
PRAAT_PATH=/Applications/Praat.app/Contents/MacOS/Praat
```

---

## Loading a Corpus

When you begin working on a corpus, run:

```bash
./scripts/load.sh ls_eng
```

Replace `ls_eng` with the corpus you want to load.

This command:

1. Downloads the required audio, TextGrid, image, and metadata files.
2. Updates your local SQLite database.

It is safe to run this command multiple times.

Run it again whenever:

* new batches are assigned to you;
* existing batch metadata has been updated;
* you want to ensure your local copy is current.

> [!NOTE]
> Each batch can range from 400 MB to 1 GB, so make sure your machine has space before loading in a corpus.
> For each corpus, allow at least 5 GB of free space. 

---

## Starting the App

Launch the annotation app:

```bash
./scripts/start_app.sh
```

Open your browser and navigate to:

```text
https://127.0.0.1:8000
```

---

## Updating Assignments

If you are assigned additional batches later:

```bash
./scripts/load.sh ls_eng
```

Run the same command again.

Only new or updated files will be synchronized.

Your existing annotations will remain unchanged.

---

## Updating the Tool

Before starting a new annotation session, make sure your local copy of the
tool is up to date:

```bash
git pull
uv sync
```

---

## Troubleshooting

### No batches appear

Run:

```bash
./scripts/load.sh <corpus>
```

and verify that:

* your `ANNOTATOR_ID` is correct;
* the corpus contains batches assigned to you.
