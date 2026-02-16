#!/usr/bin/env python3
"""
Script para buscar texto na documentacao SSW.

Suporta 3 modos de busca:
- regex (padrao): busca textual case-insensitive (original)
- semantica: busca por similaridade via Voyage AI embeddings + pgvector
- hibrida: combina regex + semantica, deduplicando e rankeando

Pesquisa em todos os arquivos .md dentro de .claude/references/ssw/
e retorna trechos relevantes com contexto.

Uso:
    python consultar_documentacao_ssw.py --busca "MDF-e"
    python consultar_documentacao_ssw.py --busca "faturamento" --limite 5
    python consultar_documentacao_ssw.py --busca "como transferir entre filiais" --modo semantica
    python consultar_documentacao_ssw.py --busca "MDF-e manifesto" --modo hibrida
    python consultar_documentacao_ssw.py --busca "CCF" --diretorio pops
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Diretorio base da documentacao SSW
SSW_BASE = Path(__file__).resolve().parent.parent.parent.parent / "references" / "ssw"


def buscar_documentacao(busca: str, limite: int = 10, diretorio: str = None, modo: str = "hibrida") -> dict:
    """
    Busca na documentacao SSW com suporte a regex, semantica ou hibrida.

    Args:
        busca: Texto a buscar
        limite: Maximo de resultados
        diretorio: Filtrar por subdiretorio (pops, visao-geral, operacional, etc.)
        modo: "regex" (textual), "semantica" (embeddings), "hibrida" (ambos)

    Returns:
        dict: {sucesso, busca, modo, resultados, total_encontrados}
    """
    resultado = {
        "sucesso": False,
        "busca": busca,
        "modo": modo,
        "diretorio_filtro": diretorio,
        "resultados": [],
        "total_encontrados": 0,
    }

    if modo == "regex":
        return _buscar_regex(busca, limite, diretorio, resultado)
    elif modo == "semantica":
        return _buscar_semantica(busca, limite, diretorio, resultado)
    elif modo == "hibrida":
        return _buscar_hibrida(busca, limite, diretorio, resultado)
    else:
        resultado["erro"] = f"Modo invalido: {modo}. Use 'regex', 'semantica' ou 'hibrida'"
        return resultado


def _buscar_regex(busca: str, limite: int, diretorio: str, resultado: dict) -> dict:
    """Busca textual case-insensitive (implementacao original)."""
    if not SSW_BASE.exists():
        resultado["erro"] = f"Diretorio SSW nao encontrado: {SSW_BASE}"
        return resultado

    search_dir = SSW_BASE
    if diretorio:
        search_dir = SSW_BASE / diretorio
        if not search_dir.exists():
            resultado["erro"] = f"Subdiretorio nao encontrado: {diretorio}"
            resultado["diretorios_disponiveis"] = [
                d.name for d in SSW_BASE.iterdir() if d.is_dir()
            ]
            return resultado

    # Compilar patterns case-insensitive (suporte multi-palavra AND)
    try:
        termos = busca.strip().split()
        patterns = [re.compile(re.escape(t), re.IGNORECASE) for t in termos]
    except re.error:
        resultado["erro"] = f"Padrao de busca invalido: {busca}"
        return resultado

    matches = []
    for md_file in sorted(search_dir.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        lines = content.split("\n")
        file_matches = []

        for i, line in enumerate(lines):
            if all(p.search(line) for p in patterns):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = "\n".join(lines[start:end])
                file_matches.append({
                    "linha": i + 1,
                    "contexto": context.strip(),
                })

        if file_matches:
            rel_path = md_file.relative_to(SSW_BASE)
            titulo = ""
            for line in lines:
                if line.startswith("# "):
                    titulo = line.lstrip("# ").strip()
                    break

            matches.append({
                "arquivo": str(rel_path),
                "titulo": titulo,
                "ocorrencias": len(file_matches),
                "trechos": file_matches[:3],
                "fonte": "regex",
            })

    matches.sort(key=lambda x: x["ocorrencias"], reverse=True)

    resultado["sucesso"] = True
    resultado["total_encontrados"] = len(matches)
    resultado["resultados"] = matches[:limite]

    if not matches:
        resultado["sugestao"] = (
            "Tente termos mais genericos ou verifique ortografia. "
            "Diretorios disponiveis: "
            + ", ".join(d.name for d in SSW_BASE.iterdir() if d.is_dir())
        )

    return resultado


def _buscar_semantica(busca: str, limite: int, diretorio: str, resultado: dict) -> dict:
    """Busca semantica via embeddings + pgvector."""
    try:
        # Setup path para imports do app
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root))

        from app import create_app
        from app.embeddings.service import EmbeddingService
        from app.embeddings.config import EMBEDDINGS_ENABLED

        if not EMBEDDINGS_ENABLED:
            resultado["erro"] = "Busca semantica desabilitada (EMBEDDINGS_ENABLED=false)"
            resultado["sugestao"] = "Use --modo regex para busca textual"
            return resultado

        app = create_app()
        with app.app_context():
            svc = EmbeddingService()
            hits = svc.search_ssw_docs(
                query=busca,
                limit=limite,
                subdir_filter=diretorio,
            )

            if not hits:
                resultado["sucesso"] = True
                resultado["total_encontrados"] = 0
                resultado["sugestao"] = (
                    "Nenhum resultado semantico. Tente --modo regex ou reformule a busca."
                )
                return resultado

            matches = []
            for hit in hits:
                # Limitar tamanho do chunk para output
                chunk_text = hit["chunk_text"]
                if len(chunk_text) > 500:
                    chunk_text = chunk_text[:500] + "..."

                matches.append({
                    "arquivo": hit["doc_path"],
                    "titulo": hit.get("doc_title", ""),
                    "secao": hit.get("heading", ""),
                    "similaridade": hit["similarity"],
                    "trechos": [{
                        "contexto": chunk_text,
                    }],
                    "fonte": "semantica",
                })

            resultado["sucesso"] = True
            resultado["total_encontrados"] = len(matches)
            resultado["resultados"] = matches

    except ImportError as e:
        resultado["erro"] = f"Modulo de embeddings nao disponivel: {e}"
        resultado["sugestao"] = "Execute: pip install voyageai pgvector"
    except Exception as e:
        resultado["erro"] = f"Erro na busca semantica: {e}"
        resultado["sugestao"] = "Use --modo regex como fallback"

    return resultado


def _buscar_hibrida(busca: str, limite: int, diretorio: str, resultado: dict) -> dict:
    """
    Busca hibrida: combina regex + semantica.

    Estrategia:
    1. Executa ambas as buscas
    2. Resultados semanticos vem primeiro (mais relevantes)
    3. Resultados regex adicionam documentos nao encontrados na semantica
    4. Deduplicacao por arquivo
    """
    # Busca regex
    regex_resultado = {"resultados": []}
    regex_resultado = _buscar_regex(busca, limite * 2, diretorio, regex_resultado.copy())
    regex_matches = regex_resultado.get("resultados", [])

    # Busca semantica (pode falhar silenciosamente)
    sem_resultado = {"resultados": []}
    try:
        sem_resultado = _buscar_semantica(busca, limite, diretorio, sem_resultado.copy())
    except Exception:
        pass
    sem_matches = sem_resultado.get("resultados", [])

    # Combinar: semantica primeiro, regex preenche gaps
    seen_files = set()
    combined = []

    # Adicionar resultados semanticos
    for match in sem_matches:
        arquivo = match.get("arquivo", "")
        if arquivo not in seen_files:
            seen_files.add(arquivo)
            combined.append(match)

    # Adicionar resultados regex que nao apareceram na semantica
    for match in regex_matches:
        arquivo = match.get("arquivo", "")
        if arquivo not in seen_files:
            seen_files.add(arquivo)
            combined.append(match)

    resultado["sucesso"] = True
    resultado["total_encontrados"] = len(combined)
    resultado["resultados"] = combined[:limite]

    # Indicar fontes usadas
    fontes = set()
    for r in resultado["resultados"]:
        fontes.add(r.get("fonte", "desconhecida"))
    resultado["fontes_usadas"] = sorted(fontes)

    if not combined:
        resultado["sugestao"] = (
            "Nenhum resultado. Tente termos mais genericos. "
            "Diretorios disponiveis: "
            + ", ".join(d.name for d in SSW_BASE.iterdir() if d.is_dir())
            if SSW_BASE.exists() else "Diretorio SSW nao encontrado"
        )

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Buscar na documentacao SSW")
    parser.add_argument("--busca", required=True, help="Texto a buscar")
    parser.add_argument("--limite", type=int, default=10, help="Max resultados (default 10)")
    parser.add_argument("--diretorio", help="Filtrar por subdiretorio (pops, operacional, etc.)")
    parser.add_argument("--modo", default="hibrida",
                        choices=["regex", "semantica", "hibrida"],
                        help="Modo de busca (default: hibrida)")

    args = parser.parse_args()

    resultado = buscar_documentacao(
        busca=args.busca,
        limite=args.limite,
        diretorio=args.diretorio,
        modo=args.modo,
    )

    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
