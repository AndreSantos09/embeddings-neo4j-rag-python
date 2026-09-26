# Gera docs/demo.gif a partir da demo do fluxo.
#
# Pré-requisitos: vhs, docker, e um venv em .venv com as deps instaladas.
#   brew install vhs
#   python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
#
# Rodar da RAIZ do repositório:
#   vhs scripts/demo.tape
#
# O Neo4j é subido/derrubado pelo próprio tape (portas 7688/7475, isoladas).

Output "docs/demo.gif"

Set Shell zsh
Set FontSize 18
Set Width 1100
Set Height 820
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 0ms

# Sobe o Neo4j isolado e espera aceitar conexões Bolt.
Hide
Type "docker rm -f rag-demo-neo4j >/dev/null 2>&1; docker run --rm -d --name rag-demo-neo4j -p 7688:7687 -p 7475:7474 -e NEO4J_AUTH=neo4j/password neo4j:5.26-community >/dev/null; until docker exec rag-demo-neo4j cypher-shell -u neo4j -p password 'RETURN 1' >/dev/null 2>&1; do sleep 2; done; clear" Enter
Sleep 30s
Show

Type "NEO4J_URI=bolt://localhost:7688 NEO4J_USER=neo4j NEO4J_PASSWORD=password EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 DEMO_PACE=0.9 .venv/bin/python scripts/demo.py"
Sleep 500ms
Enter
Sleep 30s

Hide
Type "docker rm -f rag-demo-neo4j >/dev/null 2>&1; clear" Enter
Sleep 1s
Show
