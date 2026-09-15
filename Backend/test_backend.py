import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("[PASS] Health check passed:", data)


def test_get_products():
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    print(f"[PASS] Products list passed: found {len(data)} products")


def test_get_product_detail():
    response = client.get("/api/products/1")
    assert response.status_code == 200
    data = response.json()
    assert "product" in data
    assert "standards" in data
    assert "requirements" in data
    print("[PASS] Product details (product_id=1) passed:", data["product"]["product_name"])


def test_get_product_compliance():
    response = client.get("/api/products/1/compliance")
    assert response.status_code == 200
    data = response.json()
    assert "readiness_percentage" in data
    assert "applicable_standards" in data
    print(f"[PASS] Compliance status passed: Readiness = {data['readiness_percentage']}%")


def test_get_alerts():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"[PASS] Alerts passed: {len(data)} alerts retrieved")


def test_get_standards():
    response = client.get("/api/standards")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    print(f"[PASS] Standards search passed: {len(data)} standards retrieved")


def test_get_dashboard_stats():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_products" in data
    assert "active_standards" in data
    print("[PASS] Dashboard stats passed:", data)


def test_chat():
    payload = {
        "message": "What BIS standards apply to my smart TV?",
        "product_id": 1,
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
    print("[PASS] Chat assistant passed!")
    print("  Answer snippet:", data["answer"][:120], "...")
    print("  Sources:", data["sources"])


if __name__ == "__main__":
    print("Starting FastAPI endpoint tests...")
    test_health()
    test_get_products()
    test_get_product_detail()
    test_get_product_compliance()
    test_get_alerts()
    test_get_standards()
    test_get_dashboard_stats()
    test_chat()
    print("\nALL FASTAPI BACKEND TESTS PASSED SUCCESSFULLY!")
