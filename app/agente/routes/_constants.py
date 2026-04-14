"""
Constantes compartilhadas das rotas do Agente.

Extraidas de routes.py durante modularizacao.
Importadas pelos sub-modulos que precisam.
"""

import os
import tempfile

# Configuracao de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')

# Whitelist de extensoes aceitas no upload
# Expandido em 2026-04-14 (Fase A quick wins): +word, +texto, +bancarios, +webp
ALLOWED_EXTENSIONS = {
    # Documentos (processados como document block nativo Claude ou via skill)
    'pdf', 'docx', 'doc', 'rtf',
    # Planilhas / dados tabulares
    'xlsx', 'xls', 'csv',
    # Imagens (Vision API nativo)
    'png', 'jpg', 'jpeg', 'gif', 'webp',
    # Texto / dados estruturados
    'txt', 'md', 'json', 'xml', 'log',
    # Bancarios (CNAB remessa/retorno e OFX — reusam parsers app/financeiro)
    'rem', 'ret', 'cnab', 'ofx',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Quota por sessao — Fase D (2026-04-14): evita disco encher com uploads abandonados
# Maximo de arquivos simultaneos e soma total de tamanho por sessao
MAX_FILES_PER_SESSION = int(os.getenv("AGENTE_MAX_FILES_PER_SESSION", "20"))
MAX_TOTAL_SIZE_PER_SESSION = int(
    os.getenv("AGENTE_MAX_TOTAL_SIZE_PER_SESSION", str(50 * 1024 * 1024))
)  # 50MB default

# Extensoes de texto puro — pulam validacao de magic bytes pois nao tem
# signature confiavel (qualquer conteudo textual e valido).
TEXT_EXTENSIONS = {
    'txt', 'md', 'json', 'xml', 'log', 'csv',
    'rem', 'ret', 'cnab', 'ofx',
}

# Magic bytes (header) para validar que a extensao nao foi spoofada.
# Ex: arquivo .exe renomeado para .pdf e rejeitado pois nao comeca com b"%PDF-".
# NOTE: docx/xlsx/pptx compartilham signature ZIP (b"PK\x03\x04") — a validacao
# combina extensao + signature (nao confunde porque o whitelist ja filtrou ext).
MIME_SIGNATURES = {
    # PDF
    'pdf': (b'%PDF-',),
    # Imagens
    'png': (b'\x89PNG\r\n\x1a\n',),
    'jpg': (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb', b'\xff\xd8\xff\xee'),
    'jpeg': (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb', b'\xff\xd8\xff\xee'),
    'gif': (b'GIF87a', b'GIF89a'),
    'webp': (b'RIFF',),  # WebP e container RIFF — 1a validacao suficiente aqui
    # OOXML (Office novo) — base ZIP
    'docx': (b'PK\x03\x04',),
    'xlsx': (b'PK\x03\x04',),
    # Legacy Office 97-2003 (OLE Compound File)
    'doc': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',),
    'xls': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',),
    # RTF
    'rtf': (b'{\\rtf',),
}

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
