from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)


# TODO: all tests

def test_read_todos():
    response = client.get("/get_todos/?page=1&per_page=5")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 5
    assert response.json()['total_items'] == 14
    assert len(response.json()['items']) == 5
    assert [item['item'] for item in response.json()['items']] == ['Code', 'Groceries', 'Clean', 'Call', 'Bills']


def test_get_todos_by_item_name():
    response = client.get("http://127.0.0.1:8000/get_todos_by_item_name/b?page=1&per_page=10")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 10
    assert response.json()['total_items'] == 2
    assert len(response.json()['items']) == 2
    assert [item['item'] for item in response.json()['items']] == ['Bills', 'Library']


def test_get_todos_by_plan_time():
    response = client.get("http://127.0.0.1:8000/get_todos_by_plan_time/null?page=1&per_page=20")
    assert response.status_code == 200
    assert response.json()['page'] == 1
    assert response.json()['per_page'] == 20
    assert response.json()['total_items'] == 14
    assert len(response.json()['items']) == 14
    assert [item['item'] for item in response.json()['items']] == [
        'Code',
        'Groceries',
        'Clean',
        'Call',
        'Bills',
        'Walk',
        'Report',
        'Doctor',
        'Plants',
        'Read',
        'Library',
        'Trash',
        'Laundry',
        'Desk'
    ]


def test_read_users():
    response = client.get("http://127.0.0.1:8000/get_users/?page=2&per_page=2")
    assert response.status_code == 200
    assert response.json()['page'] == 2
    assert response.json()['per_page'] == 2
    assert response.json()['total_items'] == 4
    assert len(response.json()['items']) == 2
    assert [item['user_name'] for item in response.json()['items']] == ['Amy', 'Alvin']
