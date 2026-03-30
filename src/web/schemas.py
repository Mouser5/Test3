from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=10)


class BotResponse(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class BotWithCode(BotResponse):
    code: str


class GameResultCreate(BaseModel):
    bot_id: Optional[int] = None
    opponent_type: str
    opponent_id: Optional[int] = None
    result: str
    user_score: int
    opponent_score: int
    turns: int


class GameResultResponse(BaseModel):
    id: int
    bot_id: Optional[int]
    opponent_type: str
    opponent_id: Optional[int]
    result: str
    user_score: int
    opponent_score: int
    turns: int
    played_at: datetime

    class Config:
        from_attributes = True
