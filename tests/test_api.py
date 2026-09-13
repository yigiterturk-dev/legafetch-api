"""LegaFetch API test paketi. Calistirmadan once dev uvicorn'u durdurun (Qdrant dosya kilidi)."""
import time

import pytest
from fastapi.testclient import TestClient

import main
from main import app, check_rate_limit, _hits

import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("X_API_KEY", "")
if not API_KEY:
    pytest.skip("X_API_KEY .env dosyasinda tanimli olmali", allow_module_level=True)

KEY = {"X-API-Key": API_KEY}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# --- Kimlik ---
def test_wrong_api_key_401(client):
    r = client.post("/api/chat", json={"query": "test"}, headers={"X-API-Key": "yanlis"})
    assert r.status_code == 401


def test_verify_valid_license(client):
    r = client.post("/api/auth/verify", json={"license_key": API_KEY})
    assert r.status_code == 200 and r.json()["valid"] is True


def test_verify_invalid_license(client):
    r = client.post("/api/auth/verify", json={"license_key": "hacked"})
    assert r.status_code == 401


# --- Health / jurisdiction ---
def test_health_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_jurisdiction_filter_tr(client):
    r = client.post("/api/chat", json={"query": "anonim şirket sermaye", "jurisdiction": "TR"}, headers=KEY)
    assert r.status_code == 200
    assert r.json()["sources"], "TR filtresi bos dondu"
    assert all(s["jurisdiction"] == "TR" for s in r.json()["sources"])


def test_jurisdiction_filter_es(client):
    r = client.post("/api/chat", json={"query": "sociedad anonima capital", "jurisdiction": "ES"}, headers=KEY)
    assert r.status_code == 200
    assert all(s["jurisdiction"] == "ES" for s in r.json()["sources"])


def test_chat_composition_is_numbered(client):
    r = client.post("/api/chat", json={"query": "sermaye", "jurisdiction": "TR"}, headers=KEY)
    assert "Toplam" in r.json()["text"] and "[1]" in r.json()["text"]


# --- Stats dürüstlük ---
def test_admin_stats_are_real_counters(client):
    r = client.get("/api/admin/stats", headers=KEY)
    d = r.json()
    assert d["total_queries"] == sum(d["breakdown"].values())
    assert d["active_api_keys"] == 1  # sahte 42 degil


# --- Rate limiter ---
def test_rate_limit_sliding_window():
    _hits.clear()
    old = main.RATE_LIMIT_PER_MIN
    main.RATE_LIMIT_PER_MIN = 5
    try:
        results = [check_rate_limit("10.1.0.1") for _ in range(6)]
        assert results[:5] == [True] * 5
        assert results[5] is False
        assert check_rate_limit("10.1.0.2") is True
    finally:
        main.RATE_LIMIT_PER_MIN = old
        _hits.clear()


def test_rate_limit_window_expiry():
    _hits.clear()
    old = main.RATE_LIMIT_PER_MIN
    main.RATE_LIMIT_PER_MIN = 1
    try:
        assert check_rate_limit("10.1.0.3") is True
        assert check_rate_limit("10.1.0.3") is False
        _hits["10.1.0.3"][0] = time.time() - 61
        assert check_rate_limit("10.1.0.3") is True
    finally:
        main.RATE_LIMIT_PER_MIN = old
        _hits.clear()
