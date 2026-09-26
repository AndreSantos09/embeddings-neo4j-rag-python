# Regravar o GIF da demo (`docs/demo.gif`)

A demo (`scripts/demo.py`) roda o fluxo completo do RAG — PDF -> chunks ->
embeddings locais -> Neo4j -> busca vetorial -> (opcional) resposta via LLM —
chamando os componentes do projeto diretamente. Rode da **raiz do repositório**.

## Pré-requisitos

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
# Docker (para o Neo4j) precisa estar rodando.
```

A etapa de geração via LLM só aparece se houver uma `OPENROUTER_API_KEY` real
no ambiente (ex.: `export OPENROUTER_API_KEY=...` antes de gravar). Sem ela, a
demo mostra até a busca vetorial, que já roda 100% local.

## Opção 1 — asciinema + agg (recomendado, sem dependência de browser)

```bash
brew install asciinema agg          # macOS
asciinema rec --overwrite -c "bash scripts/demo_run.sh" /tmp/demo.cast
agg --theme monokai --font-size 20 /tmp/demo.cast docs/demo.gif
```

`scripts/demo_run.sh` sobe um Neo4j isolado (portas 7688/7475), roda a demo e
derruba o Neo4j no fim.

## Opção 2 — vhs

```bash
brew install vhs
vhs scripts/demo.tape               # escreve docs/demo.gif
```

> Nota: o `vhs` depende de um Chromium headless (via go-rod). Em alguns
> ambientes esse download falha silenciosamente e o GIF não é gerado — nesse
> caso, use a Opção 1.

## Ajustar o ritmo

A variável `DEMO_PACE` (segundos entre passos, default `0.9`) controla a
velocidade da animação:

```bash
DEMO_PACE=1.2 bash scripts/demo_run.sh   # mais devagar
DEMO_PACE=0   bash scripts/demo_run.sh   # instantâneo (para testar)
```
