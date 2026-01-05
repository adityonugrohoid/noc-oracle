import pytest
from unittest.mock import MagicMock, patch, Mock
from src.engine import NOCEngine

@pytest.fixture
def mock_vectorstore():
    """Creates a mock vectorstore with sample documents."""
    mock_doc1 = Mock()
    mock_doc1.page_content = "Software Alarms - S-304\n\nFiber Link Degradation: Signal loss detected."
    mock_doc1.metadata = {"Category": "Software Alarms", "Error_Code": "S-304"}
    
    mock_doc2 = Mock()
    mock_doc2.page_content = "Hardware Alarms - E-101\n\nPower supply issue detected."
    mock_doc2.metadata = {"Category": "Hardware Alarms", "Error_Code": "E-101"}
    
    return [mock_doc1, mock_doc2]

def test_extract_error_codes():
    """Tests the error code extraction regex."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma"):
            engine = NOCEngine()
    
    # Test various formats
    codes = engine._extract_error_codes("I have error S-304 and E101")
    assert "S-304" in codes
    assert "E101" in codes
    
    # Case insensitive
    codes = engine._extract_error_codes("error s304")
    assert "s304" in codes

def test_get_solution_success(mock_vectorstore):
    """Tests successful RAG retrieval and response generation."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma") as mock_chroma:
            engine = NOCEngine()
            
            # Mock the vectorstore similarity search
            engine.vectorstore.similarity_search = MagicMock(return_value=mock_vectorstore)
            
            # Mock the LLM response
            mock_response = MagicMock()
            mock_response.text = "To fix S-304, check the fiber connection."
            engine.model.generate_content = MagicMock(return_value=mock_response)
            
            result = engine.get_solution("How to fix S-304")
            
            assert "answer" in result
            assert "source_documents" in result
            assert "fiber" in result["answer"].lower()
            assert len(result["source_documents"]) > 0

def test_get_solution_no_documents():
    """Tests behavior when no documents are found."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma"):
            engine = NOCEngine()
            
            # Mock empty search result
            engine.vectorstore.similarity_search = MagicMock(return_value=[])
            
            result = engine.get_solution("NonexistentCode-999")
            
            assert "No relevant information found" in result["answer"]
            assert len(result["source_documents"]) == 0

def test_get_solution_error_handling():
    """Tests error handling when LLM call fails."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma"):
            engine = NOCEngine()
            
            # Mock vectorstore to raise exception
            engine.vectorstore.similarity_search = MagicMock(side_effect=Exception("DB Connection Failed"))
            
            result = engine.get_solution("S-304")
            
            assert "Error processing request" in result["answer"]
            assert "DB Connection Failed" in result["answer"]

def test_get_baseline_response():
    """Tests non-RAG baseline response generation."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma"):
            engine = NOCEngine()
            
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.text = "Check the power supply and reset the device."
            engine.model.generate_content = MagicMock(return_value=mock_response)
            
            response = engine.get_baseline_response("Device not working")
            
            assert "power supply" in response.lower()

def test_hybrid_search_prioritization(mock_vectorstore):
    """Tests that error code matching prioritizes correct documents."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.engine.Chroma"):
            engine = NOCEngine()
            
            # Mock vectorstore with documents in wrong order
            wrong_order = [mock_vectorstore[1], mock_vectorstore[0]]  # E-101 before S-304
            engine.vectorstore.similarity_search = MagicMock(return_value=wrong_order)
            
            # Mock LLM
            mock_response = MagicMock()
            mock_response.text = "Solution for S-304"
            engine.model.generate_content = MagicMock(return_value=mock_response)
            
            result = engine.get_solution("s304")  # Query for S-304
            
            # The first document should now be S-304 (reordered by hybrid search)
            # We can verify by checking the prompt sent to LLM contains S-304 first
            call_args = engine.model.generate_content.call_args[0][0]
            
            # S-304 should appear before E-101 in the context
            s304_pos = call_args.find("S-304")
            e101_pos = call_args.find("E-101")
            
            assert s304_pos < e101_pos, "S-304 should be prioritized over E-101"

if __name__ == "__main__":
    import sys
    try:
        test_extract_error_codes()
        print("test_extract_error_codes passed")
        test_get_solution_no_documents()
        print("test_get_solution_no_documents passed")
        test_get_solution_error_handling()
        print("test_get_solution_error_handling passed")
        test_get_baseline_response()
        print("test_get_baseline_response passed")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)

