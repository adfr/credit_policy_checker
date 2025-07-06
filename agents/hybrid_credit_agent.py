from neo4j import GraphDatabase
from typing import Dict, List, Any, Tuple
import os
from dotenv import load_dotenv
from .base_agent import BaseAgent
import json

load_dotenv('graph-db/.env')

class HybridCreditAgent(BaseAgent):
    """Hybrid agent that combines Neo4j graph knowledge with LLM reasoning"""
    
    def __init__(self):
        super().__init__("hybrid_credit")
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'neo4j123!')
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def check(self, policy_check: Dict, credit_data: Dict) -> Dict:
        """Hybrid approach: Use graph for structure, LLM for reasoning"""
        
        # 1. Get requirements from graph database
        graph_requirements = self._get_graph_requirements(policy_check)
        
        # 2. Get linked requirements for context
        linked_requirements = self._get_linked_requirements(graph_requirements)
        
        # 3. Use LLM with graph context for intelligent checking
        result = self._hybrid_check(policy_check, credit_data, graph_requirements, linked_requirements)
        
        return result
    
    def _get_graph_requirements(self, policy_check: Dict) -> List[Dict]:
        """Retrieve relevant requirements from graph based on policy check"""
        if not self.driver:
            return []
        
        check_type = policy_check.get('check_type', '')
        
        with self.driver.session() as session:
            # Query for requirements matching the check type
            result = session.run("""
                MATCH (r:Requirement)
                WHERE toLower(r.type) CONTAINS toLower($check_type) 
                   OR toLower(r.name) CONTAINS toLower($check_type)
                   OR toLower(r.category) CONTAINS toLower($check_type)
                RETURN r.id as id, r.name as name, r.description as description,
                       r.type as type, r.threshold as threshold, r.conditions as conditions
                LIMIT 10
            """, check_type=check_type)
            
            return [record.data() for record in result]
    
    def _get_linked_requirements(self, requirements: List[Dict]) -> Dict[str, List[Dict]]:
        """Get linked requirements for each requirement"""
        if not self.driver or not requirements:
            return {}
        
        linked = {}
        
        with self.driver.session() as session:
            for req in requirements:
                req_id = req.get('id')
                if not req_id:
                    continue
                
                # Get both incoming and outgoing links
                result = session.run("""
                    MATCH (r:Requirement {id: $req_id})-[l:LINKED_TO]-(r2:Requirement)
                    RETURN r2.id as id, r2.name as name, l.type as link_type, 
                           l.strength as strength, l.description as link_description,
                           CASE WHEN startNode(l).id = $req_id THEN 'outgoing' ELSE 'incoming' END as direction
                """, req_id=req_id)
                
                linked[req_id] = [record.data() for record in result]
        
        return linked
    
    def _hybrid_check(self, policy_check: Dict, credit_data: Dict, 
                     graph_requirements: List[Dict], linked_requirements: Dict) -> Dict:
        """Perform hybrid check using both graph knowledge and LLM reasoning"""
        
        # Check for missing required fields using the check definition
        if hasattr(self, 'check_definition') and self.check_definition:
            agent_name = self.check_definition.get('agent_name', policy_check.get('description', 'Policy Check'))
            data_fields = self.check_definition.get('data_fields', [])
            
            # Check for missing required fields
            missing_fields = []
            for field in data_fields:
                if field not in credit_data or credit_data.get(field) is None:
                    missing_fields.append(field)
            
            # If critical fields are missing, check if they might not be applicable
            if missing_fields:
                missing_fields_str = ', '.join(f"'{field}'" for field in missing_fields)
                requirement = self.check_definition.get('requirement', '')
                
                applicability_prompt = f"""
                You are evaluating whether a policy check is applicable to a document.
                
                Policy Check: {agent_name}
                Requirement: {requirement}
                Missing Fields: {missing_fields_str}
                Available Data: {json.dumps(credit_data, indent=2)}
                
                Based on the available data, determine if the missing fields are:
                1. Simply not extracted from the document (but might be present)
                2. Not applicable to this type of document/application
                
                Examples:
                - If checking "Home Equity Loan Amount" but the document is a "primary mortgage application", then home_equity_loan_amount is NOT APPLICABLE
                - If checking "Credit Score" but no credit scores are found, they might just be MISSING
                
                Return JSON:
                {{
                    "applicable": true/false,
                    "reason": "explanation of why the check is or isn't applicable to this document"
                }}
                """
                
                try:
                    applicability_response = self.process(applicability_prompt)
                    applicability_result = json.loads(applicability_response)
                    
                    if not applicability_result.get('applicable', True):
                        return {
                            'passed': None,  # Neither passed nor failed - not applicable
                            'reason': f"Check not applicable: {applicability_result.get('reason', 'Required fields not applicable to this document type')}",
                            'confidence': 0.95,
                            'missing_fields': missing_fields,
                            'applicable': False,
                            'methodology': 'hybrid_graph_llm',
                            'graph_requirements_used': 0,
                            'linked_requirements_considered': 0
                        }
                except:
                    # Fallback to generic missing fields message
                    pass
                
                return {
                    'passed': False,
                    'reason': f"Cannot evaluate {agent_name}: Required field(s) {missing_fields_str} not found in the document. This check requires these fields to assess compliance.",
                    'confidence': 1.0,
                    'missing_fields': missing_fields,
                    'methodology': 'hybrid_graph_llm',
                    'graph_requirements_used': 0,
                    'linked_requirements_considered': 0
                }
        
        # Build context from graph
        graph_context = self._build_graph_context(graph_requirements, linked_requirements)
        
        # Create enhanced prompt with graph knowledge
        prompt = f"""
        You are a focused compliance checker using graph-based requirements.
        
        CRITICAL: You MUST ONLY evaluate the specific policy check requested below.
        
        Policy Check Request: {json.dumps(policy_check)}
        
        Available Data (ONLY data relevant to this check):
        {json.dumps(credit_data)}
        
        Graph-Based Requirements Context:
        {graph_context}
        
        STRICT INSTRUCTIONS:
        1. Use ONLY the graph requirements that match your specific check
        2. Consider linked requirements ONLY if they directly impact your check
        3. Do NOT evaluate aspects outside the requested policy check
        4. Focus your reasoning ONLY on the specific requirement being checked
        5. Use ONLY the data fields provided - do not infer or assume other data
        6. CRITICAL: When comparing numbers, be mathematically accurate:
           - If requirement says "must be below X%", then actual value > X% = FAILED
           - If requirement says "must be above X%", then actual value < X% = FAILED
           - Double-check your mathematical comparison logic before concluding
        
        Provide a focused compliance check result with:
        - passed: boolean
        - reason: explanation focused ONLY on the specific requirement checked
        - confidence: float (0-1)
        - requirements_evaluated: list of requirement IDs actually used for THIS check
        - linked_impacts: ONLY if linked requirements directly affect THIS check
        - recommendations: ONLY if THIS specific check failed
        
        Return as JSON.
        """
        
        response = self.process(prompt)
        
        try:
            # Check if response is already a JSON error from base agent
            if isinstance(response, str) and response.strip().startswith('{"passed": false'):
                result = json.loads(response)
                result['methodology'] = 'hybrid_graph_llm'
                return result
            
            result = json.loads(response)
            # Enhance with graph metadata
            result['graph_requirements_used'] = len(graph_requirements)
            result['linked_requirements_considered'] = sum(len(links) for links in linked_requirements.values())
            result['methodology'] = 'hybrid_graph_llm'
            return result
        except Exception as e:
            import traceback
            error_details = f"Failed to process hybrid check: {str(e)}"
            print(f"DEBUG: Hybrid agent error: {error_details}")
            print(f"DEBUG: Response was: {response[:500] if response else 'None'}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            return {
                'passed': False,
                'reason': error_details,
                'confidence': 0.0,
                'methodology': 'hybrid_graph_llm',
                'error': True,
                'debug_response': str(response)[:200] if response else None
            }
    
    def _build_graph_context(self, requirements: List[Dict], linked: Dict) -> str:
        """Build formatted context from graph data"""
        context_parts = []
        
        for req in requirements:
            req_id = req.get('id', 'Unknown')
            context_parts.append(f"\nRequirement {req_id}: {req.get('name', 'Unnamed')}")
            context_parts.append(f"Description: {req.get('description', 'No description')}")
            
            if req.get('threshold'):
                context_parts.append(f"Threshold: {req['threshold']}")
            
            if req.get('conditions'):
                try:
                    conditions = json.loads(req['conditions']) if isinstance(req['conditions'], str) else req['conditions']
                    if conditions:
                        context_parts.append(f"Conditions: {conditions}")
                except:
                    pass
            
            # Add linked requirements
            req_links = linked.get(req_id, [])
            if req_links:
                context_parts.append("Linked Requirements:")
                for link in req_links:
                    direction = "→" if link['direction'] == 'outgoing' else "←"
                    context_parts.append(f"  {direction} {link['name']} ({link['link_type']}, {link['strength']})")
        
        return "\n".join(context_parts)
    
    def get_graph_insights(self) -> Dict:
        """Get insights about the current graph structure"""
        if not self.driver:
            return {"error": "No graph connection"}
        
        with self.driver.session() as session:
            # Count nodes and relationships
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            # Get requirement type distribution
            type_dist = session.run("""
                MATCH (r:Requirement)
                RETURN r.type as type, count(*) as count
                ORDER BY count DESC
            """)
            
            return {
                "total_requirements": node_count,
                "total_linkages": rel_count,
                "requirement_types": [record.data() for record in type_dist],
                "graph_density": rel_count / node_count if node_count > 0 else 0
            }