/**
 * Phase 6.1 Type Definitions - Direct mapping to manifest/log artifacts
 * 
 * These types mirror the exact structure of the immutable artifacts.
 * No derived fields, no computed properties, no UI conveniences.
 */

export interface ExtractionHealth {
  images_attempted: number;
  images_saved: number;
  conversion_failures: number;
  success_rate: number;
  failure_rate: number;
  colorspace_distribution: Record<string, number>;
  conversion_operations: Record<string, number>;
  failure_reasons: Record<string, number>;
}

export interface TextArtifacts {
  page_text_jsonl_path: string | null;
  page_text_jsonl_sha256: string | null;
}

export interface PageSize {
  width: number;
  height: number;
}

export interface TextBlock {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  text: string;
  type: string; // "text" | "other"
}

export interface PageTextRecord {
  rulebook_id: string;
  page_index: number;
  page_size: PageSize;
  blocks: TextBlock[];
  errors: string[];
  timestamp: string;
}

export interface ManifestItem {
  image_id: string;
  file_name: string;
  page_index: number;
  classification: string;
  classification_confidence: number;
  label: string | null;
  quantity: number | null;
  metadata_confidence: number;
  dimensions: {
    width: number;
    height: number;
  };
  bbox: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  } | null;
  dedup_group_id: string | null;
  is_duplicate: boolean;
  canonical_image_id: string;
  file_path: string;
}

export interface Manifest {
  version: string;
  source_pdf: string;
  extraction_timestamp: string;
  total_items: number;
  summary: Record<string, any>;
  items: ManifestItem[];
  extraction_health: ExtractionHealth | null;
  text_artifacts: TextArtifacts | null;
}

export interface ExtractionLogEntry {
  rulebook_id: string;
  page_index: number;
  image_id: string;
  colorspace_str: string;
  status: 'persisted' | 'failed';
  reason_code: string;
  output_path: string | null;
  bytes_written: number;
  errors: string[];
  warnings: string[];
  width: number;
  height: number;
  timestamp: string;
}

export interface ArtifactBundle {
  manifest: Manifest;
  extractionLog: ExtractionLogEntry[];
  pageTextRecords: Map<number, PageTextRecord>; // Phase 6.2: keyed by page_index
  exportPath: string;
}