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
        
        # Build context from graph
        graph_context = self._build_graph_context(graph_requirements, linked_requirements)
        
        # Create enhanced prompt with graph knowledge
        prompt = f"""
        You are checking credit policy compliance using both structured requirements and intelligent reasoning.
        
        Policy Check Request: {json.dumps(policy_check)}
        
        Credit Data: {json.dumps(credit_data)}
        
        Graph-Based Requirements Context:
        {graph_context}
        
        Instructions:
        1. Use the graph requirements as authoritative rules
        2. Consider linked requirements for comprehensive evaluation
        3. Apply intelligent reasoning for edge cases not explicitly covered
        4. Evaluate both explicit requirements and implicit best practices
        
        Provide a detailed compliance check result with:
        - passed: boolean
        - reason: detailed explanation referencing specific requirements
        - confidence: float (0-1)
        - requirements_evaluated: list of requirement IDs checked
        - linked_impacts: any impacts from linked requirements
        - recommendations: specific actions if failed
        
        Return as JSON.
        """
        
        response = self.process(prompt)
        
        try:
            result = json.loads(response)
            # Enhance with graph metadata
            result['graph_requirements_used'] = len(graph_requirements)
            result['linked_requirements_considered'] = sum(len(links) for links in linked_requirements.values())
            result['methodology'] = 'hybrid_graph_llm'
            return result
        except:
            return {
                'passed': False,
                'reason': 'Failed to process hybrid check',
                'confidence': 0.0,
                'methodology': 'hybrid_graph_llm',
                'error': True
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