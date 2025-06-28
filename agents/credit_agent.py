from neo4j import GraphDatabase
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
from .base_agent import BaseAgent
import json

load_dotenv('graph-db/.env')

class CreditAgent(BaseAgent):
    """Agent that uses Neo4j graph database for credit policy analysis"""
    
    def __init__(self):
        super().__init__("credit_graph")
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
            raise
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def get_requirements(self) -> List[Dict]:
        """Fetch all requirements from the graph database"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Requirement)
                RETURN r.id as id, r.name as name, r.description as description, 
                       r.type as type, r.category as category
            """)
            return [record.data() for record in result]
    
    def get_requirement_linkages(self, requirement_id: str) -> List[Dict]:
        """Get all linkages for a specific requirement"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Requirement {id: $req_id})-[l:LINKED_TO]->(r2:Requirement)
                RETURN r2.id as linked_id, r2.name as linked_name, 
                       l.type as linkage_type, l.strength as strength
            """, req_id=requirement_id)
            return [record.data() for record in result]
    
    def analyze_credit_compliance(self, credit_data: Dict) -> Dict:
        """Analyze credit data against graph-based requirements"""
        results = {
            "overall_compliance": True,
            "requirements_checked": [],
            "linkage_analysis": [],
            "compliance_score": 0.0
        }
        
        requirements = self.get_requirements()
        passed_count = 0
        
        for req in requirements:
            check_result = self._check_requirement(req, credit_data)
            results["requirements_checked"].append(check_result)
            
            if check_result["passed"]:
                passed_count += 1
                
                linkages = self.get_requirement_linkages(req["id"])
                if linkages:
                    linkage_result = self._analyze_linkages(req, linkages, credit_data)
                    results["linkage_analysis"].append(linkage_result)
        
        results["compliance_score"] = (passed_count / len(requirements)) * 100 if requirements else 0
        results["overall_compliance"] = results["compliance_score"] >= 80
        
        return results
    
    def _check_requirement(self, requirement: Dict, credit_data: Dict) -> Dict:
        """Check a single requirement against credit data"""
        prompt = f"""
        Check if the following credit data complies with this requirement:
        
        Requirement: {requirement.get('name', 'Unknown')}
        Description: {requirement.get('description', 'No description')}
        Type: {requirement.get('type', 'Unknown')}
        
        Credit Data: {json.dumps(credit_data)}
        
        Respond with a JSON object containing:
        - passed: boolean
        - reason: string explaining the decision
        - confidence: float between 0 and 1
        """
        
        response = self.process(prompt)
        
        try:
            result = json.loads(response)
            result["requirement_id"] = requirement.get("id")
            result["requirement_name"] = requirement.get("name")
            return result
        except:
            return {
                "requirement_id": requirement.get("id"),
                "requirement_name": requirement.get("name"),
                "passed": False,
                "reason": "Failed to parse AI response",
                "confidence": 0.0
            }
    
    def _analyze_linkages(self, requirement: Dict, linkages: List[Dict], credit_data: Dict) -> Dict:
        """Analyze how linkages affect requirement compliance"""
        return {
            "requirement_id": requirement.get("id"),
            "requirement_name": requirement.get("name"),
            "linked_requirements": len(linkages),
            "linkage_details": linkages,
            "impact": "Dependencies identified - review linked requirements for full compliance"
        }
    
    def check(self, policy_check: Dict, credit_data: Dict) -> Dict:
        """Implementation of abstract method from BaseAgent"""
        return self.analyze_credit_compliance(credit_data)
    
    def query_graph(self, cypher_query: str, parameters: Dict = None) -> List[Dict]:
        """Execute custom Cypher queries on the graph"""
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            return [record.data() for record in result]