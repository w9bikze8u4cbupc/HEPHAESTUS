from __future__ import annotations

from pathlib import Path

import fitz  # type: ignore[import]


class PdfOpenError(Exception):
    """Raised when a PDF cannot be opened."""


class EncryptedPdfError(PdfOpenError):
    """Raised when a PDF is encrypted and cannot be read."""


class PdfPage:
    def __init__(self, page: fitz.Page, index: int) -> None:
        self._page = page
        self._index = index

    @property
    def index(self) -> int:
        return self._index

    @property
    def width(self) -> float:
        return float(self._page.rect.width)

    @property
    def height(self) -> float:
        return float(self._page.rect.height)

    def raw(self) -> fitz.Page:
        return self._page


class PdfDocument:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._doc = self._open_document(path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def pages(self) -> list[PdfPage]:
        return [PdfPage(self._doc.load_page(i), i) for i in range(self.page_count)]

    def _open_document(self, path: Path) -> fitz.Document:
        if not path.exists():
            raise PdfOpenError(f"PDF file does not exist: {path}")
        try:
            doc = fitz.open(path)
        except Exception as exc:  # noqa: BLE001
            raise PdfOpenError(f"Failed to open PDF: {path}") from exc

        if doc.needs_pass:
            raise EncryptedPdfError(f"PDF is encrypted: {path}")
        return doc