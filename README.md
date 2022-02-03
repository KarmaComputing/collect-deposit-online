# Collect deposits online quickly

- Display items available for booking
- Ask for time/date
- Setup payment for later (authorise payment so can collect once service confirmed)


# Definitions / Naming / nomenclature

- **product** - An item or service

- **requested_product** - A product booking *request* by the customer stating their *wish* to book a product at a given date/time.
  - Note a `requested_product` may be rejected (e.g. if not available)
  - Note a `requested_product` is not confirmed until the admin has confirmed it
  - Note a `requested_product` may require a deposit (though not all products require a deposit)

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
cp ./app/.env.example ./app/.env  # Read the example before copying!
# Update .env variable "STRIPE_API_KEY" with your Stripe "Secret key"
```

## Run

```
. venv/bin/activate
export FLASK_DEBUG=1
python app.wsgi
```

## How to run tests
```
. venv/bin/activate
python -m pytest -vv
```
or

```
./run-tests.sh
```

> Note the `-vv` gives more usefule verbose output (needed
  when tests fail. Wish this was the default personally!)

Example running the tests:
```
(venv) (base) (add-tests)$ python -m pytest
====================== test session starts ======================
platform linux -- Python 3.9.5, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
rootdir: /home/username/collect-deposit-online
collected 1 item

tests/test_app.py .                                       [100%]

======================= 1 passed in 0.20s =======================
```

### Where are the tests?

In the `tests` directory.

http://127.0.0.1:5500/

## Notes 
When running locally, SHARED_MOUNT_POINT env can simply be set to any directory on your localhost because it's not running inside a container.

