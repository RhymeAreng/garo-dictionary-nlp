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



def test_list_entries_respects_limit():
    """Confirm the limit parameter caps the number of returned entries."""

    # Create a few entries to ensure there's enough data to page through
    for i in range(5):
        client.post("/entries", json={
            "headword": f"Pagination-test-{i}",
            "part_of_speech": "n",
            "definition": "test",
            "direction": "garo_to_english",
            "source_file": "test.pdf",
            "source_page": 1
        })

    response = client.get("/entries?limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_list_entries_filters_by_direction():
    """Confirm the direction filter only returns matching entries."""

    client.post("/entries", json={
        "headword": "English-direction-test",
        "part_of_speech": "n",
        "definition": "test",
        "direction": "english_to_garo",
        "source_file": "test.pdf",
        "source_page": 1
    })

    response = client.get("/entries?direction=english_to_garo&limit=50")
    assert response.status_code == 200
    data = response.json()
    assert all(entry["direction"] == "english_to_garo" for entry in data)
    

def test_list_entries_offset_past_end_returns_empty():
    """Confirm an offset beyond available entries returns an empty list, not an error."""

    response = client.get("/entries?offset=999999")
    assert response.status_code == 200
    assert response.json() == []



def test_needs_review_prioritizes_apostrophe_flags():
    """Confirm apostrophe-flagged entries surface before other flagged entries."""
    client.post("/entries", json={
        "headword": "Suspicious-hyphen-test", "part_of_speech": "n",
        "definition": "test", "direction": "garo_to_english",
        "source_file": "test.pdf", "source_page": 1
    })
    # Manually flip needs_review + review_reason via PUT, since POST doesn't set them
    hyphen_id = client.post("/entries", json={
        "headword": "Hyphen-flag", "part_of_speech": "n", "definition": "test",
        "direction": "garo_to_english", "source_file": "test.pdf", "source_page": 1
    }).json()["id"]
    client.put(f"/entries/{hyphen_id}", json={"review_reason": "suspicious_hyphen_pattern"})

    apostrophe_id = client.post("/entries", json={
        "headword": "Apostrophe-flag", "part_of_speech": "n", "definition": "test",
        "direction": "garo_to_english", "source_file": "test.pdf", "source_page": 1
    }).json()["id"]
    client.put(f"/entries/{apostrophe_id}", json={"review_reason": "apostrophe_present"})

    response = client.get("/entries/needs-review?limit=50")
    ids_in_order = [e["id"] for e in response.json()]
    assert ids_in_order.index(apostrophe_id) < ids_in_order.index(hyphen_id)