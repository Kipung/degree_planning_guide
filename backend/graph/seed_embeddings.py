from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

NEO4J_URI    = "bolt://neo4j:7687"
NEO4J_USER   = "neo4j"
NEO4J_PASS   = "graphpassword"
MODEL_NAME   = "all-miniLM-L6-v2"
EMBEDDING_DIM = 384  # fixed output size of all-MiniLM-L6-v2

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    model  = SentenceTransformer(MODEL_NAME)

    with driver.session() as session:
        #–– Pull only courses that have a non-null description
        records = session.run(
            """
            MATCH (c:Course)
            WHERE c.description IS NOT NULL
            RETURN id(c) AS id, c.description AS text
            """
        ).data()

        #–– Compute & set embeddings
        for r in records:
            emb = model.encode(r["text"]).tolist()
            session.run(
                """
                MATCH (c)
                WHERE id(c) = $id
                SET c.embedding = $emb
                """,
                {"id": r["id"], "emb": emb}
            )

        #–– Remove old vector index if it exists
        session.run("DROP INDEX course_embedding_index IF EXISTS")

        #–– Create native vector index with correct OPTIONS block
        session.run(
            """
            CREATE VECTOR INDEX course_embedding_index
            FOR (c:Course) ON (c.embedding)
            OPTIONS {
              indexProvider: 'vector-1.0',
              indexConfig: {
                `vector.dimensions`: $dim,
                `vector.similarity_function`: 'cosine'
              }
            }
            """,
            {"dim": EMBEDDING_DIM}
        )

    print("✅ Embeddings seeded into Neo4j.")

if __name__ == "__main__":
    main()