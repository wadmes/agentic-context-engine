"""Basic tests for LiteLLM client integration."""

import unittest
from unittest.mock import patch, MagicMock


class TestLiteLLMClient(unittest.TestCase):
    """Test LiteLLM client functionality."""

    def test_import(self):
        """Test that LiteLLM client can be imported."""
        try:
            from ace.llm_providers import LiteLLMClient
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import LiteLLMClient")

    @patch('ace.llm_providers.litellm_client.completion')
    def test_basic_completion(self, mock_completion):
        """Test basic completion functionality."""
        from ace.llm_providers import LiteLLMClient

        # Mock the response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        mock_response.model = "gpt-3.5-turbo"
        mock_completion.return_value = mock_response

        # Create client and test
        client = LiteLLMClient(model="gpt-3.5-turbo")
        response = client.complete("Test prompt")

        self.assertEqual(response.text, "Test response")
        self.assertIn("usage", response.raw)

    def test_parameter_filtering(self):
        """Test that ACE-specific parameters are filtered."""
        from ace.llm_providers import LiteLLMClient

        with patch('ace.llm_providers.litellm_client.completion') as mock:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
            mock_response.usage = None
            mock_response.model = "test"
            mock.return_value = mock_response

            client = LiteLLMClient(model="test")
            client.complete("Test", refinement_round=1, max_refinement_rounds=3)

            # Check that filtered params aren't in the call
            call_kwargs = mock.call_args[1]
            self.assertNotIn('refinement_round', call_kwargs)
            self.assertNotIn('max_refinement_rounds', call_kwargs)


if __name__ == '__main__':
    unittest.main()