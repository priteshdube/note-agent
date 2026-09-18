from pydantic import BaseModel, Field
from typing import List

class KeyTerm(BaseModel):
    term: str
    definition: str

class Section(BaseModel):
    heading: str
    bullets: List[str]

class LectureNotes(BaseModel):
    title: str
    sections: List[Section]
    key_terms: List[KeyTerm] = []

class ProcessResponse(BaseModel):
    status: str
    notes: LectureNotes
    notion_page_url: str | None = None