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
