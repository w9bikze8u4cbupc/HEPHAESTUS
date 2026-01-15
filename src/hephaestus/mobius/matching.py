"""
Component matching for MOBIUS integration.

Matches detected regions against known component vocabulary using text proximity
and keyword matching.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path

from ..logging import get_logger
from ..text.index import SpatialTextIndex

logger = get_logger(__name__)


@dataclass
class ComponentVocabulary:
    """Component vocabulary from MOBIUS."""
    
    # Game name
    game: str
    
    # Component names (canonical)
    components: List[str]
    
    # Optional: component metadata (type, quantity, aliases)
    metadata: Optional[Dict[str, Dict]] = None
    
    @classmethod
    def from_json(cls, path: Path) -> "ComponentVocabulary":
        """Load vocabulary from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support two formats:
        # 1. Simple: {"game": "...", "components": ["..."]}
        # 2. Rich: {"game": "...", "components": [{"name": "...", "qty": 10, "type": "..."}]}
        
        game = data.get("game", "unknown")
        components_raw = data.get("components", [])
        
        # Normalize to list of strings
        components = []
        metadata = {}
        
        for item in components_raw:
            if isinstance(item, str):
                components.append(item)
            elif isinstance(item, dict):
                name = item.get("name", "")
                if name:
                    components.append(name)
                    metadata[name] = item
        
        return cls(game=game, components=components, metadata=metadata)


def match_component_to_vocabulary(
    bbox: Tuple[float, float, float, float],
    page_index: int,
    text_index: SpatialTextIndex,
    vocabulary: ComponentVocabulary,
    expand_distance: float = 50.0
) -> Tuple[Optional[str], float]:
    """
    Match a detected region to component vocabulary using text proximity.
    
    Strategy (v1 - deterministic keyword matching):
    1. Extract text near the region (within expand_distance)
    2. For each component name in vocabulary:
       - Check if name (or substrings) appear in nearby text
       - Score by proximity and match quality
    3. Return best match above threshold
    
    Args:
        bbox: Region bounding box in PDF coordinates (x0, y0, x1, y1)
        page_index: Page number
        text_index: Spatial text index for the document
        vocabulary: Component vocabulary to match against
        expand_distance: Distance in points to search for text
    
    Returns:
        Tuple of (matched_component_name, match_score) or (None, 0.0)
    """
    if not vocabulary.components:
        return None, 0.0
    
    # Get nearby text
    nearby_text = text_index.get_text_near_bbox(bbox, page_index, expand=expand_distance)
    
    if not nearby_text:
        return None, 0.0
    
    # Normalize nearby text for matching
    nearby_text_lower = nearby_text.lower()
    
    # Try to match each component
    best_match = None
    best_score = 0.0
    
    for component_name in vocabulary.components:
        component_lower = component_name.lower()
        
        # Exact match (highest score)
        if component_lower in nearby_text_lower:
            score = 1.0
            if score > best_score:
                best_match = component_name
                best_score = score
            continue
        
        # Partial match (word-level)
        component_words = component_lower.split()
        if len(component_words) > 1:
            # Multi-word component: check if all words present
            words_found = sum(1 for word in component_words if word in nearby_text_lower)
            if words_found > 0:
                score = 0.5 + (0.3 * words_found / len(component_words))
                if score > best_score:
                    best_match = component_name
                    best_score = score
        else:
            # Single-word component: check for substring match
            if component_words[0] in nearby_text_lower:
                score = 0.6
                if score > best_score:
                    best_match = component_name
                    best_score = score
    
    # Only return matches above threshold
    threshold = 0.5
    if best_score >= threshold:
        return best_match, best_score
    
    return None, 0.0
