"""Indexer de regras normativas do Manual ECD Leiaute 9.

Coleta chunks de:
- app/relatorios_fiscais/manual_ecd/bloco_*.md (51 registros + ~150-250 regras nomeadas)
- app/relatorios_fiscais/SPED_ECD_PLANO.md (iteracoes V1.1, V1.2, ...)

Gera embeddings via Voyage AI (voyage-4-lite, 1024 dim) e armazena em
sped_ecd_rule_embeddings com indice HNSW cosine.

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.sped_ecd_rules_indexer [--dry-run] [--reindex] [--stats]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


MANUAL_ECD_DIR = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "manual_ecd"
PLANO_FILE = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "SPED_ECD_PLANO.md"


def _content_hash(text_str: str) -> str:
    return hashlib.md5(text_str.strip().lower().encode("utf-8")).hexdigest()


def _has_app_context() -> bool:
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


# ============================================================
# COLETA — Manual ECD blocos
# ============================================================

REGISTRO_HEADER_RE = re.compile(r"^## Registro (\w+)\s*$", re.MULTILINE)

# Regras nomeadas no manual aparecem em DOIS formatos sintaticamente distintos:
# 1) Lista markdown:    - REGRA_X: descricao              (livre de severidade explicita)
# 2) Tabela markdown:   | REGRA_X | descricao |           (2 colunas, sem Tipo)
#                       | N | **REGRA_X** | descricao | Erro |   (4 colunas, com Tipo)
# Antes (V1) so o formato 1 era captado — ~37% das regras do manual ficavam de fora.
REGRA_LIST_RE = re.compile(
    r"^- \*{0,2}(REGRA_[A-Z_0-9]+)\*{0,2}\s*:\s*(.+)$",
    re.MULTILINE,
)
REGRA_TABLE_RE = re.compile(
    r"^\|\s*(?:\d+\s*\|\s*)?"
    r"\*{0,2}(REGRA_[A-Z_0-9]+)\*{0,2}\s*\|\s*"
    r"([^|\n]+?)\s*"
    r"(?:\|\s*(Erro|Aviso|—|-)\s*)?"
    r"\|\s*$",
    re.MULTILINE,
)


def _detectar_severidade(descricao: str, tipo_explicit: str | None = None) -> str:
    """Mapeia severidade SPED ECD.

    Prioridade:
    1. tipo_explicit — coluna 'Tipo' da tabela 4.1.x do Manual ECD
       (`Erro` ou `Aviso`). Fonte autoritativa.
    2. Heuristica em texto livre — captura `(aviso)`, `aviso ...`, `warning`.
       Detecta tambem casos ambiguos do bloco K do tipo
       "aviso (se menor) ou erro (se maior)" -> retorna `ambiguo`.
    3. Default `erro` — Manual ECD secao 4.1: regra de nivel 2 sem
       indicacao explicita e tratada como erro.
    """
    if tipo_explicit:
        t = tipo_explicit.strip().lower()
        if t.startswith("aviso"):
            return "aviso"
        if t.startswith("erro"):
            return "erro"
    desc_lower = descricao.lower()
    has_aviso = (
        "(aviso)" in desc_lower
        or " aviso " in desc_lower
        or " aviso." in desc_lower
        or "warning" in desc_lower
    )
    has_erro_alt = "ou erro" in desc_lower or "erro (" in desc_lower
    if has_aviso and has_erro_alt:
        return "ambiguo"
    if has_aviso:
        return "aviso"
    return "erro"


def collect_manual_ecd_chunks() -> list[dict[str, Any]]:
    """Varre app/relatorios_fiscais/manual_ecd/bloco_*.md.

    Para cada arquivo:
    - 1 chunk por **Registro** (do header `## Registro X` ate proximo header)
    - 1 chunk por **REGRA_X nomeada** dentro do registro
    """
    chunks: list[dict[str, Any]] = []

    bloco_files = sorted(MANUAL_ECD_DIR.glob("bloco_*.md"))
    for bloco_file in bloco_files:
        bloco_match = re.match(r"bloco_(\w)_", bloco_file.name)
        bloco = bloco_match.group(1).upper() if bloco_match else "?"

        content = bloco_file.read_text(encoding="utf-8")
        positions = [(m.group(1), m.start()) for m in REGISTRO_HEADER_RE.finditer(content)]
        positions.append(("__END__", len(content)))

        for i in range(len(positions) - 1):
            registro, start = positions[i]
            _, end = positions[i + 1]
            registro_text = content[start:end]

            # Chunk do REGISTRO completo — split se gigante (registros 0000 e
            # I355 facilmente passam de 4000 chars com regras + exemplos).
            registro_titulo = f"Registro {registro}"
            for sub_titulo, sub_content in _split_chunk_if_large(registro_titulo, registro_text.strip()):
                part_suffix = ""
                if sub_titulo != registro_titulo:
                    # Sub-chunk — anexa hash do titulo para chunk_id unico
                    part_suffix = ":" + hashlib.md5(sub_titulo.encode("utf-8")).hexdigest()[:8]
                chunks.append({
                    "chunk_id": f"manual_ecd:registro:{registro}{part_suffix}",
                    "chunk_type": "registro",
                    "bloco": bloco,
                    "registro": registro,
                    "regra_name": None,
                    "severidade": None,
                    "content": sub_content,
                    "content_hash": _content_hash(sub_content),
                    "source_file": f"manual_ecd/{bloco_file.name}",
                    "source_anchor": f"#registro-{registro.lower()}",
                })

            # Chunks por REGRA dentro do registro — formatos LIST e TABLE
            # Dedup por nome dentro do mesmo registro (mesma regra pode aparecer
            # listada e tabulada na mesma section).
            regras_seen: set[str] = set()
            ordered_matches: list[tuple[Any, str]] = []
            for m in REGRA_LIST_RE.finditer(registro_text):
                ordered_matches.append((m, "list"))
            for m in REGRA_TABLE_RE.finditer(registro_text):
                ordered_matches.append((m, "table"))

            for regra_match, fmt in ordered_matches:
                regra_name = regra_match.group(1)
                if regra_name in regras_seen:
                    continue
                regras_seen.add(regra_name)

                regra_desc = regra_match.group(2).strip()
                tipo_explicit = regra_match.group(3) if fmt == "table" else None
                severidade = _detectar_severidade(regra_desc, tipo_explicit)

                regra_content = (
                    f"REGRA: {regra_name}\n"
                    f"Aplicada ao registro {registro} (bloco {bloco}).\n"
                    f"Descricao: {regra_desc}"
                )
                chunks.append({
                    "chunk_id": f"manual_ecd:regra:{registro}:{regra_name}",
                    "chunk_type": "regra",
                    "bloco": bloco,
                    "registro": registro,
                    "regra_name": regra_name,
                    "severidade": severidade,
                    "content": regra_content,
                    "content_hash": _content_hash(regra_content),
                    "source_file": f"manual_ecd/{bloco_file.name}",
                    "source_anchor": f"#registro-{registro.lower()}",
                })

    return chunks


# ============================================================
# COLETA — Iteracoes do SPED_ECD_PLANO.md
# ============================================================

# Iteracoes do PLANO podem vir em DOIS formatos:
# - Antigas:  | V20 | data | erros | warn | tamanho | mudancas |
# - Atuais:   | **V31 PVA** | ... | ... | ... | ... | ... |
#             | **V27 REVERTIDO (anterior)** | ... |
# Antes (V1) so o formato antigo era captado — V21+ (mais relevantes) ficavam de fora.
PLANO_ITERACAO_RE = re.compile(
    r"^\|\s*\*{0,2}"
    r"(V[\d.]+(?:\s+(?:PVA|REVERTIDO(?:\s*\([^)]+\))?))?)"
    r"\*{0,2}\s*\|"
    r".*?\|.*?\|.*?\|.*?\|\s*(.+?)\s*\|$",
    re.MULTILINE,
)


def collect_plano_iteracoes() -> list[dict[str, Any]]:
    """Varre SPED_ECD_PLANO.md secao 'HISTORICO DE ITERACOES'."""
    chunks: list[dict[str, Any]] = []

    if not PLANO_FILE.is_file():
        logger.warning(f"PLANO_FILE nao encontrado: {PLANO_FILE}")
        return chunks

    content = PLANO_FILE.read_text(encoding="utf-8")

    for match in PLANO_ITERACAO_RE.finditer(content):
        versao = match.group(1)
        mudancas = match.group(2).strip()

        if not mudancas or mudancas == "TBD":
            continue

        chunk_content = (
            f"Iteracao SPED ECD versao {versao}.\n"
            f"Mudancas aplicadas: {mudancas}"
        )
        chunks.append({
            "chunk_id": f"plano:iteracao:{versao}",
            "chunk_type": "plano_iteracao",
            "bloco": None,
            "registro": None,
            "regra_name": None,
            "severidade": None,
            "content": chunk_content,
            "content_hash": _content_hash(chunk_content),
            "source_file": "app/relatorios_fiscais/SPED_ECD_PLANO.md",
            "source_anchor": "#historico-de-iteracoes",
        })

    return chunks


# ============================================================
# COLETA — Manual ECD capitulos (NAO blocos)
# ============================================================

# Pattern para capturar sections ## ou ### dentro de capitulos do manual
SECTION_HEADER_RE = re.compile(r"^(##+) (.+?)$", re.MULTILINE)

# Pattern para capturar sub-headers (### ou mais profundo)
SUBSECTION_HEADER_RE = re.compile(r"^(###+) (.+?)$", re.MULTILINE)

# Tamanho-alvo de chunk em chars. Chunks acima sao split (P1-1).
# 1500 chars ~ 350-500 tokens — sweet spot para voyage-4-lite manter
# precisao semantica (chunks > 2000 chars representam "media diluida").
MAX_CHUNK_CHARS = 1500


def _split_by_sections(content: str, min_chunk_len: int = 80) -> list[tuple[str, str]]:
    """Split markdown content por headers ## ou ###.

    Retorna lista de (titulo_section, conteudo). Chunks menores que
    min_chunk_len sao mergeados com proximo (evita fragmentacao excessiva).
    """
    positions = [(m.group(2), m.start()) for m in SECTION_HEADER_RE.finditer(content)]
    if not positions:
        return [("__full__", content)] if content.strip() else []

    positions.append(("__END__", len(content)))
    sections: list[tuple[str, str]] = []
    for i in range(len(positions) - 1):
        titulo, start = positions[i]
        _, end = positions[i + 1]
        section_text = content[start:end].strip()
        if len(section_text) >= min_chunk_len:
            sections.append((titulo, section_text))
    return sections


def _split_linear(titulo: str, content: str, max_chars: int) -> list[tuple[str, str]]:
    """Split linear por linhas em janelas de ~max_chars (fallback).

    Mantem agrupamento por linha — nao quebra paragrafos no meio.
    Parts numeradas: "titulo (parte 1)", "titulo (parte 2)", ...
    """
    lines = content.split("\n")
    parts: list[tuple[str, str]] = []
    current: list[str] = []
    current_len = 0
    part_num = 1
    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_chars and current:
            parts.append((f"{titulo} (parte {part_num})", "\n".join(current).strip()))
            part_num += 1
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current and "\n".join(current).strip():
        parts.append((f"{titulo} (parte {part_num})", "\n".join(current).strip()))
    return parts


def _split_chunk_if_large(
    titulo: str,
    content: str,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[tuple[str, str]]:
    """Parte chunks acima de max_chars em sub-chunks coerentes.

    Estrategia em cascata:
    1. Conteudo <= max_chars: retorna sem mexer
    2. Tem `### sub-headers`: split por sub-section, prefixa titulo.
       Sub-sections ainda grandes caem em split linear (sem recursao infinita).
    3. Caso contrario: split linear por linhas em janelas de ~max_chars.

    Cada sub-chunk recebe titulo unico para gerar `chunk_id` distinto via hash.
    """
    if len(content) <= max_chars:
        return [(titulo, content)]

    # Tentativa 1: split por sub-headers ###
    sub_matches = list(SUBSECTION_HEADER_RE.finditer(content))
    if sub_matches:
        parts: list[tuple[str, str]] = []
        first_sub_start = sub_matches[0].start()
        head = content[:first_sub_start].strip()
        if head and len(head) >= 80:
            # Cabeca pre-### — se grande, split linear
            if len(head) > max_chars:
                parts.extend(_split_linear(titulo, head, max_chars))
            else:
                parts.append((titulo, head))
        for i, sm in enumerate(sub_matches):
            sub_title = sm.group(2).strip()
            sub_start = sm.start()
            sub_end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(content)
            sub_content = content[sub_start:sub_end].strip()
            sub_titulo_full = f"{titulo} — {sub_title}"
            # Sub-section ainda grande -> linear (evita recursao infinita
            # quando sub_content comeca com '###' que re-matcheia o regex)
            if len(sub_content) > max_chars:
                parts.extend(_split_linear(sub_titulo_full, sub_content, max_chars))
            else:
                parts.append((sub_titulo_full, sub_content))
        if parts:
            return parts

    # Tentativa 2: split linear
    return _split_linear(titulo, content, max_chars)


def collect_manual_capitulos() -> list[dict[str, Any]]:
    """Varre manual_ecd/0*.md e INDEX.md.

    Cada section ## eh um chunk separado.
    Chunks de 04_regras_validacao com REGRA_X ganham metadata regra_name.
    """
    chunks: list[dict[str, Any]] = []

    capitulos = [
        ("01_informacoes_gerais.md", "informacoes_gerais"),
        ("02_dados_tecnicos.md", "dados_tecnicos"),
        ("04_regras_validacao.md", "regras_validacao"),
        ("INDEX.md", "index_manual"),
    ]

    REGRA_NAME_RE = re.compile(r"\b(REGRA_[A-Z_0-9]+)\b")

    for filename, slug in capitulos:
        filepath = MANUAL_ECD_DIR / filename
        if not filepath.is_file():
            logger.warning(f"Capitulo nao encontrado: {filepath}")
            continue

        content = filepath.read_text(encoding="utf-8")
        sections = _split_by_sections(content)

        for idx, (titulo, section_content) in enumerate(sections):
            # P1-1: parte sections gigantes (>MAX_CHUNK_CHARS) para preservar
            # precisao do embedding. Sections grandes como "Tabela Mestre de
            # Registros" (~7700 chars) viravam 1 chunk diluido.
            for sub_titulo, sub_content in _split_chunk_if_large(titulo, section_content):
                titulo_slug = re.sub(r"[^a-z0-9]+", "_", sub_titulo.lower()).strip("_")[:40] or f"section_{idx}"
                # Hash estavel do titulo COMPLETO — sobrevive a reordenamento de
                # sections no markdown (antes, sufixo `:idx` posicional deixava
                # chunks orfaos a cada edicao).
                titulo_hash = hashlib.md5(sub_titulo.encode("utf-8")).hexdigest()[:8]

                # Detectar REGRA_X dentro do sub-chunk
                regra_match = REGRA_NAME_RE.search(sub_content)
                regra_name = regra_match.group(1) if regra_match else None
                chunk_type = "regra_pva" if regra_name and slug == "regras_validacao" else "manual_capitulo"

                chunk_content = f"Capitulo Manual ECD: {filename}\nSecao: {sub_titulo}\n\n{sub_content}"

                chunks.append({
                    "chunk_id": f"manual_ecd:{slug}:{titulo_slug}:{titulo_hash}",
                    "chunk_type": chunk_type,
                    "bloco": None,
                    "registro": None,
                    "regra_name": regra_name,
                    "severidade": None,
                    "content": chunk_content,
                    "content_hash": _content_hash(chunk_content),
                    "source_file": f"manual_ecd/{filename}",
                    "source_anchor": f"#{titulo_slug}",
                })

    return chunks


# ============================================================
# COLETA — Categorias de erro do PLANO.md
# ============================================================

CATEGORIA_HEADER_RE = re.compile(r"^### (CATEGORIA[S]? [^\n]+?)$", re.MULTILINE)


def collect_plano_categorias() -> list[dict[str, Any]]:
    """Varre SPED_ECD_PLANO.md secao 'INVENTARIO DE CATEGORIAS DE ERRO'.

    Cada `### CATEGORIA N — ...` eh um chunk.
    """
    chunks: list[dict[str, Any]] = []

    if not PLANO_FILE.is_file():
        logger.warning(f"PLANO_FILE nao encontrado: {PLANO_FILE}")
        return chunks

    content = PLANO_FILE.read_text(encoding="utf-8")

    positions = [(m.group(1), m.start()) for m in CATEGORIA_HEADER_RE.finditer(content)]
    if not positions:
        return chunks

    positions.append(("__END__", len(content)))

    for i in range(len(positions) - 1):
        titulo, start = positions[i]
        _, end = positions[i + 1]
        cat_text = content[start:end].strip()

        if len(cat_text) < 100:
            continue  # Skip categorias muito curtas (provavel ruido)

        # Extrair numero da categoria (CATEGORIA 1, CATEGORIA 17, CATEGORIAS 12-16).
        # Headers sem numero (ex: "CATEGORIAS RESOLVIDAS", "CATEGORIAS PENDENTES")
        # caem no fallback hash-based para evitar colisao de chunk_id.
        cat_match = re.match(r"CATEGORIA[S]? (\d+(?:-\d+)?)", titulo)
        if cat_match:
            cat_num = cat_match.group(1)
        else:
            cat_slug = re.sub(r"[^a-z0-9]+", "_", titulo.lower()).strip("_")[:40]
            cat_num = cat_slug or hashlib.md5(titulo.encode("utf-8")).hexdigest()[:8]

        # Severidade: BLOQ ou WARN no titulo
        severidade = None
        if "BLOQ" in titulo:
            severidade = "BLOQUEANTE"
        elif "WARN" in titulo:
            severidade = "WARNING"

        # P1-1: categorias com muito detalhamento (ex: "categorias_adicionais"
        # de 17000+ chars) sao splittadas para preservar precisao do embedding.
        base_titulo = f"Categoria de erro SPED ECD: {titulo}"
        for sub_titulo, sub_content in _split_chunk_if_large(base_titulo, cat_text):
            part_suffix = ""
            if sub_titulo != base_titulo:
                part_suffix = ":" + hashlib.md5(sub_titulo.encode("utf-8")).hexdigest()[:8]
            chunk_content = f"{sub_titulo}\n\n{sub_content}"
            chunks.append({
                "chunk_id": f"plano:categoria:{cat_num}{part_suffix}",
                "chunk_type": "categoria_erro",
                "bloco": None,
                "registro": None,
                "regra_name": None,
                "severidade": severidade,
                "content": chunk_content,
                "content_hash": _content_hash(chunk_content),
                "source_file": "app/relatorios_fiscais/SPED_ECD_PLANO.md",
                "source_anchor": "#inventario-de-categorias-de-erro",
            })

    return chunks


# ============================================================
# COLETA — Sections do CLAUDE.md do modulo (sub-tipadas)
# ============================================================

CLAUDE_MD_FILE = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "CLAUDE.md"


def _classify_claude_md_section(titulo: str) -> str:
    """Mapeia titulo `##` do CLAUDE.md para sub-tipo de chunk.

    Antes (P2 pre-fix): tudo era `gotcha` indiscriminadamente. Auditor
    buscando "ja vi esse bug" trazia TECH STACK e ARQUITETURA junto, ruidoso.

    Categorias:
    - gotcha       : armadilhas / bugs conhecidos
    - decisao      : historico de versoes, decisoes arquiteturais
    - procedimento : fluxos, protocolos, comandos passo-a-passo
    - arquitetura  : referencia estrutural (services, rotas, constantes)
    - referencia   : indices, links externos
    - contexto     : meta-informacao sobre o modulo (onboarding)

    Quando o titulo nao bate em nenhum padrao, classifica como `gotcha`
    (conservador — preserva comportamento legado para sections novas).
    """
    t = titulo.upper()
    # Ordem importa: tokens mais especificos primeiro.
    # "PROTOCOLO DE NOVA VERSAO" contem "VERSAO" mas e procedimento, nao decisao.
    if "GOTCHA" in t:
        return "gotcha"
    if any(k in t for k in ("PROTOCOLO", "FLUXO", "COMO ITERAR", "COMO USAR")):
        return "procedimento"
    if any(k in t for k in ("HISTORICO", "DECISOES", "DECISAO")):
        return "decisao"
    if "VERSAO" in t or "VERSOES" in t:
        # Cai aqui so se nao bateu em procedimento (ex: "HISTORICO DE VERSOES")
        return "decisao"
    if any(k in t for k in (
        "ARQUITETURA", "TECH STACK", "CONSTANTES", "ROTAS",
        "MAPEAMENTO", "ORDEM DE EMISSAO", "VALIDATOR",
        "DADOS EXTRAIDOS", "DADOS EXTRAÍDOS", "MODELOS",
    )):
        return "arquitetura"
    if "REFERENCIA" in t or "REFERÊNCIA" in t or "INDICE" in t or "ÍNDICE" in t:
        return "referencia"
    if "CONTEXTO" in t or "CRITICO" in t or "CRÍTICO" in t:
        return "contexto"
    return "gotcha"


def collect_claude_md_gotchas() -> list[dict[str, Any]]:
    """Varre app/relatorios_fiscais/CLAUDE.md.

    Cada `## SECTION` vira 1+ chunks, sub-tipados via
    `_classify_claude_md_section()` (gotcha/decisao/procedimento/
    arquitetura/referencia/contexto). Sub-chunks de split herdam o
    tipo do titulo PAI (nao reclassificam pelo titulo " — sub").
    """
    chunks: list[dict[str, Any]] = []

    if not CLAUDE_MD_FILE.is_file():
        logger.warning(f"CLAUDE_MD_FILE nao encontrado: {CLAUDE_MD_FILE}")
        return chunks

    content = CLAUDE_MD_FILE.read_text(encoding="utf-8")
    sections = _split_by_sections(content)

    for idx, (titulo, section_text) in enumerate(sections):
        # P2-3: classifica o tipo PELO TITULO PAI (sub-chunks herdam o tipo).
        # Sub-titulos gerados pelo split tem prefixo "Pai — Sub" e poderiam
        # despistar a heuristica (ex: "ARQUITETURA — DECISOES" cairia em decisao).
        section_type = _classify_claude_md_section(titulo)

        # P1-1: parte sections gigantes do CLAUDE.md (ARQUITETURA, HISTORICO
        # DE VERSOES, etc) que podem facilmente ultrapassar 2000 chars.
        for sub_titulo, sub_content in _split_chunk_if_large(titulo, section_text):
            titulo_slug = re.sub(r"[^a-z0-9]+", "_", sub_titulo.lower()).strip("_")[:40] or f"section_{idx}"
            # Hash estavel do titulo (mesma motivacao de collect_manual_capitulos)
            titulo_hash = hashlib.md5(sub_titulo.encode("utf-8")).hexdigest()[:8]

            chunk_content = f"CLAUDE.md modulo relatorios_fiscais: {sub_titulo}\n\n{sub_content}"

            chunks.append({
                "chunk_id": f"claudemd:relatorios_fiscais:{titulo_slug}:{titulo_hash}",
                "chunk_type": section_type,
                "bloco": None,
                "registro": None,
                "regra_name": None,
                "severidade": None,
                "content": chunk_content,
                "content_hash": _content_hash(chunk_content),
                "source_file": "app/relatorios_fiscais/CLAUDE.md",
                "source_anchor": f"#{titulo_slug}",
            })

    return chunks


# ============================================================
# EMBED + STORE
# ============================================================

def embed_and_store(chunks: list[dict[str, Any]], dry_run: bool = False) -> dict[str, int]:
    """Gera embeddings em batch e armazena. Skip se hash ja existe."""
    from app import db
    from app.embeddings.client import get_voyage_client, EmbeddingUnavailableError

    if not _has_app_context():
        raise RuntimeError(
            "Sem Flask app context. Use: with app.app_context(): embed_and_store(...)"
        )

    stats = {"total": len(chunks), "inserted": 0, "skipped": 0, "errors": 0}

    if not chunks:
        return stats

    # Existing snapshot: content_hash + metadata mutavel para detectar
    # mudancas que NAO exigem re-embed (ex: chunk_type re-classificado).
    ids = [c["chunk_id"] for c in chunks]
    result = db.session.execute(
        text("""
            SELECT chunk_id, content_hash, chunk_type, severidade,
                   bloco, registro, regra_name
            FROM sped_ecd_rule_embeddings
            WHERE chunk_id = ANY(:ids)
        """),
        {"ids": ids}
    ).all()
    existing = {
        row.chunk_id: {
            "content_hash": row.content_hash,
            "chunk_type": row.chunk_type,
            "severidade": row.severidade,
            "bloco": row.bloco,
            "registro": row.registro,
            "regra_name": row.regra_name,
        }
        for row in result
    }

    chunks_to_embed: list[dict[str, Any]] = []
    chunks_to_meta_update: list[dict[str, Any]] = []
    for c in chunks:
        e = existing.get(c["chunk_id"])
        if e is None:
            chunks_to_embed.append(c)
            continue
        if e["content_hash"] != c["content_hash"]:
            chunks_to_embed.append(c)
            continue
        # Hash igual: checa metadata mutavel (sem chamar Voyage)
        if (
            e["chunk_type"] != c["chunk_type"]
            or e["severidade"] != c["severidade"]
            or e["bloco"] != c["bloco"]
            or e["registro"] != c["registro"]
            or e["regra_name"] != c["regra_name"]
        ):
            chunks_to_meta_update.append(c)
    stats["skipped"] = len(chunks) - len(chunks_to_embed) - len(chunks_to_meta_update)
    stats["meta_updated"] = 0

    # Metadata-only update (sem chamada a Voyage)
    if chunks_to_meta_update and not dry_run:
        for c in chunks_to_meta_update:
            db.session.execute(
                text("""
                    UPDATE sped_ecd_rule_embeddings
                    SET chunk_type = :chunk_type,
                        severidade = :severidade,
                        bloco      = :bloco,
                        registro   = :registro,
                        regra_name = :regra_name,
                        updated_at = NOW()
                    WHERE chunk_id = :chunk_id
                """),
                {
                    "chunk_id":   c["chunk_id"],
                    "chunk_type": c["chunk_type"],
                    "severidade": c["severidade"],
                    "bloco":      c["bloco"],
                    "registro":   c["registro"],
                    "regra_name": c["regra_name"],
                },
            )
        db.session.commit()
        stats["meta_updated"] = len(chunks_to_meta_update)
        logger.info(
            f"Metadata update (sem re-embed): {len(chunks_to_meta_update)} chunks"
        )
    elif chunks_to_meta_update and dry_run:
        logger.info(
            f"[DRY-RUN] {len(chunks_to_meta_update)} chunks teriam metadata atualizada"
        )
        stats["meta_updated"] = len(chunks_to_meta_update)

    if not chunks_to_embed:
        return stats

    if dry_run:
        logger.info(f"[DRY-RUN] {len(chunks_to_embed)} chunks seriam embedded")
        return stats

    client = get_voyage_client()
    batch_size = 128
    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i : i + batch_size]
        texts = [c["content"] for c in batch]

        try:
            response = client.embed(texts, model="voyage-4-lite", input_type="document")
            # voyageai client retorna obj com .embeddings
            embeddings = response.embeddings if hasattr(response, "embeddings") else response
        except EmbeddingUnavailableError as e:
            logger.error(f"Voyage indisponivel batch {i}: {e}")
            stats["errors"] += len(batch)
            continue
        except Exception as e:
            logger.error(f"Falha ao embedar batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        for chunk, emb in zip(batch, embeddings):
            try:
                db.session.execute(text("""
                    INSERT INTO sped_ecd_rule_embeddings
                        (chunk_id, chunk_type, bloco, registro, regra_name,
                         severidade, content, content_hash, embedding, model,
                         source_file, source_anchor, created_at, updated_at)
                    VALUES (:chunk_id, :chunk_type, :bloco, :registro, :regra_name,
                            :severidade, :content, :content_hash, :embedding, :model,
                            :source_file, :source_anchor, NOW(), NOW())
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """), {
                    **chunk,
                    "embedding": emb,
                    "model": "voyage-4-lite",
                })
                stats["inserted"] += 1
            except Exception as e:
                logger.error(f"Falha upsert chunk {chunk['chunk_id']}: {e}")
                stats["errors"] += 1

        db.session.commit()
        logger.info(f"Batch {i // batch_size + 1}: {len(batch)} chunks processados")

    return stats


def cleanup_orphans(known_ids: set[str], dry_run: bool = False) -> int:
    """Remove rows cujos chunk_ids nao estao mais nas fontes.

    Chamado apos `embed_and_store()`. Detecta chunks com `chunk_id` antigo —
    aparece quando uma section do manual ou do CLAUDE.md e renomeada,
    removida, ou quando um registro deixa de existir.

    Args:
        known_ids: set com os `chunk_id` que SAIRAM dos collectors nesta rodada.
                   Tudo no banco que nao esta neste set sera considerado orfao.
        dry_run: se True, apenas conta orfaos (nao deleta).

    Returns:
        Quantidade de rows deletadas (ou que seriam deletadas em dry-run).
    """
    from app import db
    if not known_ids:
        return 0

    if dry_run:
        count = db.session.execute(
            text("""
                SELECT COUNT(*) FROM sped_ecd_rule_embeddings
                WHERE chunk_id <> ALL(:ids)
            """),
            {"ids": list(known_ids)},
        ).scalar()
        return int(count or 0)

    result = db.session.execute(
        text("""
            DELETE FROM sped_ecd_rule_embeddings
            WHERE chunk_id <> ALL(:ids)
        """),
        {"ids": list(known_ids)},
    )
    db.session.commit()
    return int(result.rowcount or 0)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reindex", action="store_true",
                        help="Limpa tabela antes de reindexar")
    parser.add_argument("--stats", action="store_true",
                        help="Mostra so estatisticas, sem indexar")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Pula remocao de chunks orfaos pos-indexacao")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from app import create_app, db

    app = create_app()
    with app.app_context():
        if args.reindex and not args.dry_run:
            db.session.execute(text("TRUNCATE sped_ecd_rule_embeddings RESTART IDENTITY"))
            db.session.commit()
            logger.info("Tabela truncada")

        if args.stats:
            count = db.session.execute(
                text("SELECT COUNT(*) FROM sped_ecd_rule_embeddings")
            ).scalar()
            by_type = db.session.execute(text(
                "SELECT chunk_type, COUNT(*) AS c FROM sped_ecd_rule_embeddings GROUP BY chunk_type"
            )).all()
            print(f"Total chunks indexados: {count}")
            for row in by_type:
                print(f"  {row.chunk_type}: {row.c}")
            return

        start = time.time()
        chunks = (
            collect_manual_ecd_chunks()
            + collect_plano_iteracoes()
            + collect_manual_capitulos()
            + collect_plano_categorias()
            + collect_claude_md_gotchas()
        )
        logger.info(f"Coletados {len(chunks)} chunks em {time.time() - start:.1f}s")

        stats = embed_and_store(chunks, dry_run=args.dry_run)
        logger.info(f"Stats: {stats}")

        # Cleanup de chunks orfaos (sections renomeadas/removidas, registros
        # que sairam do manual, etc). Skip apenas quando explicito.
        if not args.no_cleanup:
            known_ids = {c["chunk_id"] for c in chunks}
            removed = cleanup_orphans(known_ids, dry_run=args.dry_run)
            if removed:
                action = "seriam removidos (dry-run)" if args.dry_run else "removidos"
                logger.info(f"Cleanup: {removed} chunks orfaos {action}")


if __name__ == "__main__":
    main()
