import time
from py2neo import Graph
import os

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "graphpassword")

# Retry connection up to 10 times
for i in range(10):
    try:
        graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        graph.run("RETURN 1").evaluate()
        break
    except Exception as e:
        print(f"[Neo4j Connect] Attempt {i+1}/10 failed: {e}")
        time.sleep(3)
else:
    raise ConnectionError("Failed to connect to Neo4j after 10 attempts")