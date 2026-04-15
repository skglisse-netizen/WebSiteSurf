from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("Checking DB setup...")
# Create a dummy token for admin user
from app.auth import create_access_token
token = create_access_token(data={"sub": "Administrateur"})

print(f"Token created: {token[:10]}...")

print("Calling /admin/dashboard...")
client.cookies.set("access_token", f"Bearer {token}")
try:
    response = client.get("/admin/dashboard")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 500:
        print("500 Error! Text:")
        print(response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
