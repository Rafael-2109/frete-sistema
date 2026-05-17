"""Parser SPED ECD Leiaute 9 — streaming Latin-1, output indexado.

Reusado pelas 3 skills de auditoria (auditando-sped-contabil,
comparando-sped-ground-truth, auditando-sped-vs-manual).

Output:
{
  "metadata": {"total_lines": N, "encoding": "latin-1", "path": "..."},
  "registros": {
    "0000": [{"NOME": "...", "CNPJ": "..."}, ...],
    "I050": [{"COD_NAT": "01", ...}, ...],
    ...
  }
}

Schemas dos campos por registro: app/relatorios_fiscais/manual_ecd/bloco_*.md
"""

from __future__ import annotations

import json
import sys
from typing import Any, Iterator


# Campos por registro — derivado do Manual ECD Leiaute 9.
# Lista posicional EXCLUI o primeiro campo REG (que e a chave do dict externo).
# Fonte: app/relatorios_fiscais/manual_ecd/bloco_*.md
REGISTRO_CAMPOS: dict[str, list[str]] = {
    "0000": ["LECD", "DT_INI", "DT_FIN", "NOME", "CNPJ", "UF", "COD_MUN",
             "NIRE", "IND_SIT_ESP", "IND_SIT_INI_PER", "IND_NIRE", "IND_FIN_ESC",
             "COD_HASH_SUB", "IND_GRANDE_PORTE", "TIP_ECD", "COD_SCP",
             "IDENT_MF", "IND_ESC_CONS", "IDENT_HASH", "IND_CENTRALIZADA",
             "IND_MUDANCA_PC", "COD_PLAN_REF"],
    "0001": ["IND_DAD"],
    "0007": ["COD_ENT_REF", "COD_INSCR"],
    "0020": ["COD_CTA_REF_DESC"],
    "0035": ["COD_SCP", "NOME_SCP"],
    "0150": ["COD_PART", "NOME", "COD_PAIS", "CNPJ", "CPF", "IE", "COD_MUN", "IM", "SUFRAMA", "ENDERECO", "NUM", "COMPL", "BAIRRO"],
    "0180": ["COD_REL", "DT_INI_REL", "DT_FIN_REL"],
    "0990": ["QTD_LIN_0"],
    "I001": ["IND_DAD"],
    "I010": ["IND_ESC", "COD_VER_LC"],
    "I012": ["NUM_ORD", "NAT_LIVR", "TIPO", "COD_HASH_AUX"],
    "I015": ["COD_CTA_RES"],
    "I020": ["REG_COD", "NUM_AD", "CAMPO", "DESCRICAO", "TIPO"],
    "I030": ["DNRC_ABERT", "NUM_ORD", "NAT_LIVR", "QTD_LIN", "NOME", "NIRE",
             "CNPJ", "DT_ARQ", "DT_ARQ_CONV", "DESC_MUN", "DT_EX_SOCIAL"],
    "I050": ["DT_ALT", "COD_NAT", "IND_CTA", "NIVEL", "COD_CTA", "COD_CTA_SUP", "CTA"],
    "I051": ["COD_CCUS", "COD_CTA_REF"],
    "I052": ["COD_CCUS", "COD_AGL"],
    "I053": ["COD_IDT", "COD_CNT_CORR", "NAT_SUB_CNT"],
    "I075": ["COD_HIST_PAD", "DESCR_HIST_PAD"],
    "I100": ["COD_CCUS", "CCUS"],
    "I150": ["DT_INI", "DT_FIN"],
    "I155": ["COD_CTA", "COD_CCUS", "VL_SLD_INI", "IND_DC_INI", "VL_DEB",
             "VL_CRED", "VL_SLD_FIN", "IND_DC_FIN"],
    "I157": ["COD_CTA_REF_TRANSF", "VL_SLD_INI", "IND_DC_INI", "COD_CTA_CORR"],
    "I200": ["NUM_LCTO", "DT_LCTO", "VL_LCTO", "IND_LCTO"],
    "I250": ["COD_CTA", "COD_CCUS", "VL_DC", "IND_DC", "NUM_ARQ", "COD_HIST_PAD",
             "HIST", "COD_PART"],
    "I300": ["DT_BCT", "VL_BCT"],
    "I310": ["NUM_ORD_BCT", "COD_CTA_BCT", "VAL_DEB_BCT", "VAL_CRED_BCT"],
    "I350": ["DT_RES"],
    "I355": ["COD_CTA", "COD_CCUS", "VL_CTA", "IND_DC"],
    "I990": ["QTD_LIN_I"],
    "J001": ["IND_DAD"],
    "J005": ["DT_INI", "DT_FIN", "ID_DEM", "CAB_DEM"],
    "J100": ["COD_AGL", "IND_COD_AGL", "COD_AGL_SUP", "IND_GRP_BAL", "DESCR_COD_AGL",
             "VL_CTA", "IND_DC_BAL", "VL_CTA_INI", "IND_DC_INI_BAL", "NIVEL_AGL"],
    "J150": ["NUM_ORD", "COD_AGL", "NIVEL_AGL", "COD_AGL_SUP", "IND_GRP_DRE",
             "DESCR_COD_AGL", "VL_CTA_DRE", "IND_VL_CTA_DRE", "VL_CTA_DRE_INI",
             "IND_VL_CTA_DRE_INI", "IND_GRP_DRE_INI", "DESCR_COD_AGL_INI", "NIVEL_AGL_INI"],
    "J800": ["ARQ_RTF"],
    "J900": ["DNRC_ENCER", "IDENT_NOM", "IDENT_CPF_CNPJ", "IDENT_QUALIF", "ID_DEM",
             "DT_EX_SOCIAL", "NAT_LIVRO", "NUM_ORD", "QTD_LIN"],
    "J930": ["IDENT_NOM", "IDENT_CPF_CNPJ", "IDENT_QUALIF", "COD_ASSIN", "IND_CRC",
             "EMAIL", "FONE", "UF_CRC", "NUM_SEQ_CRC", "DT_CRC", "CRC_PROF"],
    "J990": ["QTD_LIN_J"],
    "9001": ["IND_MOV"],
    "9900": ["REG_BLC", "QTD_REG_BLC"],
    "9990": ["QTD_LIN_9"],
    "9999": ["QTD_LIN"],
}


def parse_sped_line(line: str) -> list[str]:
    """Split linha por pipe, remove pipes inicial e final.

    Args:
        line: linha SPED com CRLF removido.

    Returns:
        Lista posicional de campos. Campos vazios (||) ficam como string "".
    """
    if not line.startswith("|"):
        raise ValueError(f"Linha SPED nao comeca com pipe: {line[:50]}")
    line = line.rstrip("\r\n")
    if not line.endswith("|"):
        raise ValueError(f"Linha SPED nao termina com pipe: {line[-50:]}")
    return line[1:-1].split("|")


def iter_sped_records(path: str) -> Iterator[tuple[str, dict[str, str]]]:
    """Streaming generator de (REG, registro_dict) lendo arquivo Latin-1.

    Nao carrega arquivo inteiro em memoria — line-by-line.
    """
    with open(path, "rb") as f:
        for line_num, raw_line in enumerate(f, start=1):
            try:
                line = raw_line.decode("latin-1")
            except UnicodeDecodeError as e:
                raise ValueError(f"Encoding nao Latin-1 em linha: {e}")

            # BOM detection — UTF-8 BOM (\xef\xbb\xbf) lido como Latin-1 vira "\xef\xbb\xbf"
            # BOM UTF-16 (\xff\xfe ou \xfe\xff) tambem indica encoding incorreto.
            if line_num == 1 and (
                line.startswith("\xef\xbb\xbf")  # UTF-8 BOM como Latin-1
                or line.startswith("\xff\xfe")    # UTF-16 LE BOM
                or line.startswith("\xfe\xff")    # UTF-16 BE BOM
            ):
                raise ValueError(
                    f"BOM detectado na primeira linha — arquivo nao eh Latin-1 puro. "
                    f"Conferir geracao do SPED (deve ser ISO-8859-1 sem BOM)."
                )

            line = line.rstrip("\r\n")
            if not line:
                continue

            fields = parse_sped_line(line)
            reg = fields[0]
            payload_fields = fields[1:]

            schema = REGISTRO_CAMPOS.get(reg)
            if schema is None:
                # Registro nao mapeado — guardar como posicional
                record = {f"campo_{i+1}": v for i, v in enumerate(payload_fields)}
            else:
                # Map por schema; se registro tem MAIS campos que schema, sobrescreve;
                # se tem MENOS, deixa schema fields faltantes como ""
                record = {}
                for i, field_name in enumerate(schema):
                    record[field_name] = payload_fields[i] if i < len(payload_fields) else ""

            yield reg, record


def parse_sped_file(path: str) -> dict[str, Any]:
    """Parse completo do SPED em dict indexado por REG.

    Args:
        path: caminho do arquivo SPED .txt (Latin-1).

    Returns:
        {
          "metadata": {"total_lines": N, "encoding": "latin-1", "path": ...},
          "registros": {
            "0000": [registro_dict, ...],
            ...
          }
        }
    """
    registros: dict[str, list[dict[str, str]]] = {}
    total_lines = 0

    for reg, record in iter_sped_records(path):
        registros.setdefault(reg, []).append(record)
        total_lines += 1

    return {
        "metadata": {
            "total_lines": total_lines,
            "encoding": "latin-1",
            "path": path,
        },
        "registros": registros,
    }


def parse_and_save(sped_path: str, output_path: str) -> dict[str, Any]:
    """CLI entry point — parse + grava JSON em /tmp.

    Uso pelo subagente:
        python parse_sped.py /path/to/sped.txt /tmp/sped-parsed-{token}.json
    """
    parsed = parse_sped_file(sped_path)

    # Stats: registro -> count
    stats = {reg: len(records) for reg, records in parsed["registros"].items()}
    parsed["metadata"]["stats"] = stats

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    return {
        "output_path": output_path,
        "total_lines": parsed["metadata"]["total_lines"],
        "registros_distintos": len(parsed["registros"]),
        "stats": stats,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python parse_sped.py <sped_path> <output_json>", file=sys.stderr)
        sys.exit(2)
    result = parse_and_save(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
