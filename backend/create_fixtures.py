import os
from pathlib import Path

def create_fixtures():
    base = Path("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend/tests/fixtures/sample_repo")
    base.mkdir(parents=True, exist_ok=True)
    
    (base / "app" / "services").mkdir(parents=True, exist_ok=True)
    (base / "tests").mkdir(parents=True, exist_ok=True)
    (base / "app" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (base / "app" / "__pycache__" / "ignore_me.pyc").write_text("binary garbage")
    
    (base / "app" / "main.py").write_text("""\
from fastapi import FastAPI, APIRouter
from .services.user_service import UserService, validate_user
from .utils import helper as h
import app.db as db

app = FastAPI()
router = APIRouter()

@app.get("/users")
def get_users():
    return db.query_users()

@app.post("/users")
async def create_user_endpoint(data: dict):
    svc = UserService()
    h()
    return svc.create(data)

@router.delete("/users/{user_id}")
# some comment
# another comment

def delete_user_handler(user_id: str):
    pass
""")

    (base / "app" / "services" / "user_service.py").write_text("""\
from ..db import connect

def validate_user():
    pass

class UserService:
    def __init__(self):
        self.db = connect()
    def get(self):
        pass
    def create(self, data):
        validate_user()
        return True
    def delete(self):
        pass
""")

    (base / "app" / "services" / "order_service.py").write_text("""\
def validate_user():
    # same name as in user_service.py
    pass

class OrderService:
    def __init__(self):
        pass
    def create(self):
        validate_user()
    def delete(self):
        pass
""")

    (base / "app" / "utils.py").write_text("""\
def my_decorator(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

@my_decorator
def helper():
    def nested():
        pass
    nested()
    l = lambda x: x
    return l(1)

class Base:
    def method(self):
        pass
        
class Derived(Base):
    def method(self):
        super().method()
""")

    (base / "app" / "db.py").write_text("""\
def connect():
    pass

def query_users():
    d = {"k": 1}
    # This must not become a route
    val = d.get("k")
    lst = []
    lst.append(val)
    s = "a,b"
    s.split(",")
    return val
""")

    (base / "tests" / "test_users.py").write_text("""\
from app.services.user_service import UserService, validate_user

def test_user_creation():
    validate_user()
    u = UserService()
    u.create({"name": "test"})
""")
    
    # edge cases
    (base / "empty.py").write_text("")
    (base / "comments.py").write_text("# just comments\n# nothing else")
    (base / "syntax_error.py").write_text("def broken():\n  yield return True\n  def")
    (base / "unicode_äöü.py").write_text("def f_äöü():\n  pass")
    (base / "README.md").write_text("# docs")
    (base / "data.json").write_text('{"a": 1}')
    
    with open(base.parent / "EXPECTED.md", "w", encoding="utf-8") as f:
        f.write("Ground truth goes here.\n")

if __name__ == '__main__':
    create_fixtures()
