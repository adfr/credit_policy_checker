from typing import Dict, List
from app.parsers.document_parser import DocumentParser
from app.services.policy_agent_extractor import PolicyAgentExtractor
from app.services.agent_compliance_checker import AgentComplianceChecker
import json

class DocumentProcessor:
    """Processes documents using agent-based policy extraction and compliance checking"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.agent_extractor = PolicyAgentExtractor()
        self.compliance_checker = AgentComplianceChecker()
    
    def extract_policy_agents(self, file_path: str, domain_hint: str = None) -> Dict:
        """Extract policy agents from a policy document"""
        # Parse the document to get text content
        parsed_doc = self.parser.parse_document(file_path)
        
        if 'error' in parsed_doc:
            return parsed_doc
        
        # Get text content for agent extraction
        text_content = parsed_doc.get('text_content', '')
        if not text_content:
            return {
                'error': 'No text content found in document for agent extraction',
                'document_summary': self.parser.get_document_summary(parsed_doc)
            }
        
        # Extract policy agents using LLM
        extracted_agents = self.agent_extractor.extract_policy_agents(text_content, domain_hint)
        
        if 'error' in extracted_agents:
            return extracted_agents
        
        # Validate extracted agents
        validation_results = self.agent_extractor.validate_agents(extracted_agents)
        
        return {
            'extracted_agents': extracted_agents,
            'validation': validation_results,
            'document_summary': self.parser.get_document_summary(parsed_doc),
            'text_content_length': len(text_content),
            'processing_status': 'success'
        }
    
    def check_document_compliance(self, file_path: str, selected_agents: List[Dict], applicant_data: Dict = None) -> Dict:
        """Check document compliance using selected policy agents"""
        # Parse the document to get text content
        parsed_doc = self.parser.parse_document(file_path)
        
        if 'error' in parsed_doc:
            return parsed_doc
        
        # Get text content for compliance checking
        text_content = parsed_doc.get('text_content', '')
        if not text_content:
            return {
                'error': 'No text content found in document for compliance checking',
                'document_summary': self.parser.get_document_summary(parsed_doc)
            }
        
        # Run compliance check using selected agents
        compliance_results = self.compliance_checker.check_compliance(
            text_content, 
            selected_agents, 
            applicant_data
        )
        
        return {
            'compliance_results': compliance_results,
            'document_summary': self.parser.get_document_summary(parsed_doc),
            'selected_agents_summary': self.compliance_checker.get_agent_summary(selected_agents),
            'processing_status': 'success'
        }
    
    def refine_extracted_agents(self, extracted_agents: Dict, user_feedback: Dict) -> Dict:
        """Refine extracted agents based on user feedback"""
        return self.agent_extractor.refine_agents(extracted_agents, user_feedback)
    
    def get_agent_data_requirements(self, selected_agents: List[Dict]) -> Dict:
        """Get data requirements for selected agents"""
        return self.compliance_checker.get_agent_summary(selected_agents)
    
    def extract_text(self, file_path: str) -> str:
        """Extract plain text from a document file"""
        try:
            parsed_doc = self.parser.parse_document(file_path)
            if 'error' in parsed_doc:
                return f"Error extracting text: {parsed_doc['error']}"
            
            # Get the text content from the parsed document
            text_content = parsed_doc.get('text_content', '')
            if not text_content:
                return "No text content found in document"
            
            return text_content
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    # Legacy method - kept for backward compatibility but discouraged
    def process_document(self, file_path: str, domain_hint: str = None) -> Dict:
        """Legacy method - use extract_policy_agents for new implementations"""
        return self.extract_policy_agents(file_path, domain_hint)

    def validate_document_completeness(self, parsed_doc: Dict) -> Dict:
        """Validate if document contains sufficient information for policy extraction"""
        validation = {
            'is_complete': True,
            'missing_elements': [],
            'recommendations': [],
            'confidence_score': 1.0
        }
        
        # Check for text content
        if not parsed_doc.get('text_content') or len(parsed_doc['text_content'].strip()) < 100:
            validation['missing_elements'].append('substantial_text_content')
            validation['confidence_score'] -= 0.3
        
        # Check for structured data
        has_tables = len(parsed_doc.get('tables', [])) > 0
        has_charts = len(parsed_doc.get('charts', [])) > 0
        
        if not has_tables and not has_charts:
            validation['missing_elements'].append('structured_data')
            validation['confidence_score'] -= 0.2
        
        # Check for policy indicators
        text = parsed_doc.get('text_content', '').lower()
        policy_keywords = ['policy', 'requirement', 'compliance', 'standard', 'threshold']
        policy_indicators = sum(1 for keyword in policy_keywords if keyword in text)
        
        if policy_indicators < 2:
            validation['missing_elements'].append('policy_indicators')
            validation['confidence_score'] -= 0.2
        
        # Generate recommendations
        if 'substantial_text_content' in validation['missing_elements']:
            validation['recommendations'].append("Document may need additional text content for comprehensive policy extraction")
        
        if 'structured_data' in validation['missing_elements']:
            validation['recommendations'].append("Consider adding tables or charts with specific metrics and thresholds")
        
        if 'policy_indicators' in validation['missing_elements']:
            validation['recommendations'].append("Document may benefit from clearer policy language and requirements")
        
        validation['is_complete'] = validation['confidence_score'] >= 0.6
        
        return validation