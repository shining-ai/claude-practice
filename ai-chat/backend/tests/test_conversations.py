"""会話 CRUD エンドポイントのテスト"""


def test_create_conversation(client):
    response = client.post("/api/conversations")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] is None
    assert "created_at" in data
    assert "updated_at" in data


def test_list_conversations_empty(client):
    response = client.get("/api/conversations")
    assert response.status_code == 200
    assert response.json() == []


def test_list_conversations_returns_created(client):
    client.post("/api/conversations")
    client.post("/api/conversations")

    response = client.get("/api/conversations")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_conversation(client):
    create_res = client.post("/api/conversations")
    conv_id = create_res.json()["id"]

    response = client.get(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["messages"] == []


def test_get_conversation_not_found(client):
    response = client.get("/api/conversations/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "会話が見つかりません"


def test_delete_conversation(client):
    create_res = client.post("/api/conversations")
    conv_id = create_res.json()["id"]

    delete_res = client.delete(f"/api/conversations/{conv_id}")
    assert delete_res.status_code == 204

    # 削除後は 404 になる
    get_res = client.get(f"/api/conversations/{conv_id}")
    assert get_res.status_code == 404


def test_delete_conversation_not_found(client):
    response = client.delete("/api/conversations/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "会話が見つかりません"


def test_list_conversations_ordered_by_updated_at(client):
    res1 = client.post("/api/conversations")
    res2 = client.post("/api/conversations")
    id1 = res1.json()["id"]
    id2 = res2.json()["id"]

    # 最新の会話が先頭に来ることを確認
    response = client.get("/api/conversations")
    ids = [c["id"] for c in response.json()]
    # id2 は id1 より後に作成されたので先頭のはず
    assert ids.index(id2) < ids.index(id1)
