import math
from uuid import uuid4

from app.db.mongodb import get_db
from app.models.rag import Citation, ProjectFile
from .chunker import chunk_file
from .embeddings import embed_text


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    magnitude = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return max(0.0, min(1.0, dot / magnitude)) if magnitude else 0.0


async def index_project_files(project_id: str, files: list[ProjectFile]) -> int:
    db = get_db()
    await db.project_chunks.delete_many({"project_id": project_id})
    records = []
    for project_file in files:
        for chunk in chunk_file(project_file):
            records.append({
                "chunk_id": str(uuid4()),
                "project_id": project_id,
                **chunk,
                "embedding": embed_text(chunk["text"]),
            })
    if records:
        await db.project_chunks.insert_many(records)
    return len(records)


async def retrieve_context(project_id: str, query: str, limit: int = 5) -> tuple[str, list[Citation]]:
    db = get_db()
    query_embedding = embed_text(query)
    chunks = await db.project_chunks.find({"project_id": project_id}).to_list(1000)
    ranked = sorted(
        (( _cosine(query_embedding, chunk.get("embedding", [])), chunk) for chunk in chunks),
        key=lambda item: item[0],
        reverse=True,
    )[:limit]
    selected = ranked
    citations = [
        Citation(
            file_path=chunk["file_path"],
            start_line=chunk.get("start_line"),
            end_line=chunk.get("end_line"),
            relevance_score=round(score, 4),
            chunk_type=chunk.get("chunk_type", "document"),
        )
        for score, chunk in selected
    ]
    context = "\n\n".join(
        f"[Source: {citation.file_path}:{citation.start_line}-{citation.end_line}]\n{chunk['text']}"
        for citation, (_, chunk) in zip(citations, selected)
    )
    return context, citations
