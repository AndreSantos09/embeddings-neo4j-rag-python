"""Ponto de entrada do pipeline de RAG.

Espelha o `index.ts`:
  1. Carrega o PDF e divide em chunks.
  2. Cria os embeddings locais (HuggingFace).
  3. Popula o vector store no Neo4j.
  4. Executa buscas por similaridade e gera respostas com o LLM.
  5. Salva cada resposta em um arquivo Markdown.
"""

from __future__ import annotations

import time
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j import Neo4jVector
from langchain_openai import ChatOpenAI

from .ai import AI, AIParams
from .config import load_config
from .document_processor import DocumentProcessor

# Perguntas fixas, iguais às do projeto original.
QUESTIONS = [
    # "O que são tensores e como são representados em JavaScript?",
    "Como converter objetos JavaScript em tensores?",
    "O que é normalização de dados e por que é necessária?",
    "Como funciona uma rede neural no TensorFlow.js?",
    "O que significa treinar uma rede neural?",
    "o que é hot enconding e quando usar?",
]


def clear_all(vector_store: Neo4jVector, node_label: str) -> None:
    print("🗑️  Removendo todos os documentos existentes...")
    vector_store.query(f"MATCH (n:`{node_label}`) DETACH DELETE n")
    print("✅ Documentos removidos com sucesso\n")


def main() -> None:
    config = load_config()
    neo4j_vector_store: Neo4jVector | None = None

    try:
        print("🚀 Inicializando sistema de Embeddings com Neo4j...\n")

        # ==================== ETAPA 1: INDEXAÇÃO ====================
        document_processor = DocumentProcessor(config.pdf_path, config.text_splitter)
        documents = document_processor.load_and_split()

        embeddings = HuggingFaceEmbeddings(model_name=config.embedding.model_name)

        nlp_model = ChatOpenAI(
            temperature=config.open_router.temperature,
            max_retries=config.open_router.max_retries,
            model=config.open_router.nlp_model,
            api_key=config.open_router.api_key,
            base_url=config.open_router.url,
            default_headers=config.open_router.default_headers,
        )

        neo4j_vector_store = Neo4jVector.from_existing_graph(
            embedding=embeddings,
            url=config.neo4j.url,
            username=config.neo4j.username,
            password=config.neo4j.password,
            index_name=config.neo4j.index_name,
            node_label=config.neo4j.node_label,
            text_node_properties=list(config.neo4j.text_node_properties),
            embedding_node_property="embedding",
            search_type=config.neo4j.search_type,
        )

        clear_all(neo4j_vector_store, config.neo4j.node_label)
        for index, doc in enumerate(documents):
            print(f"✅ Adicionando documento {index + 1}/{len(documents)}")
            neo4j_vector_store.add_documents([doc])
        print("\n✅ Base de dados populada com sucesso!\n")

        # ==================== ETAPA 2: BUSCA POR SIMILARIDADE ====================
        print("🔍 ETAPA 2: Executando buscas por similaridade...\n")

        ai = AI(
            AIParams(
                nlp_model=nlp_model,
                debug_log=print,
                vector_store=neo4j_vector_store,
                prompt_config=config.prompt_config,
                template_text=config.template_text,
                top_k=config.top_k,
            )
        )

        answers_folder: Path = config.output.answers_folder
        answers_folder.mkdir(parents=True, exist_ok=True)

        for index, question in enumerate(QUESTIONS):
            print(f"\n{'=' * 80}")
            print(f"📌 PERGUNTA: {question}")
            print("=" * 80)

            result = ai.answer_question(question)
            if result.error:
                print(f"\n❌ Erro: {result.error}\n")
                continue

            print(f"\n{result.answer}\n")

            timestamp = int(time.time() * 1000)
            file_name = answers_folder / f"{config.output.file_name}-{index}-{timestamp}.md"
            file_name.write_text(result.answer or "", encoding="utf-8")

        print(f"\n{'=' * 80}")
        print("✅ Processamento concluído com sucesso!\n")

    except Exception as error:  # noqa: BLE001 - queremos logar qualquer falha
        print("error", error)
        raise
    finally:
        if neo4j_vector_store is not None:
            # O Neo4jVector do langchain-neo4j expõe o driver interno em _driver.
            driver = getattr(neo4j_vector_store, "_driver", None)
            if driver is not None:
                driver.close()


if __name__ == "__main__":
    main()
