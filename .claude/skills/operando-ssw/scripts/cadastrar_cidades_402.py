#!/usr/bin/env python3
"""
cadastrar_cidades_402.py — Cadastra cidades atendidas no SSW (opcao 402).

LIMITACAO: SSW 402 usa virtual scroll (~90 cidades no DOM de 400+ por UF).
Cidades fora do viewport NAO podem ser alteradas via ATU — hidden inputs
injetados sao ignorados pelo servidor. Para bulk (>3 cidades) ou cidades
fora do viewport, PREFERIR importar_cidades_402.py (workflow CSV).

Fluxo:
  1. Login SSW
  2. Abre opcao 402 (popup)
  3. Preenche UF e chama VIS_UF para listar cidades
  4. Para cada cidade: localiza <tr> na grid, preenche campos inline
  5. --dry-run: captura preview sem submeter
  6. Sem flag: submete via ATU (Atualizar)

Uso:
    python cadastrar_cidades_402.py \
      --uf MS \
      --unidade CGR \
      --cidades '[
        {"cidade": "CAMPO GRANDE", "polo": "P", "prazo": 2},
        {"cidade": "DOURADOS", "polo": "R", "prazo": 3},
        {"cidade": "CORUMBA", "polo": "I", "prazo": 5}
      ]' \
      [--defaults-file ../ssw_defaults.json] \
      [--dry-run]

Formato cidades (JSON array):
  cidade  — nome da cidade (case-insensitive, busca parcial)
  polo    — P (Polo), R (Regiao), I (Interior)
  prazo   — prazo de entrega em dias uteis
  tipo_frete    — (opc) C/F/A, default A do defaults
  coleta        — (opc) S/N, default S
  entrega       — (opc) S/N, default S
  restrita      — (opc) S/N, default N
  prazo_ecomm   — (opc) prazo e-commerce
  pedagogios    — (opc) qtde pedagogios
  distancia     — (opc) distancia em km
  tda           — (opc) valor TDA
  suframa       — (opc) valor SUFRAMA
  col_ent_valor — (opc) valor coleta/entrega
  praca         — (opc) praca comercial

Mapeamento de campos inline (fonte: discovery 402 real, 2026-02-17):
  A grid 402 usa <tr cid="X"> por cidade. Cada TR contem:
  - 3 colunas texto: UF, Cidade, IBGE
  - 14 inputs com IDs cid+1 a cid+14:
    cid+1  → Unidade (3 chars, col=3)
    cid+2  → Polo P/R/I (1 char, col=4)
    cid+3  → Tipo frete C/F/A (1 char, col=5)
    cid+4  → Restrita S/N (1 char, col=6)
    cid+5  → Coleta S/N (1 char, col=7)
    cid+6  → Entrega S/N (1 char, col=8)
    cid+7  → Prazo entrega (2 chars, col=9)
    cid+8  → Prazo e-commerce (2 chars, col=10)
    cid+9  → Qtde Pedagogios (2 chars, col=11)
    cid+10 → Distancia km (4 chars, col=12)
    cid+11 → Valor TDA (11 chars, col=13)
    cid+12 → Valor Suframa (8 chars, col=14)
    cid+13 → Valor Coleta/Entrega (8 chars, col=15)
    cid+14 → Praca Comercial (4 chars, col=16)
  - Links: Mais, Excluir (se configurada), Replicar

  Filtro usa VIS_UF (campo id="2", name="f2") — NAO PES.
  Submissao usa ATU (Atualizar).

Retorno: JSON {"sucesso": bool, "cidades_processadas": [...], ...}
"""
import argparse
import asyncio
import json
import os
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    carregar_defaults,
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
    preencher_campo_inline,
    capturar_screenshot,
    gerar_saida,
    verificar_mensagem_ssw,
)


# ──────────────────────────────────────────────
# Inline field offsets (relativos ao cid do <tr>)
# Input IDs = cid + offset
# ──────────────────────────────────────────────
OFFSET_UNIDADE = 1
OFFSET_POLO = 2
OFFSET_TIPO_FRETE = 3
OFFSET_RESTRITA = 4
OFFSET_COLETA = 5
OFFSET_ENTREGA = 6
OFFSET_PRAZO = 7
OFFSET_PRAZO_ECOMM = 8
OFFSET_PEDAGOGIOS = 9
OFFSET_DISTANCIA = 10
OFFSET_TDA = 11
OFFSET_SUFRAMA = 12
OFFSET_COL_ENT = 13
OFFSET_PRACA = 14

# ──────────────────────────────────────────────
# Opcoes validas para campos com dominio restrito
# ──────────────────────────────────────────────
VALID_OPTIONS = {
    "polo": ["P", "R", "I"],       # P=Polo, R=Regiao, I=Interior
    "tipo_frete": ["A", "C", "F"],  # A=Ambos, C=CIF, F=FOB
    "restrita": ["S", "N"],
    "coleta": ["S", "N"],
    "entrega": ["S", "N"],
}

# Limites de tamanho dos campos inline
FIELD_LIMITS = {
    "unidade": 3,
    "polo": 1,
    "tipo_frete": 1,
    "restrita": 1,
    "coleta": 1,
    "entrega": 1,
    "prazo": 2,          # max 99 dias
    "prazo_ecomm": 2,
    "pedagogios": 2,
    "distancia": 4,      # max 9999 km
    "tda": 11,
    "suframa": 8,
    "col_ent_valor": 8,
    "praca": 4,
}


async def encontrar_cidade_na_grid(popup, cidade_nome, html_response=None):
    """
    Localiza uma cidade na grid da 402 e retorna o cid (ID base da linha).

    A grid 402 usa <tr cid="X" rid="Y"> por cidade.
    cid e o ID base; inputs sao cid+1 a cid+14.

    Estrategia:
    1. Buscar <tr> no DOM via evaluate (mais confiavel apos document.write)
    2. Fallback: regex no HTML interceptado

    Args:
        popup: Playwright Page
        cidade_nome: Nome da cidade (case-insensitive)
        html_response: HTML capturado da response (opcional, para fallback regex)

    Returns:
        dict com {cid: int, valores_atuais: dict} ou None se nao encontrada
    """
    cidade_upper = cidade_nome.upper().strip()

    # Estrategia 1: Buscar <tr cid="X"> no DOM injetado
    result = await popup.evaluate(f"""() => {{
        const cidadeTarget = '{cidade_upper}';
        const trs = document.querySelectorAll('tr[cid]');

        for (const tr of trs) {{
            // Buscar divs de texto dentro da TR
            const divs = tr.querySelectorAll('div.srdvl, div.srdvr');
            let cidadeDiv = null;
            for (const d of divs) {{
                if (d.textContent.trim().toUpperCase() === cidadeTarget) {{
                    cidadeDiv = d;
                    break;
                }}
            }}

            if (!cidadeDiv) continue;

            const cid = parseInt(tr.getAttribute('cid'));
            const rid = parseInt(tr.getAttribute('rid'));

            // Capturar valores atuais dos inputs
            const valores = {{}};
            const inputs = tr.querySelectorAll('input');
            for (const inp of inputs) {{
                const col = inp.getAttribute('col');
                if (col) valores['col_' + col] = inp.value || '';
            }}

            return {{ cid: cid, rid: rid, valores_atuais: valores }};
        }}

        // Busca parcial (caso nome no SSW seja ligeiramente diferente)
        for (const tr of trs) {{
            const text = tr.textContent.toUpperCase();
            if (text.includes(cidadeTarget)) {{
                const cid = parseInt(tr.getAttribute('cid'));
                const rid = parseInt(tr.getAttribute('rid'));

                const valores = {{}};
                const inputs = tr.querySelectorAll('input');
                for (const inp of inputs) {{
                    const col = inp.getAttribute('col');
                    if (col) valores['col_' + col] = inp.value || '';
                }}

                return {{ cid: cid, rid: rid, valores_atuais: valores, match_parcial: true }};
            }}
        }}

        return null;
    }}""")

    if result:
        return result

    # Estrategia 2: Regex no XML bruto (fallback para lazy rendering)
    # O HTML interceptado usa XML customizado: <r><f0>UF</f0><f1>CIDADE</f1>...<f20>seq</f20></r>
    # rid = posicao ordinal da <r> no XML (0-based)
    # cid = rid * 17 (formula confirmada empiricamente)
    if html_response:
        # Parsear TODAS as linhas <r> para obter rid pela posicao ordinal
        all_rows = re.findall(r'<r>(.*?)</r>', html_response, re.DOTALL)
        for rid, row_xml in enumerate(all_rows):
            cidade_match = re.search(r'<f1>(.*?)</f1>', row_xml)
            if not cidade_match:
                continue
            cidade_xml = cidade_match.group(1).strip().upper()
            if cidade_xml != cidade_upper:
                continue

            cid = rid * 17
            # Extrair valores atuais dos campos f3-f16
            valores = {}
            for i in range(3, 17):
                fm = re.search(rf'<f{i}>(.*?)</f{i}>', row_xml)
                if fm:
                    valores[f"col_{i}"] = fm.group(1)
            return {"cid": cid, "rid": rid, "valores_atuais": valores, "from_xml": True}

    return None


async def preencher_cidade_inline(popup, cid, unidade, dados_cidade, defaults_402):
    """
    Preenche os campos inline de uma cidade.

    Args:
        popup: Playwright Page
        cid: ID base da linha (atributo cid do <tr>)
        unidade: Sigla da unidade (3 chars)
        dados_cidade: dict com dados da cidade
        defaults_402: defaults da opcao 402

    Returns:
        dict com campos_preenchidos e erros
    """
    campos_preenchidos = {}
    erros = []

    # Montar valores: dados_cidade > defaults
    valores = {
        OFFSET_UNIDADE: unidade.upper(),
        OFFSET_POLO: dados_cidade.get("polo", "P").upper(),
        OFFSET_TIPO_FRETE: dados_cidade.get("tipo_frete", defaults_402.get("tipo_frete", "A")),
        OFFSET_RESTRITA: dados_cidade.get("restrita", defaults_402.get("restrita", "N")),
        OFFSET_COLETA: dados_cidade.get("coleta", defaults_402.get("coleta", "S")),
        OFFSET_ENTREGA: dados_cidade.get("entrega", defaults_402.get("entrega", "S")),
        OFFSET_PRAZO: str(dados_cidade.get("prazo", "0")),
        OFFSET_PRAZO_ECOMM: str(dados_cidade.get("prazo_ecomm", defaults_402.get("prazo_ecommerce", "0"))),
        OFFSET_PEDAGOGIOS: str(dados_cidade.get("pedagogios", defaults_402.get("qtde_pedagios", "0"))),
    }

    # Campos opcionais (preencher somente se informados)
    if dados_cidade.get("distancia"):
        valores[OFFSET_DISTANCIA] = str(dados_cidade["distancia"])
    if dados_cidade.get("tda"):
        valores[OFFSET_TDA] = str(dados_cidade["tda"])
    if dados_cidade.get("suframa"):
        valores[OFFSET_SUFRAMA] = str(dados_cidade["suframa"])
    if dados_cidade.get("col_ent_valor"):
        valores[OFFSET_COL_ENT] = str(dados_cidade["col_ent_valor"])
    if dados_cidade.get("praca"):
        valores[OFFSET_PRACA] = str(dados_cidade["praca"])

    # Mapeamento offset → nome legivel
    offset_names = {
        OFFSET_UNIDADE: "unidade",
        OFFSET_POLO: "polo",
        OFFSET_TIPO_FRETE: "tipo_frete",
        OFFSET_RESTRITA: "restrita",
        OFFSET_COLETA: "coleta",
        OFFSET_ENTREGA: "entrega",
        OFFSET_PRAZO: "prazo",
        OFFSET_PRAZO_ECOMM: "prazo_ecomm",
        OFFSET_PEDAGOGIOS: "pedagogios",
        OFFSET_DISTANCIA: "distancia",
        OFFSET_TDA: "tda",
        OFFSET_SUFRAMA: "suframa",
        OFFSET_COL_ENT: "col_ent_valor",
        OFFSET_PRACA: "praca",
    }

    for offset, value in valores.items():
        field_id = str(cid + offset)
        nome_campo = offset_names.get(offset, f"offset_{offset}")
        try:
            # Grid da 402 esta na pagina principal do popup (nao em frame)
            await preencher_campo_inline(popup, field_id, value)
            campos_preenchidos[nome_campo] = value
        except ValueError:
            erros.append(f"{nome_campo} (id={field_id}): campo nao encontrado")

    return {"campos_preenchidos": campos_preenchidos, "erros": erros}


async def cadastrar_cidades(args):
    from playwright.async_api import async_playwright

    verificar_credenciais()
    defaults = carregar_defaults(args.defaults_file)
    defaults_402 = defaults.get("opcao_402", {})

    # Parsear lista de cidades
    try:
        cidades = json.loads(args.cidades)
    except json.JSONDecodeError as e:
        return gerar_saida(False, erro=f"JSON invalido em --cidades: {e}")

    if not isinstance(cidades, list) or len(cidades) == 0:
        return gerar_saida(False, erro="--cidades deve ser um JSON array com pelo menos 1 cidade")

    # Validar cada cidade
    for i, c in enumerate(cidades):
        nome = c.get("cidade", f"cidade_{i}")
        if "cidade" not in c:
            return gerar_saida(False, erro=f"Cidade {i}: campo 'cidade' obrigatorio")
        if "polo" not in c:
            return gerar_saida(False, erro=f"Cidade {i} ({nome}): campo 'polo' obrigatorio (P/R/I)")

        # Validar opcoes restritas
        for campo, label in [
            ("polo", "polo"),
            ("tipo_frete", "tipo_frete"),
            ("restrita", "restrita"),
            ("coleta", "coleta"),
            ("entrega", "entrega"),
        ]:
            valor = c.get(campo, "").upper()
            if valor and campo in VALID_OPTIONS and valor not in VALID_OPTIONS[campo]:
                return gerar_saida(
                    False,
                    erro=f"Cidade {i} ({nome}): {label}='{valor}' invalido. "
                         f"Opcoes: {', '.join(VALID_OPTIONS[campo])}",
                )

        # Validar limites de tamanho
        for campo in ("prazo", "prazo_ecomm", "pedagogios", "distancia", "praca"):
            valor = str(c.get(campo, ""))
            limit = FIELD_LIMITS.get(campo)
            if valor and limit and len(valor) > limit:
                return gerar_saida(
                    False,
                    erro=f"Cidade {i} ({nome}): {campo}='{valor}' excede "
                         f"limite de {limit} chars",
                )

    unidade = args.unidade.upper()
    uf = args.uf.upper()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            # ── 2. Abrir opcao 402 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 402)

            # ── 3. Preencher UF e chamar VIS_UF ──
            # 402 tem campo UF com id="2" (name="f2"), acao VIS_UF
            await asyncio.sleep(2)

            # Preencher campo de UF (id=2)
            await popup.evaluate(f"""() => {{
                const el = document.getElementById('2');
                if (el) {{
                    el.value = '{uf}';
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")

            # Interceptar response da busca por UF
            vis_html = await interceptar_ajax_response(
                popup, popup.main_frame, "ajaxEnvia('VIS_UF', 0)", timeout_s=30
            )

            if not vis_html:
                screenshot = await capturar_screenshot(popup, "402_vis_uf_falhou")
                return gerar_saida(
                    False,
                    erro=f"Nao recebeu lista de cidades para UF={uf}",
                    screenshot=screenshot,
                )

            # Verificar se response contem dados de cidade
            # Nota: HTML interceptado usa XML customizado (<r><f0>UF</f0><f1>CIDADE</f1>...)
            # O JS do SSW converte isso em <tr> com inputs ao renderizar
            if len(vis_html) < 1000 or '<r>' not in vis_html:
                screenshot = await capturar_screenshot(popup, "402_vis_uf_vazio")
                return gerar_saida(
                    False,
                    erro=f"VIS_UF retornou resposta sem grid de cidades (UF={uf}, {len(vis_html)} bytes)",
                    screenshot=screenshot,
                )

            # Injetar HTML no DOM (SSW AJAX nao atualiza DOM em Playwright headless)
            await injetar_html_no_dom(popup, vis_html)

            # Esperar JS do SSW renderizar a tabela (converte XML <r> → HTML <tr>)
            table_ready = False
            for _ in range(10):
                await asyncio.sleep(1)
                count = await popup.evaluate(
                    "() => document.querySelectorAll('tr[cid]').length"
                )
                if count and count > 0:
                    table_ready = True
                    break

            if not table_ready:
                screenshot = await capturar_screenshot(popup, "402_tabela_nao_renderizou")
                return gerar_saida(
                    False,
                    erro=f"Tabela de cidades nao renderizou apos injecao do HTML (UF={uf})",
                    screenshot=screenshot,
                )

            # ── 4. Processar cada cidade ──
            resultados = []

            for dados_cidade in cidades:
                cidade_nome = dados_cidade["cidade"].upper().strip()

                # Localizar cidade na grid via <tr cid="X"> no DOM renderizado
                # (Estrategia 1 busca no DOM, Estrategia 2 busca no XML bruto)
                cidade_info = await encontrar_cidade_na_grid(popup, cidade_nome, vis_html)

                if cidade_info is None:
                    resultados.append({
                        "cidade": cidade_nome,
                        "sucesso": False,
                        "erro": f"Cidade '{cidade_nome}' nao encontrada na grid UF={uf}",
                    })
                    continue

                cid = cidade_info["cid"]
                valores_atuais = cidade_info.get("valores_atuais", {})
                match_parcial = cidade_info.get("match_parcial", False)

                # Se veio do XML (lazy rendering), injetar inputs hidden no DOM
                if cidade_info.get("from_xml"):
                    # Tentar encontrar no DOM primeiro (pode ter sido renderizado)
                    dom_info = await popup.evaluate(f"""() => {{
                        const tr = document.querySelector('tr[cid="{cid}"]');
                        if (tr) return {{ found: true }};
                        return {{ found: false }};
                    }}""")

                    if not dom_info.get("found"):
                        # Cidade fora do viewport virtual — injetar inputs hidden
                        # O ATU serializa todos os inputs do form, incluindo hidden
                        await popup.evaluate(f"""() => {{
                            const form = document.querySelector('form') || document.body;
                            for (let offset = 1; offset <= 14; offset++) {{
                                const id = String({cid} + offset);
                                if (!document.getElementById(id)) {{
                                    const inp = document.createElement('input');
                                    inp.type = 'hidden';
                                    inp.id = id;
                                    inp.setAttribute('col', String(offset + 2));
                                    inp.setAttribute('rid', String({cidade_info.get("rid", 0)}));
                                    form.appendChild(inp);
                                }}
                            }}
                        }}""")

                # Verificar se cidade ja esta configurada (tem unidade preenchida)
                unidade_atual = valores_atuais.get("col_3", "")
                ja_configurada = bool(unidade_atual)

                # Preencher campos inline
                result = await preencher_cidade_inline(
                    popup, cid, unidade, dados_cidade, defaults_402
                )

                resultados.append({
                    "cidade": cidade_nome,
                    "cid": cid,
                    "rid": cidade_info.get("rid", -1),
                    "polo": dados_cidade.get("polo", "P").upper(),
                    "prazo": dados_cidade.get("prazo", 0),
                    "ja_configurada": ja_configurada,
                    "unidade_anterior": unidade_atual if ja_configurada else None,
                    "match_parcial": match_parcial,
                    "sucesso": len(result["erros"]) == 0,
                    "campos_preenchidos": result["campos_preenchidos"],
                    "erros": result["erros"],
                })

            # ── 5. Screenshot pre-submit ──
            screenshot_path = await capturar_screenshot(
                popup, f"402_{'dryrun' if args.dry_run else 'presubmit'}_{uf}_{unidade}"
            )

            if args.dry_run:
                sucesso_count = sum(1 for r in resultados if r.get("sucesso"))
                return gerar_saida(
                    True,
                    modo="dry-run",
                    uf=uf,
                    unidade=unidade,
                    cidades_processadas=resultados,
                    total_cidades=len(cidades),
                    sucesso_count=sucesso_count,
                    screenshot=screenshot_path,
                    mensagem=f"Preview de {sucesso_count}/{len(cidades)} cidades para "
                             f"{unidade}/{uf}. Nenhum dado foi submetido.",
                )

            # ── 6. Submeter (ATU = Atualizar) ──
            alert_msg = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                atu_html = await interceptar_ajax_response(
                    popup, popup.main_frame, "ajaxEnvia('ATU', 1)", timeout_s=20
                )

                # Injetar response do ATU para ler mensagens de sucesso/erro
                if atu_html:
                    await injetar_html_no_dom(popup, atu_html)

                await asyncio.sleep(2)

                msg_ssw = await verificar_mensagem_ssw(popup)
                screenshot_pos = await capturar_screenshot(
                    popup, f"402_resultado_{uf}_{unidade}"
                )

                # Avaliar resultado
                erro = None
                if alert_msg and any(
                    e in alert_msg.lower() for e in ["erro", "invalido", "obrigat"]
                ):
                    erro = f"SSW alert: {alert_msg}"
                elif msg_ssw and msg_ssw.get("tipo") == "erro":
                    erro = msg_ssw["mensagem"]

                if erro:
                    return gerar_saida(
                        False,
                        uf=uf,
                        unidade=unidade,
                        erro=erro,
                        cidades_processadas=resultados,
                        screenshot=screenshot_pos,
                    )

                sucesso_count = sum(1 for r in resultados if r.get("sucesso"))

                return gerar_saida(
                    True,
                    uf=uf,
                    unidade=unidade,
                    cidades_processadas=resultados,
                    total_cidades=len(cidades),
                    sucesso_count=sucesso_count,
                    resposta_ssw=msg_ssw,
                    alert=alert_msg,
                    screenshot=screenshot_pos,
                    mensagem=f"{sucesso_count}/{len(cidades)} cidades cadastradas "
                             f"para {unidade}/{uf}.",
                )

            finally:
                popup.remove_listener("dialog", on_dialog)

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cadastrar cidades atendidas no SSW (opcao 402)"
    )
    parser.add_argument(
        "--uf", required=True,
        help="UF para filtrar cidades (ex: MS, SP, PR)"
    )
    parser.add_argument(
        "--unidade", required=True,
        help="Sigla da unidade responsavel (ex: CGR)"
    )
    parser.add_argument(
        "--cidades", required=True,
        help='JSON array de cidades. Cada cidade: {"cidade": "...", "polo": "P/R/I", "prazo": N}'
    )
    parser.add_argument(
        "--defaults-file",
        default=os.path.join(SCRIPT_DIR, "..", "ssw_defaults.json"),
        help="Caminho para ssw_defaults.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview dos campos preenchidos, sem submeter"
    )

    args = parser.parse_args()

    # Validacoes
    if len(args.uf) != 2:
        print(json.dumps({"sucesso": False, "erro": "UF deve ter 2 caracteres"}))
        sys.exit(1)

    if len(args.unidade) != 3:
        print(json.dumps({"sucesso": False, "erro": "Unidade deve ter 3 caracteres (sigla IATA)"}))
        sys.exit(1)

    asyncio.run(cadastrar_cidades(args))


if __name__ == "__main__":
    main()
