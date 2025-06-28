from neo4j import GraphDatabase
import os
from typing import Dict, List, Tuple
import json
import openai
from dotenv import load_dotenv
import re

load_dotenv()

class DocumentToGraph:
    """Convert policy documents to Neo4j graph database"""
    
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'neo4j123!')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    def process_document(self, document_content: str, document_name: str) -> Dict:
        """Process document and create graph database"""
        print(f"Processing document: {document_name}")
        
        # Extract requirements and linkages using LLM
        requirements = self._extract_requirements(document_content)
        linkages = self._extract_linkages(document_content, requirements)
        
        # Clear existing graph
        self._clear_graph()
        
        # Create nodes and relationships
        self._create_requirement_nodes(requirements)
        self._create_linkage_relationships(linkages)
        
        # Create document metadata
        self._create_document_node(document_name, len(requirements))
        
        return {
            "document": document_name,
            "requirements_extracted": len(requirements),
            "linkages_created": len(linkages),
            "status": "success"
        }
    
    def _extract_requirements(self, content: str) -> List[Dict]:
        """Extract requirements from document using LLM"""
        prompt = """
        Extract all policy requirements from this document. For each requirement, provide:
        - id: unique identifier (e.g., REQ001, REQ002)
        - name: short descriptive name
        - description: full requirement text
        - type: category (e.g., Credit Score, Income, Documentation, Risk Assessment)
        - category: broader category (e.g., Financial, Legal, Operational)
        - threshold: any numeric threshold mentioned
        - conditions: specific conditions that must be met
        
        Return as JSON array.
        
        Document:
        {content}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a policy requirement extraction expert."},
                {"role": "user", "content": prompt.format(content=content[:8000])}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("requirements", [])
        except:
            return []
    
    def _extract_linkages(self, content: str, requirements: List[Dict]) -> List[Dict]:
        """Extract linkages between requirements using LLM"""
        req_summary = "\n".join([f"{r['id']}: {r['name']}" for r in requirements])
        
        prompt = """
        Based on this document and the extracted requirements, identify linkages between requirements.
        A linkage exists when:
        - One requirement depends on another
        - Requirements must be evaluated together
        - One requirement references or impacts another
        
        For each linkage provide:
        - source_id: ID of the source requirement
        - target_id: ID of the target requirement
        - type: DEPENDS_ON, REFERENCES, VALIDATES, CONFLICTS_WITH, or SUPPLEMENTS
        - strength: STRONG, MEDIUM, or WEAK
        - description: brief explanation of the relationship
        
        Requirements:
        {requirements}
        
        Return as JSON array of linkages.
        
        Document excerpt:
        {content}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a policy linkage analysis expert."},
                {"role": "user", "content": prompt.format(requirements=req_summary, content=content[:6000])}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("linkages", [])
        except:
            return []
    
    def _clear_graph(self):
        """Clear existing graph data"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def _create_requirement_nodes(self, requirements: List[Dict]):
        """Create requirement nodes in Neo4j"""
        with self.driver.session() as session:
            for req in requirements:
                session.run("""
                    CREATE (r:Requirement {
                        id: $id,
                        name: $name,
                        description: $description,
                        type: $type,
                        category: $category,
                        threshold: $threshold,
                        conditions: $conditions
                    })
                """, 
                id=req.get('id'),
                name=req.get('name'),
                description=req.get('description'),
                type=req.get('type', 'General'),
                category=req.get('category', 'General'),
                threshold=req.get('threshold', ''),
                conditions=json.dumps(req.get('conditions', []))
                )
    
    def _create_linkage_relationships(self, linkages: List[Dict]):
        """Create linkage relationships in Neo4j"""
        with self.driver.session() as session:
            for link in linkages:
                session.run("""
                    MATCH (r1:Requirement {id: $source_id})
                    MATCH (r2:Requirement {id: $target_id})
                    CREATE (r1)-[l:LINKED_TO {
                        type: $type,
                        strength: $strength,
                        description: $description
                    }]->(r2)
                """,
                source_id=link.get('source_id'),
                target_id=link.get('target_id'),
                type=link.get('type', 'REFERENCES'),
                strength=link.get('strength', 'MEDIUM'),
                description=link.get('description', '')
                )
    
    def _create_document_node(self, document_name: str, requirement_count: int):
        """Create document metadata node"""
        with self.driver.session() as session:
            session.run("""
                CREATE (d:Document {
                    name: $name,
                    requirement_count: $count,
                    processed_at: datetime()
                })
            """,
            name=document_name,
            count=requirement_count
            )
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()