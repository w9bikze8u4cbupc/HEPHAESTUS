"""
MOBIUS-mode extraction: component-aware region cropping.

Phase 9: Dual-mode architecture
- Legacy mode: embedded image extraction (Phase 8)
- MOBIUS mode: page-region cropping for component-centric output
"""

from .extraction import extract_mobius_components, MobiusExtractionResult

__all__ = ["extract_mobius_components", "MobiusExtractionResult"]
