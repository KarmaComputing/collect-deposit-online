# Collect deposits online quickly

- Display items available for booking
- Ask for time/date
- Setup payment for later (authorise payment so can collect once service confirmed)


## Setup

Move app-data.json.example to your shared folder and rename it to app-data.json

### What is `app-data.json` for?
For storing app data which changes. It is used to store Stripe Connect data (e.g. Stripe Connect account id) and other data which is not stricly sensitive.

This should really be a database but havins a file is sufficient for now.
### What is `.env` for?
    - It contains the API keys and other secrets that are needed to run the app.
    - It is not stored in the repository, so you can move it to a shared folder and keep it private.

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cp ./app/.env.example ./app/.env  # update with your stripe key
```

## Run

```
. venv/bin/activate
export FLASK_DEBUG=1
python app.wsgi
```

http://127.0.0.1:5500/

## Notes 
When running locally, SHARED_MOUNT_POINT env can simply be set to any directory on your localhost because it's not running inside a container.

