from pydantic import BaseModel
from typing import Literal
class NotePayload(BaseModel):
    project: str
    section: str
    title: str
    body: str
    mode: Literal["append", "replace"] = "append"
