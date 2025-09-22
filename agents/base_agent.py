from abc import ABC, abstractmethod
from typing import Any, Dict
import os
import json
import sys

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, app_path)

from services.galileo_client_v2 import get_galileo_client_v2

class BaseAgent(ABC):
    """Base class for all compliance checking agents"""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        # Use simplified Galileo V2 client for automatic observability
        self.galileo_client = get_galileo_client_v2()
        self.client = self.galileo_client.client
    
    def process(self, prompt: str) -> Any:
        """Process a prompt using OpenAI API with Galileo logging"""
        try:
            # Use Galileo V2 client's chat_completion for automatic tracing
            response = self.galileo_client.chat_completion(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": f"You are a {self.agent_type} agent for credit policy compliance checking."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            # Return a valid JSON error response instead of a string
            # Galileo will automatically capture this error
            error_response = {
                "passed": False,
                "reason": f"OpenAI API error: {str(e)}",
                "confidence": 0.0,
                "error": True
            }
            return json.dumps(error_response)
    
    @abstractmethod
    def check(self, policy_check: Dict, credit_data: Dict) -> Dict:
        """Check compliance for a specific policy requirement"""
        pass

class GeneralAgent(BaseAgent):
    """Concrete agent for general-purpose AI tasks that don't require compliance checking"""
    
    def __init__(self, agent_type: str):
        super().__init__(agent_type)
    
    def check(self, policy_check: Dict, credit_data: Dict) -> Dict:
        """Not used for general tasks - this is a general-purpose agent"""
        return {
            'check_type': 'general',
            'passed': True,
            'reason': 'General agent - use process() method instead'
        }