from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from .loader import PDFLoader

class VectorDB:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = Chroma(
            persist_directory="data/vector_db",
            embedding_function=self.embeddings
        )

    def initialize(self):
        loader = PDFLoader()
        documents = loader.load_documents()
        if documents:
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()