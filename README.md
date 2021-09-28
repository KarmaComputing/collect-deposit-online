# Collect deposits online quickly

- Display items available for booking
- Ask for time/date
- Setup payment for later (authorise payment so can collect once service confirmed)


## Setup

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # update with your stripe key
```

## Run

```
. venv/bin/activate
flask run
```

http://127.0.0.1:5001
