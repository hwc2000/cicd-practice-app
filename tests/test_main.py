"""Tests for the CI/CD Practice App — realistic endpoint and business logic tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import build_item_record, calculate_total_price, reset_store

client = TestClient(app)


def setup_function():
    """Reset state before each test."""
    reset_store()


# --- Root & Health ---

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello cicd"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Price Calculation (unit tests for business logic) ---

def test_calculate_total_no_discount():
    """100원 × 3개, 할인 0% → 300.0"""
    assert calculate_total_price(100, 3, 0) == 300.0


def test_calculate_total_with_discount():
    """100원 × 2개, 할인 10% → 180.0 (not 220.0!)"""
    result = calculate_total_price(100, 2, 10)
    assert result == 180.0, f"Expected 180.0, got {result}"


def test_calculate_total_full_discount():
    """50원 × 4개, 할인 100% → 0.0"""
    assert calculate_total_price(50, 4, 100) == 0.0


def test_calculate_total_half_discount():
    """200원 × 1개, 할인 50% → 100.0"""
    assert calculate_total_price(200, 1, 50) == 100.0


def test_build_item_record_normalizes_name():
    item = build_item_record(
        item_id=7,
        name="   deluxe    widget   pro  ",
        price=100.0,
        quantity=2,
        discount_percent=10.0,
        total_price=180.0,
    )
    assert item == {
        "id": 7,
        "name": "Deluxe Widget Pro",
        "price": 100.0,
        "quantity": 2,
        "discount_percent": 10.0,
        "total_price": 180.0,
        "source": "api",
    }


# --- Item CRUD Endpoints ---

def test_create_item():
    response = client.post("/items", json={
        "name": "Widget",
        "price": 100.0,
        "quantity": 2,
        "discount_percent": 10.0,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 100.0
    assert data["quantity"] == 2
    assert data["discount_percent"] == 10.0
    assert data["total_price"] == 180.0  # 100 * 2 * 0.9
    assert data["source"] == "api"


def test_create_item_no_discount():
    response = client.post("/items", json={
        "name": "   gadget   ",
        "price": 50.0,
        "quantity": 3,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Gadget"
    assert data["total_price"] == 150.0  # 50 * 3 * 1.0
    assert data["source"] == "api"


def test_get_item():
    # Create first
    client.post("/items", json={"name": "Test Item", "price": 25.0})
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"


def test_get_item_not_found():
    response = client.get("/items/999")
    assert response.status_code == 404


def test_list_items():
    client.post("/items", json={"name": "Cheap", "price": 10.0})
    client.post("/items", json={"name": "Expensive", "price": 500.0})
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_items_with_min_price():
    client.post("/items", json={"name": "Cheap", "price": 10.0})
    client.post("/items", json={"name": "Expensive", "price": 500.0})
    response = client.get("/items?min_price=100")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Expensive"


# --- Validation ---

def test_create_item_invalid_price():
    response = client.post("/items", json={"name": "Bad", "price": -10.0})
    assert response.status_code == 422


def test_create_item_empty_name():
    response = client.post("/items", json={"name": "", "price": 10.0})
    assert response.status_code == 422
