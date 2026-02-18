#!/usr/bin/env python3
"""
gerar_csv_comissao_408.py — Gera CSVs de comissao por cidade para importacao na 408 do SSW.

Le planilha Excel (backup_vinculos.xlsx) com precos por cidade e gera um CSV
por unidade IATA no formato exato aceito pela importacao da opcao 408.

Nao usa Playwright — e um gerador de CSVs puro (pandas + csv).

Formato CSV de saida:
  - Linha 1: metadata (descricao das colunas de origem)
  - Linha 2: headers (238 colunas)
  - Linhas 3+: dados (2 linhas por cidade: E=expedicao, R=recepcao)
  - Separador: ;
  - Encoding: ISO-8859-1
  - Decimais com virgula (ex: 1193,4)

Mapeamento Excel -> CSV (verificado contra BVH/Colorado do Oeste):
  Excel col 21 (Acr. Frete)         x100  -> EXP/REC_1_PERC_FRETE_*
  Excel col 18 (GRIS/ADV)           x100  -> EXP/REC_2_PERC_VLR_MERC_*
  Excel col 19 (DESPACHO/CTE/TAS)   x1    -> EXP/REC_3_DESPACHO_*
  Excel col 17 (FRETE PESO R$/KG)   x1000 -> EXP/REC_3_APOS_ULT_FX_*
  Excel col 16 (VALOR MINIMO)       x1    -> EXP/REC_4_MINIMO_R$_*
  Excel col 20 (PEDAGIO)            x1    -> EXP/REC_5_PEDAGIO_FRACAO_100KG

POLO/REGIAO/INTERIOR recebem o MESMO valor (comissao por cidade).

Uso:
    python gerar_csv_comissao_408.py \\
      --excel /tmp/backup_vinculos.xlsx \\
      [--aba Sheet] \\
      [--output-dir /tmp/ssw_408_csvs/] \\
      [--unidades BVH,CGR] \\
      [--template ../comissao_408_template.json] \\
      [--dry-run]

Retorno: JSON {"sucesso": bool, "unidades": [...], "total_cidades": N, ...}
"""
import argparse
import json
import math
import os
import unicodedata

import pandas as pd


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(SCRIPT_DIR, "..", "comissao_408_template.json")
DEFAULT_OUTPUT_DIR = "/tmp/ssw_408_csvs/"
DEFAULT_ABA = "Sheet"

# Colunas do Excel (por indice)
EXCEL_COL_CIDADE = 1    # Cidade
EXCEL_COL_UF = 2        # UF
EXCEL_COL_IATA = 7      # IATA


# ──────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────

def remover_acentos(texto):
    """Remove acentos e caracteres diacriticos de uma string."""
    if not isinstance(texto, str):
        return str(texto)
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def formatar_numero_br(valor, casas_decimais=None):
    """
    Formata numero float para string com virgula decimal brasileira.

    Regras:
      - Remove trailing zeros desnecessarios (1193.40 -> "1193,4")
      - Inteiros puros nao recebem virgula (0.0 -> "0")
      - Usa arredondamento para evitar float imprecision (0.0085*100 -> "0,85")
    """
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "0"

    # Arredondar para evitar imprecisao de float
    if casas_decimais is not None:
        valor = round(valor, casas_decimais)
    else:
        # Arredondar a 10 casas decimais para eliminar imprecisao de float
        valor = round(valor, 10)

    # Se e inteiro puro, retornar sem decimal
    if valor == int(valor):
        return str(int(valor))

    # Formatar com casas decimais necessarias (sem trailing zeros)
    texto = f"{valor:.10f}".rstrip("0").rstrip(".")

    # Trocar ponto por virgula
    return texto.replace(".", ",")


def formatar_cidade_uf(cidade, uf):
    """Formata CIDADE/UF no padrao SSW: uppercase, sem acentos."""
    cidade_limpa = remover_acentos(str(cidade)).upper().strip()
    uf_limpa = str(uf).upper().strip()
    return f"{cidade_limpa}/{uf_limpa}"


def gerar_saida(sucesso, **kwargs):
    """Gera saida JSON padrao (compativel com ssw_common.gerar_saida)."""
    resultado = {"sucesso": sucesso, **kwargs}
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return resultado


# ──────────────────────────────────────────────
# Carregar template
# ──────────────────────────────────────────────

def carregar_template(caminho):
    """Carrega e valida o template JSON de 238 colunas."""
    with open(caminho, "r", encoding="utf-8") as f:
        template = json.load(f)

    headers = template.get("headers", [])
    if len(headers) != 238:
        raise ValueError(
            f"Template invalido: esperado 238 headers, encontrado {len(headers)}"
        )

    metadata = template.get("metadata", [])
    if len(metadata) != 238:
        raise ValueError(
            f"Template invalido: esperado 238 metadata, encontrado {len(metadata)}"
        )

    padrao = template.get("padrao", {})
    conversoes = template.get("conversoes", {})

    if not conversoes:
        raise ValueError("Template invalido: nenhuma conversao definida")

    return {
        "headers": headers,
        "metadata": metadata,
        "padrao": padrao,
        "conversoes": conversoes,
    }


# ──────────────────────────────────────────────
# Gerar linha CSV (238 colunas)
# ──────────────────────────────────────────────

def gerar_linha(template, unidade, tipo_er, cidade_uf, valores_excel):
    """
    Gera uma linha de 238 colunas para o CSV.

    Args:
        template: dict com headers, padrao, conversoes
        unidade: codigo IATA (ex: "BVH")
        tipo_er: "E" ou "R"
        cidade_uf: "CIDADE/UF" formatado (ex: "COLORADO DO OESTE/RO")
        valores_excel: dict com valores numericos do Excel por nome da conversao

    Returns:
        list de 238 strings
    """
    headers = template["headers"]
    padrao = template["padrao"]
    conversoes = template["conversoes"]

    # Inicializar todas as 238 colunas com defaults
    linha = [""] * 238

    # Indexar headers para lookup rapido
    header_idx = {h: i for i, h in enumerate(headers)}

    # 1. Preencher defaults
    for header_nome, valor_default in padrao.items():
        idx = header_idx.get(header_nome)
        if idx is not None:
            linha[idx] = valor_default

    # 2. Preencher campos compartilhados
    linha[header_idx["UNIDADE"]] = unidade
    linha[header_idx["EXPEDICAO/RECEPCAO"]] = tipo_er
    linha[header_idx["CIDADE/UF"]] = cidade_uf
    linha[header_idx["COD_MERCADORIA"]] = "0"

    # 3. Aplicar conversoes do Excel
    # IMPORTANTE: Cada linha (E ou R) contem AMBAS as secoes EXP e REC
    # preenchidas com os mesmos valores. O campo EXPEDICAO/RECEPCAO (col 1)
    # identifica o tipo, mas os dados sao duplicados nas duas secoes.
    for nome_conv, spec in conversoes.items():
        valor_raw = valores_excel.get(nome_conv, 0)
        if valor_raw is None or (isinstance(valor_raw, float) and math.isnan(valor_raw)):
            valor_raw = 0

        multiplicador = spec.get("multiplicador", 1)
        valor_convertido = float(valor_raw) * multiplicador
        valor_str = formatar_numero_br(valor_convertido)

        # Preencher AMBAS as secoes (EXP e REC) em cada linha
        for targets_key in ("targets_exp", "targets_rec"):
            targets = spec.get(targets_key, [])
            for target_header in targets:
                idx = header_idx.get(target_header)
                if idx is not None:
                    linha[idx] = valor_str

    return linha


# ──────────────────────────────────────────────
# Processar Excel e gerar CSVs
# ──────────────────────────────────────────────

def processar(args):
    """Fluxo principal: ler Excel, agrupar por IATA, gerar CSVs."""

    # Validar arquivo Excel
    if not os.path.exists(args.excel):
        return gerar_saida(False, erro=f"Arquivo Excel nao encontrado: {args.excel}")

    # Carregar template
    template_path = args.template or DEFAULT_TEMPLATE
    if not os.path.exists(template_path):
        return gerar_saida(False, erro=f"Template nao encontrado: {template_path}")

    try:
        template = carregar_template(template_path)
    except (ValueError, json.JSONDecodeError) as e:
        return gerar_saida(False, erro=f"Erro ao carregar template: {e}")

    # Ler Excel
    try:
        df = pd.read_excel(args.excel, sheet_name=args.aba)
    except Exception as e:
        return gerar_saida(False, erro=f"Erro ao ler Excel: {e}")

    total_linhas_excel = len(df)
    if total_linhas_excel == 0:
        return gerar_saida(False, erro="Planilha vazia")

    # Agrupar por IATA
    df_iata = df.iloc[:, EXCEL_COL_IATA]
    iatas_unicas = sorted(df_iata.dropna().unique())

    # Filtrar por unidades especificas (se solicitado)
    if args.unidades:
        filtro = [u.strip().upper() for u in args.unidades.split(",")]
        iatas_invalidas = [u for u in filtro if u not in iatas_unicas]
        if iatas_invalidas:
            return gerar_saida(
                False,
                erro=f"Unidades nao encontradas no Excel: {iatas_invalidas}",
                unidades_disponiveis=iatas_unicas,
            )
        iatas_unicas = [u for u in iatas_unicas if u in filtro]

    # Mapear nomes de conversao para indices de coluna do Excel
    conversoes = template["conversoes"]

    # Estatisticas
    stats = {
        "total_unidades": len(iatas_unicas),
        "total_linhas_excel": total_linhas_excel,
        "unidades": [],
        "total_cidades": 0,
        "total_linhas_csv": 0,
        "total_duplicadas_removidas": 0,
    }

    # Criar diretorio de saida
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Processar cada unidade IATA
    for iata in iatas_unicas:
        grupo = df[df_iata == iata].copy()

        # Deduplicar por (Cidade, UF)
        col_cidade = df.columns[EXCEL_COL_CIDADE]
        col_uf = df.columns[EXCEL_COL_UF]
        antes_dedup = len(grupo)
        grupo = grupo.drop_duplicates(subset=[col_cidade, col_uf], keep="first")
        duplicadas = antes_dedup - len(grupo)
        stats["total_duplicadas_removidas"] += duplicadas

        n_cidades = len(grupo)
        stats["total_cidades"] += n_cidades
        n_linhas = n_cidades * 2  # E + R
        stats["total_linhas_csv"] += n_linhas

        unit_stat = {
            "iata": iata,
            "cidades": n_cidades,
            "linhas_csv": n_linhas,
            "duplicadas_removidas": duplicadas,
        }

        if not args.dry_run:
            # Gerar CSV
            csv_path = os.path.join(output_dir, f"{iata}_comissao_408.csv")
            linhas_csv = []

            for _, row in grupo.iterrows():
                cidade = row.iloc[EXCEL_COL_CIDADE]
                uf = row.iloc[EXCEL_COL_UF]
                cidade_uf = formatar_cidade_uf(cidade, uf)

                # Extrair valores do Excel para cada conversao
                valores_excel = {}
                for nome_conv, spec in conversoes.items():
                    excel_col_idx = spec["excel_col"]
                    valor = row.iloc[excel_col_idx]
                    valores_excel[nome_conv] = valor

                # Gerar linha E (expedicao)
                linha_e = gerar_linha(template, iata, "E", cidade_uf, valores_excel)
                linhas_csv.append(linha_e)

                # Gerar linha R (recepcao) — mesmos valores, diferente tipo
                linha_r = gerar_linha(template, iata, "R", cidade_uf, valores_excel)
                linhas_csv.append(linha_r)

            # Escrever CSV
            with open(csv_path, "w", encoding="iso-8859-1", newline="") as f:
                # Linha 1: metadata
                f.write(";".join(template["metadata"]) + "\n")
                # Linha 2: headers
                f.write(";".join(template["headers"]) + "\n")
                # Linhas 3+: dados
                for linha in linhas_csv:
                    f.write(";".join(linha) + "\n")

            unit_stat["arquivo"] = csv_path

        stats["unidades"].append(unit_stat)

    # Resultado
    if args.dry_run:
        return gerar_saida(
            True,
            modo="dry-run",
            mensagem=(
                f"Preview: {stats['total_unidades']} unidades, "
                f"{stats['total_cidades']} cidades, "
                f"{stats['total_linhas_csv']} linhas CSV (E+R)"
            ),
            **stats,
        )

    arquivos_gerados = [u["arquivo"] for u in stats["unidades"] if "arquivo" in u]
    return gerar_saida(
        True,
        modo="geracao",
        mensagem=(
            f"Gerados {len(arquivos_gerados)} CSVs em {output_dir} "
            f"({stats['total_cidades']} cidades, "
            f"{stats['total_linhas_csv']} linhas)"
        ),
        output_dir=output_dir,
        arquivos_gerados=arquivos_gerados,
        **stats,
    )


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gera CSVs de comissao por cidade para importacao na 408 do SSW"
    )
    parser.add_argument(
        "--excel",
        required=True,
        help="Caminho do arquivo Excel (backup_vinculos.xlsx)",
    )
    parser.add_argument(
        "--aba",
        default=DEFAULT_ABA,
        help=f"Nome da aba do Excel (default: {DEFAULT_ABA})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Diretorio de saida dos CSVs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--unidades",
        default=None,
        help="Filtrar por unidades IATA (virgula-sep, ex: BVH,CGR). Sem = todas",
    )
    parser.add_argument(
        "--template",
        default=None,
        help=f"Caminho do template JSON (default: {DEFAULT_TEMPLATE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra estatisticas sem gerar arquivos",
    )

    args = parser.parse_args()
    processar(args)


if __name__ == "__main__":
    main()
