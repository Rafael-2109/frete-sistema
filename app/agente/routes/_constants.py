"""
Constantes compartilhadas das rotas do Agente.

Extraidas de routes.py durante modularizacao.
Importadas pelos sub-modulos que precisam.
"""

import os
import tempfile

# Configuracao de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# FEAT-030: Configuracao de heartbeat
HEARTBEAT_INTERVAL_SECONDS = 10  # Envia heartbeat a cada 10s (reduzido de 20s)

# Cache de health check (TTL 5 min) — evita chamada API real a cada request
_health_cache = {'result': None, 'timestamp': 0}
_HEALTH_CACHE_TTL = 300  # segundos (5 min — models.retrieve nao gasta tokens)

# Deadline com renewal: teto absoluto + inatividade renovavel
# MAX_STREAM_DURATION_SECONDS: teto absoluto (540s = 9 min, margem de 1 min antes do Render 600s)
# INACTIVITY_TIMEOUT_SECONDS: deadline renovavel — cada evento real renova. Heartbeats NAO renovam.
MAX_STREAM_DURATION_SECONDS = 540
INACTIVITY_TIMEOUT_SECONDS = 240  # 4 min sem evento real = timeout (mantem valor original)

# Threshold de cosine similarity para considerar memoria efetiva (semantico)
# Configuravel via env var. 0.50 e mais alto que retrieval (0.40) porque
# efetividade exige que o agente tenha *usado* a informacao, nao apenas relevancia.
EFFECTIVENESS_COSINE_THRESHOLD = float(
    os.getenv("MEMORY_EFFECTIVENESS_COSINE_THRESHOLD", "0.50")
)

# Threshold de word overlap para fallback heuristico (relaxado de 0.60 para 0.35)
EFFECTIVENESS_WORD_OVERLAP_THRESHOLD = 0.35

# Maximo de chars da resposta do assistente para embedding (evita diluicao semantica)
EFFECTIVENESS_RESPONSE_MAX_CHARS = 3000
