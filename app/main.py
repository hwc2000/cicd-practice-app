from fastapi import FastAPI, HTTPException

from app.models import ItemCreate, ItemResponse
from app.services import create_item, get_item, list_items, reset_store

app = FastAPI(title="CI/CD Practice App")


@app.get("/")
def read_root():
    return {"message": "hello cicd"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item_endpoint(item: ItemCreate):
    """Create a new item with price calculation."""
    result = create_item(
        name=item.name,
        price=item.price,
        quantity=item.quantity,
        discount_percent=item.discount_percent,
    )
    return result


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item_endpoint(item_id: int):
    """Get a specific item by ID."""
    item = get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return item


@app.get("/items", response_model=list[ItemResponse])
def list_items_endpoint(min_price: float | None = None):
    """List all items with optional price filter."""
    return list_items(min_price=min_price)
