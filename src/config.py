"""Configuração central da aplicação.

Carrega os prompts a partir de arquivos, lê variáveis de ambiente e expõe um
objeto de configuração imutável, espelhando o `config.ts` do projeto original.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env, se existir.
load_dotenv()

# Diretório raiz do projeto (pai da pasta src/).
ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(_read_text(path))


@dataclass(frozen=True)
class TextSplitterConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200


@dataclass(frozen=True)
class Neo4jConfig:
    url: str
    username: str
    password: str
    index_name: str = "tensors_index"
    search_type: str = "vector"
    text_node_properties: tuple[str, ...] = ("text",)
    node_label: str = "Chunk"


@dataclass(frozen=True)
class OpenRouterConfig:
    nlp_model: str | None
    url: str = "https://openrouter.ai/api/v1"
    api_key: str | None = None
    temperature: float = 0.3
    max_retries: int = 2
    default_headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str


@dataclass(frozen=True)
class OutputConfig:
    answers_folder: Path = ROOT_DIR / "respostas"
    file_name: str = "resposta"


@dataclass(frozen=True)
class Config:
    prompt_config: dict[str, Any]
    template_text: str
    output: OutputConfig
    neo4j: Neo4jConfig
    open_router: OpenRouterConfig
    pdf_path: Path
    text_splitter: TextSplitterConfig
    embedding: EmbeddingConfig
    top_k: int = 3


def load_config() -> Config:
    """Monta o objeto de configuração a partir do ambiente e dos prompts."""
    return Config(
        prompt_config=_read_json(PROMPTS_DIR / "answerPrompt.json"),
        template_text=_read_text(PROMPTS_DIR / "template.txt"),
        output=OutputConfig(),
        neo4j=Neo4jConfig(
            url=os.environ["NEO4J_URI"],
            username=os.environ["NEO4J_USER"],
            password=os.environ["NEO4J_PASSWORD"],
        ),
        open_router=OpenRouterConfig(
            nlp_model=os.environ.get("NLP_MODEL"),
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            default_headers={
                "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", ""),
                "X-Title": os.environ.get("OPENROUTER_SITE_NAME", ""),
            },
        ),
        pdf_path=ROOT_DIR / "tensores.pdf",
        text_splitter=TextSplitterConfig(),
        embedding=EmbeddingConfig(
            model_name=os.environ["EMBEDDING_MODEL"],
        ),
        top_k=3,
    )
