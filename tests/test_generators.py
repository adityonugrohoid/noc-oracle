import pytest
import pathlib
from unittest.mock import MagicMock, patch
from src.generators import generate_manual

def test_generate_manual_success():
    """Tests successful manual generation with Gemini."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.generators.genai") as mock_genai:
            # Setup mock model
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            # Mock response with realistic manual content
            mock_response = MagicMock()
            mock_response.text = """# Orbit-5G Base Station Troubleshooting Manual

## Hardware Alarms

### E-101: Power Unit Failure

**Description**: Primary power supply unit has failed.

**Resolution Procedure**:
1. Check voltage at test point TP4
2. Replace power supply unit
3. Verify LED indicators

## Software Alarms

### S-304: Fiber Link Degradation

**Description**: Signal loss on fiber connection.

**Resolution Procedure**:
1. Clean fiber connectors
2. Check cable for damage
3. Run diagnostic: `nebula-cli check-link`
"""
            mock_model.generate_content.return_value = mock_response
            
            # Mock file operations
            with patch("pathlib.Path.mkdir"), \
                 patch("builtins.open", create=True) as mock_open:
                
                generate_manual()
                
                # Verify model was called
                mock_model.generate_content.assert_called_once()
                
                # Verify file write was attempted
                mock_open.assert_called_once()

def test_generate_manual_missing_api_key():
    """Tests behavior when API key is missing."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("builtins.print") as mock_print:
            generate_manual()
            
            # Should print error message
            mock_print.assert_called_with("Error: GEMINI_API_KEY not found in environment variables.")

def test_generate_manual_api_error():
    """Tests error handling when API call fails."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.generators.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            # Simulate API error
            mock_model.generate_content.side_effect = Exception("API Rate Limit")
            
            with patch("builtins.print") as mock_print:
                generate_manual()
                
                # Should catch and print error
                assert any("Error during generation" in str(call) for call in mock_print.call_args_list)

def test_generate_manual_model_initialization_error():
    """Tests error handling when model initialization fails."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.generators.genai") as mock_genai:
            # Simulate model initialization failure
            mock_genai.GenerativeModel.side_effect = Exception("Model not available")
            
            with patch("builtins.print") as mock_print:
                generate_manual()
                
                # Should catch and print error
                assert any("Error initializing model" in str(call) for call in mock_print.call_args_list)

def test_generate_manual_output_structure():
    """Tests that generated content follows expected structure."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch("src.generators.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            mock_response = MagicMock()
            mock_response.text = """# Manual Title
## Hardware Alarms
### E-101: Error
**Description**: Test
**Resolution Procedure**:
1. Step 1
"""
            mock_model.generate_content.return_value = mock_response
            
            # Capture written content
            written_content = None
            
            def mock_write(content):
                nonlocal written_content
                written_content = content
            
            with patch("pathlib.Path.mkdir"), \
                 patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.write = mock_write
                mock_open.return_value = mock_file
                
                generate_manual()
                
                # Verify structure
                assert written_content is not None
                assert "# Manual Title" in written_content
                assert "## Hardware Alarms" in written_content
                assert "### E-101" in written_content

if __name__ == "__main__":
    import sys
    try:
        test_generate_manual_missing_api_key()
        print("test_generate_manual_missing_api_key passed")
        test_generate_manual_model_initialization_error()
        print("test_generate_manual_model_initialization_error passed")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)

