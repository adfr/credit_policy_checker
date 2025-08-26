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

neo4j_conn = Neo4jConnection(
            uri = os.getenv('NEO4J_URI', 'neo4j+s://71b9f1cc.databases.neo4j.io'),
            user = os.getenv('NEO4J_USER', 'neo4j'),
            password = os.getenv('NEO4J_PASSWORD', 'R0-PQxTKcNZfCQoPRQon_iUsemRwZNpgSdn1TOpfJiU') )

from neo4j import GraphDatabase
import sys

uri = "neo4j+s://71b9f1cc.databases.neo4j.io'"
user = "neo4j"
password = "R0-PQxTKcNZfCQoPRQon_iUsemRwZNpgSdn1TOpfJiU"

try:
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