from app.app import app

import pytest


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_homepage_200_ok(client):
    req = client.get("/")
    assert req.status_code == 200
