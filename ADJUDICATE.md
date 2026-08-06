# Adjudication GUI

The adjudication app runs on oka and can be accessed through an SSH tunnel.

## 1. Open the SSH tunnel

Run the following command on your local machine:

```bash
ssh -N -L 8001:127.0.0.1:8000 username@oka
```

Replace `username` with your oka username.

Keep this terminal open while using the adjudication GUI. The command may appear to do nothing after connecting; this is expected because it is maintaining the SSH tunnel.

## 2. Open the adjudication GUI

Navigate to the following address in your browser:

```text
http://127.0.0.1:8001/adjudicate
```

When finished, return to the terminal running the SSH tunnel and press `Ctrl+C` to close it.
