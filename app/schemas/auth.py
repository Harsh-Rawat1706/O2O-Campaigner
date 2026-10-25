from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Registration ----------

class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["customer", "merchant"] = "customer"


# ---------- Login ----------

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ---------- User response ----------

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: Literal["customer", "merchant", "admin"]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- JWT token response ----------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"