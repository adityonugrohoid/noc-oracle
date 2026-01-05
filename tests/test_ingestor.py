import pytest
import pathlib
from unittest.mock import MagicMock, patch, mock_open
from src.ingestor import ingest_manual

SAMPLE_MANUAL = """# Orbit-5G Troubleshooting Guide

## Hardware Alarms

### E-101: Power Unit Failure

**Description**: Primary power supply has failed.

**Resolution Procedure**:
1. Check voltage at test point TP4
2. Replace the power supply unit
3. Verify all LED indicators return to green

## Software Alarms

### S-304: Fiber Link Degradation

**Description**: Signal loss detected on fiber optic connection.

**Resolution Procedure**:
1. Clean fiber connectors with lint-free cloth
2. Inspect cable for physical damage
3. Run diagnostic: `nebula-cli check-link`
"""

def test_ingest_manual_success():
    """Tests successful manual ingestion and vectorization."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=SAMPLE_MANUAL)), \
             patch("os.path.exists", return_value=True), \
             patch("shutil.rmtree") as mock_rmtree, \
             patch("src.ingestor.GoogleGenerativeAIEmbeddings") as mock_embeddings, \
             patch("src.ingestor.Chroma") as mock_chroma:
            
            # Mock Chroma.from_documents
            mock_vectorstore = MagicMock()
            mock_chroma.from_documents.return_value = mock_vectorstore
            
            ingest_manual()
            
            # Verify old DB was removed
            mock_rmtree.assert_called_once_with("./chroma_db")
            
            # Verify Chroma.from_documents was called
            mock_chroma.from_documents.assert_called_once()
            
            # Verify documents were processed
            call_args = mock_chroma.from_documents.call_args
            docs = call_args.kwargs['documents']
            
            # Should have split by headers
            assert len(docs) > 0
            
            # Check metadata injection worked (Error Code should be in content)
            assert any("E-101" in doc.page_content for doc in docs)

def test_ingest_manual_missing_api_key():
    """Tests behavior when API key is missing."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("builtins.print") as mock_print:
            ingest_manual()
            
            mock_print.assert_called_with("Error: GEMINI_API_KEY not found.")

def test_ingest_manual_missing_file():
    """Tests behavior when manual file doesn't exist."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("pathlib.Path.exists", return_value=False):
            with patch("builtins.print") as mock_print:
                ingest_manual()
                
                # Should print error about missing file
                assert any("Manual file not found" in str(call) for call in mock_print.call_args_list)

def test_ingest_manual_cleanup_skipped_if_no_db():
    """Tests that cleanup is skipped if database doesn't exist."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=SAMPLE_MANUAL)), \
             patch("os.path.exists", return_value=False), \
             patch("shutil.rmtree") as mock_rmtree, \
             patch("src.ingestor.GoogleGenerativeAIEmbeddings"), \
             patch("src.ingestor.Chroma"):
            
            ingest_manual()
            
            # rmtree should NOT be called if DB doesn't exist
            mock_rmtree.assert_not_called()

def test_ingest_manual_header_splitting():
    """Tests that MarkdownHeaderTextSplitter correctly splits sections."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=SAMPLE_MANUAL)), \
             patch("os.path.exists", return_value=False), \
             patch("src.ingestor.GoogleGenerativeAIEmbeddings"), \
             patch("src.ingestor.Chroma") as mock_chroma:
            
            mock_vectorstore = MagicMock()
            mock_chroma.from_documents.return_value = mock_vectorstore
            
            ingest_manual()
            
            # Get the documents that were passed to Chroma
            call_args = mock_chroma.from_documents.call_args
            docs = call_args.kwargs['documents']
            
            # Should have at least 2 error codes (E-101 and S-304)
            error_codes = [doc.metadata.get('Error_Code', '') for doc in docs]
            
            assert 'E-101: Power Unit Failure' in error_codes
            assert 'S-304: Fiber Link Degradation' in error_codes

def test_ingest_manual_metadata_injection():
    """Tests that metadata is properly injected into page content."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=SAMPLE_MANUAL)), \
             patch("os.path.exists", return_value=False), \
             patch("src.ingestor.GoogleGenerativeAIEmbeddings"), \
             patch("src.ingestor.Chroma") as mock_chroma:
            
            mock_vectorstore = MagicMock()
            mock_chroma.from_documents.return_value = mock_vectorstore
            
            ingest_manual()
            
            # Get the documents
            call_args = mock_chroma.from_documents.call_args
            docs = call_args.kwargs['documents']
            
            # Find a specific error code document
            e101_doc = next((d for d in docs if 'E-101' in d.metadata.get('Error_Code', '')), None)
            
            assert e101_doc is not None
            # The Category should be prepended to content
            assert 'Hardware Alarms' in e101_doc.page_content
            # The Error Code should be prepended to content
            assert 'E-101' in e101_doc.page_content

if __name__ == "__main__":
    import sys
    try:
        test_ingest_manual_missing_api_key()
        print("test_ingest_manual_missing_api_key passed")
        test_ingest_manual_missing_file()
        print("test_ingest_manual_missing_file passed")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)

