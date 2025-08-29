#!/usr/bin/env python3
"""
Test script for Neo4j database connection
"""

import os
from neo4j import GraphDatabase
import sys

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def test_connection(self):
        """Test the connection to Neo4j database"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record and record["num"] == 1:
                    return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
        return False
    
    def get_database_info(self):
        """Get basic database information"""
        try:
            with self.driver.session() as session:
                # Get database version
                version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                print("\n📊 Database Components:")
                for record in version_result:
                    print(f"  - {record['name']}: {', '.join(record['versions'])}")
                
                # Get node count
                node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
                print(f"\n📈 Total Nodes: {node_count}")
                
                # Get relationship count
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
                print(f"📈 Total Relationships: {rel_count}")
                
                # Get node labels
                labels_result = session.run("CALL db.labels() YIELD label RETURN label")
                labels = [record["label"] for record in labels_result]
                print(f"\n🏷️  Node Labels: {', '.join(labels) if labels else 'None'}")
                
                # Get relationship types
                rel_types_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                rel_types = [record["relationshipType"] for record in rel_types_result]
                print(f"🔗 Relationship Types: {', '.join(rel_types) if rel_types else 'None'}")
                
        except Exception as e:
            print(f"Failed to get database info: {e}")
    
    def run_sample_queries(self):
        """Run some sample queries"""
        try:
            with self.driver.session() as session:
                print("\n🔍 Running Sample Queries:")
                
                # Create a test node
                print("\n1. Creating a test node...")
                create_result = session.run(
                    "CREATE (n:TestNode {name: 'Test', timestamp: timestamp()}) RETURN n"
                )
                node = create_result.single()["n"]
                print(f"   ✅ Created node with properties: {dict(node)}")
                
                # Query the test node
                print("\n2. Querying the test node...")
                query_result = session.run("MATCH (n:TestNode {name: 'Test'}) RETURN n")
                for record in query_result:
                    print(f"   Found: {dict(record['n'])}")
                
                # Clean up - delete test node
                print("\n3. Cleaning up test data...")
                session.run("MATCH (n:TestNode {name: 'Test'}) DELETE n")
                print("   ✅ Test node deleted")
                
        except Exception as e:
            print(f"Failed to run sample queries: {e}")


def main():
    print("🚀 Neo4j Connection Test Script")
    print("=" * 50)
    
    # Get connection parameters from environment or use defaults
    neo4j_conn = Neo4jConnection(
        uri=os.getenv('NEO4J_URI', 'neo4j+s://71b9f1cc.databases.neo4j.io'),
        user=os.getenv('NEO4J_USER', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD', 'R0-PQxTKcNZfCQoPRQon_iUsemRwZNpgSdn1TOpfJiU')
    )
    
    print("\n🔌 Testing connection to Neo4j...")
    print(f"   URI: {os.getenv('NEO4J_URI', 'neo4j+s://71b9f1cc.databases.neo4j.io')}")
    print(f"   User: {os.getenv('NEO4J_USER', 'neo4j')}")
    
    if neo4j_conn.test_connection():
        print("   ✅ Connection successful!")
        
        # Get database information
        neo4j_conn.get_database_info()
        
        # Run sample queries
        neo4j_conn.run_sample_queries()
        
    else:
        print("   ❌ Connection failed!")
        sys.exit(1)
    
    # Clean up
    neo4j_conn.close()
    print("\n✅ Connection closed successfully")
    print("=" * 50)


if __name__ == "__main__":
    main()