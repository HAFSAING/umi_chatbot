from .vector_db import VectorDB

class RagRetriever:
    def __init__(self):
        self.vector_db = VectorDB()

    def search(self, query: str, k: int = 3) -> str:
        docs = self.vector_db.vectorstore.similarity_search(query, k=k)
        return "\n---\n".join([d.page_content for d in docs])