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
        logger.info(f"🔍 Starting requirement extraction from document (length: {len(content)} chars)")

        prompt = """
        Extract all policy requirements and product offerings from this lending/financial document.

        First, identify KEY PRODUCTS mentioned (e.g., Conventional Loans, FHA Loans, VA Loans, Jumbo Loans, etc.)

        Then, for each requirement, provide:
        - id: unique identifier (e.g., REQ001 for requirements, PROD001 for products)
        - name: short descriptive name
        - description: full requirement or product description
        - type: category (e.g., Product, Credit Score, DTI, LTV, Income, Documentation, Down Payment, Property Type)
        - category: broader category (e.g., Product, Financial, Documentation, Property, Risk)
        - threshold: any numeric threshold or limit mentioned
        - conditions: specific conditions that must be met
        - applicable_products: list of products this requirement applies to (if mentioned)
        - is_product: boolean - true if this is a product, false if it's a requirement

        Focus on extracting:
        1. All loan/financial products offered
        2. Credit score requirements and tiers
        3. DTI (Debt-to-Income) limits and exceptions
        4. LTV (Loan-to-Value) requirements
        5. Down payment requirements
        6. Income and employment requirements
        7. Documentation requirements
        8. Property requirements

        Return as a JSON object with a "requirements" key containing an array.
        Example format:
        {{
            "requirements": [
                {{
                    "id": "PROD001",
                    "name": "Conventional Loan",
                    "description": "Standard conventional mortgage loan product",
                    "type": "Product",
                    "category": "Product",
                    "threshold": null,
                    "conditions": ["Primary residence", "Investment property"],
                    "applicable_products": [],
                    "is_product": true
                }},
                {{
                    "id": "REQ001",
                    "name": "Minimum Credit Score - Conventional",
                    "description": "Borrower must have minimum credit score of 620 for conventional loans",
                    "type": "Credit Score",
                    "category": "Financial",
                    "threshold": "620",
                    "conditions": ["Primary borrower", "All co-borrowers"],
                    "applicable_products": ["Conventional Loan"],
                    "is_product": false
                }}
            ]
        }}

        Document:
        {content}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a policy requirement extraction expert."},
                {"role": "user", "content": prompt.format(content=content[:8000])}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        logger.info(f"🤖 LLM response received")
        raw_response = response.choices[0].message.content
        logger.info(f"📝 Raw LLM response (first 500 chars): {raw_response[:500]}...")

        try:
            result = json.loads(raw_response)
            logger.info(f"🔑 JSON keys in response: {list(result.keys())}")
            requirements = result.get("requirements", [])
            logger.info(f"📋 LLM returned {len(requirements)} requirements")
            if not requirements:
                logger.warning(f"⚠️ No requirements found. LLM response: {response.choices[0].message.content[:200]}...")
            return requirements
        except Exception as e:
            logger.error(f"❌ Error parsing requirements: {e}")
            logger.error(f"❌ LLM response: {response.choices[0].message.content[:500]}...")
            return []
    
    def _extract_linkages(self, content: str, requirements: List[Dict]) -> List[Dict]:
        """Extract linkages between requirements and products using LLM"""
        req_summary = "\n".join([f"{r['id']}: {r['name']} (Product: {r.get('is_product', False)})" for r in requirements])

        prompt = """
        Based on this document and the extracted requirements/products, identify linkages.

        CRITICAL: Create linkages between:
        1. Products and their requirements (PRODUCT_REQUIRES)
        2. Requirements that depend on each other (DEPENDS_ON)
        3. Requirements that must be evaluated together (EVALUATED_WITH)
        4. Requirements that reference each other (REFERENCES)
        5. Requirements that supplement each other (SUPPLEMENTS)

        Focus especially on linking:
        - Each product to its specific requirements (credit score, DTI, LTV, etc.)
        - DTI requirements to income/debt requirements
        - LTV requirements to down payment requirements
        - Credit score tiers to pricing/eligibility

        For each linkage provide:
        - source_id: ID of the source (often a product)
        - target_id: ID of the target (often a requirement)
        - type: PRODUCT_REQUIRES, DEPENDS_ON, REFERENCES, EVALUATED_WITH, SUPPLEMENTS, or DETERMINES
        - strength: STRONG (mandatory), MEDIUM (typical), or WEAK (optional)
        - description: brief explanation of the relationship

        Requirements/Products:
        {requirements}
        
        Return as a JSON object with a "linkages" key containing an array of linkages.
        
        Document excerpt:
        {content}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4.1",
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
        """Create requirement and product nodes in Neo4j"""
        logger.info(f"📊 Creating {len(requirements)} requirement/product nodes...")

        products = [r for r in requirements if r.get('is_product', False)]
        reqs = [r for r in requirements if not r.get('is_product', False)]

        logger.info(f"📦 Found {len(products)} products and {len(reqs)} requirements")

        with self.driver.session() as session:
            for i, req in enumerate(requirements, 1):
                is_product = req.get('is_product', False)
                node_type = 'Product' if is_product else 'Requirement'
                logger.info(f"📝 Creating {node_type} {i}/{len(requirements)}: {req.get('name', 'Unnamed')}")

                # Create different labels for products vs requirements
                if is_product:
                    session.run("""
                        CREATE (p:Product {
                            id: $id,
                            name: $name,
                            description: $description,
                            type: $type,
                            category: $category,
                            conditions: $conditions
                        })
                    """,
                    id=req.get('id'),
                    name=req.get('name'),
                    description=req.get('description'),
                    type=req.get('type', 'Product'),
                    category=req.get('category', 'Product'),
                    conditions=json.dumps(req.get('conditions', []))
                    )
                else:
                    session.run("""
                        CREATE (r:Requirement {
                            id: $id,
                            name: $name,
                            description: $description,
                            type: $type,
                            category: $category,
                            threshold: $threshold,
                            conditions: $conditions,
                            applicable_products: $applicable_products
                        })
                    """,
                    id=req.get('id'),
                    name=req.get('name'),
                    description=req.get('description'),
                    type=req.get('type', 'General'),
                    category=req.get('category', 'General'),
                    threshold=req.get('threshold', ''),
                    conditions=json.dumps(req.get('conditions', [])),
                    applicable_products=json.dumps(req.get('applicable_products', []))
                    )
                
        # Verify nodes were created
        with self.driver.session() as session:
            result = session.run("MATCH (r:Requirement) RETURN count(r) as count")
            count = result.single()['count']
            logger.info(f"✅ Successfully created {len(requirements)} requirement nodes in Neo4j (Total in DB: {count})")
    
    def _create_linkage_relationships(self, linkages: List[Dict]):
        """Create linkage relationships in Neo4j"""
        logger.info(f"🔗 Creating {len(linkages)} linkage relationships...")
        
        created_count = 0
        with self.driver.session() as session:
            for i, link in enumerate(linkages, 1):
                logger.info(f"🔗 Creating linkage {i}/{len(linkages)}: {link.get('source_id')} -> {link.get('target_id')}")
                
                # Use MERGE and handle both Product and Requirement nodes
                # First check if source is a product
                result = session.run("""
                    MATCH (source) WHERE (source:Product OR source:Requirement) AND source.id = $source_id
                    MATCH (target) WHERE (target:Product OR target:Requirement) AND target.id = $target_id
                    CREATE (source)-[l:LINKED_TO {
                        type: $type,
                        strength: $strength,
                        description: $description
                    }]->(target)
                    RETURN l
                """,
                source_id=link.get('source_id'),
                target_id=link.get('target_id'),
                type=link.get('type', 'REFERENCES'),
                strength=link.get('strength', 'MEDIUM'),
                description=link.get('description', '')
                )
                
                try:
                    if result.single():
                        created_count += 1
                    else:
                        logger.warning(f"⚠️ Failed to create linkage: {link.get('source_id')} -> {link.get('target_id')}")
                except Exception as e:
                    logger.error(f"❌ Error creating linkage: {e}")
                    
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