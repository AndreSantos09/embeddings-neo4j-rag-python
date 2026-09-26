"""Camada de IA: recuperação vetorial no Neo4j + geração de resposta via LLM.

Espelha o `ai.ts`: um encadeamento (chain) de duas etapas que compartilham um
estado — primeiro busca os trechos mais similares no vector store, depois gera
a resposta em linguagem natural com o modelo configurado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jVector
from langchain_openai import ChatOpenAI

DebugLog = Callable[..., None]


@dataclass
class ChainState:
    question: str
    context: str | None = None
    top_score: float | None = None
    error: str | None = None
    answer: str | None = None


@dataclass
class AIParams:
    debug_log: DebugLog
    vector_store: Neo4jVector
    nlp_model: ChatOpenAI
    prompt_config: dict[str, Any]
    template_text: str
    top_k: int


class AI:
    def __init__(self, params: AIParams):
        self.params = params

    def retrieve_vector_search_results(self, state: ChainState) -> ChainState:
        self.params.debug_log("🔍 Buscando no vector store do Neo4j...")
        vector_results = self.params.vector_store.similarity_search_with_score(
            state.question, k=self.params.top_k
        )

        if not vector_results:
            self.params.debug_log("⚠️  Nenhum resultado encontrado no vector store.")
            state.error = (
                "Desculpe, não encontrei informações relevantes sobre essa "
                "pergunta na base de conhecimento."
            )
            return state

        top_score = vector_results[0][1]
        self.params.debug_log(
            f"✅ Encontrados {len(vector_results)} resultados relevantes "
            f"(melhor score: {top_score:.3f})"
        )

        contexts = "\n\n---\n\n".join(
            doc.page_content for doc, score in vector_results if score > 0.5
        )

        state.context = contexts
        state.top_score = top_score
        return state

    def generate_nlp_response(self, state: ChainState) -> ChainState:
        if state.error:
            return state

        self.params.debug_log("🤖 Gerando resposta com IA...")

        response_prompt = ChatPromptTemplate.from_template(self.params.template_text)
        response_chain = response_prompt | self.params.nlp_model | StrOutputParser()

        instructions = "\n".join(
            f"{idx + 1}. {instruction}"
            for idx, instruction in enumerate(self.params.prompt_config["instructions"])
        )
        constraints = self.params.prompt_config["constraints"]

        raw_response = response_chain.invoke(
            {
                "role": self.params.prompt_config["role"],
                "task": self.params.prompt_config["task"],
                "tone": constraints["tone"],
                "language": constraints["language"],
                "format": constraints["format"],
                "instructions": instructions,
                "question": state.question,
                "context": state.context,
            }
        )

        state.answer = raw_response
        return state

    def answer_question(self, question: str) -> ChainState:
        state = ChainState(question=question)
        state = self.retrieve_vector_search_results(state)
        state = self.generate_nlp_response(state)
        return state
