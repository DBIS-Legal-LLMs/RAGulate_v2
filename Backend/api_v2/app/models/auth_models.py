# Backend/api_v2/app/models/auth_models.py

from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """The verified identity of the caller, built directly from the JWT
    payload issued by auth-service — no local DB lookup. Only `id` is
    actually used anywhere in this codebase today; `app_roles` carries
    the per-app role claim once auth-service starts issuing it."""

    id: str
    app_roles: dict[str, str] = Field(default_factory=dict)
