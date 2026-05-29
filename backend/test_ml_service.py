import unittest
from unittest.mock import patch, MagicMock
from app.services.ml_service import generate_tags

@patch('app.services.ml_service.mimetypes.guess_type')
@patch('app.services.ml_service.types.Part.from_bytes')
@patch('app.services.ml_service.genai.Client')
def test_generate_tags_with_mock(mock_client_class, mock_part_from_bytes, mock_guess_type):
    # Setup mocks
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Mock mimetypes.guess_type to return a valid mime type
    mock_guess_type.return_value = ('image/jpeg', None)
    
    # Mock types.Part.from_bytes to return a mock part
    mock_part = MagicMock()
    mock_part_from_bytes.return_value = mock_part
    
    # Mock the response from models.generate_content
    mock_response = MagicMock()
    mock_response.text = '["portrait", "moody", "lighting"]'
    mock_client.models.generate_content.return_value = mock_response

    # Call the function with file mocking
    with patch('builtins.open', unittest.mock.mock_open(read_data=b'dummy data')):
        tags = generate_tags("dummy_path.jpg")
    
    assert isinstance(tags, list)
    assert len(tags) == 3
    assert tags == ["portrait", "moody", "lighting"]
    
    # Verify the mock was called
    mock_client.models.generate_content.assert_called()
    
@patch('app.services.ml_service.mimetypes.guess_type')
@patch('app.services.ml_service.types.Part.from_bytes')
@patch('app.services.ml_service.genai.Client')
def test_generate_tags_fallback_models(mock_client_class, mock_part_from_bytes, mock_guess_type):
    """Test that fallback models are tried when primary fails."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_guess_type.return_value = ('image/jpeg', None)
    mock_part = MagicMock()
    mock_part_from_bytes.return_value = mock_part
    
    # Primary model (gemini-2.5-flash) fails, secondary (gemini-1.5-flash) succeeds
    mock_response_success = MagicMock()
    mock_response_success.text = '["landscape", "sunset"]'
    
    mock_client.models.generate_content.side_effect = [
        Exception("503 Model overloaded"),  # First call fails
        mock_response_success,              # Second call succeeds
    ]

    with patch('builtins.open', unittest.mock.mock_open(read_data=b'dummy data')):
        tags = generate_tags("dummy_path.jpg")
    
    assert tags == ["landscape", "sunset"]
    # Should have been called twice (once for each model tried)
    assert mock_client.models.generate_content.call_count == 2
    
