from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
old_password = os.getenv('NEO4J_PASSWORD', 'neo4j')
new_password = 'neo4j123!'  # Change this to your desired password

print("Setting up Neo4j...")
print(f"Connecting to {uri} as {user}")

try:
    # First, change the password
    driver = GraphDatabase.driver(uri, auth=(user, old_password))
    
    with driver.session(database="system") as session:
        session.run(
            "ALTER CURRENT USER SET PASSWORD FROM $old_password TO $new_password",
            old_password=old_password,
            new_password=new_password
        )
    
    print("Password changed successfully!")
    driver.close()
    
    # Update .env file
    with open('.env', 'w') as f:
        f.write(f"NEO4J_URI={uri}\n")
        f.write(f"NEO4J_USER={user}\n")
        f.write(f"NEO4J_PASSWORD={new_password}\n")
    
    print("Updated .env file with new password")
    print(f"New password: {new_password}")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nIf you're getting an authentication error, the password might have already been changed.")
    print("Try updating the .env file manually with your Neo4j password.")