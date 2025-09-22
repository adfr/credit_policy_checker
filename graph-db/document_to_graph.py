from neo4j import GraphDatabase
import os
from typing import Dict, List, Tuple
import json
import openai
from dotenv import load_dotenv
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()  # Load from main .env file

class DocumentToGraph:
    """Convert policy documents to Neo4j graph database"""
    
    def __init__(self):
        logger.info("🔌 Initializing DocumentToGraph...")
        
        # Get credentials from main .env - no hardcoded defaults
        self.uri = os.getenv('NEO4J_URI')
        self.user = os.getenv('NEO4J_USER')
        self.password = os.getenv('NEO4J_PASSWORD')
        
        if not all([self.uri, self.user, self.password]):
            raise ValueError("Neo4j credentials not found in main .env file")
            
        logger.info(f"🔗 Connecting to Neo4j at {self.uri}")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
        # Test connection
        try:
            self.driver.verify_connectivity()
            logger.info("✅ Neo4j connection verified successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise
            
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        logger.info("✅ DocumentToGraph initialized successfully")
    
    def process_document(self, document_content: str, document_name: str) -> Dict:
        """Process document and create graph database"""
        logger.info(f"📄 Processing document: {document_name}")
        logger.info(f"📏 Document length: {len(document_content)} characters")
        
        try:
            # Extract requirements and linkages using LLM
            logger.info("🤖 Extracting requirements using LLM...")
            requirements = self._extract_requirements(document_content)
            logger.info(f"📋 Extracted {len(requirements)} requirements")
            
            logger.info("🔗 Extracting linkages using LLM...")
            linkages = self._extract_linkages(document_content, requirements)
            logger.info(f"🔗 Extracted {len(linkages)} linkages")
            
            # Clear existing graph
            logger.info("🗑️ Clearing existing graph data...")
            self._clear_graph()
            
            # Create nodes and relationships
            logger.info("📊 Creating requirement nodes in Neo4j...")
            self._create_requirement_nodes(requirements)
            
            logger.info("🔗 Creating linkage relationships in Neo4j...")
            self._create_linkage_relationships(linkages)
            
            # Create document metadata
            logger.info("📝 Creating document metadata node...")
            self._create_document_node(document_name, len(requirements))
            
            result = {
                "document": document_name,
                "requirements_extracted": len(requirements),
                "linkages_created": len(linkages),
                "status": "success"
            }
            
            logger.info(f"✅ Graph creation completed successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing document {document_name}: {e}")
            logger.error(f"🔍 Error details:", exc_info=True)
            return {
                "document": document_name,
                "requirements_extracted": 0,
                "linkages_created": 0,
                "status": "error",
                "error": str(e)
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
            model="gpt-4o-mini",
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
            model="gpt-4o-mini",
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
        logger.info(f"📊 Creating {len(requirements)} requirement nodes...")
        
        with self.driver.session() as session:
            for i, req in enumerate(requirements, 1):
                logger.info(f"📝 Creating requirement {i}/{len(requirements)}: {req.get('name', 'Unnamed')}")
                
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
                
        logger.info(f"✅ Successfully created {len(requirements)} requirement nodes in Neo4j")
    
    def _create_linkage_relationships(self, linkages: List[Dict]):
        """Create linkage relationships in Neo4j"""
        logger.info(f"🔗 Creating {len(linkages)} linkage relationships...")
        
        created_count = 0
        with self.driver.session() as session:
            for i, link in enumerate(linkages, 1):
                logger.info(f"🔗 Creating linkage {i}/{len(linkages)}: {link.get('source_id')} -> {link.get('target_id')}")
                
                result = session.run("""
                    MATCH (r1:Requirement {id: $source_id})
                    MATCH (r2:Requirement {id: $target_id})
                    CREATE (r1)-[l:LINKED_TO {
                        type: $type,
                        strength: $strength,
                        description: $description
                    }]->(r2)
                    RETURN l
                """,
                source_id=link.get('source_id'),
                target_id=link.get('target_id'),
                type=link.get('type', 'REFERENCES'),
                strength=link.get('strength', 'MEDIUM'),
                description=link.get('description', '')
                )
                
                if result.single():
                    created_count += 1
                    
        logger.info(f"✅ Successfully created {created_count}/{len(linkages)} relationships in Neo4j")
    
    def _create_document_node(self, document_name: str, requirement_count: int):
        """Create document metadata node"""
        logger.info(f"📝 Creating document metadata node for '{document_name}'...")
        
        with self.driver.session() as session:
            result = session.run("""
                CREATE (d:Document {
                    name: $name,
                    requirement_count: $count,
                    processed_at: datetime()
                })
                RETURN d
            """,
            name=document_name,
            count=requirement_count
            )
            
            if result.single():
                logger.info(f"✅ Successfully created document node for '{document_name}' with {requirement_count} requirements")
            else:
                logger.warning(f"⚠️ Failed to create document node for '{document_name}'")
    
    def close(self):
        """Close database connection"""
        if self.driver:
            logger.info("🔌 Closing Neo4j connection...")
            self.driver.close()
            logger.info("✅ Neo4j connection closed")