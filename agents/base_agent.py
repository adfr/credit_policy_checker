from abc import ABC, abstractmethod
from typing import Any, Dict
import openai
import os

class BaseAgent(ABC):
    """Base class for all compliance checking agents"""
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    def process(self, prompt: str) -> Any:
        """Process a prompt using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": f"You are a {self.agent_type} agent for credit policy compliance checking."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error processing request: {str(e)}"
    
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