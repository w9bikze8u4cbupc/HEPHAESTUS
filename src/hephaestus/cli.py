from pathlib import Path

import typer

from .config import Settings
from .logging import get_logger
from .pdf.ingestion import EncryptedPdfError, PdfDocument, PdfOpenError
from .pdf.images import extract_embedded_images, save_images_flat

app = typer.Typer(help="HEPHAESTUS – board-game component extractor")


@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("output"), "--out", "-o"),
    min_width: int = typer.Option(50, help="Minimum image width in pixels"),
    min_height: int = typer.Option(50, help="Minimum image height in pixels"),
) -> None:
    logger = get_logger(__name__)

    try:
        logger.info(f"Opening PDF: {pdf_path}")
        doc = PdfDocument(pdf_path)
    except EncryptedPdfError as exc:
        logger.error(exc)
        raise typer.Exit(code=2) from exc
    except PdfOpenError as exc:
        logger.error(exc)
        raise typer.Exit(code=1) from exc

    logger.info("Extracting embedded images...")
    images = extract_embedded_images(doc, min_width=min_width, min_height=min_height)
    logger.info(f"Retained {len(images)} images after filtering")

    logger.info(f"Saving images to {out}")
    paths = save_images_flat(images, out)
    logger.info(f"Saved {len(paths)} images")


def main() -> None:
    app()


if __name__ == "__main__":
    main()