#!/usr/bin/env bash
# Runner da demo para gravação (asciinema/agg). Sobe um Neo4j isolado,
# roda a demo e derruba o Neo4j. Ver scripts/record-demo.md.
set -e

NEO4J_NAME="rag-demo-neo4j"
BOLT_PORT="7688"
HTTP_PORT="7475"

cleanup() { docker rm -f "$NEO4J_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker rm -f "$NEO4J_NAME" >/dev/null 2>&1 || true
docker run --rm -d --name "$NEO4J_NAME" \
  -p "${BOLT_PORT}:7687" -p "${HTTP_PORT}:7474" \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.26-community >/dev/null

# Espera o Neo4j aceitar conexões Bolt.
echo "aguardando o Neo4j subir..."
until docker exec "$NEO4J_NAME" cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; do
  sleep 2
done

NEO4J_URI="bolt://localhost:${BOLT_PORT}" \
NEO4J_USER="neo4j" \
NEO4J_PASSWORD="password" \
EMBEDDING_MODEL="${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}" \
DEMO_PACE="${DEMO_PACE:-0.9}" \
  .venv/bin/python scripts/demo.py

sleep 2
