#!/usr/bin/env python3
"""
Script para buscar texto na documentacao SSW.

Pesquisa em todos os arquivos .md dentro de .claude/references/ssw/
e retorna trechos relevantes com contexto.

Uso:
    python consultar_documentacao_ssw.py --busca "MDF-e"
    python consultar_documentacao_ssw.py --busca "faturamento" --limite 5
    python consultar_documentacao_ssw.py --busca "CCF" --diretorio pops
"""

import argparse
import json
import re
from pathlib import Path


# Diretorio base da documentacao SSW
SSW_BASE = Path(__file__).resolve().parent.parent.parent.parent / "references" / "ssw"


def buscar_documentacao(busca: str, limite: int = 10, diretorio: str = None) -> dict:
    """
    Busca textual case-insensitive em todos os .md da documentacao SSW.

    Args:
        busca: Texto a buscar
        limite: Maximo de resultados
        diretorio: Filtrar por subdiretorio (pops, visao-geral, operacional, etc.)

    Returns:
        dict: {sucesso, busca, resultados, total_encontrados}
    """
    resultado = {
        "sucesso": False,
        "busca": busca,
        "diretorio_filtro": diretorio,
        "resultados": [],
        "total_encontrados": 0,
    }

    if not SSW_BASE.exists():
        resultado["erro"] = f"Diretorio SSW nao encontrado: {SSW_BASE}"
        return resultado

    # Determinar diretorio de busca
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

    # Buscar em todos os .md
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
                # Capturar contexto (2 linhas antes e 2 depois)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = "\n".join(lines[start:end])
                file_matches.append({
                    "linha": i + 1,
                    "contexto": context.strip(),
                })

        if file_matches:
            rel_path = md_file.relative_to(SSW_BASE)
            # Extrair titulo do arquivo (primeira linha que comeca com #)
            titulo = ""
            for line in lines:
                if line.startswith("# "):
                    titulo = line.lstrip("# ").strip()
                    break

            matches.append({
                "arquivo": str(rel_path),
                "titulo": titulo,
                "ocorrencias": len(file_matches),
                "trechos": file_matches[:3],  # Max 3 trechos por arquivo
            })

    # Ordenar por numero de ocorrencias (mais relevante primeiro)
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


def main():
    parser = argparse.ArgumentParser(description="Buscar na documentacao SSW")
    parser.add_argument("--busca", required=True, help="Texto a buscar")
    parser.add_argument("--limite", type=int, default=10, help="Max resultados (default 10)")
    parser.add_argument("--diretorio", help="Filtrar por subdiretorio (pops, operacional, etc.)")

    args = parser.parse_args()

    resultado = buscar_documentacao(
        busca=args.busca,
        limite=args.limite,
        diretorio=args.diretorio,
    )

    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
