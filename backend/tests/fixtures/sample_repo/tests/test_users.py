from app.services.user_service import UserService, validate_user

def test_user_creation():
    validate_user()
    u = UserService()
    u.create({"name": "test"})
