from app.app import app

import pytest


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def login(client, password="changeme"):
    return client.post(
        "/login", data=dict(password=password), follow_redirects=True
    )  # noqa: E501


def test_get_homepage_200_ok(client):
    req = client.get("/")
    assert req.status_code == 200


def test_get_login_200_ok(client):
    req = client.get("/login")
    assert req.status_code == 200


def test_post_login_200_ok(client):
    req = login(
        client,
    )
    assert b"Deposit Collection System" in req.data


def test_get_reqest_date_time_200_ok(client):
    req = client.get("/request-date-time")
    assert req.status_code == 200


def test_get_deposit_200_ok(client):
    req = client.get("/deposit")
    assert req.status_code == 200


def test_get_create_checkout_session_302_redirect(client):
    req = client.get("/create-checkout-session")
    assert req.status_code == 302


def test_get_cancel_302_redirect(client):
    req = client.get("/cancel")
    assert req.status_code == 302


def test_get_admin_deposits_302_redirect(client):
    req = client.get("/admin/deposits")
    assert req.status_code == 302


def test_get_admin_collected_deposits_302_redirect(client):
    req = client.get("/admin/collected-deposits")
    assert req.status_code == 302


def test_get_admin_cancelled_bookings_302_redirect(client):
    req = client.get("/admin/cancelled-bookings")
    assert req.status_code == 302


def test_get_admin_reschedule_302_redirect(client):
    req = client.get("/admin/reschedule")
    assert req.status_code == 302


def test_get_admin_save_rescheduled_deposit_302_redirect(client):
    req = client.get("/admin/save-rescheduled-deposit")
    assert req.status_code == 302


def test_get_admin_cancel_booking_302_redirect(client):
    req = client.get("/admin/cancel-booking")
    assert req.status_code == 302


def test_get_admin_refund_deposit_302_redirect(client):
    req = client.get("/admin/refund-deposit")
    assert req.status_code == 302


def test_get_admin_charge_deposit_302_redirect(client):
    req = client.get("/admin/charge-deposit")
    assert req.status_code == 302


def test_get_admin_refunded_deposits_302_redirect(client):
    req = client.get("/admin/refunded-deposits")
    assert req.status_code == 302


def test_get_admin_302_redirect(client):
    req = client.get("/admin")
    assert req.status_code == 302
