from flask import Flask, render_template, redirect, request
import stripe
from dotenv import load_dotenv
import os
import time
import json
from pathlib import Path

load_dotenv(verbose=True)  # take environment variables from .env.
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
SHARED_MOUNT_POINT = os.getenv("SHARED_MOUNT_POINT")


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

    requested_product = request.form.get("product")
    requested_time = request.form.get("time")
    requested_date = request.form.get("date")
    customer_email = request.form.get("email", None)

    metadata = {
        "requested_product": requested_product,
        "requested_date": requested_date,
        "requested_time": requested_time,
        "customer_email": customer_email,
    }

    stripe_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="setup",
        customer_email=customer_email,
        success_url=f"{request.host_url}/stripe-success?session_id={{CHECKOUT_SESSION_ID}}",  # noqa: E501
        cancel_url=f"{request.host_url}/cancel",
        metadata=metadata,
    )
    return redirect(stripe_session.url)


@app.route("/stripe-success")
def stripe_success():
    stripe.api_key = STRIPE_API_KEY
    stripe_session_id = request.args.get("session_id")
    session = stripe.checkout.Session.retrieve(stripe_session_id)
    print(session)
    setup_intent = stripe.SetupIntent.retrieve(session.setup_intent)
    # Create customer
    stripe_customer = stripe.Customer.create(
        email=session.metadata["customer_email"]
    )  # noqa: E501
    # Attach PaymentMethod to a customer
    payment_method = setup_intent.payment_method
    stripe.PaymentMethod.attach(
        payment_method,
        customer=stripe_customer,
    )
    filename = str(time.time_ns())
    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath, "w") as fp:
        metadata = session.metadata
        metadata["payment_method"] = payment_method
        metadata["setup_intent"] = setup_intent.id
        fp.write(json.dumps(metadata))
    print(session.metadata)
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return redirect("/")
