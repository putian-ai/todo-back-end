from fastapi.testclient import TestClient
import sqlalchemy
from datetime import datetime, timedelta

from .main import app, Importance, TodoDto, UpdateTodoDto, TagDto

client = TestClient(app)


def test_read_todos():
    response = client.get("/get_todos/?page=1&per_page=5")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 5
    assert response.json()['total_items'] == 14
    assert len(response.json()['items']) == 5
    assert [item['item'] for item in response.json()['items']] == ['Code', 'Groceries', 'Clean', 'Call', 'Bills']


def test_get_todos_by_item_name():
    response = client.get("/get_todos_by_item_name/b?page=1&per_page=10")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 10
    assert response.json()['total_items'] == 2
    assert len(response.json()['items']) == 2
    assert [item['item'] for item in response.json()['items']] == ['Bills', 'Library']


def test_get_todos_by_importance():
    response = client.get("/get_todos_by_item_importance/2?page=1&per_page=10")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 10
    assert response.json()['total_items'] == 14
    assert len(response.json()['items']) == 14


def test_get_todos_by_plan_time():
    # Test with date only
    response = client.get("/get_todos_by_plan_time/2023-12-27?page=1&per_page=10")
    assert response.status_code == 200

    # Test with date and hour
    response = client.get("/get_todos_by_plan_time/2023-12-27 10?page=1&per_page=10")
    assert response.status_code == 200

    # Test with null plan time
    response = client.get("/get_todos_by_plan_time/null?page=1&per_page=10")
    assert response.status_code == 200

    # Test with invalid plan time format
    response = client.get("/get_todos_by_plan_time/invalid_format?page=1&per_page=10")
    assert response.status_code == 400


def test_create_user():
    response = client.post("/create_users/", json={"user_name": "test_user", "pwd": "password"})
    assert response.status_code == 200
    assert response.json()['user_name'] == "test_user"
    response = client.post("/create_users/", json={"user_name": "test_user", "pwd": "test_password"})
    assert response.status_code == 400
    assert response.json()['detail'] == "min_length=3, max_length=12"


def test_create_todo():
    response = client.post("/create_todos/", json={
        "item": "Test Todo",
        "plan_time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": 1,
        "content": "Test Content",
        "importance": Importance.HIGH.value
    })
    assert response.status_code == 200
    assert response.json()['item'] == "Test Todo"
    assert response.json()['content'] == "Test Content"
    assert response.json()['importance'] == Importance.HIGH.value


def test_create_tag():
    response = client.post("/create_tag/", json={
        "user_id": 1,
        "todo_id": 1,
        "name": "Test Tag",
        "color": "#123456"
    })
    assert response.status_code == 200
    assert response.json()['name'] == "Test Tag"
    assert response.json()['color'] == "#123456"


def test_update_todos():
    response = client.post("/update_todos/1", json={
        "item": "Updated Test Todo",
        "plan_time": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "content": "Updated Test Content",
        "importance": Importance.LOW.value
    })
    assert response.status_code == 200
    assert response.json()['item'] == "Updated Test Todo"
    assert response.json()['content'] == "Updated Test Content"
    assert response.json()['importance'] == Importance.LOW.value


def test_delete_todos():
    response = client.delete("/delete_todos/1")
    assert response.status_code == 200
    assert response.json() == {"detail": "Todo deleted successfully"}


def test_delete_tag():
    # Assuming a tag with id 1 exists
    response = client.delete("/delete_tag/1")
    assert response.status_code == 200
    assert response.json() == {"detail": "tag deleted successfully"}


def test_get_user_by_todo():
    response = client.get("/get_user_by_todo/2")
    assert response.status_code == 200
    assert response.json()['id'] == 2


def test_get_todos_by_user():
    response = client.get("/get_todos_by_user/1?page=1&per_page=10")
    assert response.status_code == 200
    assert len(response.json()['items']) > 0


def test_error_handling():
    # Test creating a todo with a non-existent user
    response = client.post("/create_todos/", json={
        "item": "Test Todo",
        "plan_time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": 999,  # Non-existent user
        "content": "Test Content",
        "importance": Importance.HIGH.value
    })
    assert response.status_code == 400
    assert response.json()['detail'] == "User does not exist!"

    # Test deleting a non-existent todo
    response = client.delete("/delete_todos/999")  # Non-existent todo
    assert response.status_code == 404
    assert response.json()['detail'] == "Todo not found"

    # Test deleting a non-existent tag
    response = client.delete("/delete_tag/999")  # Non-existent tag
    assert response.status_code == 404
    assert response.json()['detail'] == "tag not found"

    # Test updating a non-existent todo
    response = client.post("/update_todos/999", json={  # Non-existent todo
        "item": "Updated Test Todo",
        "plan_time": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "content": "Updated Test Content",
        "importance": Importance.LOW.value
    })
    assert response.status_code == 404
    assert response.json()['detail'] == "Todo not found"

    # Test getting a user by a non-existent todo
    response = client.get("/get_user_by_todo/999")  # Non-existent todo
    assert response.status_code == 404
    assert response.json()['detail'] == "Todo or User not found"

    # Test getting todos by a non-existent user
    response = client.get("/get_todos_by_user/999?page=1&per_page=10")  # Non-existent user
    assert response.status_code == 404
    assert response.json()['detail'] == "User not found or no todos for this user"
