"""
Document parsing module for MentorOS.
Extracts raw text and page/slide numbers from PDF, DOCX, PPTX, and TXT/MD files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Union


#all the format checks
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

#output is like for single page
@dataclass
class ParsedPage:
    """Represents a single page or slide extracted from a document."""
    page_number: int  # 1-indexed page or slide number
    text: str
    source_file: str
    metadata: dict


class DocumentParser:
    """Multi-format document parser extracting page/slide-level text."""
    #all acceptable
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}

    @classmethod
    def is_supported(cls, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Union[str, Path]) -> List[ParsedPage]:
        """Parse a document and return a list of ParsedPage objects."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._parse_pdf(path)
        elif ext == ".docx":
            return self._parse_docx(path)
        elif ext == ".pptx":
            return self._parse_pptx(path)
        elif ext in {".txt", ".md"}:
            return self._parse_text(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: {self.SUPPORTED_EXTENSIONS}")

    #for pdfs
    def _parse_pdf(self, path: Path) -> List[ParsedPage]:
        """Extract text page-by-page from PDF."""
        if PdfReader is None:
            raise ImportError("pypdf is required to parse PDF files. Run `pip install pypdf`.")

        pages = []
        reader = PdfReader(str(path))
        filename = path.name

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            # Clean up excessive blank lines while preserving paragraph spacing
            cleaned_text = "\n".join(
                line.strip() for line in text.splitlines() if line.strip()
            )
            if cleaned_text:
                pages.append(
                    ParsedPage(
                        page_number=idx,
                        text=cleaned_text,
                        source_file=filename,
                        metadata={"total_pages": len(reader.pages), "file_type": "pdf"}
                    )
                )

        return pages

    #for docx files
    def _parse_docx(self, path: Path) -> List[ParsedPage]:
        """Extract text from DOCX documents."""
        if docx is None:
            raise ImportError("python-docx is required to parse DOCX files. Run `pip install python-docx`.")

        doc = docx.Document(str(path))
        filename = path.name
        
        # Extract paragraph text and table text
        paragraphs_text = []
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs_text.append(p.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs_text.append(row_text)

        full_text = "\n\n".join(paragraphs_text)
        
        # DOCX format does not have explicit native pages; we segment by approximate page sizes (~400 words)
        words = full_text.split()
        words_per_page = 400
        pages = []

        if not words:
            return []

        for page_idx, i in enumerate(range(0, len(words), words_per_page), start=1):
            page_text = " ".join(words[i:i + words_per_page])
            pages.append(
                ParsedPage(
                    page_number=page_idx,
                    text=page_text,
                    source_file=filename,
                    metadata={"file_type": "docx"}
                )
            )

        return pages

    #for ppt
    def _parse_pptx(self, path: Path) -> List[ParsedPage]:
        """Extract text slide-by-slide from PPTX presentations."""
        if Presentation is None:
            raise ImportError("python-pptx is required to parse PPTX files. Run `pip install python-pptx`.")

        prs = Presentation(str(path))
        filename = path.name
        pages = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_lines = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_lines.append(text)
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            slide_lines.append(row_text)

            slide_text = "\n".join(slide_lines)
            if slide_text.strip():
                pages.append(
                    ParsedPage(
                        page_number=slide_idx,
                        text=slide_text.strip(),
                        source_file=filename,
                        metadata={"total_slides": len(prs.slides), "file_type": "pptx"}
                    )
                )

        return pages

    def _parse_text(self, path: Path) -> List[ParsedPage]:
        """Extract text from plain text or markdown files."""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        filename = path.name
        return [
            ParsedPage(
                page_number=1,
                text=content.strip(),
                source_file=filename,
                metadata={"file_type": path.suffix.lstrip(".")}
            )
        ]


def parse_document(file_path: Union[str, Path]) -> List[ParsedPage]:
    """Convenience function to parse any supported document."""
    parser = DocumentParser()
    return parser.parse(file_path)
