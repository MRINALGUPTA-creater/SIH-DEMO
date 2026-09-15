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


def test_create_product():
    payload = {
        "product_name": "Solar Photovoltaic Inverter",
        "model_number": "SPI-5KW-2026",
        "category_code": "ELEC",
        "manufacturer_name": "Surya Power Systems Ltd",
        "country_of_origin": "India",
        "description": "5kW Grid-tie solar inverter"
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "product_id" in data
    print(f"[PASS] Product creation passed: created product ID {data['product_id']}")


def test_get_product_requirements():
    response = client.get("/api/products/1/requirements")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    print(f"[PASS] Product requirements passed: {len(data)} requirements found")


def test_get_product_alerts():
    response = client.get("/api/products/1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"[PASS] Product alerts passed: {len(data)} alerts found")


def test_search_standards_endpoint():
    response = client.get("/api/standards/search?q=13252")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "13252" in data[0]["standard_number"]
    print(f"[PASS] Standards dedicated search passed: matched {data[0]['standard_number']}")


def test_resolve_alert():
    response = client.post("/api/alerts/4/resolve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RESOLVED"
    print("[PASS] Alert resolution passed: Alert 4 resolved")


def test_clarifying_questions_chat():
    payload = {"message": "I want BIS certification for my product"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["clarifying_questions"]) > 0
    assert len(data["suggested_prompts"]) > 0
    print("[PASS] AI clarifying questions passed! Questions generated:", len(data["clarifying_questions"]))


def test_verify_licence():
    response = client.get("/api/consumer/verify-licence?licence_number=CRS-2026-DEL-0042")
    assert response.status_code == 200
    data = response.json()
    assert "certificate_number" in data
    assert data["status"] == "ACTIVE"
    print(f"[PASS] Licence verification passed: {data['certificate_number']} is {data['status']}")


def test_submit_complaint():
    payload = {
        "consumer_name": "Rohan Sharma",
        "consumer_email": "rohan@example.com",
        "consumer_phone": "9876543210",
        "product_name": "Electric Immersion Rod",
        "brand_or_model": "ShockSafe 1500W",
        "licence_number": "CM/L-1234567",
        "complaint_type": "SUBSTANDARD_PRODUCT",
        "description": "Heating element failed dielectric test and caused shock hazard."
    }
    response = client.post("/api/consumer/complaint", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "complaint_number" in data
    assert data["status"] == "REGISTERED"
    print(f"[PASS] Complaint submission passed: Ref {data['complaint_number']}")


def test_rag_ingest():
    payload = {
        "text": "Indian Standard IS 16102 specifies safety requirements for self-ballasted LED lamps for general lighting services.",
        "source_id": "IS 16102 (Part 1)"
    }
    response = client.post("/api/rag/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    print(f"[PASS] RAG ingestion passed: {data['ingested_chunks']} chunks ingested for {data['source_id']}")


if __name__ == "__main__":
    print("Starting FastAPI endpoint tests...")
    test_health()
    test_get_products()
    test_get_product_detail()
    test_get_product_compliance()
    test_get_product_requirements()
    test_get_product_alerts()
    test_get_alerts()
    test_resolve_alert()
    test_get_standards()
    test_search_standards_endpoint()
    test_get_dashboard_stats()
    test_chat()
    test_clarifying_questions_chat()
    test_verify_licence()
    test_submit_complaint()
    test_create_product()
    test_rag_ingest()
    print("\nALL FASTAPI BACKEND TESTS PASSED SUCCESSFULLY!")

