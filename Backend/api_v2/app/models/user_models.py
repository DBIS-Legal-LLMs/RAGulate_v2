# Backend/api_v2/app/models/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    username: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserInDB(UserBase):
    # speichern MongoDB-ID als String; benutzen _id als Feldalias
    id: str | None = Field(default=None, alias="_id")
    password_hash: str
    role: Literal["user", "admin"] = "user"
    preferred_llm_provider: str | None = None      # "huggingface" | "openrouter" | "ollama"
    preferred_model: str | None = None
    created_at: datetime

    class Config:
        populate_by_name = True # erlaubt Nutzung von 'id' <-> '_id'

class UserPublic(UserBase):
    id: str
    role: Literal["user", "admin"] = "user"
    preferred_llm_provider: str | None = None
    preferred_model: str | None = None
    created_at: datetime
