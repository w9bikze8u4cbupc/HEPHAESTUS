"""Test configuration for pytest."""

import logging
import os
import pytest


@pytest.fixture(autouse=True)
def configure_test_logging():
    """Configure logging for tests to be minimal."""
    # Set environment variable to ensure minimal logging during tests
    os.environ['HEPHAESTUS_LOG_LEVEL'] = 'WARNING'
    
    # Also configure root logger to be quiet
    logging.getLogger().setLevel(logging.WARNING)
    
    # Specifically quiet the hephaestus loggers
    for logger_name in ['hephaestus.pdf.images', 'hephaestus.text.spatial']:
        logging.getLogger(logger_name).setLevel(logging.ERROR)