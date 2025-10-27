from pydantic import BaseModel

class NotePayload(BaseModel):
    project: str
    section: str
    title: str
    body: str
    mode: str = "append"
