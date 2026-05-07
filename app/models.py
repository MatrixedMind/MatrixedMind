from pydantic import BaseModel, field_validator
from typing import Literal
class NotePayload(BaseModel):
    project: str
    section: str
    title: str
    body: str
    mode: Literal["append", "replace"] = "append"
    
    @field_validator("section")
    @classmethod
    def validate_section(cls, v: str) -> str:
        """Validate that section doesn't have leading/trailing slashes."""
        if v.startswith("/") or v.endswith("/"):
            raise ValueError("section must not start or end with '/'")
        return v
