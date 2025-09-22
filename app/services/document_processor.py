from typing import Dict, List
from app.parsers.document_parser import DocumentParser
from app.services.policy_agent_extractor import PolicyAgentExtractor
from app.services.agent_compliance_checker import AgentComplianceChecker
from app.services.galileo_client_v2 import get_galileo_client_v2
import json
import os
import sys
import time

# Add the project root and graph-db directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
graph_db_path = os.path.join(project_root, 'graph-db')
sys.path.insert(0, project_root)
sys.path.insert(0, graph_db_path)

from document_to_graph import DocumentToGraph

class DocumentProcessor:
    """Processes documents using agent-based policy extraction and compliance checking"""

    def __init__(self):
        self.parser = DocumentParser()
        self.agent_extractor = PolicyAgentExtractor()
        self.compliance_checker = AgentComplianceChecker()
        self.graph_builder = None
        self._init_graph_builder()

        # Initialize Galileo V2 client with session support
        self.galileo_client = get_galileo_client_v2()
        print(f"DocumentProcessor initialized with Galileo V2 observability")
        print(f"  Project: {self.galileo_client.project_name}")
        print(f"  Log Stream: {self.galileo_client.log_stream}")
    
    def extract_policy_agents(self, file_path: str, domain_hint: str = None) -> Dict:
        """Extract policy agents from a policy document"""
        # Use extraction-specific client
        from services.galileo_client_v2 import GalileoClientV2
        extraction_client = GalileoClientV2(log_stream="policy_extraction")

        # Start a new Galileo session for policy extraction
        session_id = f"policy_extraction_{int(time.time())}"
        extraction_client.start_session(session_id)

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

        # Create a new agent extractor with the extraction client to avoid dual tracing
        from services.policy_agent_extractor import PolicyAgentExtractor
        extraction_agent_extractor = PolicyAgentExtractor(galileo_client=extraction_client)

        # Extract policy agents using LLM (traces will be captured for each chunk)
        extracted_agents = extraction_agent_extractor.extract_policy_agents(text_content, domain_hint)

        if 'error' in extracted_agents:
            return extracted_agents

        # Validate extracted agents
        validation_results = extraction_agent_extractor.validate_agents(extracted_agents)

        # Auto-save extracted agents with document name
        document_summary = self.parser.get_document_summary(parsed_doc)

        # Extract actual filename from file_path
        import os
        actual_filename = os.path.basename(file_path)
        policy_name = actual_filename
        if policy_name.endswith('.pdf'):
            policy_name = policy_name[:-4]  # Remove .pdf extension

        save_metadata = {
            'filename': actual_filename,
            'domain_hint': domain_hint,
            'auto_saved': True,
            'document_summary': document_summary
        }

        save_result = extraction_agent_extractor.save_extracted_agents(
            policy_name,
            extracted_agents,
            save_metadata
        )

        # Flush traces to ensure they are sent to Galileo
        extraction_client.flush_traces()

        return {
            'extracted_agents': extracted_agents,
            'validation': validation_results,
            'document_summary': document_summary,
            'text_content_length': len(text_content),
            'save_result': save_result,
            'processing_status': 'success',
            'galileo_session_id': session_id,
            'galileo_log_stream': 'policy_extraction'
        }
    
    def check_document_compliance(self, file_path: str, selected_agents: List[Dict], applicant_data: Dict = None) -> Dict:
        """Check document compliance using selected policy agents"""
        # Use compliance-specific client
        from services.galileo_client_v2 import GalileoClientV2
        compliance_client = GalileoClientV2(log_stream="compliance_checking")

        # Start a new Galileo session for this compliance check
        session_id = f"compliance_check_{int(time.time())}"
        compliance_client.start_session(session_id)

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

        # Run compliance check using selected agents (traces will be captured automatically)
        compliance_results = self.compliance_checker.check_compliance(
            text_content,
            selected_agents,
            applicant_data
        )

        # Flush traces to ensure they are sent to Galileo
        compliance_client.flush_traces()

        return {
            'compliance_results': compliance_results,
            'document_summary': self.parser.get_document_summary(parsed_doc),
            'selected_agents_summary': self.compliance_checker.get_agent_summary(selected_agents),
            'processing_status': 'success',
            'galileo_session_id': session_id,
            'galileo_log_stream': 'compliance_checking'
        }
    
    def refine_extracted_agents(self, extracted_agents: Dict, user_feedback: Dict) -> Dict:
        """Refine extracted agents based on user feedback"""
        # Create a refinement-specific client
        from services.galileo_client_v2 import GalileoClientV2
        from services.policy_agent_extractor import PolicyAgentExtractor

        refinement_client = GalileoClientV2(log_stream="agent_refinement")
        refinement_extractor = PolicyAgentExtractor(galileo_client=refinement_client)

        # Start session for refinement
        session_id = f"agent_refinement_{int(time.time())}"
        refinement_client.start_session(session_id)

        result = refinement_extractor.refine_agents(extracted_agents, user_feedback)

        # Flush traces
        refinement_client.flush_traces()

        # Add session info to result if it's a dict
        if isinstance(result, dict):
            result['galileo_session_id'] = session_id
            result['galileo_log_stream'] = 'agent_refinement'

        return result

    def check_document_compliance_automatic(
        self,
        file_path: str,
        available_agents: Dict,
        applicant_data: Dict = None,
        min_relevance_score: float = 0.3,
        max_agents: int = 20
    ) -> Dict:
        """
        Check document compliance using automatic agent selection

        Args:
            file_path: Path to the credit memo/document
            available_agents: All available agents from policy extraction
            applicant_data: Optional structured applicant data
            min_relevance_score: Minimum relevance score for agent selection
            max_agents: Maximum number of agents to auto-select

        Returns:
            Compliance results with automatic selection metadata
        """
        # Use automatic-specific client
        from services.galileo_client_v2 import GalileoClientV2
        from services.automatic_agent_selector import AutomaticAgentSelector

        auto_compliance_client = GalileoClientV2(log_stream="automatic_compliance")

        # Start a new Galileo session for automatic compliance check
        session_id = f"auto_compliance_{int(time.time())}"
        auto_compliance_client.start_session(session_id)

        try:
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

            # Step 1: Automatically select relevant agents
            auto_selector = AutomaticAgentSelector()
            selection_result = auto_selector.select_agents_automatically(
                text_content,
                available_agents,
                min_score=min_relevance_score,
                max_agents=max_agents
            )

            selected_agents = selection_result['selected_agents']

            if not selected_agents:
                return {
                    'error': 'No relevant agents found for automatic selection',
                    'loan_detection': selection_result.get('loan_detection', {}),
                    'selection_metadata': selection_result.get('selection_metadata', {}),
                    'document_summary': self.parser.get_document_summary(parsed_doc)
                }

            # Step 1.5: Set up hierarchical workflow logging for automatic compliance
            # Convert available_agents dict to list for workflow logging
            all_available_agents_list = []
            for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']:
                agents = available_agents.get(agent_type, [])
                all_available_agents_list.extend(agents)

            # Create a workflow logger instance for automatic compliance
            from app.services.galileo_agent_workflow_logger import get_agent_workflow_logger
            workflow_logger = get_agent_workflow_logger(
                project_name="policy_compliance",
                log_stream="automatic_compliance"
            )

            # Start the main workflow for automatic compliance check
            document_id = f"auto_{int(time.time())}"
            workflow = workflow_logger.start_credit_evaluation_workflow(document_id, "automatic_compliance")

            # Start automatic selection sub-workflow
            workflow_logger.start_automatic_selection_span(
                document_content=text_content,
                all_available_agents=all_available_agents_list,
                selection_metadata={
                    "min_relevance_score": min_relevance_score,
                    "max_agents": max_agents,
                    "selection_mode": "automatic"
                }
            )

            # Log loan detection step within the selection span
            workflow_logger.log_loan_detection_step(selection_result.get('loan_detection', {}))

            # Log agent scoring step within the selection span
            workflow_logger.log_agent_scoring_step(all_available_agents_list, selected_agents)

            # Complete automatic selection span
            workflow_logger.complete_automatic_selection_span(selected_agents)

            # Start agent execution sub-workflow
            workflow_logger.start_agent_execution_span()

            # Step 2: Run compliance check using automatically selected agents
            compliance_results = self.compliance_checker.check_compliance(
                text_content,
                selected_agents,
                applicant_data,
                all_available_agents=all_available_agents_list,
                external_workflow_logger=workflow_logger
            )

            # Complete agent execution span
            execution_summary = {
                "total_agents_executed": len(selected_agents),
                "compliance_results_summary": {
                    "passed_agents": len([r for r in compliance_results.get('agent_results', []) if r.get('passed', False)]),
                    "total_agents": len(compliance_results.get('agent_results', []))
                }
            }
            workflow_logger.complete_agent_execution_span(execution_summary)

            # Log overall assessment in main workflow
            if compliance_results.get('agent_results') and compliance_results.get('compliance_summary'):
                workflow_logger.log_overall_assessment(
                    compliance_results.get('agent_results', []),
                    compliance_results.get('compliance_summary', {})
                )

            # Complete the main workflow
            final_result = {
                "automatic_selection": selection_result,
                "compliance_results": compliance_results,
                "processing_status": "success",
                "hierarchical_structure": {
                    "automatic_selection_span": "completed",
                    "agent_execution_span": "completed"
                }
            }
            workflow_logger.complete_workflow(final_result)

            # Flush traces to ensure they are sent to Galileo
            auto_compliance_client.flush_traces()
            workflow_logger.galileo_client.flush_traces()

            return {
                'compliance_results': compliance_results,
                'document_summary': self.parser.get_document_summary(parsed_doc),
                'selected_agents_summary': self.compliance_checker.get_agent_summary(selected_agents),
                'automatic_selection': selection_result,
                'processing_status': 'success',
                'selection_mode': 'automatic',
                'galileo_session_id': session_id,
                'galileo_log_stream': 'automatic_compliance',
                'hierarchical_structure': {
                    "automatic_selection_span": "completed",
                    "agent_execution_span": "completed"
                }
            }

        except Exception as e:
            # Log error to workflow if logger exists
            if 'workflow_logger' in locals():
                workflow_logger.log_error(f'Automatic compliance checking failed: {str(e)}', {
                    "error_type": "automatic_compliance_error",
                    "session_id": session_id
                })
                workflow_logger.galileo_client.flush_traces()

            # Flush traces even on error
            auto_compliance_client.flush_traces()

            return {
                'error': f'Automatic compliance checking failed: {str(e)}',
                'processing_status': 'error',
                'selection_mode': 'automatic',
                'galileo_session_id': session_id
            }

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
    
    def _init_graph_builder(self):
        """Initialize graph builder with Neo4j"""
        self.graph_builder = DocumentToGraph()
        print(f"Graph builder initialized successfully")
    
    def process_with_graph(self, file_path: str, domain_hint: str = None) -> Dict:
        """Process document with both LLM and graph-based approaches"""
        # First, do standard processing
        result = self.extract_policy_agents(file_path, domain_hint)
        
        if 'error' in result:
            return result
        
        # If graph builder is available, also build graph
        if self.graph_builder:
            try:
                # Get text content
                text_content = result.get('text_content_length', 0)
                parsed_doc = self.parser.parse_document(file_path)
                text = parsed_doc.get('text_content', '')
                
                # Build graph
                graph_result = self.graph_builder.process_document(
                    text, 
                    os.path.basename(file_path)
                )
                
                result['graph_creation'] = graph_result
                result['methodology'] = 'hybrid_llm_graph'
                
            except Exception as e:
                result['graph_error'] = str(e)
                result['methodology'] = 'llm_only'
        else:
            result['methodology'] = 'llm_only'
        
        return result