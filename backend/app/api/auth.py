from fastapi import APIRouter, HTTPException

from app.auth import issue_token, new_user, verify_password
from app.db.mongodb import get_db
from app.models.auth import LoginRequest, Token, UserCreate, UserPublic

router = APIRouter()


def _public(user: dict) -> UserPublic:
    return UserPublic(user_id=user["user_id"], username=user["username"], role=user["role"])


@router.post("/register", response_model=Token)
async def register(user_in: UserCreate):
    db = get_db()
    if await db.users.find_one({"username": user_in.username}):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = new_user(user_in.username, user_in.password)
    await db.users.insert_one(user)
    return Token(access_token=issue_token(user), user=_public(user))


@router.post("/login", response_model=Token)
async def login(user_in: LoginRequest):
    user = await get_db().users.find_one({"username": user_in.username})
    if not user or not verify_password(user_in.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return Token(access_token=issue_token(user), user=_public(user))
