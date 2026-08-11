"""Extraction de texte des documents sources.

Extraction texte native uniquement pour cette V2 (pas d'OCR, pas de DOCX/Excel,
pas de crawler/upload). Le texte est extrait page par page afin de conserver le
numero de page pour chaque passage indexe.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class ParsedPage:
    page_number: int  # 1-indexe
    text: str


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> list[ParsedPage]: ...


class PdfDocumentParser(DocumentParser):
    """Extraction de texte natif, page par page, via `pypdf`."""

    def parse(self, file_path: Path) -> list[ParsedPage]:
        reader = PdfReader(str(file_path))
        pages: list[ParsedPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ParsedPage(page_number=index, text=text))
        return pages
