# Backend/api_v2/app/services/user_services.py

from datetime import datetime
from datetime import timezone
from typing import Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

import random
import time
import asyncio

from ..data import func
from ..models.user import UserCreate, UserInDB
from ..core.security import hash_password, verify_password

USERS_COLLECTION = "users"


def _generate_random_username_base() -> str:
    """
    Erzeugt einen Basis-Username wie 'TopDogReptile8907' (ohne DB-Check).
    - 1 Prefix-Wort
    - 1–2 Suffix-Wörter
    - 3–5 Ziffern (basierend auf NUMBER_CHARS)
    """
    parts: list[str] = []
    PREFIX_WORDS, SUFFIX_WORDS, NUMBER_CHARS = func.get_username_parts()

    # 1 Prefix
    if PREFIX_WORDS:
        parts.append(random.choice(PREFIX_WORDS))

    # mindestens 1, höchstens 2 Suffix-Wörter
    suffix_count = 1 if len(SUFFIX_WORDS) < 2 else random.randint(1, 2)
    for _ in range(suffix_count):
        if SUFFIX_WORDS:
            parts.append(random.choice(SUFFIX_WORDS))

    # 3–5 Ziffern
    digit_count = random.randint(3, 5)
    digits = "".join(random.choice(NUMBER_CHARS) for _ in range(digit_count))

    return "".join(parts) + digits


class UserService:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    @property
    def collection(self):
        return self._db[USERS_COLLECTION]

    # ----- CREATE USER -----
    async def create_user(self, user_in: UserCreate) -> UserInDB:        
        # E-Mail validieren
        from ..core.security import validate_email_address, validate_password_policy
        try:
            normalized_email = validate_email_address(user_in.email)
        except ValueError:
            raise ValueError("EMAIL_INVALID")

        # E-Mail check
        existing = await self.get_by_email(normalized_email)
        if existing:
            raise ValueError("EMAIL_EXISTS")
        
        # Username prüfen
        username = user_in.username
        if username:
            username_exists = await self.collection.find_one({"username": username})
            if username_exists:
                raise ValueError("USERNAME_EXISTS")
        else:
            raise ValueError("USERNAME_EMPTY")

        # Passwort prüfen
        pw_errors = validate_password_policy(user_in.password)
        if pw_errors:
            raise ValueError({"type": "PASSWORD_POLICY", "errors": pw_errors})

        password_hash = hash_password(user_in.password)

        doc = {
            "email": normalized_email,
            "full_name": user_in.full_name,
            "username": username,
            "password_hash": password_hash,
            "role": "user",
            "preferred_llm_provider": None,
            "preferred_model": None,
            "created_at": datetime.now(timezone.utc),
        }

        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserInDB(**doc)
    
    async def generate_unique_username(self) -> Optional[str]:
        start = time.monotonic()
        while True:
            candidate = _generate_random_username_base()
            existing = await self.collection.find_one({"username": candidate})
            if not existing:
                return candidate
            if time.monotonic() - start > 15:
                return None
            await asyncio.sleep(0.01)

    # ----- GET USER -----
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
    
    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        doc = await self.collection.find_one({"username": username})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return UserInDB(**doc)


    # ----- VERIFY USER -----
    async def verify_user(self, login: str, password: str) -> Optional[UserInDB]:
        user_by_email = await self.get_by_email(login)
        user_by_username = await self.get_by_username(login)
        user = user_by_email if user_by_email else user_by_username
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
