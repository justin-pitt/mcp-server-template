import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

import health as health_module


@pytest.fixture(autouse=True)
def reset_ready():
    health_module._ready = False
    yield
    health_module._ready = False


def test_health_returns_503_before_ready():
    app = Starlette()
    health_module.attach_health_endpoints(app)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 503


def test_health_returns_200_after_ready():
    app = Starlette()
    health_module.attach_health_endpoints(app)
    health_module.set_ready()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_metrics_exposes_prometheus_format():
    app = Starlette()
    health_module.attach_health_endpoints(app)
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "# HELP" in resp.text or "# TYPE" in resp.text
