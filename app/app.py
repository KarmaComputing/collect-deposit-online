from flask import Flask, render_template, redirect, request, flash, url_for
import stripe
from dotenv import load_dotenv
import os
import time
import json
from pathlib import Path
from .email import (
    send_deposit_collected_email,
    send_booking_rescheduled_email,
    send_booking_cancelled_email,
)

load_dotenv(verbose=True)  # take environment variables from .env.
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
SHARED_MOUNT_POINT = os.getenv("SHARED_MOUNT_POINT")
SECRET_KEY = os.getenv("SECRET_KEY")


app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


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
    customer_name = request.form.get("name", None)
    customer_mobile = request.form.get("mobile", None)

    metadata = {
        "requested_product": requested_product,
        "requested_date": requested_date,
        "requested_time": requested_time,
        "customer_email": customer_email,
        "customer_name": customer_name,
        "customer_mobile": customer_mobile,
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
        metadata["timestamp"] = filename
        metadata["payment_method"] = payment_method
        metadata["setup_intent"] = setup_intent.id
        metadata["stripe_customer_id"] = stripe_customer.id
        metadata["deposit_status"] = "available_for_collection"
        fp.write(json.dumps(metadata))
    print(session.metadata)
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return redirect("/")


@app.route("/deposits")
def available_deposits():
    """List available deposits"""
    deposit_intents_path = Path(SHARED_MOUNT_POINT)
    deposit_intents = list(
        filter(lambda y: y.is_file(), deposit_intents_path.iterdir())
    )

    available_deposits = []
    for path in deposit_intents:
        with open(path) as fp:
            deposit_intent = json.loads(fp.read())
            if deposit_intent["deposit_status"] == "available_for_collection":
                available_deposits.append(deposit_intent)

    return render_template(
        "admin/deposits.html", available_deposits=available_deposits
    )  # noqa: E501


@app.route("/collected-deposits")
def collected_deposits():
    """List collected deposits"""
    deposit_intents_path = Path(SHARED_MOUNT_POINT)
    deposit_intents = list(
        filter(lambda y: y.is_file(), deposit_intents_path.iterdir())
    )

    collected_deposits = []
    for path in deposit_intents:
        with open(path) as fp:
            deposit_intent = json.loads(fp.read())
            if deposit_intent["deposit_status"] == "collected":
                collected_deposits.append(deposit_intent)

    return render_template(
        "admin/deposits-collected.html", collected_deposits=collected_deposits
    )  # noqa: E501


@app.route("/cancelled-bookings")
def cancelled_bookings():
    """List cancelled bookings"""
    deposit_intents_path = Path(SHARED_MOUNT_POINT)
    deposit_intents = list(
        filter(lambda y: y.is_file(), deposit_intents_path.iterdir())
    )

    deposits = []
    for path in deposit_intents:
        with open(path) as fp:
            deposit_intent = json.loads(fp.read())
            if deposit_intent["deposit_status"] == "cancelled":
                deposits.append(deposit_intent)

    return render_template(
        "admin/cancelled-bookings.html", deposits=deposits
    )  # noqa: E501


@app.route("/charge-deposit")
def charge_deposit():
    """Charge the request to pay a deposit."""
    payment_method_id = request.args.get("payment_method_id", None)
    stripe_customer_id = request.args.get("stripe_customer_id", None)
    filename = request.args.get("timestamp", None)

    stripe.api_key = STRIPE_API_KEY
    payment_intent = stripe.PaymentIntent.create(
        amount=1500,
        currency="gbp",
        payment_method_types=["card"],
        payment_method=payment_method_id,
        customer=stripe_customer_id,
    )
    # Confirm the PaymentIntent
    # Note: the PaymentIntent will automatically transation to succeeded if possible # noqa: E501
    # See https://stripe.com/docs/payments/intents#intent-statuses
    stripe.PaymentIntent.confirm(payment_intent)

    # Set deposit_status as collected
    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath, "r+") as fp:
        metadata = json.loads(fp.read())
        metadata["deposit_status"] = "collected"
        fp.seek(0)
        fp.write(json.dumps(metadata))
        fp.truncate()

    # Note: There may be no need to stripe.PaymentIntent.capture it manually
    # See https://stripe.com/docs/api/payment_intents/confirm?lang=python
    notify_deposit_collected(metadata)
    flash("Deposit taken &amp; notification email sent")
    return redirect(url_for("collected_deposits"))


def notify_deposit_collected(metadata):
    send_deposit_collected_email(metadata["customer_email"])


@app.route("/reschedule")
def reschedule_deposit():
    filename = request.args.get("timestamp", None)
    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath) as fp:
        metadata = json.loads(fp.read())

    return render_template("admin/reschedule.html", metadata=metadata)


@app.route("/save-rescheduled-deposit")
def save_rescheduled_desposit():
    requested_product = request.args.get("product")
    requested_time = request.args.get("time")
    requested_date = request.args.get("date")
    filename = request.args.get("timestamp", None)

    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath, "r+") as fp:
        metadata = json.loads(fp.read())
        metadata["requested_date"] = requested_date
        metadata["requested_time"] = requested_time
        metadata["requested_product"] = requested_product

        fp.seek(0)
        fp.write(json.dumps(metadata))
        fp.truncate()
    message = f"""Booking has been rescheduled to:
            Date: {metadata['requested_date']}
            Time: {metadata['requested_time']}
            Service/Product: {metadata['requested_product']}"""
    send_booking_rescheduled_email(
        to=metadata["customer_email"], content=message
    )  # noqa: E501
    flash("Reschedule complete")
    return redirect(url_for("reschedule_deposit", timestamp=filename))


@app.route("/cancel-booking")
def cancel_booking():
    filename = request.args.get("timestamp", None)

    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath, "r+") as fp:
        metadata = json.loads(fp.read())
        metadata["deposit_status"] = "cancelled"

        fp.seek(0)
        fp.write(json.dumps(metadata))
        fp.truncate()

    message = f"""Booking has been cancelled:
            Service/Product: {metadata['requested_product']}
            Date: {metadata['requested_date']}
            Time: {metadata['requested_time']}.
            Has now been cancelled."""
    send_booking_cancelled_email(
        to=metadata["customer_email"], content=message
    )  # noqa: E501
    flash("Booking has been cancelled")
    return redirect(url_for("available_deposits"))
