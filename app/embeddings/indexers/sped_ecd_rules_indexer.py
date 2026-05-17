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
REGRA_RE = re.compile(r"^- (REGRA_[A-Z_0-9]+):\s*(.+)$", re.MULTILINE)


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

            # Chunk do REGISTRO completo
            chunk_id = f"manual_ecd:registro:{registro}"
            chunks.append({
                "chunk_id": chunk_id,
                "chunk_type": "registro",
                "bloco": bloco,
                "registro": registro,
                "regra_name": None,
                "severidade": None,
                "content": registro_text.strip(),
                "content_hash": _content_hash(registro_text),
                "source_file": f"manual_ecd/{bloco_file.name}",
                "source_anchor": f"#registro-{registro.lower()}",
            })

            # Chunks por REGRA dentro do registro
            for regra_match in REGRA_RE.finditer(registro_text):
                regra_name = regra_match.group(1)
                regra_desc = regra_match.group(2)
                # Heuristica simples de severidade
                if "Aviso" in regra_desc or "warning" in regra_desc.lower():
                    severidade = "aviso"
                else:
                    severidade = "erro"

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

PLANO_ITERACAO_RE = re.compile(
    r"^\|\s*(V[\d.]+)\s*\|.*?\|.*?\|.*?\|.*?\|\s*(.+?)\s*\|$",
    re.MULTILINE
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
            titulo_slug = re.sub(r"[^a-z0-9]+", "_", titulo.lower()).strip("_")[:40] or f"section_{idx}"

            # Detectar REGRA_X dentro do section (especialmente em 04_regras_validacao)
            regra_match = REGRA_NAME_RE.search(section_content)
            regra_name = regra_match.group(1) if regra_match else None
            chunk_type = "regra_pva" if regra_name and slug == "regras_validacao" else "manual_capitulo"

            chunk_content = f"Capitulo Manual ECD: {filename}\nSecao: {titulo}\n\n{section_content}"

            chunks.append({
                "chunk_id": f"manual_ecd:{slug}:{titulo_slug}:{idx}",
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

        # Extrair numero da categoria (CATEGORIA 1, CATEGORIA 17, CATEGORIAS 12-16)
        cat_match = re.match(r"CATEGORIA[S]? (\d+(?:-\d+)?)", titulo)
        cat_num = cat_match.group(1) if cat_match else "?"

        # Severidade: BLOQ ou WARN no titulo
        severidade = None
        if "BLOQ" in titulo:
            severidade = "BLOQUEANTE"
        elif "WARN" in titulo:
            severidade = "WARNING"

        chunk_content = f"Categoria de erro SPED ECD: {titulo}\n\n{cat_text}"

        chunks.append({
            "chunk_id": f"plano:categoria:{cat_num}",
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
# COLETA — Gotchas e decisoes do CLAUDE.md do modulo
# ============================================================

CLAUDE_MD_FILE = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "CLAUDE.md"


def collect_claude_md_gotchas() -> list[dict[str, Any]]:
    """Varre app/relatorios_fiscais/CLAUDE.md.

    Cada `## SECTION` ou `### SECTION` eh um chunk (gotchas, decisoes,
    historico de versoes).
    """
    chunks: list[dict[str, Any]] = []

    if not CLAUDE_MD_FILE.is_file():
        logger.warning(f"CLAUDE_MD_FILE nao encontrado: {CLAUDE_MD_FILE}")
        return chunks

    content = CLAUDE_MD_FILE.read_text(encoding="utf-8")
    sections = _split_by_sections(content)

    for idx, (titulo, section_text) in enumerate(sections):
        titulo_slug = re.sub(r"[^a-z0-9]+", "_", titulo.lower()).strip("_")[:40] or f"section_{idx}"

        chunk_content = f"CLAUDE.md modulo relatorios_fiscais: {titulo}\n\n{section_text}"

        chunks.append({
            "chunk_id": f"claudemd:relatorios_fiscais:{titulo_slug}:{idx}",
            "chunk_type": "gotcha",
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

    # Skip chunks com hash ja indexado
    ids = [c["chunk_id"] for c in chunks]
    result = db.session.execute(
        text("""
            SELECT chunk_id, content_hash FROM sped_ecd_rule_embeddings
            WHERE chunk_id = ANY(:ids)
        """),
        {"ids": ids}
    ).all()
    existing = {row.chunk_id: row.content_hash for row in result}
    chunks_to_embed = [
        c for c in chunks
        if existing.get(c["chunk_id"]) != c["content_hash"]
    ]
    stats["skipped"] = len(chunks) - len(chunks_to_embed)

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


if __name__ == "__main__":
    main()
