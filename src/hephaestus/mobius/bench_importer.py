"""
G18: MOBIUS Bench Bundle Importer

Non-invasive integration harness for consuming validated bench bundles.
Imports tm_g6_g7_g10.zip (or extracted folder) with SHA verification.
"""

import json
import hashlib
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Tuple, List

import typer

app = typer.Typer(help="Bench bundle import commands")


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_sha256(zip_path: Path, sha_path: Path) -> Tuple[bool, str, str]:
    """
    Verify ZIP SHA-256 against expected hash.
    
    Returns:
        (is_valid, expected_hash, actual_hash)
    """
    if not sha_path.exists():
        raise FileNotFoundError(f"SHA file not found: {sha_path}")
    
    # Read expected hash (format: "<hash>  <filename>")
    expected_line = sha_path.read_text().strip()
    expected_hash = expected_line.split()[0].lower()
    
    if len(expected_hash) != 64:
        raise ValueError(f"Invalid SHA256 hash length: {len(expected_hash)}")
    
    # Compute actual hash
    actual_hash = compute_sha256(zip_path)
    
    return (actual_hash == expected_hash, expected_hash, actual_hash)


def extract_bundle(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract bundle ZIP to directory.
    
    Returns:
        Path to extracted bundle root
    """
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    return extract_dir


def validate_bundle_structure(bundle_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate bundle has required structure.
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Check MOBIUS_READY directory
    mobius_ready = bundle_dir / "MOBIUS_READY"
    if not mobius_ready.exists():
        errors.append("Missing MOBIUS_READY directory")
        return (False, errors)
    
    # Check images directory
    images_dir = mobius_ready / "images"
    if not images_dir.exists():
        errors.append("Missing MOBIUS_READY/images directory")
    else:
        png_files = list(images_dir.glob("*.png"))
        if len(png_files) == 0:
            errors.append("No PNG files in MOBIUS_READY/images")
    
    # Check manifest.json
    manifest_path = mobius_ready / "manifest.json"
    if not manifest_path.exists():
        errors.append("Missing MOBIUS_READY/manifest.json")
    else:
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            # Validate manifest structure
            if "components_extracted" not in manifest:
                errors.append("manifest.json missing 'components_extracted' field")
            if "items" not in manifest:
                errors.append("manifest.json missing 'items' field")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid manifest.json: {e}")
    
    return (len(errors) == 0, errors)


def load_manifest(bundle_dir: Path) -> dict:
    """Load and return manifest from bundle."""
    manifest_path = bundle_dir / "MOBIUS_READY" / "manifest.json"
    with open(manifest_path) as f:
        return json.load(f)


@app.command("import-tm")
def import_terraforming_mars(
    zip_path: Path = typer.Option(..., "--zip", help="Path to tm_g6_g7_g10.zip"),
    extract_dir: Optional[Path] = typer.Option(None, "--extract-to", help="Directory to extract bundle (default: temp)"),
    verify_sha: bool = typer.Option(True, "--verify-sha/--no-verify-sha", help="Verify SHA-256 integrity"),
    keep_extracted: bool = typer.Option(False, "--keep-extracted", help="Keep extracted files after import")
):
    """
    Import Terraforming Mars bench bundle (tm_g6_g7_g10.zip).
    
    Validates:
    - ZIP SHA-256 integrity (optional)
    - Bundle structure (MOBIUS_READY/images/*.png + manifest.json)
    - Manifest schema
    
    Expected baseline:
    - 28 components extracted
    - Recall: 90.3% (28/31)
    - False positives: 0
    """
    typer.echo("=== MOBIUS Bench Import: Terraforming Mars ===")
    typer.echo(f"ZIP: {zip_path}")
    
    # Validate ZIP exists
    if not zip_path.exists():
        typer.echo(f"[FAIL] ZIP not found: {zip_path}", err=True)
        raise typer.Exit(1)
    
    # Verify SHA-256 if requested
    if verify_sha:
        sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
        typer.echo(f"SHA: {sha_path}")
        
        try:
            is_valid, expected, actual = verify_sha256(zip_path, sha_path)
            
            typer.echo(f"Expected: {expected}")
            typer.echo(f"Actual:   {actual}")
            
            if not is_valid:
                typer.echo("[FAIL] SHA-256 mismatch", err=True)
                raise typer.Exit(1)
            
            typer.echo("[PASS] SHA-256 integrity verified")
        except Exception as e:
            typer.echo(f"[FAIL] SHA verification failed: {e}", err=True)
            raise typer.Exit(1)
    
    # Determine extract directory
    if extract_dir is None:
        extract_dir = Path("bench_bundle") / "tmp_import_tm_g6_g7_g10"
    
    typer.echo(f"Extract: {extract_dir}")
    
    # Extract bundle
    try:
        bundle_dir = extract_bundle(zip_path, extract_dir)
        typer.echo("[PASS] Bundle extracted")
    except Exception as e:
        typer.echo(f"[FAIL] Extraction failed: {e}", err=True)
        raise typer.Exit(1)
    
    # Validate structure
    is_valid, errors = validate_bundle_structure(bundle_dir)
    if not is_valid:
        typer.echo("[FAIL] Bundle structure validation failed:", err=True)
        for error in errors:
            typer.echo(f"  - {error}", err=True)
        
        if not keep_extracted:
            shutil.rmtree(extract_dir)
        
        raise typer.Exit(1)
    
    typer.echo("[PASS] Bundle structure validated")
    
    # Load manifest
    try:
        manifest = load_manifest(bundle_dir)
        components_extracted = manifest.get("components_extracted", 0)
        items_count = len(manifest.get("items", []))
        
        typer.echo(f"[INFO] Components extracted: {components_extracted}")
        typer.echo(f"[INFO] Manifest items: {items_count}")
        
        # Validate expected baseline
        if components_extracted != 28:
            typer.echo(f"[WARN] Expected 28 components, got {components_extracted}")
        
        typer.echo("[PASS] Manifest loaded")
    except Exception as e:
        typer.echo(f"[FAIL] Manifest loading failed: {e}", err=True)
        
        if not keep_extracted:
            shutil.rmtree(extract_dir)
        
        raise typer.Exit(1)
    
    # Report ingestion paths
    images_dir = bundle_dir / "MOBIUS_READY" / "images"
    manifest_path = bundle_dir / "MOBIUS_READY" / "manifest.json"
    
    typer.echo("\n=== MOBIUS Ingestion Paths ===")
    typer.echo(f"Images:   {images_dir}")
    typer.echo(f"Manifest: {manifest_path}")
    typer.echo(f"Count:    {len(list(images_dir.glob('*.png')))} PNG files")
    
    # Cleanup if requested
    if not keep_extracted:
        typer.echo("\n[INFO] Cleaning up extracted files...")
        shutil.rmtree(extract_dir)
    else:
        typer.echo(f"\n[INFO] Extracted bundle kept at: {extract_dir}")
    
    typer.echo("\n[PASS] Import complete")
    typer.echo("\nExpected baseline:")
    typer.echo("  Recall: 90.3% (28/31)")
    typer.echo("  False positives: 0")
    typer.echo("  Theoretical ceiling: 28 components vs 31 references")


if __name__ == "__main__":
    app()
