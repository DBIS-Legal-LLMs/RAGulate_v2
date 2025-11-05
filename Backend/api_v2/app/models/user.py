# Backend/api_v2/app/models/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from datetime import datetime
from bson import ObjectId

# Helper, um ObjectId als str in/out zu bekommen
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        return ObjectId(str(v))

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserInDB(UserBase):
    id: PyObjectId | None = Field(default=None, alias="_id")
    password_hash: str
    role: Literal["user", "admin"] = "user"
    preferred_llm_provider: str | None = None      # "huggingface" | "openrouter" | "ollama"
    preferred_model: str | None = None
    created_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserPublic(UserBase):
    id: str
    role: Literal["user", "admin"] = "user"
    preferred_llm_provider: str | None = None
    preferred_model: str | None = None
    created_at: datetime
