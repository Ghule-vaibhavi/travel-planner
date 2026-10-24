from typing import List, Literal
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=1000)


class ChatRequest(BaseModel):
    trip_id: str = Field(min_length=4, max_length=40)
    message: str = Field(min_length=1, max_length=500)
    history: List[ChatTurn] = Field(default_factory=list, max_length=10)