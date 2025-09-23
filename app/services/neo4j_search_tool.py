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
import time
from datetime import datetime
import galileo

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
    start_time = time.time()
    tool_success = True
    search_type = "unknown"
    result_count = 0
    error_details = None

    # Handle both string and dictionary inputs
    if isinstance(search_query, dict):
        # Extract search term from dictionary if CrewAI passes it as such
        search_term = search_query.get('description') or search_query.get('query') or str(search_query)
        logger.info(f"🔧 Neo4j tool received dict input, extracted: {search_term}")
    else:
        search_term = str(search_query)
        logger.info(f"🔧 Neo4j tool received string input: {search_term}")

    # Start Galileo tracking
    galileo.trace(
        operation_name="neo4j_graph_search",
        input_text=search_term,
        metadata={
            "tool_name": "Neo4j Graph Search",
            "input_type": "dict" if isinstance(search_query, dict) else "string",
            "neo4j_available": NEO4J_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }
    )

    if not NEO4J_AVAILABLE:
        result = "Neo4j graph database is not available. Please check the connection."
        tool_success = False
        error_details = "Neo4j connection not available"

        # Log failure to Galileo
        galileo.log(
            operation_name="neo4j_graph_search",
            input_text=search_term,
            output_text=result,
            metadata={
                "success": False,
                "error": error_details,
                "search_type": "unavailable",
                "execution_time_ms": (time.time() - start_time) * 1000,
                "result_count": 0
            }
        )
        return result

    try:
        # Parse the query to determine search type
        query_lower = search_term.lower()

        if "product" in query_lower or "loan" in query_lower:
            search_type = "products"
            result = _search_products(driver, search_term)
        elif "linked" in query_lower or "related" in query_lower or "relationship" in query_lower:
            search_type = "relationships"
            result = _search_relationships(driver, search_term)
        elif any(term in query_lower for term in ["credit", "dti", "ltv", "income", "down payment"]):
            search_type = "requirements_by_type"
            result = _search_requirements_by_type(driver, search_term)
        else:
            search_type = "general"
            result = _general_search(driver, search_term)

        # Count results in the response
        result_count = _count_results_in_response(result)

        # Log successful search to Galileo
        galileo.log(
            operation_name="neo4j_graph_search",
            input_text=search_term,
            output_text=result,
            metadata={
                "success": True,
                "search_type": search_type,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "result_count": result_count,
                "query_length": len(search_term),
                "response_length": len(result)
            }
        )

        logger.info(f"🎯 Neo4j search completed: {search_type}, {result_count} results, {(time.time() - start_time)*1000:.1f}ms")
        return result

    except Exception as e:
        tool_success = False
        error_details = str(e)
        result = f"Error searching graph database: {str(e)}"

        logger.error(f"❌ Neo4j search error: {e}")

        # Log error to Galileo
        galileo.log(
            operation_name="neo4j_graph_search",
            input_text=search_term,
            output_text=result,
            metadata={
                "success": False,
                "error": error_details,
                "search_type": search_type,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "result_count": 0
            }
        )

        return result


def _count_results_in_response(response: str) -> int:
    """Count the number of results in the response"""
    try:
        # Count different result indicators
        count = 0
        count += response.count('📦')  # Product indicators
        count += response.count('📋')  # Requirement indicators
        count += response.count('🔗')  # Relationship indicators

        # Also look for "Found X items/results/requirements" patterns
        import re
        found_patterns = re.findall(r'Found (\d+)', response)
        if found_patterns:
            count = max(count, int(found_patterns[0]))

        return count
    except:
        return 0


def _search_products(driver, query: str) -> str:
    """Search for products and their requirements"""
    start_time = time.time()

    try:
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
            total_requirements = 0

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
                            total_requirements += 1

                products.append(product_info)

            execution_time = (time.time() - start_time) * 1000

            # Log to Galileo with detailed metrics
            galileo.log(
                operation_name="neo4j_product_search",
                input_text=query,
                output_text=f"Found {len(products)} products with {total_requirements} requirements",
                metadata={
                    "search_function": "_search_products",
                    "products_found": len(products),
                    "total_requirements": total_requirements,
                    "execution_time_ms": execution_time,
                    "query_contains_product": "product" in query.lower(),
                    "query_contains_loan": "loan" in query.lower()
                }
            )

            if products:
                return "Found the following products and requirements:\n\n" + "\n".join(products)
            else:
                return f"No products found matching '{query}'"

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        galileo.log(
            operation_name="neo4j_product_search",
            input_text=query,
            output_text=f"Error: {str(e)}",
            metadata={
                "search_function": "_search_products",
                "error": str(e),
                "execution_time_ms": execution_time,
                "success": False
            }
        )
        raise e


def _search_requirements_by_type(driver, query: str) -> str:
    """Search for specific types of requirements"""
    start_time = time.time()

    try:
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
            requirements_with_thresholds = 0
            requirements_with_conditions = 0
            total_linked_products = 0

            for record in result:
                req_info = f"📋 **{record['name']}** (Type: {record['type']})\n"
                req_info += f"   Description: {record['description']}\n"

                if record['threshold']:
                    req_info += f"   Threshold: {record['threshold']}\n"
                    requirements_with_thresholds += 1

                if record['conditions']:
                    conditions = json.loads(record['conditions']) if isinstance(record['conditions'], str) else record['conditions']
                    if conditions:
                        req_info += f"   Conditions: {', '.join(conditions)}\n"
                        requirements_with_conditions += 1

                if record['linked_products']:
                    req_info += f"   Applies to: {', '.join(record['linked_products'])}\n"
                    total_linked_products += len(record['linked_products'])
                elif record['applicable_products']:
                    products = json.loads(record['applicable_products']) if isinstance(record['applicable_products'], str) else record['applicable_products']
                    if products:
                        req_info += f"   Applicable to: {', '.join(products)}\n"
                        total_linked_products += len(products)

                requirements.append(req_info)

            execution_time = (time.time() - start_time) * 1000

            # Determine query type for tracking
            query_type = "unknown"
            if "credit" in query.lower():
                query_type = "credit_score"
            elif "dti" in query.lower():
                query_type = "debt_to_income"
            elif "ltv" in query.lower():
                query_type = "loan_to_value"
            elif "income" in query.lower():
                query_type = "income"
            elif "down payment" in query.lower():
                query_type = "down_payment"

            # Log to Galileo with detailed metrics
            galileo.log(
                operation_name="neo4j_requirements_search",
                input_text=query,
                output_text=f"Found {len(requirements)} requirements",
                metadata={
                    "search_function": "_search_requirements_by_type",
                    "requirements_found": len(requirements),
                    "requirements_with_thresholds": requirements_with_thresholds,
                    "requirements_with_conditions": requirements_with_conditions,
                    "total_linked_products": total_linked_products,
                    "execution_time_ms": execution_time,
                    "query_type": query_type
                }
            )

            if requirements:
                return f"Found {len(requirements)} requirements:\n\n" + "\n".join(requirements)
            else:
                return f"No requirements found matching '{query}'"

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        galileo.log(
            operation_name="neo4j_requirements_search",
            input_text=query,
            output_text=f"Error: {str(e)}",
            metadata={
                "search_function": "_search_requirements_by_type",
                "error": str(e),
                "execution_time_ms": execution_time,
                "success": False
            }
        )
        raise e


def _search_relationships(driver, query: str) -> str:
    """Search for relationships between requirements"""
    start_time = time.time()
    keywords = query.lower().replace("linked to", "").replace("related to", "").replace("requirements", "").strip()

    try:
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
            strong_relationships = 0
            typed_relationships = 0

            for record in result:
                rel_info = f"🔗 {record['source']} --[{record['link_type']}]--> {record['target']}\n"
                if record['description']:
                    rel_info += f"   Relationship: {record['description']}\n"
                if record['strength']:
                    rel_info += f"   Strength: {record['strength']}\n"
                    if record['strength'] == 'STRONG':
                        strong_relationships += 1
                if record['link_type']:
                    typed_relationships += 1
                relationships.append(rel_info)

            execution_time = (time.time() - start_time) * 1000

            # Log to Galileo
            galileo.log(
                operation_name="neo4j_relationships_search",
                input_text=query,
                output_text=f"Found {len(relationships)} relationships",
                metadata={
                    "search_function": "_search_relationships",
                    "relationships_found": len(relationships),
                    "strong_relationships": strong_relationships,
                    "typed_relationships": typed_relationships,
                    "execution_time_ms": execution_time,
                    "keywords_extracted": keywords
                }
            )

            if relationships:
                return f"Found {len(relationships)} relationships:\n\n" + "\n".join(relationships)
            else:
                return f"No relationships found for '{query}'"

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        galileo.log(
            operation_name="neo4j_relationships_search",
            input_text=query,
            output_text=f"Error: {str(e)}",
            metadata={
                "search_function": "_search_relationships",
                "error": str(e),
                "execution_time_ms": execution_time,
                "success": False
            }
        )
        raise e


def _general_search(driver, query: str) -> str:
    """General search across all nodes"""
    start_time = time.time()

    try:
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
            products_found = 0
            requirements_found = 0
            items_with_thresholds = 0

            for record in result:
                node_info = f"{'📦' if record['node_type'] == 'Product' else '📋'} "
                node_info += f"**{record['name']}** ({record['node_type']})\n"

                if record['type']:
                    node_info += f"   Type: {record['type']}\n"
                if record['description']:
                    node_info += f"   Description: {record['description'][:200]}...\n"
                if record['threshold']:
                    node_info += f"   Threshold: {record['threshold']}\n"
                    items_with_thresholds += 1

                if record['node_type'] == 'Product':
                    products_found += 1
                else:
                    requirements_found += 1

                results.append(node_info)

            execution_time = (time.time() - start_time) * 1000

            # Log to Galileo
            galileo.log(
                operation_name="neo4j_general_search",
                input_text=query,
                output_text=f"Found {len(results)} items ({products_found} products, {requirements_found} requirements)",
                metadata={
                    "search_function": "_general_search",
                    "total_results": len(results),
                    "products_found": products_found,
                    "requirements_found": requirements_found,
                    "items_with_thresholds": items_with_thresholds,
                    "execution_time_ms": execution_time,
                    "fallback_to_stats": len(results) == 0
                }
            )

            if results:
                return f"Found {len(results)} items in the graph:\n\n" + "\n".join(results)
            else:
                return _get_graph_stats(driver, query)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        galileo.log(
            operation_name="neo4j_general_search",
            input_text=query,
            output_text=f"Error: {str(e)}",
            metadata={
                "search_function": "_general_search",
                "error": str(e),
                "execution_time_ms": execution_time,
                "success": False
            }
        )
        raise e


def _get_graph_stats(driver, query: str) -> str:
    """Get graph database statistics"""
    start_time = time.time()

    try:
        with driver.session() as session:
            products = session.run("MATCH (p:Product) RETURN count(p) as count").single()['count']
            requirements = session.run("MATCH (r:Requirement) RETURN count(r) as count").single()['count']
            relationships = session.run("MATCH ()-[r:LINKED_TO]->() RETURN count(r) as count").single()['count']

            execution_time = (time.time() - start_time) * 1000

            # Log to Galileo
            galileo.log(
                operation_name="neo4j_graph_stats",
                input_text=query,
                output_text=f"Graph stats: {products} products, {requirements} requirements, {relationships} relationships",
                metadata={
                    "search_function": "_get_graph_stats",
                    "products_count": products,
                    "requirements_count": requirements,
                    "relationships_count": relationships,
                    "execution_time_ms": execution_time,
                    "trigger_query": query,
                    "reason": "no_specific_results_found"
                }
            )

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

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        galileo.log(
            operation_name="neo4j_graph_stats",
            input_text=query,
            output_text=f"Error: {str(e)}",
            metadata={
                "search_function": "_get_graph_stats",
                "error": str(e),
                "execution_time_ms": execution_time,
                "success": False
            }
        )
        return f"Error retrieving graph statistics: {str(e)}"


# For backward compatibility
def create_neo4j_search_tool():
    """Create a Neo4j search tool for CrewAI agents"""
    if NEO4J_AVAILABLE:
        return search_policy_graph
    else:
        return None