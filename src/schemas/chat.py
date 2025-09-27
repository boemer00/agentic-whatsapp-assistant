from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client session identifier")
    message: str = Field(..., description="User message")
    locale: Optional[str] = "en-GB"

class ChatResponse(BaseModel):
    session_id: str
    reply: str
