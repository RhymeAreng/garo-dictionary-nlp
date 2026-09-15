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



def test_update_entry():
    """Confirm PUT updates only the fields provided, leaving others intact."""

    create_response = client.post("/entries", json={
        "headword": "Update-test",
        "part_of_speech": "n",
        "definition": "Original definition",
        "direction": "garo_to_english",
        "source_file": "test.pdf",
        "source_page": 1
    })
    entry_id = create_response.json()["id"]

    update_response = client.put(f"/entries/{entry_id}", json={
        "definition": "Updated definition"
    })
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["definition"] == "Updated definition"
    assert data["headword"] == "Update-test"  # unchanged

def test_delete_entry():
    """Confirm DELETE removes the entry, and it's gone afterward."""

    create_response = client.post("/entries", json={
        "headword": "Delete-test",
        "part_of_speech": "n",
        "definition": "To be deleted",
        "direction": "garo_to_english",
        "source_file": "test.pdf",
        "source_page": 1
    })
    entry_id = create_response.json()["id"]

    delete_response = client.delete(f"/entries/{entry_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/entries/{entry_id}")
    assert get_response.status_code == 404

def test_update_nonexistent_entry():
    """Confirm updating a nonexistent entry returns 404, not a crash."""
    
    response = client.put("/entries/999999", json={"definition": "doesn't matter"})
    assert response.status_code == 404