from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import fitz  # type: ignore[import]

from .ingestion import PdfDocument


ImageSourceType = Literal["embedded"]


@dataclass
class ExtractedImage:
    id: str
    page_index: int
    source_type: ImageSourceType
    width: int
    height: int
    pixmap: fitz.Pixmap


def extract_embedded_images(
    pdf: PdfDocument,
    min_width: int,
    min_height: int,
) -> list[ExtractedImage]:
    images: list[ExtractedImage] = []
    for page in pdf.pages():
        raw_page = page.raw()
        img_refs = raw_page.get_images(full=True)
        for local_idx, img in enumerate(img_refs):
            xref = img[0]
            pix = fitz.Pixmap(pdf._doc, xref)  # type: ignore[attr-defined]
            width, height = pix.width, pix.height
            if width < min_width or height < min_height:
                continue
            img_id = f"p{page.index}_img{local_idx}"
            images.append(
                ExtractedImage(
                    id=img_id,
                    page_index=page.index,
                    source_type="embedded",
                    width=width,
                    height=height,
                    pixmap=pix,
                )
            )
    return images


def save_images_flat(
    images: Sequence[ExtractedImage],
    output_dir: Path,
    fmt: str = "png",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    for image in images:
        filename = f"component_{image.id}.{fmt.lower()}"
        path = output_dir / filename
        image.pixmap.save(path.as_posix())
        saved_paths.append(path)

    return saved_paths