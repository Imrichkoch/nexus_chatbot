$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$env:NEXUS_DATABASE = Join-Path $projectRoot 'data\nexus.sqlite3'
$env:NEXUS_SYNTHETIC_DATABASE = Join-Path $projectRoot 'data\synthetic-business.sqlite3'
$env:NEXUS_INFRA_SNAPSHOT = Join-Path $projectRoot 'data\infra-snapshot.json'
$env:NEXUS_SECURE_COOKIES = '0'
$env:NEXUS_ALLOWED_HOSTS = 'localhost,127.0.0.1,testserver'
$env:NEXUS_RAG_EMBEDDINGS_ENABLED = '1'
$env:NEXUS_RAG_EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
$env:NEXUS_RAG_EMBEDDING_CACHE = Join-Path $projectRoot 'data\embedding-models'
$env:NEXUS_RAG_EMBEDDING_THREADS = '4'

& (Join-Path $projectRoot '.venv\Scripts\python.exe') -m uvicorn nexus.app:app --host 127.0.0.1 --port 8000 --reload
