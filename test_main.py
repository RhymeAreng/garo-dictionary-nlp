from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_entry():
    response = client.post("/entries", json={
        "headword": "Wrong-word",
        "part_of_speech": "n",
        "definition": "A test definition",
        "direction": "garo_to_english",
        "source_file": "test.pdf",
        "source_page": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert data["headword"] == "Wrong-word"
    assert data["needs_review"] is True
    assert "id" in data

def test_read_entry():
    """
    Create read entry to test
    """
    create_response = client.post("/entries", json={
        "headword": "Another-word",
        "part_of_speech": "v",
        "definition": "Another test definition",
        "direction": "english_to_garo",
        "source_file": "test.pdf",
        "source_page": 2
    })
    entry_id = create_response.json()["id"]

    # Now read it back
    read_response = client.get(f"/entries/{entry_id}")
    assert read_response.status_code == 200
    assert read_response.json()["headword"] == "Another-word"

def test_read_nonexistent_entry():
    response = client.get("/entries/999999")
    assert response.status_code == 404