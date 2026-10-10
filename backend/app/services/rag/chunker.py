import re

from app.models.rag import ProjectFile


def _language(file_path: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    suffix = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "text"
    return {"md": "markdown", "py": "python", "ts": "typescript", "tsx": "typescript", "java": "java"}.get(suffix, suffix)


def chunk_file(project_file: ProjectFile, max_lines: int = 80, overlap: int = 8) -> list[dict]:
    """Chunk code/docs by useful declaration boundaries, with bounded overlap."""
    lines = project_file.content.splitlines()
    language = _language(project_file.file_path, project_file.language)
    boundary = re.compile(r"^\s*(class|interface|enum|def|function|export\s+(default\s+)?class|#+\s)")
    starts = [index for index, line in enumerate(lines) if boundary.search(line)]
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    chunks: list[dict] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        while end - start > max_lines:
            chunk_end = min(start + max_lines, len(lines))
            chunks.append(_make_chunk(project_file, language, lines, start, chunk_end))
            start = max(start + max_lines - overlap, chunk_end - overlap)
        if start < end:
            chunks.append(_make_chunk(project_file, language, lines, start, end))
    return chunks


def _make_chunk(project_file: ProjectFile, language: str, lines: list[str], start: int, end: int) -> dict:
    text = "\n".join(lines[start:end]).strip()
    first = lines[start].strip() if start < len(lines) else ""
    symbol_match = re.search(r"(?:class|interface|enum|def|function)\s+([A-Za-z_][A-Za-z0-9_]*)", first)
    chunk_type = "markdown" if language == "markdown" else ("class" if symbol_match else "document")
    return {
        "file_path": project_file.file_path,
        "language": language,
        "symbol": symbol_match.group(1) if symbol_match else None,
        "chunk_type": chunk_type,
        "start_line": start + 1,
        "end_line": end,
        "text": text,
    }
