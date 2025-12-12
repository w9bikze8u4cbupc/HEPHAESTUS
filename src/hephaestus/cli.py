from pathlib import Path
import sys

import typer

from .config import Settings
from .logging import get_logger
from .pdf.ingestion import EncryptedPdfError, PdfDocument, PdfOpenError
from .pdf.images import extract_embedded_images, save_images_flat
from .classifier.model import HybridClassifier
from .text.spatial import extract_spatial_text
from .text.index import SpatialTextIndex
from .metadata.annotator import annotate_components
from .dedup.model import deduplicate_images
from .output.manifest import build_manifest, write_manifest_json

app = typer.Typer(help="HEPHAESTUS – board-game component extractor", no_args_is_help=True)


@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to the PDF file to process"),
    out: Path = typer.Option(Path("output"), "--out", "-o", help="Output directory for extracted images"),
    min_width: int = typer.Option(50, help="Minimum image width in pixels"),
    min_height: int = typer.Option(50, help="Minimum image height in pixels"),
    text_expand: float = typer.Option(24.0, help="Text proximity expansion distance in points"),
    write_manifest: bool = typer.Option(True, "--write-manifest/--no-write-manifest", help="Write JSON manifest file"),
    dedup: bool = typer.Option(True, "--dedup/--no-dedup", help="Enable perceptual deduplication"),
    dedup_threshold: int = typer.Option(8, help="Perceptual hash distance threshold for deduplication"),
) -> None:
    """
    Extract embedded images from a PDF and save them as PNG files.
    
    This command processes the specified PDF file, extracts all embedded raster images,
    applies size-based filtering, and saves the results to the output directory.
    """
    logger = get_logger(__name__)

    try:
        logger.info(f"Opening PDF: {pdf_path}")
        with PdfDocument(pdf_path) as doc:
            logger.info(f"Successfully opened PDF with {doc.page_count} pages")
            
            logger.info("Extracting embedded images...")
            images = extract_embedded_images(doc, min_width=min_width, min_height=min_height)
            
            if not images:
                logger.warning("No images found matching the specified criteria")
                logger.info("Try reducing --min-width and --min-height if you expected to find images")
                return

            # Phase 2: Add classification (non-destructive)
            logger.info("Classifying extracted images...")
            classifier = HybridClassifier(enable_vision=False)  # Vision disabled for Phase 2
            classification_results = classifier.classify_batch(images)
            
            # Create classification mapping for easier access
            classification_map = {result.signals["image_id"]: result for result in classification_results}
            
            # Log classification summary
            summary = classifier.get_classification_summary(classification_results)
            logger.info(f"Classification complete: {summary['components']}/{summary['total']} identified as components")
            
            # Phase 3: Add spatial text extraction and metadata annotation
            logger.info("Extracting spatial text...")
            text_spans = extract_spatial_text(doc)
            
            logger.info("Building spatial text index...")
            text_index = SpatialTextIndex(text_spans)
            
            logger.info("Annotating components with metadata...")
            metadata_list = annotate_components(images, classification_map, text_index, expand=text_expand)
            
            logger.info(f"Saving {len(images)} images to {out}")
            try:
                paths = save_images_flat(images, out)
                logger.info(f"Successfully saved {len(paths)} images")
                
                # Phase 4: Deduplicate images
                dedup_groups = {}
                if dedup:
                    logger.info("Deduplicating images...")
                    # Create temporary manifest items for deduplication
                    temp_manifest_items = []
                    for i, image in enumerate(images):
                        if i < len(paths):
                            from .output.manifest import ManifestItem
                            temp_item = ManifestItem(
                                image_id=image.id,
                                file_name=paths[i].name,
                                page_index=image.page_index,
                                classification="temp",
                                classification_confidence=0.0,
                                label=None,
                                quantity=None,
                                metadata_confidence=0.0,
                                dimensions={"width": image.width, "height": image.height},
                                bbox=None,
                                dedup_group_id=None,
                                is_duplicate=False,
                                canonical_image_id=image.id,
                                file_path=str(paths[i])
                            )
                            temp_manifest_items.append(temp_item)
                    
                    dedup_groups = deduplicate_images(images, temp_manifest_items, threshold=dedup_threshold)
                    
                    duplicate_count = sum(1 for group in dedup_groups.values() if len(group.image_ids) > 1)
                    logger.info(f"Deduplication complete: found {duplicate_count} duplicate groups")
                
                # Phase 3: Generate and write manifest
                manifest = None
                if write_manifest:
                    logger.info("Generating component manifest...")
                    manifest = build_manifest(pdf_path, images, classification_map, metadata_list, paths, dedup_groups)
                    manifest_path = write_manifest_json(manifest, out)
                    logger.info(f"Wrote manifest to {manifest_path}")
                
                # Display enhanced summary with metadata
                metadata_with_labels = sum(1 for m in metadata_list if m.has_label())
                metadata_with_quantities = sum(1 for m in metadata_list if m.has_quantity())
                metadata_complete = sum(1 for m in metadata_list if m.is_complete())
                
                # Deduplication summary
                duplicate_groups = len(set(group.group_id for group in dedup_groups.values() if len(group.image_ids) > 1))
                total_duplicates = sum(len(group.image_ids) - 1 for group in dedup_groups.values() if len(group.image_ids) > 1)
                
                typer.echo(f"\n✅ Extraction complete!")
                typer.echo(f"📄 Processed: {pdf_path}")
                typer.echo(f"🖼️  Images extracted: {len(images)}")
                typer.echo(f"🎯 Components identified: {summary['components']}")
                typer.echo(f"🎨 Non-components: {summary['non_components']}")
                typer.echo(f"🏷️  With labels: {metadata_with_labels}")
                typer.echo(f"🔢 With quantities: {metadata_with_quantities}")
                typer.echo(f"✨ Complete metadata: {metadata_complete}")
                if dedup:
                    typer.echo(f"🔄 Duplicate groups: {duplicate_groups}")
                    typer.echo(f"📋 Total duplicates: {total_duplicates}")
                typer.echo(f"📁 Output directory: {out}")
                typer.echo(f"🔍 Filter criteria: {min_width}x{min_height} pixels minimum")
                
                if write_manifest and manifest:
                    typer.echo(f"📋 Manifest: manifest.json")
                
                # Show classification breakdown
                if summary['labels']:
                    typer.echo(f"📊 Classification breakdown:")
                    for label, count in summary['labels'].items():
                        typer.echo(f"   {label}: {count}")
                
            except Exception as exc:
                logger.error(f"Failed to save images: {exc}")
                raise typer.Exit(code=1) from exc
                
    except EncryptedPdfError as exc:
        logger.error(f"Cannot process encrypted PDF: {exc}")
        raise typer.Exit(code=2) from exc
    except PdfOpenError as exc:
        logger.error(f"Failed to open PDF: {exc}")
        raise typer.Exit(code=1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()