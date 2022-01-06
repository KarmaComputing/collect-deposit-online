from flask import (
    Flask,
    render_template,
    redirect,
    request,
    flash,
    url_for,
    session,
)  # noqa: E501
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
    send_deposit_refund_email,
)
from functools import wraps

load_dotenv(verbose=True)  # take environment variables from .env.
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
SHARED_MOUNT_POINT = os.getenv("SHARED_MOUNT_POINT")
SECRET_KEY = os.getenv("SECRET_KEY")


app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged-in" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    if request.form.get("password") == ADMIN_PASSWORD:
        session["logged-in"] = True
        return redirect(url_for("admin"))
    else:
        flash("Try again")
        return render_template("admin/login.html")


@app.route("/admin")
@login_required
def admin():
    return render_template("admin/dashboard.html")


@app.route("/")
def choose():
    return render_template("choose.html", products=get_products())

def get_products():
    products_path = Path(SHARED_MOUNT_POINT, "products")
    product_files = list(
        filter(lambda y: y.is_file(), products_path.iterdir())
    )  # noqa: E501
    products = []
    for path in product_files:
        with open(path) as fp:
            product = json.loads(fp.read())
            print(path)
            if validate_product(path):
                products.append(product)
            else:
                print("Product at " + str(path) + "is not active. Skipping.")
    return products

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


@app.route("/admin/deposits")
@login_required
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


@app.route("/admin/collected-deposits")
@login_required
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


@app.route("/admin/cancelled-bookings")
@login_required
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


@app.route("/admin/charge-deposit")
@login_required
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
        metadata["stripe_payment_intent_id"] = payment_intent.id
        fp.seek(0)
        fp.write(json.dumps(metadata))
        fp.truncate()

    # Note: There may be no need to stripe.PaymentIntent.capture it manually
    # See https://stripe.com/docs/api/payment_intents/confirm?lang=python
    notify_deposit_collected(metadata)
    flash("Deposit taken & notification email sent")
    return redirect(url_for("collected_deposits"))


def notify_deposit_collected(metadata):
    send_deposit_collected_email(metadata["customer_email"])


@app.route("/admin/reschedule")
@login_required
def reschedule_deposit():
    filename = request.args.get("timestamp", None)
    filePath = Path(SHARED_MOUNT_POINT, filename)
    with open(filePath) as fp:
        metadata = json.loads(fp.read())

    return render_template("admin/reschedule.html", metadata=metadata)


@app.route("/admin/save-rescheduled-deposit")
@login_required
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


@app.route("/admin/cancel-booking")
@login_required
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
    return redirect(url_for("cancelled_bookings"))


@app.route("/admin/refund-deposit")
@login_required
def refund_deposit():
    filename = request.args.get("timestamp", None)
    filePath = Path(SHARED_MOUNT_POINT, filename)

    with open(filePath, "r+") as fp:
        metadata = json.loads(fp.read())
        # Perform refund
        stripe.api_key = STRIPE_API_KEY
        try:
            stripe_refund = stripe.Refund.create(
                payment_intent=metadata["stripe_payment_intent_id"]
            )
            metadata["stripe_refund_id"] = stripe_refund.id
            metadata["deposit_status"] = "refunded"
            fp.seek(0)
            fp.write(json.dumps(metadata))
            fp.truncate()
            message = f"""Booking deposit refund started:
                    Service/Product: {metadata['requested_product']}
                    Date: {metadata['requested_date']}
                    Time: {metadata['requested_time']}.
                    Is being refunded."""
            send_deposit_refund_email(
                to=metadata["customer_email"], content=message
            )  # noqa: E501
            flash("Deposit has been refunded")
        except stripe.error.InvalidRequestError as error:
            if error.code == "charge_already_refunded":
                flash("Charge has already been refunded")
            else:
                raise

    return redirect(url_for("refunded_deposits"))


@app.route("/admin/refunded-deposits")
@login_required
def refunded_deposits():
    """List refunded deposits"""
    deposit_intents_path = Path(SHARED_MOUNT_POINT)
    deposit_intents = list(
        filter(lambda y: y.is_file(), deposit_intents_path.iterdir())
    )
    deposits = []
    for path in deposit_intents:
        with open(path) as fp:
            deposit_intent = json.loads(fp.read())
            if deposit_intent["deposit_status"] == "refunded":
                deposits.append(deposit_intent)

    return render_template(
        "admin/refunded-deposits.html", deposits=deposits
    )  # noqa: E501


@app.route("/admin/products", methods=["GET", "POST"])
@login_required
def products():
    """Products dashboard
    Links to add/update/delete products
    """
    products=get_products()
    if request.method == 'POST':
        if request.form.get('Delete') == 'Delete':
            try_remove = True
            product_id = request.form['product_id']
            if remove_product(product_id):
                is_removed = True
                return redirect(url_for("products"))  # noqa: E501
            else:
                is_removed = False
                return render_template("admin/products.html", products=get_products(), is_removed=is_removed, try_remove=try_remove)  # noqa: E501
        elif request.form.get('Edit') == 'Edit':
            product_id = request.form['product_id']
            new_name = request.form['new_name']
            if edit_product(product_id, new_name):
                edit_success(new_name)
    return render_template("admin/products.html", products=get_products())  # noqa: E501


@app.route("/admin/add-product")
@login_required
def add_product():
    """Add new product"""
    if request.args.get("product_name") and request.args.get("deposit_amount"):
        filename = str(time.time_ns())
        metadata = {}
        metadata["product_name"] = request.args.get("product_name")
        metadata["deposit_amount"] = request.args.get("deposit_amount")
        metadata["product_id"] = filename
        metadata["active"] = "1"
        filePath = Path(SHARED_MOUNT_POINT, "products", filename)
        Path.mkdir(filePath.parent, parents=True, exist_ok=True)
        with open(filePath, "w") as fp:
            fp.write(json.dumps(metadata))
        flash("Product saved.")
        return redirect(url_for("products"))
    return render_template("admin/add-product.html")  # noqa: E501

def edit_product(product_id, new_name):
    products_path = Path(SHARED_MOUNT_POINT, "products")
    product_files = list(
        filter(lambda y: y.is_file(), products_path.iterdir())
    )  # noqa: E501
    target_product = (str(products_path) + '/' + product_id)
    if validate_product(target_product):
        try:
            file = open(target_product, "r")
            jsonObject = json.load(file)
            file.close()
            jsonObject["product_name"] = str(new_name)
            file = open(target_product, "w")
            json.dump(jsonObject, file)
            file.close()
            return True
        except Exception as e:
            return False


@app.route("/admin/edit-success")
@login_required
def edit_success(product):
    time.sleep(1)
    return render_template("admin/edit-success.html",product=product)


def remove_product(product_id):
    products_path = Path(SHARED_MOUNT_POINT, "products")
    product_files = list(
        filter(lambda y: y.is_file(), products_path.iterdir())
    )  # noqa: E501
    target_product = (str(products_path) + '/' + product_id)
    if validate_product(target_product):
        print("FOUND PRODUCT FOR DELETION " + product_id + " @ " + (str(products_path) + '/' + product_id))
        try:
            file = open(target_product, "r")
            jsonObject = json.load(file)
            file.close()
            jsonObject["active"] = "0"
            file = open(target_product, "w")
            json.dump(jsonObject, file)
            file.close()
            return True
        except Exception as e:
            return False

def validate_product(target_product):
    if os.path.isfile(target_product):
        try:
            file = open(target_product, "r")
            jsonObject = json.load(file)
            file.close()
            if (jsonObject["active"] == "1"):
                return True
            else:
                return False
        except Exception as e:
            print(e)
    else:
        print("File " + target_product + "does not exist")
        return False
