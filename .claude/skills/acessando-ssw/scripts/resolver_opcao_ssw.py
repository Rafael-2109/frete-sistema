#!/usr/bin/env python3
"""
Script para resolver opcao SSW por numero ou nome.

Mapeia numero/nome de opcao para arquivo .md, URL de ajuda e POP relacionado.

Uso:
    python resolver_opcao_ssw.py --numero 436
    python resolver_opcao_ssw.py --nome "faturamento"
    python resolver_opcao_ssw.py --numero 062
"""

import argparse
import json
import re
from pathlib import Path


# Diretorio base da documentacao SSW
SSW_BASE = Path(__file__).resolve().parent.parent.parent.parent / "references" / "ssw"

# Mapeamento de opcoes para diretorios de docs
# (numero da opcao → provavel diretorio)
OPCAO_DIRETORIOS = [
    "operacional",
    "comercial",
    "financeiro",
    "fiscal",
    "cadastros",
    "logistica",
    "contabilidade",
    "edi",
    "embarcador",
    "relatorios",
]

# Mapeamento estatico de opcoes → POPs (baseado em CATALOGO_POPS.md)
OPCAO_POP = {
    "002": "POP-B01-cotar-frete.md",
    "004": "POP-C01-emitir-cte-fracionado.md",  # ou POP-C02 para carga direta
    "007": "POP-C01-emitir-cte-fracionado.md",  # multiplos POPs usam 007
    "020": "POP-D03-manifesto-mdfe.md",
    "025": "POP-D03-manifesto-mdfe.md",
    "026": "POP-A08-cadastrar-veiculo.md",
    "028": "POP-A09-cadastrar-motorista.md",
    "030": "POP-D04-chegada-veiculo.md",
    "033": "POP-D06-registrar-ocorrencias.md",
    "035": "POP-D02-romaneio-entregas.md",
    "038": "POP-D05-baixa-entrega.md",
    "040": "POP-D07-comprovantes-entrega.md",
    "048": "POP-E05-liquidar-fatura.md",
    "049": "POP-D07-comprovantes-entrega.md",
    "056": "POP-B05-relatorios-gerenciais.md",
    "062": "POP-B03-parametros-frete.md",
    "072": "POP-D01-contratar-veiculo.md",
    "101": "POP-B04-resultado-ctrc.md",
    "108": "POP-D06-registrar-ocorrencias.md",
    "131": "POP-G03-custos-frota.md",
    "320": "POP-G03-custos-frota.md",
    "384": "POP-A01-cadastrar-cliente.md",
    "390": "POP-G02-checklist-gerenciadora-risco.md",
    "401": "POP-A02-cadastrar-unidade-parceira.md",
    "402": "POP-A03-cadastrar-cidades.md",
    "403": "POP-A04-cadastrar-rotas.md",
    "408": "POP-A06-cadastrar-custos-comissoes.md",
    "420": "POP-A07-cadastrar-tabelas-preco.md",
    "428": "POP-D07-comprovantes-entrega.md",
    "435": "POP-E01-pre-faturamento.md",
    "436": "POP-E03-faturamento-automatico.md",
    "437": "POP-E02-faturar-manualmente.md",
    "444": "POP-E04-cobranca-bancaria.md",
    "457": "POP-E06-manutencao-faturas.md",
    "458": "POP-E05-liquidar-fatura.md",
    "459": "POP-C04-custos-extras.md",
    "462": "POP-F05-bloqueio-financeiro-ctrc.md",
    "475": "POP-F01-contas-a-pagar.md",
    "476": "POP-F03-liquidar-despesa.md",
    "478": "POP-A05-cadastrar-fornecedor.md",
    "483": "POP-A01-cadastrar-cliente.md",
    "486": "POP-F02-ccf-conta-corrente-fornecedor.md",
    "512": "POP-G04-relatorios-contabilidade.md",
    "515": "POP-G04-relatorios-contabilidade.md",
    "560": "POP-F06-aprovar-despesas.md",
    "567": "POP-G04-relatorios-contabilidade.md",
    "569": "POP-F04-conciliacao-bancaria.md",
    "469": "POP-B03-parametros-frete.md",  # Resultados minimos por rota
    "518": None,  # Aprovacao tabelas — sem POP dedicado
    "903": "POP-B03-parametros-frete.md",
}


def carregar_url_map() -> dict:
    """Carrega url-map.json com mapeamento opcao → URLs de ajuda."""
    url_map_path = SSW_BASE / "url-map.json"
    if url_map_path.exists():
        try:
            with open(url_map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError):
            return {}
    return {}


def encontrar_doc_por_numero(numero: str) -> list:
    """
    Busca arquivo .md que corresponde ao numero da opcao.

    Procura padrao: NNN-nome.md ou NNN_nome.md nos diretorios de docs.
    """
    resultados = []
    padrao = re.compile(rf"^0*{re.escape(numero)}\b", re.IGNORECASE)

    for dir_name in OPCAO_DIRETORIOS:
        dir_path = SSW_BASE / dir_name
        if not dir_path.exists():
            continue

        for md_file in sorted(dir_path.glob("*.md")):
            if padrao.match(md_file.stem):
                # Extrair titulo do arquivo
                titulo = ""
                try:
                    content = md_file.read_text(encoding="utf-8")
                    for line in content.split("\n"):
                        if line.startswith("# "):
                            titulo = line.lstrip("# ").strip()
                            break
                except (UnicodeDecodeError, PermissionError):
                    pass

                resultados.append({
                    "arquivo": str(md_file.relative_to(SSW_BASE)),
                    "titulo": titulo,
                })

    # Tambem buscar em visao-geral (podem referenciar opcoes)
    vg_path = SSW_BASE / "visao-geral"
    if vg_path.exists():
        for md_file in sorted(vg_path.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                # Contar quantas vezes a opcao e mencionada
                mentions = len(re.findall(rf"\b0*{re.escape(numero)}\b", content))
                if mentions >= 3:  # So incluir se tem 3+ mencoes (relevante)
                    titulo = ""
                    for line in content.split("\n"):
                        if line.startswith("# "):
                            titulo = line.lstrip("# ").strip()
                            break
                    resultados.append({
                        "arquivo": str(md_file.relative_to(SSW_BASE)),
                        "titulo": f"(visao-geral) {titulo}",
                        "mencoes": mentions,
                    })
            except (UnicodeDecodeError, PermissionError):
                continue

    return resultados


def encontrar_doc_por_nome(nome: str) -> list:
    """Busca arquivos .md cujo nome ou titulo contem o termo."""
    resultados = []
    pattern = re.compile(re.escape(nome), re.IGNORECASE)

    for dir_name in OPCAO_DIRETORIOS + ["visao-geral", "pops"]:
        dir_path = SSW_BASE / dir_name
        if not dir_path.exists():
            continue

        for md_file in sorted(dir_path.glob("*.md")):
            # Buscar no nome do arquivo
            nome_match = pattern.search(md_file.stem.replace("-", " ").replace("_", " "))

            # Buscar no titulo (primeira linha #)
            titulo = ""
            titulo_match = False
            try:
                content = md_file.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("# "):
                        titulo = line.lstrip("# ").strip()
                        titulo_match = pattern.search(titulo)
                        break
            except (UnicodeDecodeError, PermissionError):
                pass

            if nome_match or titulo_match:
                resultados.append({
                    "arquivo": str(md_file.relative_to(SSW_BASE)),
                    "titulo": titulo,
                    "match_em": "nome" if nome_match else "titulo",
                })

    return resultados


def resolver_opcao(numero: str = None, nome: str = None) -> dict:
    """
    Resolve opcao SSW para documentacao completa.

    Args:
        numero: Numero da opcao (ex: "436", "004")
        nome: Nome/descricao (ex: "faturamento")

    Returns:
        dict: {sucesso, opcao, docs, urls_ajuda, pop_relacionado}
    """
    resultado = {
        "sucesso": False,
        "numero": numero,
        "nome": nome,
        "docs": [],
        "urls_ajuda": [],
        "pop_relacionado": None,
        "pop_arquivo": None,
    }

    if not numero and not nome:
        resultado["erro"] = "Informe --numero ou --nome"
        return resultado

    url_map = carregar_url_map()

    if numero:
        # Normalizar (remover zeros a esquerda para comparacao, manter para display)
        numero_norm = numero.lstrip("0") or "0"
        numero_padded = numero.zfill(3)

        # Buscar docs
        resultado["docs"] = encontrar_doc_por_numero(numero_norm)

        # Buscar URLs de ajuda no url-map.json
        for key, urls in url_map.items():
            if key == numero_norm or key == numero_padded or key == numero:
                resultado["urls_ajuda"] = urls if isinstance(urls, list) else [urls]
                break

        # Buscar POP relacionado
        pop_file = OPCAO_POP.get(numero_padded) or OPCAO_POP.get(numero_norm)
        if pop_file:
            pop_path = SSW_BASE / "pops" / pop_file
            if pop_path.exists():
                resultado["pop_relacionado"] = pop_file
                resultado["pop_arquivo"] = f"pops/{pop_file}"
            else:
                resultado["pop_relacionado"] = pop_file
                resultado["pop_arquivo"] = f"pops/{pop_file} (ARQUIVO NAO ENCONTRADO)"
        elif pop_file is None and numero_padded in OPCAO_POP:
            resultado["pop_relacionado"] = "NAO DOCUMENTADO"
            resultado["aviso"] = f"Opcao {numero_padded} ainda nao possui documentacao .md"

        resultado["sucesso"] = len(resultado["docs"]) > 0 or len(resultado["urls_ajuda"]) > 0

    elif nome:
        resultado["docs"] = encontrar_doc_por_nome(nome)
        resultado["sucesso"] = len(resultado["docs"]) > 0

    if not resultado["sucesso"]:
        resultado["sugestao"] = (
            "Opcao nao encontrada na documentacao local. "
            "Tente: (1) Consultar ROUTING_SSW.md para encontrar o doc correto, "
            "(2) Buscar via consultar_documentacao_ssw.py --busca '...', "
            "(3) Verificar url-map.json para URLs de ajuda SSW."
        )

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Resolver opcao SSW")
    parser.add_argument("--numero", help="Numero da opcao SSW (ex: 436, 004)")
    parser.add_argument("--nome", help="Nome/descricao da opcao (busca parcial)")

    args = parser.parse_args()

    resultado = resolver_opcao(numero=args.numero, nome=args.nome)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
