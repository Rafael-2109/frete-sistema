#!/usr/bin/env python3
"""
importar_cidades_402.py — Importa cidades atendidas via CSV na opcao 402 do SSW.

Metodo preferido para bulk (>5 cidades). Aceita CSV no formato 402
(45 colunas, separador ';', encoding ISO-8859-1).

Uso:
    python importar_cidades_402.py --csv /tmp/cidades_cgr.csv [--dry-run] [--timeout 30]

O CSV deve seguir o formato padrao da 402:
    UF;CIDADE;UNIDADE;POLO;TIPO_FRETE;RESTRITA;COLETA;ENTREGA;PRAZO_ENTREGA;...

Em modo --dry-run, valida o CSV sem importar no SSW.
Sem --dry-run, faz login no SSW e importa via ajaxEnvia('IMPORTA2', 0).

IMPORTANTE — FIX MULTIPART:
  Playwright set_input_files() registra o arquivo no <input>, mas quando
  ajaxEnvia('IMPORTA2') faz POST multipart nativo para ssw0475, o body
  chega vazio no servidor. Fix: page.route() intercepta o POST e reconstroi
  o multipart body com os bytes reais do CSV.

PRACA_COMERCIAL:
  Para INCLUIR cidades novas (sem UNIDADE existente), o CSV DEVE ter o campo
  PRACA_COMERCIAL (indice 15) = UNIDADE + POLO (ex: "SSAI", "JPAI").
  Sem este campo, cidades sem UNIDADE sao silenciosamente ignoradas.
"""
import argparse
import asyncio
import os
import re
import sys

# Adicionar raiz do projeto e diretorio da skill ao path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

from ssw_common import verificar_credenciais, login_ssw, abrir_opcao_popup, gerar_saida


# Colunas obrigatorias do CSV 402
COLUNAS_OBRIGATORIAS = [
    "UF", "CIDADE", "UNIDADE", "POLO", "TIPO_FRETE",
    "RESTRITA", "COLETA", "ENTREGA", "PRAZO_ENTREGA",
]

# Total de colunas esperadas
TOTAL_COLUNAS = 45

# Valores validos por campo
VALIDACOES = {
    "POLO": {"P", "R", "I"},
    "TIPO_FRETE": {"A", "C", "F"},
    "RESTRITA": {"S", "N"},
    "COLETA": {"S", "N"},
    "ENTREGA": {"S", "N"},
    "TIPO_ALIQUOTA": {"N", "S"},
}


def validar_csv(csv_path):
    """Valida o CSV antes de importar. Retorna (valido, erros, info)."""
    erros = []
    info = {"linhas": 0, "unidades": set(), "ufs": set(), "cidades": []}

    if not os.path.exists(csv_path):
        return False, [f"Arquivo nao encontrado: {csv_path}"], info

    try:
        with open(csv_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Tentar UTF-8
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return False, [f"Erro ao ler arquivo: {e}"], info

    lines = [l for l in content.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return False, ["CSV deve ter header + pelo menos 1 linha de dados"], info

    header = lines[0]
    header_fields = [h.strip() for h in header.split(";") if h.strip()]

    # Verificar colunas obrigatorias no header
    for col in COLUNAS_OBRIGATORIAS:
        if col not in header_fields:
            erros.append(f"Coluna obrigatoria ausente no header: {col}")

    # Validar linhas de dados
    for i, line in enumerate(lines[1:], start=2):
        fields = line.split(";")
        # O CSV pode ter trailing ; resultando em campo extra vazio
        fields_clean = [f.strip() for f in fields]

        # Verificar numero de campos (tolerancia: pode ter 45 ou 46 com trailing ;)
        if len(fields_clean) < TOTAL_COLUNAS:
            erros.append(f"Linha {i}: {len(fields_clean)} campos (esperado {TOTAL_COLUNAS})")
            continue

        uf = fields_clean[0]
        cidade = fields_clean[1]
        unidade = fields_clean[2]

        # Validar UF
        if len(uf) != 2 or not uf.isalpha():
            erros.append(f"Linha {i}: UF invalida '{uf}'")

        # Validar cidade
        if not cidade:
            erros.append(f"Linha {i}: CIDADE vazia")

        # Validar unidade
        if not unidade or len(unidade) > 4:
            erros.append(f"Linha {i}: UNIDADE invalida '{unidade}'")

        # Validar campos com valores fixos
        for col_name, valid_values in VALIDACOES.items():
            col_idx = header_fields.index(col_name) if col_name in header_fields else -1
            if col_idx >= 0 and col_idx < len(fields_clean):
                val = fields_clean[col_idx]
                if val and val not in valid_values:
                    erros.append(f"Linha {i}: {col_name}='{val}' (validos: {valid_values})")

        info["linhas"] += 1
        info["unidades"].add(unidade)
        info["ufs"].add(uf)
        info["cidades"].append(f"{cidade}/{uf}")

    info["unidades"] = sorted(info["unidades"])
    info["ufs"] = sorted(info["ufs"])

    return len(erros) == 0, erros, info


async def importar_csv(context, page, csv_path, csv_bytes, timeout_s=20):
    """
    Importa CSV na 402 via ajaxEnvia com fix para multipart vazio.

    Mecanismo SSW:
    1. Abre 402 → clica 'Importar' → abre popup nativo (ssw0137.08)
    2. set_input_files no <input type="file" name="f1">
    3. page.route() intercepta POST para ssw0475 e reconstroi multipart body
    4. ajaxEnvia('IMPORTA2', 0) → JS faz:
       a) Upload multipart para /bin/ssw0475 (interceptado com bytes reais)
       b) Recebe fileId
       c) POST para /bin/ssw0137 com act=IMPORTA2&f1=<fileId>
    5. SSW processa CSV: cidades existentes sao atualizadas, novas adicionadas

    Args:
        context: Playwright BrowserContext
        page: Playwright Page (logada)
        csv_path: Caminho do CSV
        csv_bytes: Conteudo binario do CSV (lido antecipadamente)
        timeout_s: Tempo de espera apos IMPORTA2 (default 20s)
    """
    popup = await abrir_opcao_popup(context, page.frames[0], 402)
    await asyncio.sleep(2)

    # Abrir tela de importacao (popup nativo — NAO usar createNewDoc override)
    async with context.expect_page() as new_page_info:
        await popup.evaluate("ajaxEnvia('IMPORTAR', 1)")
    import_page = await new_page_info.value
    await import_page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)

    # Upload arquivo (set_input_files necessario para ajaxEnvia detectar bupload=true)
    file_input = await import_page.query_selector('input[type="file"]')
    if not file_input:
        await import_page.close()
        await popup.close()
        return gerar_saida(False, erro="Input file nao encontrado na tela de importacao")

    await file_input.set_input_files(csv_path)
    await asyncio.sleep(1)

    # ── FIX MULTIPART ──
    # Playwright set_input_files registra o arquivo no DOM, mas quando
    # ajaxEnvia faz POST multipart nativo para ssw0475, o body chega vazio.
    # Interceptamos o POST e reconstruimos o body com os bytes reais.
    async def fix_multipart(route, request):
        ct = request.headers.get("content-type", "")
        m = re.search(r"boundary=(.+)", ct)
        if not m:
            await route.continue_()
            return

        boundary = m.group(1)
        filename = os.path.basename(csv_path)
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="f1"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("ascii")
        body += csv_bytes
        body += (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="act"\r\n\r\n'
            f"\r\n--{boundary}--\r\n"
        ).encode("ascii")
        await route.continue_(post_data=body)

    await import_page.route("**/ssw0475**", fix_multipart)

    # Interceptar response do ssw0137 (resultado do processamento)
    import_result = None

    async def on_response(response):
        nonlocal import_result
        if "/ssw0137" in response.url and response.status == 200:
            try:
                body = await response.text()
                text = re.sub(r'<[^>]+>', ' ', body).strip()
                text = re.sub(r'\s+', ' ', text)
                if "conclu" in text.lower() or "process" in text.lower():
                    import_result = text
            except Exception:
                pass

    import_page.on("response", on_response)

    # Submeter via ajaxEnvia (que faz upload para ssw0475 + POST para ssw0137)
    await import_page.evaluate("ajaxEnvia('IMPORTA2', 0)")
    await asyncio.sleep(timeout_s)

    import_page.remove_listener("response", on_response)
    await import_page.unroute("**/ssw0475**")

    # Fallback 1: verificar iframe (SSW usa iframe hidden para submit)
    if not import_result:
        try:
            iframe_body = await import_page.evaluate("""() => {
                const iframe = document.querySelector('#uploadframe');
                if (iframe?.contentDocument?.body) return iframe.contentDocument.body.innerText;
                return '';
            }""")
            if iframe_body:
                import_result = iframe_body.strip()
        except Exception:
            pass

    # Fallback 2: verificar texto da pagina
    if not import_result:
        try:
            page_text = await import_page.evaluate("() => document.body?.innerText || ''")
            match = re.search(r"Processamento.*", page_text)
            if match:
                import_result = match.group(0)[:300]
        except Exception:
            pass

    # Fechar paginas
    try:
        await import_page.close()
    except Exception:
        pass
    try:
        await popup.close()
    except Exception:
        pass

    # Analisar resultado
    if not import_result:
        return gerar_saida(False, erro="Sem resposta do SSW")

    erro_detectado = (
        "erro" in import_result.lower() or "Informe" in import_result
    )

    # Extrair contagem de inclusoes/alteracoes/nao inclusas
    inclusoes = None
    alteracoes = None
    nao_inclusas = None
    match_inc = re.search(r'Inclus[^:]*:\s*(\d+)', import_result)
    match_alt = re.search(r'Altera[^:]*:\s*(\d+)', import_result)
    match_nao = re.search(r'[Nn]ao\s+inclus[^:]*:\s*(\d+)', import_result)
    if match_inc:
        inclusoes = int(match_inc.group(1))
    if match_alt:
        alteracoes = int(match_alt.group(1))
    if match_nao:
        nao_inclusas = int(match_nao.group(1))

    return gerar_saida(
        not erro_detectado,
        resposta=import_result[:500],
        inclusoes=inclusoes,
        alteracoes=alteracoes,
        nao_inclusas=nao_inclusas,
    )


async def run_import(csv_path, timeout_s=20):
    """Executa a importacao real no SSW."""
    from playwright.async_api import async_playwright

    verificar_credenciais()

    # Ler bytes do CSV antecipadamente (necessario para fix multipart)
    with open(csv_path, "rb") as f:
        csv_bytes = f.read()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = await context.new_page()

        if not await login_ssw(page):
            await browser.close()
            return gerar_saida(False, erro="Falha no login SSW")
        await asyncio.sleep(2)

        result = await importar_csv(context, page, csv_path, csv_bytes, timeout_s)

        await asyncio.sleep(2)
        await browser.close()

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Importa cidades atendidas via CSV na opcao 402 do SSW."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Caminho do CSV (formato 402, separador ';', ISO-8859-1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas valida o CSV sem importar no SSW",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Timeout em segundos apos IMPORTA2 (default: 20). Aumentar para CSVs grandes.",
    )
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)

    # Validar CSV
    valido, erros, info = validar_csv(csv_path)

    if args.dry_run:
        gerar_saida(
            valido,
            modo="dry-run",
            csv=csv_path,
            validacao={
                "valido": valido,
                "erros": erros[:20],
                "total_erros": len(erros),
            },
            info={
                "linhas": info["linhas"],
                "unidades": info["unidades"],
                "ufs": info["ufs"],
                "amostra_cidades": info["cidades"][:10],
            },
        )
        return

    if not valido:
        gerar_saida(
            False,
            erro="CSV invalido",
            erros=erros[:20],
            total_erros=len(erros),
        )
        sys.exit(1)

    # Importar
    asyncio.run(run_import(csv_path, args.timeout))


if __name__ == "__main__":
    main()
