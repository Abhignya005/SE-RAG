from typing import Literal, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    relevance_score: float = Field(ge=0, le=1)
    chunk_type: str = "document"


class ProjectFile(BaseModel):
    file_path: str = Field(min_length=1)
    content: str = Field(min_length=1)
    language: Optional[str] = None


class ProjectFileBatch(BaseModel):
    files: list[ProjectFile] = Field(min_length=1)


class IndexedChunk(BaseModel):
    chunk_id: str
    project_id: str
    file_path: str
    language: str
    symbol: Optional[str] = None
    chunk_type: Literal["class", "method", "markdown", "document"]
    start_line: int
    end_line: int
    text: str
    embedding: list[float]
