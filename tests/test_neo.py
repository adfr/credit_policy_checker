from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def create_node(self, label, properties):
        with self.driver.session() as session:
            result = session.run(
                f"CREATE (n:{label} $props) RETURN n",
                props=properties
            )
            return result.single()[0]
    
    def find_nodes(self, label, properties=None):
        with self.driver.session() as session:
            if properties:
                result = session.run(
                    f"MATCH (n:{label} $props) RETURN n",
                    props=properties
                )
            else:
                result = session.run(f"MATCH (n:{label}) RETURN n")
            return [record["n"] for record in result]

# Get credentials from main .env - no hardcoded defaults
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

if not all([uri, user, password]):
    raise ValueError("Neo4j credentials not found in main .env file")

neo4j_conn = Neo4jConnection(uri, user, password)

# Test the connection using the Neo4jConnection class
try:
    # Test basic connectivity
    print("Testing Neo4j connection...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("Connection successful!")
    
    # Test query
    with driver.session() as session:
        result = session.run("RETURN 1 AS num")
        print(f"Test query result: {result.single()['num']}")
        
    driver.close()
    
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()