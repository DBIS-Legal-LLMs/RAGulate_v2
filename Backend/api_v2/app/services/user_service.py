# Backend/api_v2/app/services/user_services.py

from datetime import datetime
from datetime import timezone
from typing import Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..models.user import UserCreate, UserInDB
from ..core.security import hash_password, verify_password

USERS_COLLECTION = "users"


class UserService:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    @property
    def collection(self):
        return self._db[USERS_COLLECTION]

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        doc = await self.collection.find_one({"email": email})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return UserInDB(**doc)

    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return UserInDB(**doc)

    async def create_user(self, user_in: UserCreate) -> UserInDB:
        existing = await self.get_by_email(user_in.email)
        if existing:
            raise ValueError("User already exists")

        password_hash = hash_password(user_in.password)
        doc = {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "password_hash": password_hash,
            "role": "user",
            "preferred_llm_provider": None,
            "preferred_model": None,
            "created_at": datetime.now(timezone.utc),
        }

        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserInDB(**doc)

    async def verify_user(self, email: str, password: str) -> Optional[UserInDB]:
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
