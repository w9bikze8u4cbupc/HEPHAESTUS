/**
 * Phase 6.1 Main Application
 * 
 * Read-only forensic inspection UI for Hephaestus extraction artifacts.
 * Implements View 1: Extraction Health Panel as the primary interface.
 */

import React, { useState } from 'react';
import { ArtifactBundle } from './types';
import { ArtifactLoader } from './components/ArtifactLoader';
import { ExtractionHealthPanel } from './components/ExtractionHealthPanel';
import './App.css';

export const App: React.FC = () => {
  const [artifacts, setArtifacts] = useState<ArtifactBundle | null>(null);

  const handleArtifactsLoaded = (bundle: ArtifactBundle) => {
    setArtifacts(bundle);
  };

  const handleReset = () => {
    setArtifacts(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 Hephaestus Inspector</h1>
        <p className="app-subtitle">Read-only forensic inspection of extraction artifacts</p>
        {artifacts && (
          <div className="artifact-info">
            <span className="export-path">Export: {artifacts.exportPath}</span>
            <span className="source-pdf">PDF: {artifacts.manifest.source_pdf}</span>
            <span className="extraction-time">
              Extracted: {new Date(artifacts.manifest.extraction_timestamp).toLocaleString()}
            </span>
            <button onClick={handleReset} className="reset-button">
              Load Different Export
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        {!artifacts ? (
          <ArtifactLoader onArtifactsLoaded={handleArtifactsLoaded} />
        ) : (
          <div className="inspection-views">
            {/* View 1: Extraction Health Panel - FIRST AND PRIMARY */}
            <ExtractionHealthPanel 
              health={artifacts.manifest.extraction_health}
              extractionLog={artifacts.extractionLog}
            />
            
            {/* Future views will be added here in strict order:
                View 2: Failure Viewer
                View 3: Component Inventory  
                View 4: Component Drilldown */}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>
          Phase 6.1: Inspection-First UI | 
          Manifest is truth | 
          Logs are first-class data | 
          Failures visible by default
        </p>
      </footer>
    </div>
  );
};