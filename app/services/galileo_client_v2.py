"""
Simplified Galileo AI Observability Client V2
Provides Galileo-enabled OpenAI client with proper initialization
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from galileo import galileo_context
    from galileo.openai import openai
    GALILEO_AVAILABLE = True
except ImportError:
    import openai
    GALILEO_AVAILABLE = False
    print("Warning: Galileo not available, falling back to regular OpenAI")


class GalileoClientV2:
    """Simplified OpenAI client with Galileo observability"""

    def __init__(self, project_name: str = None, log_stream: str = None):
        self.project_name = project_name or os.environ.get('GALILEO_PROJECT_NAME', 'policy_compliance_checker')
        self.log_stream = log_stream or 'policy_processing'
        self.galileo_enabled = False

        if GALILEO_AVAILABLE and os.environ.get('GALILEO_API_KEY'):
            try:
                # Initialize Galileo context with project and log stream
                galileo_context.init(
                    project=self.project_name,
                    log_stream=self.log_stream
                )

                # Use Galileo's wrapped OpenAI client for automatic tracing
                self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                self.galileo_enabled = True

                print(f"✅ Galileo initialized for project: {self.project_name}, log_stream: {self.log_stream}")

            except Exception as e:
                print(f"⚠️  Could not initialize Galileo: {str(e)}")
                # Fallback to regular OpenAI
                import openai as regular_openai
                self.client = regular_openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        else:
            # Use regular OpenAI if Galileo is not available
            import openai as regular_openai
            self.client = regular_openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            if not GALILEO_AVAILABLE:
                print("⚠️  Galileo package not available")
            elif not os.environ.get('GALILEO_API_KEY'):
                print("⚠️  GALILEO_API_KEY not set")

    def chat_completion(self, **kwargs) -> Any:
        """
        Create chat completion with automatic Galileo tracing
        """
        try:
            # The Galileo-wrapped client automatically traces calls
            response = self.client.chat.completions.create(**kwargs)

            # Explicitly flush traces for immediate upload
            if self.galileo_enabled and GALILEO_AVAILABLE:
                try:
                    galileo_context.flush()
                except:
                    pass  # Ignore flush errors

            return response
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            raise e

    def start_session(self, session_id: str = None):
        """Start a new Galileo session for grouping traces"""
        if self.galileo_enabled and GALILEO_AVAILABLE:
            try:
                if session_id:
                    galileo_context.start_session(external_id=session_id)
                else:
                    galileo_context.start_session()
                print(f"📝 Started Galileo session: {session_id or 'auto-generated'}")
            except Exception as e:
                print(f"⚠️  Could not start session: {str(e)}")

    def flush_traces(self):
        """Manually flush traces to Galileo"""
        if self.galileo_enabled and GALILEO_AVAILABLE:
            try:
                galileo_context.flush()
                print("✅ Traces flushed to Galileo")
            except Exception as e:
                print(f"⚠️  Could not flush traces: {str(e)}")


# Global instance for easy access
_galileo_client_v2 = None

def get_galileo_client_v2() -> GalileoClientV2:
    """Get or create the global Galileo client instance"""
    global _galileo_client_v2
    if _galileo_client_v2 is None:
        _galileo_client_v2 = GalileoClientV2()
    return _galileo_client_v2