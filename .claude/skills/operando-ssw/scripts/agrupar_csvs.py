#!/usr/bin/env python3
"""
agrupar_csvs.py — Merge generico de multiplos CSVs em um unico arquivo.

Reutilizavel para CSVs da 402 (cidades atendidas) e 408 (comissao por cidade).
Python puro — sem Playwright, sem Flask, sem pandas.

Preserva encoding original (ISO-8859-1) e separador (;).

Uso:
    # Para 402:
    python agrupar_csvs.py \\
      --input-dir /tmp/402_export_all/ \\
      --output /tmp/402_todas_cidades.csv \\
      --pattern "*_402_export.csv" \\
      [--skip-header-lines 1]

    # Para 408:
    python agrupar_csvs.py \\
      --input-dir /tmp/408_export/ \\
      --output /tmp/408_todas_comissoes.csv \\
      --pattern "*_408_export.csv" \\
      [--skip-header-lines 1]

Retorno: JSON {"sucesso": bool, "total_arquivos": N, "total_linhas": N, "arquivo_saida": "..."}
"""
import argparse
import fnmatch
import json
import os
import sys


def descobrir_arquivos(input_dir, pattern):
    """
    Descobre arquivos no diretorio que casam com o pattern glob.

    Retorna lista ordenada de caminhos absolutos.
    """
    if not os.path.isdir(input_dir):
        return []

    arquivos = []
    for fname in sorted(os.listdir(input_dir)):
        if fnmatch.fnmatch(fname, pattern):
            arquivos.append(os.path.join(input_dir, fname))

    return arquivos


def detectar_encoding(caminho):
    """
    Detecta encoding tentando ISO-8859-1 e UTF-8.

    Retorna o encoding que consegue ler sem erros.
    """
    for enc in ["iso-8859-1", "utf-8", "cp1252"]:
        try:
            with open(caminho, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "iso-8859-1"  # fallback


def agrupar(args):
    """Merge de CSVs com header unico."""
    input_dir = os.path.abspath(args.input_dir)
    output_path = os.path.abspath(args.output)
    pattern = args.pattern
    skip_n = args.skip_header_lines

    # Descobrir arquivos
    arquivos = descobrir_arquivos(input_dir, pattern)

    if not arquivos:
        resultado = {
            "sucesso": False,
            "erro": f"Nenhum arquivo encontrado com pattern '{pattern}' em {input_dir}",
        }
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        return

    # Detectar encoding do primeiro arquivo
    encoding = detectar_encoding(arquivos[0])

    # Processar primeiro arquivo: extrair headers
    headers = []
    all_data_lines = []
    arquivos_processados = []

    for idx, arq in enumerate(arquivos):
        fname = os.path.basename(arq)

        try:
            with open(arq, "r", encoding=encoding) as f:
                lines = f.readlines()
        except Exception as e:
            print(f">>> AVISO: Erro ao ler {fname}: {e}", file=sys.stderr)
            arquivos_processados.append({
                "arquivo": fname,
                "sucesso": False,
                "erro": str(e),
            })
            continue

        # Remover linhas vazias no final
        while lines and not lines[-1].strip():
            lines.pop()

        if len(lines) <= skip_n:
            print(f">>> AVISO: {fname} tem apenas {len(lines)} linhas (skip={skip_n}), ignorando",
                  file=sys.stderr)
            arquivos_processados.append({
                "arquivo": fname,
                "sucesso": False,
                "erro": f"Apenas {len(lines)} linhas, menos que skip_header_lines={skip_n}",
            })
            continue

        # Extrair headers do primeiro arquivo
        if idx == 0:
            headers = lines[:skip_n]

        # Coletar linhas de dados (apos headers)
        data_lines = lines[skip_n:]
        # Filtrar linhas vazias
        data_lines = [l for l in data_lines if l.strip()]

        all_data_lines.extend(data_lines)

        arquivos_processados.append({
            "arquivo": fname,
            "sucesso": True,
            "linhas_dados": len(data_lines),
        })

    if not all_data_lines:
        resultado = {
            "sucesso": False,
            "erro": "Nenhuma linha de dados encontrada nos arquivos",
            "arquivos": arquivos_processados,
        }
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        return

    # Escrever arquivo merged
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding=encoding) as f:
        # Headers
        for h in headers:
            f.write(h if h.endswith("\n") else h + "\n")
        # Dados
        for line in all_data_lines:
            f.write(line if line.endswith("\n") else line + "\n")

    # Estatisticas
    total_arquivos_ok = sum(1 for a in arquivos_processados if a.get("sucesso"))
    total_arquivos_erro = sum(1 for a in arquivos_processados if not a.get("sucesso"))
    total_linhas = len(all_data_lines)

    # Tentar detectar coluna UNIDADE (se existir)
    unidades_unicas = set()
    if headers:
        header_line = headers[-1].strip()  # Ultimo header (pode ter metadata antes)
        cols = header_line.split(";")
        # Procurar coluna UNIDADE ou UF
        col_unidade = None
        for ci, col in enumerate(cols):
            col_upper = col.strip().upper()
            if col_upper in ("UNIDADE", "UF", "SIGLA"):
                col_unidade = ci
                break

        if col_unidade is not None:
            for line in all_data_lines:
                fields = line.split(";")
                if len(fields) > col_unidade:
                    val = fields[col_unidade].strip()
                    if val:
                        unidades_unicas.add(val)

    resultado = {
        "sucesso": total_arquivos_erro == 0,
        "total_arquivos": len(arquivos),
        "arquivos_ok": total_arquivos_ok,
        "arquivos_erro": total_arquivos_erro,
        "total_linhas": total_linhas,
        "arquivo_saida": output_path,
        "encoding": encoding,
    }

    if unidades_unicas:
        resultado["unidades_unicas"] = sorted(unidades_unicas)
        resultado["total_unidades"] = len(unidades_unicas)

    resultado["detalhes"] = arquivos_processados

    print(json.dumps(resultado, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Merge generico de multiplos CSVs em um unico arquivo."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Diretorio contendo os CSVs a agrupar.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Caminho do arquivo CSV merged de saida.",
    )
    parser.add_argument(
        "--pattern",
        default="*.csv",
        help='Glob pattern para filtrar arquivos (default: "*.csv").',
    )
    parser.add_argument(
        "--skip-header-lines",
        type=int,
        default=1,
        help="Quantidade de linhas de header a extrair do primeiro arquivo e pular nos demais (default: 1).",
    )

    args = parser.parse_args()

    agrupar(args)


if __name__ == "__main__":
    main()
