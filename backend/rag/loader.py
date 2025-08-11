from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

class PDFLoader:
    def __init__(self, data_dir="data/documents"):
        self.data_dir = data_dir
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    def load_documents(self):
        documents = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".pdf"):
                loader = PDFPlumberLoader(os.path.join(self.data_dir, filename))
                docs = loader.load()
                split_docs = self.text_splitter.split_documents(docs)
                documents.extend(split_docs)
        return documents