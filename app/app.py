from flask import Flask, render_template, redirect, request
import stripe
from dotenv import load_dotenv
import os

load_dotenv(verbose=True)  # take environment variables from .env.
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")


app = Flask(__name__)


@app.route("/")
def choose():
    return render_template("choose.html", locale="es")


@app.route("/request-date-time", methods=["GET", "POST"])
def set_date_time():
    return render_template("request-date-time.html")


@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    return render_template("deposit.html")


@app.route("/create-checkout-session", methods=["GET", "POST"])
def create_checkout_session():
    stripe.api_key = STRIPE_API_KEY

    stripe_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="setup",
        success_url=f"{request.host_url}/stripe-success?session_id={{CHECKOUT_SESSION_ID}}",  # noqa: E501
        cancel_url=f"{request.host_url}/cancel",
    )
    return redirect(stripe_session.url)


@app.route("/stripe-success")
def stripe_success():
    stripe.api_key = STRIPE_API_KEY
    stripe_session_id = request.args.get("session_id")
    session = stripe.checkout.Session.retrieve(stripe_session_id)
    print(session)
    # TODO store: session.setup_intent in database
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return redirect("/")
