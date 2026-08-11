"""Decoupage des documents en passages indexables (section 9).

Le decoupage tente de respecter les sections plutot que de fragmenter tous les
`chunk_size` caracteres aveuglement : un titre de section detecte (numerotation
"1.", "3.2", etc.) ne declenche la cloture du passage courant que si celui-ci a
deja atteint une taille significative, afin de ne pas fragmenter excessivement
les petits paragraphes.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.rag.parsing import ParsedPage

SECTION_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*\.?)\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇ][^\n]{2,90})\s*$")


@dataclass
class ParsedChunk:
    section_title: str | None
    page_number: int
    content: str
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, pages: list[ParsedPage]) -> list[ParsedChunk]: ...


class SectionAwareChunkingStrategy(ChunkingStrategy):
    """Regroupe les lignes par section detectee, avec chevauchement configurable."""

    def __init__(self, target_size: int = 800, overlap: int = 120, min_size_before_section_break: float = 0.4):
        self.target_size = target_size
        self.overlap = overlap
        self.min_size_before_section_break = min_size_before_section_break

    def chunk(self, pages: list[ParsedPage]) -> list[ParsedChunk]:
        chunks: list[ParsedChunk] = []
        buffer_lines: list[str] = []
        buffer_section: str | None = None
        buffer_start_page: int | None = None
        current_section: str | None = None

        def buffer_length() -> int:
            return sum(len(line) + 1 for line in buffer_lines)

        def flush() -> None:
            nonlocal buffer_lines, buffer_section, buffer_start_page
            content = " ".join(buffer_lines).strip()
            if content:
                chunks.append(
                    ParsedChunk(section_title=buffer_section, page_number=buffer_start_page or 1, content=content)
                )
            buffer_lines = []

        for page in pages:
            for raw_line in page.text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                match = SECTION_HEADING_RE.match(line)
                if match:
                    new_title = match.group(2).strip()
                    if buffer_lines and buffer_length() >= self.target_size * self.min_size_before_section_break:
                        flush()
                    current_section = new_title
                    # Le titre du chunk en cours reflete toujours le dernier titre
                    # rencontre (meme si le buffer contient un chevauchement reporte
                    # d'un flush precedent) : evite qu'un ancien titre reste attache
                    # indefiniment apres un changement de section.
                    buffer_section = current_section
                    if not buffer_lines:
                        buffer_start_page = page.page_number
                    continue

                if not buffer_lines:
                    buffer_section = current_section
                    buffer_start_page = page.page_number

                buffer_lines.append(line)

                if buffer_length() >= self.target_size:
                    joined = " ".join(buffer_lines)
                    overlap_text = joined[-self.overlap :].strip() if self.overlap else ""
                    flush()
                    if overlap_text:
                        buffer_lines = [overlap_text]
                        buffer_section = current_section
                        buffer_start_page = page.page_number

        flush()

        for index, parsed_chunk in enumerate(chunks):
            parsed_chunk.chunk_index = index
        return chunks
