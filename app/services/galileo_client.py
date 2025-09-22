"""
Galileo AI Observability Client
Provides Galileo-enabled OpenAI client and workflow tracking for LLM observability
"""

import os
from typing import Dict, Any, Optional
import json

try:
    from galileo import log
    import openai
    GALILEO_AVAILABLE = True
except ImportError:
    # Fallback to regular OpenAI if Galileo is not available
    import openai
    GALILEO_AVAILABLE = False
    print("Warning: Galileo not available, falling back to regular OpenAI")

class GalileoClient:
    """Enhanced OpenAI client with Galileo observability"""

    def __init__(self, project_name: str = None):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        self.project_name = project_name or os.environ.get('GALILEO_PROJECT_NAME', 'policy_compliance_checker')

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

        # Initialize Galileo if available
        if GALILEO_AVAILABLE and os.environ.get('GALILEO_API_KEY'):
            try:
                # Configure Galileo with proper initialization
                from galileo.config import GalileoConfig

                # Create a proper config object
                config = GalileoConfig(
                    api_key=os.environ.get('GALILEO_API_KEY'),
                    console_url=os.environ.get('GALILEO_CONSOLE_URL', 'https://console.galileo.ai')
                )

                # Set the config globally
                import galileo.config as galileo_config
                galileo_config._config = config

                print(f"✅ Galileo observability initialized for project: {self.project_name}")
                print(f"   API Key: {os.environ.get('GALILEO_API_KEY')[:10]}...")
                print(f"   Console URL: {os.environ.get('GALILEO_CONSOLE_URL')}")
                self.galileo_enabled = True

            except Exception as e:
                print(f"⚠️  Warning: Could not initialize Galileo: {str(e)}")
                # Fallback to simpler config
                try:
                    import galileo.config as galileo_config
                    galileo_config.api_key = os.environ.get('GALILEO_API_KEY')
                    self.galileo_enabled = True
                    print(f"✅ Galileo fallback initialization successful")
                except Exception as e2:
                    print(f"⚠️  Fallback also failed: {str(e2)}")
                    self.galileo_enabled = False
        else:
            self.galileo_enabled = False
            if not GALILEO_AVAILABLE:
                print("⚠️  Galileo package not available")
            elif not os.environ.get('GALILEO_API_KEY'):
                print("⚠️  GALILEO_API_KEY not set in environment")

    @log
    def chat_completion(self, **kwargs) -> Any:
        """
        Create chat completion with automatic Galileo logging using @log decorator
        """
        try:
            # Execute the OpenAI API call
            response = self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            raise e

# Global instance for easy access
_galileo_client = None

def get_galileo_client() -> GalileoClient:
    """Get or create the global Galileo client instance"""
    global _galileo_client
    if _galileo_client is None:
        _galileo_client = GalileoClient()
    return _galileo_client