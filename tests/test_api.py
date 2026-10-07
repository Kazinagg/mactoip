import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from mactoip.database import Base, get_db
from mactoip.main import app

# Тестовая in-memory база данных со StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_heartbeat_create_new_device(client):
    payload = {
        "mac": "aa:bb:cc:dd:ee:01",
        "ip": "192.168.1.101",
        "hostname": "wb-test-01",
    }
    response = client.post("/api/devices/heartbeat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["device"]["mac"] == "AA:BB:CC:DD:EE:01"
    assert data["device"]["ip"] == "192.168.1.101"
    assert data["device"]["hostname"] == "wb-test-01"
    assert data["device"]["update_count"] == 1
    assert "last_seen" in data["device"]
    assert "first_seen" in data["device"]

def test_heartbeat_same_ip(client):
    payload = {
        "mac": "AA:BB:CC:DD:EE:02",
        "ip": "192.168.1.102",
        "hostname": "wb-test-02",
    }
    client.post("/api/devices/heartbeat", json=payload)
    
    # Повторный пинг
    response = client.post("/api/devices/heartbeat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "heartbeat"
    assert data["device"]["update_count"] == 2

def test_heartbeat_ip_updated(client):
    payload1 = {
        "mac": "AA:BB:CC:DD:EE:03",
        "ip": "192.168.1.103",
    }
    client.post("/api/devices/heartbeat", json=payload1)

    # Обновление IP (например, DHCP выдал новый)
    payload2 = {
        "mac": "AA:BB:CC:DD:EE:03",
        "ip": "192.168.1.203",
    }
    response = client.post("/api/devices/heartbeat", json=payload2)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ip_updated"
    assert data["device"]["ip"] == "192.168.1.203"
    assert data["device"]["update_count"] == 2

def test_get_all_devices(client):
    client.post("/api/devices/heartbeat", json={"mac": "AA:11:11:11:11:11", "ip": "10.0.0.1"})
    client.post("/api/devices/heartbeat", json={"mac": "AA:22:22:22:22:22", "ip": "10.0.0.2"})

    response = client.get("/api/devices")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 2

def test_get_ip_by_mac_json_and_text(client):
    client.post("/api/devices/heartbeat", json={"mac": "AA:BB:CC:11:22:33", "ip": "192.168.1.55"})

    # JSON формат
    res_json = client.get("/api/devices/AA:BB:CC:11:22:33/ip")
    assert res_json.status_code == 200
    assert res_json.json()["ip"] == "192.168.1.55"

    # Plain text формат
    res_text = client.get("/api/devices/AA:BB:CC:11:22:33/ip?format=text")
    assert res_text.status_code == 200
    assert res_text.text == "192.168.1.55"

    # Альтернативный формат записи MAC в URL (дефисы, строчные буквы)
    res_alt = client.get("/api/devices/aa-bb-cc-11-22-33/ip?format=text")
    assert res_alt.status_code == 200
    assert res_alt.text == "192.168.1.55"

def test_get_unknown_device_404(client):
    response = client.get("/api/devices/00:00:00:00:00:00")
    assert response.status_code == 404

def test_patch_device_meta(client):
    client.post("/api/devices/heartbeat", json={"mac": "AA:BB:CC:44:55:66", "ip": "192.168.1.66"})
    
    patch_res = client.patch(
        "/api/devices/AA:BB:CC:44:55:66",
        json={"hostname": "wb-boiler-room", "comment": "Котельная щит №2"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["hostname"] == "wb-boiler-room"
    assert data["comment"] == "Котельная щит №2"

def test_delete_device(client):
    client.post("/api/devices/heartbeat", json={"mac": "AA:BB:CC:77:88:99", "ip": "192.168.1.77"})

    del_res = client.delete("/api/devices/AA:BB:CC:77:88:99")
    assert del_res.status_code == 200

    check_res = client.get("/api/devices/AA:BB:CC:77:88:99")
    assert check_res.status_code == 404

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "total_devices" in data

def test_index_dashboard(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Wiren Board Registry" in res.text

