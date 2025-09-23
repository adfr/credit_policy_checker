#!/usr/bin/env python3
"""
Neo4j Search Tool for CrewAI Agents
Provides graph database search capabilities to CrewAI agents
"""

from neo4j import GraphDatabase
from crewai.tools import tool
from typing import Dict, List, Any, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)


# Initialize Neo4j connection at module level
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD')

if all([uri, user, password]):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        logger.info("✅ Neo4j tool connected successfully")
        NEO4J_AVAILABLE = True
    except Exception as e:
        logger.error(f"❌ Failed to connect to Neo4j: {e}")
        driver = None
        NEO4J_AVAILABLE = False
else:
    logger.warning("⚠️ Neo4j credentials not found - tool will not be available")
    driver = None
    NEO4J_AVAILABLE = False


@tool("Neo4j Graph Search")
def search_policy_graph(search_query) -> str:
    """
    Search the policy knowledge graph for requirements and products.

    Args:
        search_query: A search query string describing what you're looking for.

    Examples:
    - "requirements for conventional loan"
    - "credit score requirements"
    - "DTI limits and exceptions"
    - "requirements linked to minimum down payment"
    """
    # Handle both string and dictionary inputs
    if isinstance(search_query, dict):
        # Extract search term from dictionary if CrewAI passes it as such
        search_term = search_query.get('description') or search_query.get('query') or str(search_query)
        logger.info(f"🔧 Neo4j tool received dict input, extracted: {search_term}")
    else:
        search_term = str(search_query)
        logger.info(f"🔧 Neo4j tool received string input: {search_term}")

    if not NEO4J_AVAILABLE:
        return "Neo4j graph database is not available. Please check the connection."

    try:
        # Parse the query to determine search type
        query_lower = search_term.lower()

        if "product" in query_lower or "loan" in query_lower:
            return _search_products(driver, search_term)
        elif "linked" in query_lower or "related" in query_lower or "relationship" in query_lower:
            return _search_relationships(driver, search_term)
        elif any(term in query_lower for term in ["credit", "dti", "ltv", "income", "down payment"]):
            return _search_requirements_by_type(driver, search_term)
        else:
            return _general_search(driver, search_term)

    except Exception as e:
        logger.error(f"❌ Neo4j search error: {e}")
        return f"Error searching graph database: {str(e)}"


def _search_products(driver, query: str) -> str:
    """Search for products and their requirements"""
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Product)
            WHERE toLower(p.name) CONTAINS toLower($search_term)
               OR toLower(p.description) CONTAINS toLower($search_term)
            OPTIONAL MATCH (p)-[r:LINKED_TO]->(req:Requirement)
            RETURN p.name as product_name,
                   p.description as product_desc,
                   collect({
                       name: req.name,
                       type: req.type,
                       threshold: req.threshold,
                       conditions: req.conditions
                   }) as requirements
            LIMIT 5
        """, search_term=query)

        products = []
        for record in result:
            product_info = f"📦 **{record['product_name']}**\n"
            product_info += f"   Description: {record['product_desc']}\n"

            if record['requirements']:
                product_info += "   Requirements:\n"
                for req in record['requirements']:
                    if req['name']:
                        product_info += f"   - {req['name']} ({req['type']})"
                        if req['threshold']:
                            product_info += f" - Threshold: {req['threshold']}"
                        product_info += "\n"

            products.append(product_info)

        if products:
            return "Found the following products and requirements:\n\n" + "\n".join(products)
        else:
            return f"No products found matching '{query}'"


def _search_requirements_by_type(driver, query: str) -> str:
    """Search for specific types of requirements"""
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Requirement)
            WHERE toLower(r.type) CONTAINS toLower($search_term)
               OR toLower(r.name) CONTAINS toLower($search_term)
               OR toLower(r.description) CONTAINS toLower($search_term)
            OPTIONAL MATCH (p:Product)-[:LINKED_TO]->(r)
            RETURN r.name as name,
                   r.type as type,
                   r.description as description,
                   r.threshold as threshold,
                   r.conditions as conditions,
                   r.applicable_products as applicable_products,
                   collect(DISTINCT p.name) as linked_products
            LIMIT 10
        """, search_term=query)

        requirements = []
        for record in result:
            req_info = f"📋 **{record['name']}** (Type: {record['type']})\n"
            req_info += f"   Description: {record['description']}\n"

            if record['threshold']:
                req_info += f"   Threshold: {record['threshold']}\n"

            if record['conditions']:
                conditions = json.loads(record['conditions']) if isinstance(record['conditions'], str) else record['conditions']
                if conditions:
                    req_info += f"   Conditions: {', '.join(conditions)}\n"

            if record['linked_products']:
                req_info += f"   Applies to: {', '.join(record['linked_products'])}\n"
            elif record['applicable_products']:
                products = json.loads(record['applicable_products']) if isinstance(record['applicable_products'], str) else record['applicable_products']
                if products:
                    req_info += f"   Applicable to: {', '.join(products)}\n"

            requirements.append(req_info)

        if requirements:
            return f"Found {len(requirements)} requirements:\n\n" + "\n".join(requirements)
        else:
            return f"No requirements found matching '{query}'"


def _search_relationships(driver, query: str) -> str:
    """Search for relationships between requirements"""
    keywords = query.lower().replace("linked to", "").replace("related to", "").replace("requirements", "").strip()

    with driver.session() as session:
        result = session.run("""
            MATCH (r1:Requirement)-[link:LINKED_TO]-(r2)
            WHERE toLower(r1.name) CONTAINS toLower($search_keywords)
               OR toLower(r1.type) CONTAINS toLower($search_keywords)
               OR toLower(r2.name) CONTAINS toLower($search_keywords)
            RETURN r1.name as source,
                   r2.name as target,
                   link.type as link_type,
                   link.strength as strength,
                   link.description as description
            LIMIT 15
        """, search_keywords=keywords)

        relationships = []
        for record in result:
            rel_info = f"🔗 {record['source']} --[{record['link_type']}]--> {record['target']}\n"
            if record['description']:
                rel_info += f"   Relationship: {record['description']}\n"
            if record['strength']:
                rel_info += f"   Strength: {record['strength']}\n"
            relationships.append(rel_info)

        if relationships:
            return f"Found {len(relationships)} relationships:\n\n" + "\n".join(relationships)
        else:
            return f"No relationships found for '{query}'"


def _general_search(driver, query: str) -> str:
    """General search across all nodes"""
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            WHERE (n:Product OR n:Requirement)
              AND (toLower(n.name) CONTAINS toLower($search_term)
                   OR toLower(n.description) CONTAINS toLower($search_term)
                   OR toLower(n.type) CONTAINS toLower($search_term))
            RETURN labels(n)[0] as node_type,
                   n.name as name,
                   n.type as type,
                   n.description as description,
                   n.threshold as threshold
            LIMIT 15
        """, search_term=query)

        results = []
        for record in result:
            node_info = f"{'📦' if record['node_type'] == 'Product' else '📋'} "
            node_info += f"**{record['name']}** ({record['node_type']})\n"

            if record['type']:
                node_info += f"   Type: {record['type']}\n"
            if record['description']:
                node_info += f"   Description: {record['description'][:200]}...\n"
            if record['threshold']:
                node_info += f"   Threshold: {record['threshold']}\n"

            results.append(node_info)

        if results:
            return f"Found {len(results)} items in the graph:\n\n" + "\n".join(results)
        else:
            return _get_graph_stats(driver, query)


def _get_graph_stats(driver, query: str) -> str:
    """Get graph database statistics"""
    with driver.session() as session:
        products = session.run("MATCH (p:Product) RETURN count(p) as count").single()['count']
        requirements = session.run("MATCH (r:Requirement) RETURN count(r) as count").single()['count']
        relationships = session.run("MATCH ()-[r:LINKED_TO]->() RETURN count(r) as count").single()['count']

        return f"""
No specific results for '{query}'. Graph Database Statistics:
- Products: {products}
- Requirements: {requirements}
- Relationships: {relationships}

Try searching for:
- "conventional loan requirements"
- "credit score requirements"
- "DTI limits"
- "requirements linked to down payment"
"""


# For backward compatibility
def create_neo4j_search_tool():
    """Create a Neo4j search tool for CrewAI agents"""
    if NEO4J_AVAILABLE:
        return search_policy_graph
    else:
        return None