# Formant Annotation Tool

A local application for annotating formant tracks from FastTrack candidate spectrograms.

## First-Time Setup

> [!IMPORTANT]
> This project requires a **POSIX-compliant environment**. It natively supports macOS and Linux. Windows users must use **WSL**, which can be installed with `wsl --install`.

### 1. Install the project

Clone the repository and install its dependencies:

```bash
git clone https://github.com/iangif/formant-annotation-tool
cd formant-annotation-tool
uv sync
```

### 2. Configure your annotator ID

Copy the example environment file:

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

Replace `name` with your annotator ID and `username` with your oka username.

---

## Loading or Updating a Corpus

When you begin working on a corpus, run:

```bash
./scripts/load.sh ls_eng
```

Replace `ls_eng` with the corpus you want to load.

This command:

1. Downloads the audio, TextGrid, image, and metadata files for the batches assigned to you.
2. Adds new corpus, batch, and token information to your local SQLite database.

It is safe to run this command multiple times. Your existing annotations will remain unchanged.

Run it again whenever:

- new batches are assigned to you;
- existing batch files or metadata are updated; or
- you want to make sure your local copy is current.


> [!NOTE]
> Each batch can range from approximately **400 MB to 1 GB**. Allow at least **5 GB of free space per corpus** before loading it.

---

## Starting the App

> [!TIP]
> Before starting a new annotation session, it is a good idea to update the tool:
>
> ```bash
> git pull
> uv sync
> ```

Launch the annotation app:

```bash
./scripts/start_app.sh
```

Then open the following address in your browser:

```text
http://127.0.0.1:8000
```

Keep the terminal running while you use the app. To stop the app, return to the terminal and press `Ctrl+C`.

---

## Uploading Snapshots

When you are ready to upload your current annotations for a corpus and batch, run:

```bash
./scripts/upload.sh <corpus> <batch>
```

For example:

```bash
./scripts/upload.sh ls_eng batch1
```

This command:

1. Creates a snapshot containing the latest annotations and notes for the selected corpus and batch.
2. Uploads the snapshot to your annotator-specific directory on oka.
3. Deletes the temporary local upload snapshot after the transfer succeeds.

You can run the command again later to replace the remote snapshot with your latest annotation state. Your main local annotation database is not deleted or modified by the upload.

> [!IMPORTANT]
> Make sure `ANNOTATOR_ID` and `REMOTE_USER_HOST` are configured correctly in `.env` before uploading.

---

## Troubleshooting

### No batches appear

Run:

```bash
./scripts/load.sh <corpus>
```

Then verify that:

- your `ANNOTATOR_ID` is correct; and
- the corpus contains batches assigned to you.

### Upload fails

Verify that:

- `REMOTE_USER_HOST` uses the format `username@oka`;
- you can connect to oka through SSH; and
- the corpus and batch names are correct.

You can rerun the upload command after correcting the problem. The temporary snapshot is removed only after a successful upload.

### Open Praat failure

If you are a Windows user running the app through WSL, you may need to reinstall Praat:

```bash
sudo apt update
sudo apt install praat
```

If errors continue, manually add the path to the Praat executable in `.env`.

The Praat executable must be installed on the same operating system that is running this project.

---

## Adjudication

Instructions for opening the adjudication interface are available in [ADJUDICATE.md](ADJUDICATE.md).
