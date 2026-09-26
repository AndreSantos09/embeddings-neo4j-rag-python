#!/usr/bin/env python3
"""
Demo cinematográfica do embeddings-neo4j-rag-python.

Roda o fluxo completo do RAG — PDF -> chunks -> embeddings locais -> Neo4j ->
busca vetorial -> (opcional) resposta via LLM — chamando os componentes do
projeto diretamente, com narração passo a passo. Serve para gravar um GIF
(ver scripts/demo.tape) e para entender o pipeline lendo um arquivo só.

A etapa de geração via LLM só roda se houver uma OPENROUTER_API_KEY real no
ambiente; caso contrário a demo mostra apenas a recuperação (que já roda 100%
local, sem custo de API).

Uso:
    docker run --rm -d -p 7688:7687 -p 7475:7474 \\
        -e NEO4J_AUTH=neo4j/password neo4j:5.26-community
    NEO4J_URI=bolt://localhost:7688 NEO4J_USER=neo4j NEO4J_PASSWORD=password \\
        EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \\
        python3 scripts/demo.py
"""

import os
import sys
import time

# Garante import de `src` rodando de qualquer lugar.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Padrões seguros para a demo (Neo4j isolado + embeddings locais).
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7688")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")
os.environ.setdefault(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# --- estética ---------------------------------------------------------------
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"

PACE = float(os.environ.get("DEMO_PACE", "0.9"))  # segundos entre passos


def pause(mult: float = 1.0) -> None:
    time.sleep(PACE * mult)


def step(n: int, title: str) -> None:
    print(f"\n{BOLD}{CYAN}[{n}] {title}{RESET}")
    pause()


def user(msg: str) -> None:
    print(f"  {MAGENTA}pergunta ▸{RESET} {msg}")
    pause(0.7)


def server(msg: str) -> None:
    print(f"  {DIM}pipeline · {msg}{RESET}")
    pause(0.5)


def ok(msg: str) -> None:
    print(f"  {GREEN}ok{RESET} {msg}")
    pause(0.6)


def main() -> None:
    print(f"{BOLD}embeddings-neo4j-rag-python — demo do fluxo{RESET}")
    print(f"{DIM}PDF -> embeddings locais -> Neo4j -> busca vetorial -> LLM{RESET}")
    pause()

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_neo4j import Neo4jVector

    from src.config import load_config
    from src.document_processor import DocumentProcessor

    config = load_config()

    # 1. Carrega e fatia o PDF
    step(1, "Carrega o PDF e divide em chunks")
    server("DocumentProcessor.load_and_split()")
    documents = DocumentProcessor(config.pdf_path, config.text_splitter).load_and_split()
    ok(f"{len(documents)} chunks (chunk_size={config.text_splitter.chunk_size}, "
       f"overlap={config.text_splitter.chunk_overlap})")

    # 2. Embeddings locais
    step(2, "Gera embeddings localmente (sem custo de API)")
    server(f"modelo = {YELLOW}{config.embedding.model_name}{RESET}")
    embeddings = HuggingFaceEmbeddings(model_name=config.embedding.model_name)
    ok("modelo carregado — roda 100% na sua máquina")

    # 3. Indexa no Neo4j
    step(3, "Indexa os vetores no Neo4j")
    vector_store = Neo4jVector.from_existing_graph(
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
    vector_store.query(f"MATCH (n:`{config.neo4j.node_label}`) DETACH DELETE n")
    for doc in documents:
        vector_store.add_documents([doc])
    count = vector_store.query(
        f"MATCH (n:`{config.neo4j.node_label}`) RETURN count(n) AS c"
    )[0]["c"]
    server(f"index = {YELLOW}{config.neo4j.index_name}{RESET} · "
           f"label = {YELLOW}{config.neo4j.node_label}{RESET}")
    ok(f"{count} nós indexados com vetor de embedding")

    # 4. Busca por similaridade
    question = "O que é normalização de dados e por que é necessária?"
    step(4, "Recupera os trechos mais relevantes (top-K)")
    user(question)
    results = vector_store.similarity_search_with_score(question, k=config.top_k)
    server(f"top-{config.top_k} por similaridade de cosseno")
    for i, (doc, score) in enumerate(results, 1):
        snippet = " ".join(doc.page_content.split())[:70]
        print(f"    {i}. {GREEN}score={score:.3f}{RESET} {DIM}{snippet}...{RESET}")
        pause(0.3)
    ok("contexto recuperado direto do grafo")

    # 5. Geração via LLM (opcional — precisa de chave real)
    step(5, "Gera a resposta com o LLM (via OpenRouter)")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key and "xxxx" not in api_key:
        from langchain_openai import ChatOpenAI

        from src.ai import AI, AIParams

        nlp_model = ChatOpenAI(
            temperature=config.open_router.temperature,
            max_retries=config.open_router.max_retries,
            model=config.open_router.nlp_model,
            api_key=config.open_router.api_key,
            base_url=config.open_router.url,
            default_headers=config.open_router.default_headers,
        )
        ai = AI(
            AIParams(
                nlp_model=nlp_model,
                debug_log=lambda *a, **k: None,  # silencia logs internos na demo
                vector_store=vector_store,
                prompt_config=config.prompt_config,
                template_text=config.template_text,
                top_k=config.top_k,
            )
        )
        result = ai.answer_question(question)
        answer = " ".join((result.answer or "").split())
        server(f"modelo = {YELLOW}{config.open_router.nlp_model}{RESET}")
        print(f"  {BLUE}resposta ▸{RESET} {answer[:220]}...")
        pause()
        ok("resposta gerada só com o contexto recuperado (grounded)")
    else:
        server(f"{RED}OPENROUTER_API_KEY ausente{RESET} — pulando a geração")
        ok("defina a chave no .env para ver a resposta do LLM")

    # Cleanup da conexão
    driver = getattr(vector_store, "_driver", None)
    if driver is not None:
        driver.close()

    print(f"\n{BOLD}{GREEN}✓ fluxo completo.{RESET} "
          f"{DIM}github.com/AndreSantos09/embeddings-neo4j-rag-python{RESET}\n")


if __name__ == "__main__":
    main()
