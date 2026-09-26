"""Carregamento e fatiamento (chunking) do documento PDF.

Espelha o `documentProcessor.ts`: carrega o PDF, divide em chunks com
sobreposição e normaliza os metadados para conter apenas a origem (source).
"""

from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import TextSplitterConfig


class DocumentProcessor:
    def __init__(self, pdf_path: Path | str, text_splitter_config: TextSplitterConfig):
        self.pdf_path = str(pdf_path)
        self.text_splitter_config = text_splitter_config

    def load_and_split(self) -> list[Document]:
        loader = PyPDFLoader(self.pdf_path)
        raw_documents = loader.load()
        print(f"📄 Carregadas {len(raw_documents)} páginas do PDF")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.text_splitter_config.chunk_size,
            chunk_overlap=self.text_splitter_config.chunk_overlap,
        )
        documents = splitter.split_documents(raw_documents)
        print(f"✂️  Dividido em {len(documents)} chunks")

        # Mantém apenas o metadado de origem, como no projeto original.
        return [
            Document(
                page_content=doc.page_content,
                metadata={"source": doc.metadata.get("source")},
            )
            for doc in documents
        ]
