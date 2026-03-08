#!/usr/bin/env python3
"""
consultar_saldo.py -- Consulta saldo disponivel para agendamento no portal Atacadao.

Exporta CSV de /relatorio/planilhaPedidos com saldo de produtos disponiveis
para agendamento. Opcionalmente cruza com CadastroPalletizacao.codigo_ean
para identificar produtos no sistema interno.

Uso:
    python consultar_saldo.py
    python consultar_saldo.py --cnpj 75315333003043
    python consultar_saldo.py --cruzar-local
    python consultar_saldo.py --cnpj 75315333003043 --cruzar-local

Saida:
    JSON padronizado com registros do CSV + resumo + caminho do CSV salvo.
"""
import argparse
import csv
import io
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Adicionar raiz do projeto ao path para imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from atacadao_common import (
    gerar_saida,
    capturar_screenshot,
    verificar_sessao_sync,
    criar_sessao_download,
    ATACADAO_URLS,
    TIMEOUTS,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

CSV_DIR = Path("/tmp/saldo_atacadao")

URL_PLANILHA_PEDIDOS = ATACADAO_URLS["planilha_pedidos"]

SELETORES_SALDO = {
    "toggle_filtros": 'a[data-toggle="collapse"][data-target="#filtros-collapse"]',
    "toggle_filtros_alt": "body > div.wrapper > div.content-wrapper > div.listagem-vue > div.filtros > div > a > div > div:nth-child(1) > h4 > i",
    "limpar_datas": "#filtros-collapse > div.filtros-body > div > div.col-md-3.bootstrap-daterangepicker > div > span:nth-child(5) > button",
    "aplicar_filtros": "#enviarFiltros",
    "exportar_csv": "#exportarExcel",
    # Modal de unidade (compartilhado com outras paginas)
    "abrir_modal_unidade": "#filtro-unidade > div.input-group.f_editando > span:nth-child(3) > button",
    "campo_cnpj_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-5.form-group > input",
    "botao_filtrar_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-1.form-group > button",
    "radio_unidade": 'input[name="m_unidades_modal-unidades"]',
    "botao_confirmar_modal": "#modal-unidades > div > div > div.modal-footer > div > div > button.btn.btn-primary.selecionar",
    "modal_unidades": "#modal-unidades",
}

# Mapeamento de colunas do CSV de saldo (posicao → nome interno)
# Headers reais sao lidos do CSV; este mapeamento e para referencia
COLUNAS_SALDO = {
    0: "nr_carga",
    1: "cnpj_fornecedor",
    2: "filial",
    3: "pedido_cliente",
    4: "nr_pedido_portal",  # ignorado
    5: "codigo_ean",
    6: "qtd_total_pedido",  # ignorado
    7: "saldo_disponivel",
    8: "data_de",
    9: "data_ate",
    10: "codigo_veiculo",
}

# GOTCHA: O Atacadao gera pedidos fantasmas com saldo=1 por item.
# Esses registros devem ser IGNORADOS pois nao representam saldo real.
SALDO_MINIMO_VALIDO = 2

# GOTCHA: EANs validos do Atacadao comecam com "17" (prefixo Brasil).
# EANs com prefixos 000, 037, 37, 57 sao codigos internos do portal, nao EAN reais.
PREFIXOS_EAN_INVALIDOS = ("000", "037", "37", "57")


# ──────────────────────────────────────────────
# Validacao de entradas
# ──────────────────────────────────────────────

def _validar_cnpj(cnpj):
    """Valida e limpa CNPJ opcional.

    Args:
        cnpj: CNPJ com ou sem formatacao, ou None

    Returns:
        str ou None: CNPJ limpo (14 digitos) ou None
    """
    if not cnpj:
        return None

    cnpj_limpo = re.sub(r"[.\-/]", "", cnpj.strip())
    if not cnpj_limpo.isdigit():
        raise ValueError(f"CNPJ invalido (deve conter apenas numeros): '{cnpj}'")
    if len(cnpj_limpo) != 14:
        raise ValueError(
            f"CNPJ invalido (deve ter 14 digitos, recebeu {len(cnpj_limpo)}): '{cnpj_limpo}'"
        )
    return cnpj_limpo


# ──────────────────────────────────────────────
# Abrir area de filtros (mesma estrategia de consultar_agendamentos)
# ──────────────────────────────────────────────

def _abrir_filtros(page):
    """Abre a area de filtros colapsavel na pagina de planilhaPedidos.

    Estrategia em 3 niveis:
    1. Verificar se filtros ja estao visiveis
    2. JS: forcar Bootstrap collapse show
    3. Fallback: clicar toggle

    Args:
        page: Playwright Page (sync)

    Returns:
        bool: True se filtros abertos
    """
    try:
        page.wait_for_timeout(2000)

        # 1. Verificar se filtros ja estao visiveis
        try:
            collapse = page.locator("#filtros-collapse")
            if collapse.is_visible():
                height = page.evaluate("""() => {
                    const el = document.querySelector('#filtros-collapse');
                    return el ? el.offsetHeight : 0;
                }""")
                if height > 50:
                    logger.info("Filtros ja estao abertos")
                    return True
        except Exception:
            pass

        # 2. JS: forcar collapse aberto
        logger.info("Filtros fechados, forcando abertura via JS...")
        page.evaluate("""() => {
            const collapse = document.querySelector('#filtros-collapse');
            if (collapse) {
                collapse.classList.add('in', 'show');
                collapse.classList.remove('collapsing');
                collapse.style.height = '';
                collapse.style.display = 'block';
                collapse.style.overflow = 'visible';
                try { $(collapse).collapse('show'); } catch(e) {}
            }
        }""")
        page.wait_for_timeout(500)

        height = page.evaluate("""() => {
            const el = document.querySelector('#filtros-collapse');
            return el ? el.offsetHeight : 0;
        }""")
        if height > 50:
            logger.info("Filtros abertos via JS")
            return True

        # 3. Fallback: clicar toggle
        logger.info("JS nao funcionou, tentando click no toggle...")
        for seletor in [SELETORES_SALDO["toggle_filtros"], SELETORES_SALDO["toggle_filtros_alt"]]:
            toggle = page.locator(seletor)
            if toggle.count() > 0:
                toggle.first.click()
                page.wait_for_timeout(1000)
                height = page.evaluate("""() => {
                    const el = document.querySelector('#filtros-collapse');
                    return el ? el.offsetHeight : 0;
                }""")
                if height > 50:
                    logger.info("Filtros abertos via click")
                    return True

        logger.error("Nao foi possivel abrir filtros")
        return False
    except Exception as e:
        logger.warning(f"Erro ao abrir filtros: {e}")
        return False


# ──────────────────────────────────────────────
# Filtrar por Unidade (CNPJ) via modal
# ──────────────────────────────────────────────

def _filtrar_unidade(page, cnpj):
    """Seleciona Unidade via modal de CNPJ.

    Fluxo: abrir modal -> preencher CNPJ -> filtrar -> selecionar radio -> confirmar.

    Args:
        page: Playwright Page (sync)
        cnpj: CNPJ limpo (14 digitos)

    Returns:
        str ou None: Texto da unidade selecionada
    """
    try:
        # 1. Abrir modal Unidade
        logger.info("Abrindo modal de Unidades...")
        btn_modal = page.locator(SELETORES_SALDO["abrir_modal_unidade"])
        btn_modal.click(timeout=TIMEOUTS["element_wait"])

        # 2. Aguardar modal visivel
        page.wait_for_selector(
            SELETORES_SALDO["modal_unidades"],
            state="visible",
            timeout=TIMEOUTS["modal_wait"],
        )
        page.wait_for_timeout(500)

        # 3. Preencher CNPJ
        logger.info(f"Preenchendo CNPJ: {cnpj}")
        campo_cnpj = page.locator(SELETORES_SALDO["campo_cnpj_modal"])
        campo_cnpj.fill(cnpj)

        # 4. Filtrar no modal
        logger.info("Filtrando no modal...")
        btn_filtrar = page.locator(SELETORES_SALDO["botao_filtrar_modal"])
        btn_filtrar.click()
        page.wait_for_timeout(2000)

        # 5. Selecionar primeiro radio
        radios = page.locator(SELETORES_SALDO["radio_unidade"])
        total_radios = radios.count()

        if total_radios == 0:
            logger.error(f"Nenhuma unidade encontrada para CNPJ {cnpj}")
            return None

        logger.info(f"Encontrada(s) {total_radios} unidade(s). Selecionando primeira...")
        radios.first.click()

        # Extrair nome da unidade
        unidade_texto = None
        try:
            import json as json_mod
            value = radios.first.get_attribute("value")
            if value:
                data = json_mod.loads(value)
                nome = data.get("nome_fantasia") or data.get("razao_social") or data.get("nome", "")
                cod = data.get("codigo") or data.get("id", "")
                if cod and nome:
                    unidade_texto = f"{cod} - {nome}"
                elif nome:
                    unidade_texto = nome
        except Exception:
            pass

        if not unidade_texto:
            try:
                parent_row = radios.first.locator("xpath=ancestor::tr")
                unidade_texto = parent_row.text_content().strip()[:80]
            except Exception:
                unidade_texto = f"CNPJ {cnpj}"

        # 6. Confirmar selecao
        logger.info("Confirmando selecao...")
        btn_confirmar = page.locator(SELETORES_SALDO["botao_confirmar_modal"])
        btn_confirmar.click()
        page.wait_for_timeout(1000)

        logger.info(f"Unidade selecionada: {unidade_texto}")
        return unidade_texto

    except Exception as e:
        logger.error(f"Erro ao filtrar unidade: {e}")
        return None


# ──────────────────────────────────────────────
# Limpar datas de agendamento (especifico de planilhaPedidos)
# ──────────────────────────────────────────────

def _limpar_datas_agendamento(page):
    """Limpa filtros de data de agendamento para trazer todo o saldo.

    O portal planilhaPedidos pode ter datas pre-preenchidas que limitam resultados.
    Limpar garante que todo o saldo disponivel seja exportado.

    Args:
        page: Playwright Page (sync)

    Returns:
        bool: True se limpeza executada (ou nao havia datas para limpar)
    """
    try:
        # Tentar clicar botao de limpar datas
        btn_limpar = page.locator(SELETORES_SALDO["limpar_datas"])
        if btn_limpar.count() > 0 and btn_limpar.first.is_visible():
            logger.info("Limpando datas de agendamento...")
            btn_limpar.first.click()
            page.wait_for_timeout(500)
            logger.info("Datas de agendamento limpas")
            return True

        # Fallback: tentar limpar via JS — buscar botoes de limpar daterangepicker
        resultado = page.evaluate("""() => {
            const botoes = document.querySelectorAll('button[data-action="remove"]');
            let limpou = 0;
            botoes.forEach(btn => {
                if (btn.offsetParent !== null) {  // visivel
                    btn.click();
                    limpou++;
                }
            });
            return limpou;
        }""")

        if resultado > 0:
            logger.info(f"Limpou {resultado} filtro(s) de data via JS")
            page.wait_for_timeout(500)
            return True

        logger.info("Nenhum filtro de data para limpar (ok)")
        return True

    except Exception as e:
        logger.warning(f"Erro ao limpar datas (nao-bloqueante): {e}")
        return True


# ──────────────────────────────────────────────
# Exportar CSV
# ──────────────────────────────────────────────

def _exportar_csv(page, diretorio, cnpj=None):
    """Exporta CSV clicando em #exportarExcel e interceptando download.

    Args:
        page: Playwright Page (sync) — DEVE ter accept_downloads=True no context
        diretorio: Path de destino
        cnpj: CNPJ para nome do arquivo (ou 'todos')

    Returns:
        Path ou None: Caminho do CSV salvo
    """
    diretorio.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo = cnpj or "todos"
    csv_filename = f"saldo_{sufixo}_{timestamp}.csv"
    csv_path = diretorio / csv_filename

    try:
        # Verificar se botao exportar existe
        btn_exportar = page.locator(SELETORES_SALDO["exportar_csv"])
        if btn_exportar.count() == 0:
            logger.error("Botao #exportarExcel nao encontrado")
            return None

        logger.info("Clicando em exportar CSV...")

        # Interceptar download (sync API)
        with page.expect_download(timeout=30000) as download_info:
            page.evaluate("document.querySelector('#exportarExcel').click()")

        download = download_info.value
        download.save_as(str(csv_path))

        if csv_path.exists():
            tamanho_kb = csv_path.stat().st_size / 1024
            logger.info(f"CSV exportado: {csv_path} ({tamanho_kb:.1f} KB)")
            return csv_path
        else:
            logger.error("CSV nao foi salvo")
            return None

    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {e}")
        return None


# ──────────────────────────────────────────────
# Parsing do CSV de saldo
# ──────────────────────────────────────────────

def _limpar_ean(valor):
    """Limpa formato EAN do portal: {="17898075642344"} → 17898075642344.

    O portal exporta EAN com formato Excel-safe {="..."} para evitar que
    o Excel trate como numero e perca zeros a esquerda.

    Args:
        valor: String do CSV (pode ter formato {="..."} ou ser numerico)

    Returns:
        str: EAN limpo (apenas digitos) ou string original se nao for EAN
    """
    if not valor:
        return ""

    valor = valor.strip()

    # Formato {="17898075642344"}
    match = re.match(r'\{="?([^"}\s]+)"?\}', valor)
    if match:
        return match.group(1).strip()

    # Formato ="17898075642344"
    match = re.match(r'="?([^"}\s]+)"?', valor)
    if match:
        return match.group(1).strip()

    return valor


def _limpar_pedido(valor):
    """Limpa formato de pedido do portal (mesmo padrao de EAN).

    Args:
        valor: String do CSV

    Returns:
        str: Pedido limpo
    """
    return _limpar_ean(valor)


def _parsear_csv(csv_path):
    """Le CSV de saldo exportado do portal.

    Tenta multiplos encodings. Detecta delimitador automaticamente.
    Limpa formatos {="..."} nas colunas de EAN e pedido.

    Args:
        csv_path: Path do arquivo CSV

    Returns:
        tuple: (list[dict], encoding_usado, delimitador)

    Raises:
        ValueError: Se nao conseguir ler o CSV
    """
    for encoding in ["utf-8", "utf-8-sig", "iso-8859-1", "windows-1252"]:
        try:
            with open(csv_path, "r", encoding=encoding) as f:
                # Ler primeira linha para detectar delimitador
                primeira_linha = f.readline()
                f.seek(0)

                # Detectar delimitador
                if primeira_linha.count(";") > primeira_linha.count(","):
                    delimitador = ";"
                else:
                    delimitador = ","

                reader = csv.DictReader(f, delimiter=delimitador)
                registros_raw = list(reader)

                if not registros_raw:
                    logger.warning(f"CSV vazio (encoding={encoding})")
                    return [], encoding, delimitador

                # Mapear colunas por posicao (fallback) e por nome (preferido)
                headers = list(registros_raw[0].keys())
                logger.info(
                    f"CSV parseado: {len(registros_raw)} registros, "
                    f"encoding={encoding}, delimitador='{delimitador}', "
                    f"colunas={headers}"
                )

                # Processar registros: limpar EAN e pedido
                registros = []
                for raw in registros_raw:
                    values = list(raw.values())
                    reg = {}

                    # Mapear por posicao (colunas A-K = indices 0-10)
                    if len(values) >= 11:
                        reg["nr_carga"] = (values[0] or "").strip()
                        reg["cnpj_fornecedor"] = (values[1] or "").strip()
                        reg["filial"] = (values[2] or "").strip()
                        reg["pedido_cliente"] = _limpar_pedido(values[3] or "")
                        # values[4] = nr_pedido_portal (ignorado)
                        reg["codigo_ean"] = _limpar_ean(values[5] or "")
                        # values[6] = qtd_total_pedido (ignorado)
                        reg["saldo_disponivel"] = (values[7] or "").strip()
                        reg["data_de"] = (values[8] or "").strip()
                        reg["data_ate"] = (values[9] or "").strip()
                        reg["codigo_veiculo"] = (values[10] or "").strip()
                    else:
                        # Fallback: usar headers originais com limpeza
                        for k, v in raw.items():
                            reg[k] = (v or "").strip()

                    registros.append(reg)

                return registros, encoding, delimitador

        except (UnicodeDecodeError, csv.Error):
            continue

    raise ValueError(f"Nao foi possivel ler CSV: {csv_path}")


# ──────────────────────────────────────────────
# Resumo
# ──────────────────────────────────────────────

def _gerar_resumo(registros):
    """Gera resumo estatistico dos registros de saldo.

    Args:
        registros: list[dict] do CSV parseado

    Returns:
        dict: Resumo com contadores
    """
    resumo = {
        "total": len(registros),
        "total_produtos_distintos": 0,
        "total_saldo": 0,
        "por_filial": {},
    }

    eans_unicos = set()
    for reg in registros:
        # Contar EANs distintos
        ean = reg.get("codigo_ean", "")
        if ean:
            eans_unicos.add(ean)

        # Somar saldo
        try:
            saldo = float(reg.get("saldo_disponivel", "0").replace(",", "."))
            resumo["total_saldo"] += saldo
        except (ValueError, AttributeError):
            pass

        # Agrupar por filial
        filial = reg.get("filial", "desconhecida")
        if filial:
            try:
                saldo_val = float(reg.get("saldo_disponivel", "0").replace(",", "."))
                resumo["por_filial"][filial] = resumo["por_filial"].get(filial, 0) + saldo_val
            except (ValueError, AttributeError):
                resumo["por_filial"][filial] = resumo["por_filial"].get(filial, 0)

    resumo["total_produtos_distintos"] = len(eans_unicos)
    resumo["total_saldo"] = round(resumo["total_saldo"], 2)

    # Arredondar valores por filial
    for filial in resumo["por_filial"]:
        resumo["por_filial"][filial] = round(resumo["por_filial"][filial], 2)

    return resumo


# ──────────────────────────────────────────────
# Cruzamento com CadastroPalletizacao (opcional)
# ──────────────────────────────────────────────

def _cruzar_com_local(registros):
    """Cruza EAN do CSV com CadastroPalletizacao.codigo_ean.

    Permite identificar quais produtos do portal correspondem a
    produtos do cadastro interno.

    Args:
        registros: list[dict] do CSV parseado

    Returns:
        dict: {com_match, sem_match, produtos_identificados}
    """
    # Suprimir stdout durante create_app/queries
    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        from app import create_app, db

        app = create_app()
        with app.app_context():
            # Buscar todos os EANs cadastrados
            resultado = db.session.execute(
                db.text("""
                    SELECT cod_produto, nome_produto, codigo_ean, palletizacao, peso_bruto
                    FROM cadastro_palletizacao
                    WHERE codigo_ean IS NOT NULL
                      AND codigo_ean != ''
                      AND ativo = true
                """)
            ).fetchall()
    finally:
        sys.stdout = _old_stdout

    # Indexar por EAN
    ean_para_produto = {}
    for r in resultado:
        if r.codigo_ean:
            ean_para_produto[r.codigo_ean.strip()] = {
                "cod_produto": r.cod_produto,
                "nome_produto": r.nome_produto,
                "palletizacao": float(r.palletizacao) if r.palletizacao else 0,
                "peso_bruto": float(r.peso_bruto) if r.peso_bruto else 0,
            }

    com_match = 0
    sem_match = 0
    produtos_identificados = []
    eans_vistos = set()

    for reg in registros:
        ean = reg.get("codigo_ean", "").strip()
        if not ean:
            sem_match += 1
            continue

        produto = ean_para_produto.get(ean)
        if produto:
            com_match += 1
            reg["cod_produto_local"] = produto["cod_produto"]
            reg["nome_produto_local"] = produto["nome_produto"]
            reg["palletizacao"] = produto["palletizacao"]
            reg["peso_bruto"] = produto["peso_bruto"]

            if ean not in eans_vistos:
                eans_vistos.add(ean)
                produtos_identificados.append({
                    "ean": ean,
                    "cod_produto": produto["cod_produto"],
                    "nome_produto": produto["nome_produto"],
                })
        else:
            sem_match += 1

    return {
        "com_match": com_match,
        "sem_match": sem_match,
        "total_ean_cadastrados": len(ean_para_produto),
        "produtos_identificados": produtos_identificados,
    }


# ──────────────────────────────────────────────
# Filtrar registros por CNPJ
# ──────────────────────────────────────────────

def _filtrar_por_cnpj(registros, cnpj):
    """Filtra registros pelo CNPJ do fornecedor.

    Args:
        registros: list[dict]
        cnpj: CNPJ limpo (14 digitos)

    Returns:
        list[dict]: Registros filtrados
    """
    if not cnpj:
        return registros

    # Formatar CNPJ para comparacao (portal pode ter formatacao)
    cnpj_formatado = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

    filtrados = []
    for reg in registros:
        cnpj_reg = reg.get("cnpj_fornecedor", "")
        cnpj_reg_limpo = re.sub(r"[.\-/]", "", cnpj_reg)
        if cnpj_reg_limpo == cnpj or cnpj_reg == cnpj_formatado:
            filtrados.append(reg)

    return filtrados


# ──────────────────────────────────────────────
# Orquestrador principal
# ──────────────────────────────────────────────

def _filtrar_por_filial(registros, filial):
    """Filtra registros pelo codigo de filial.

    Args:
        registros: list[dict]
        filial: Codigo da filial (string)

    Returns:
        list[dict]: Registros filtrados
    """
    if not filial:
        return registros
    filial_str = str(filial).strip()
    return [
        reg for reg in registros
        if reg.get("filial", "").strip() == filial_str
    ]


def consultar_saldo(cnpj=None, filial=None, cruzar_local=False):
    """Orquestra consulta de saldo do portal Atacadao.

    Args:
        cnpj: CNPJ da filial para filtrar (opcional, 14 digitos)
        filial: Codigo de filial para filtrar (opcional, ex: "183")
        cruzar_local: Se True, cruza com CadastroPalletizacao.codigo_ean

    Returns:
        dict: Resultado JSON padronizado via gerar_saida()
    """
    # 1. Validar entradas
    try:
        cnpj = _validar_cnpj(cnpj)
    except ValueError as e:
        return gerar_saida(False, erro=str(e))

    # 2. Execucao real
    pw = None
    browser = None
    try:
        # Criar sessao com accept_downloads=True
        pw, browser, _context, page = criar_sessao_download(headless=True)

        # Verificar sessao
        if not verificar_sessao_sync(page):
            return gerar_saida(
                False,
                erro="Sessao do Atacadao expirada",
                requer_login=True,
                instrucao="Faca re-login interativo: python -m app.portal.atacadao.login_interativo",
            )

        # 3. Navegar para /relatorio/planilhaPedidos
        logger.info(f"Navegando para {URL_PLANILHA_PEDIDOS}...")
        page.goto(
            URL_PLANILHA_PEDIDOS,
            wait_until="domcontentloaded",
            timeout=TIMEOUTS["page_load"],
        )
        page.wait_for_timeout(2000)

        # Verificar se chegou na pagina correta
        url_atual = page.url.lower()
        if "login" in url_atual or "signin" in url_atual:
            return gerar_saida(
                False,
                erro="Redirecionado para login ao acessar /relatorio/planilhaPedidos",
                requer_login=True,
                instrucao="Faca re-login interativo: python -m app.portal.atacadao.login_interativo",
            )

        # 4. Abrir filtros
        if not _abrir_filtros(page):
            screenshot = capturar_screenshot(page, "erro_filtros_saldo")
            return gerar_saida(
                False,
                erro="Nao foi possivel abrir area de filtros em /relatorio/planilhaPedidos",
                screenshot=screenshot,
            )

        # 5. Limpar datas de agendamento (para trazer todo o saldo)
        _limpar_datas_agendamento(page)

        # 6. Filtrar por Unidade (se CNPJ informado)
        unidade_texto = None
        if cnpj:
            unidade_texto = _filtrar_unidade(page, cnpj)
            if not unidade_texto:
                screenshot = capturar_screenshot(page, "erro_unidade_saldo")
                return gerar_saida(
                    False,
                    erro=f"Nenhuma unidade encontrada para CNPJ {cnpj}",
                    cnpj=cnpj,
                    screenshot=screenshot,
                )

        # 7. Aplicar filtros
        logger.info("Aplicando filtros...")
        page.evaluate("document.querySelector('#enviarFiltros').click()")
        page.wait_for_timeout(3000)

        # 8. Screenshot como evidencia
        screenshot = capturar_screenshot(page, f"saldo_{cnpj or 'todos'}")

        # 9. Exportar CSV
        csv_path = _exportar_csv(page, CSV_DIR, cnpj)
        if not csv_path:
            return gerar_saida(
                False,
                erro="Falha ao exportar CSV de saldo",
                cnpj=cnpj,
                unidade=unidade_texto,
                screenshot=screenshot,
            )

        # 10. Parsear CSV
        try:
            registros, encoding, delimitador = _parsear_csv(csv_path)
        except ValueError as e:
            return gerar_saida(
                False,
                erro=str(e),
                csv_path=str(csv_path),
                screenshot=screenshot,
            )

        # 11. Filtrar por CNPJ pos-parse (caso portal retorne mais resultados)
        if cnpj:
            total_antes = len(registros)
            registros = _filtrar_por_cnpj(registros, cnpj)
            if total_antes != len(registros):
                logger.info(
                    f"Filtro CNPJ: {total_antes} -> {len(registros)} registros"
                )

        # 11b. Filtrar por filial (se informado)
        if filial:
            total_antes_filial = len(registros)
            registros = _filtrar_por_filial(registros, filial)
            if total_antes_filial != len(registros):
                logger.info(
                    f"Filtro filial: {total_antes_filial} -> {len(registros)} registros"
                )

        # 11c. GOTCHA: Remover pedidos fantasmas (saldo=1 por item)
        # O Atacadao gera pedidos com qtd=1 que nao representam saldo real.
        total_antes_fantasma = len(registros)
        registros_fantasma = []
        registros_validos = []
        for reg in registros:
            try:
                saldo = float(reg.get("saldo_disponivel", "0").replace(",", "."))
            except (ValueError, AttributeError):
                saldo = 0
            if saldo < SALDO_MINIMO_VALIDO:
                registros_fantasma.append(reg)
            else:
                registros_validos.append(reg)

        if registros_fantasma:
            logger.info(
                f"Filtro fantasma (saldo<{SALDO_MINIMO_VALIDO}): "
                f"{total_antes_fantasma} -> {len(registros_validos)} registros "
                f"({len(registros_fantasma)} fantasmas removidos)"
            )
        registros = registros_validos

        # 11c. GOTCHA: Remover registros com EAN invalido (codigos internos do portal)
        # EANs validos do Atacadao comecam com "17" (prefixo Brasil).
        # Prefixos 000, 037, 37, 57 sao codigos internos, nao EAN reais.
        total_antes_ean = len(registros)
        registros = [
            reg for reg in registros
            if not reg.get("codigo_ean", "").startswith(PREFIXOS_EAN_INVALIDOS)
        ]
        ean_invalidos = total_antes_ean - len(registros)
        if ean_invalidos:
            logger.info(
                f"Filtro EAN invalido (prefixos {PREFIXOS_EAN_INVALIDOS}): "
                f"{total_antes_ean} -> {len(registros)} registros "
                f"({ean_invalidos} com EAN interno removidos)"
            )

        # 12. Gerar resumo
        resumo = _gerar_resumo(registros)

        # 13. Cruzamento local (opcional)
        cruzamento = None
        if cruzar_local and registros:
            try:
                cruzamento = _cruzar_com_local(registros)
            except Exception as e:
                logger.error(f"Erro no cruzamento local: {e}")
                cruzamento = {"erro": str(e)}

        # 14. Montar resultado
        resultado = {
            "cnpj": cnpj,
            "filial": filial,
            "unidade": unidade_texto,
            "total_registros": len(registros),
            "csv_path": str(csv_path),
            "csv_encoding": encoding,
            "csv_delimitador": delimitador,
            "screenshot": screenshot,
            "registros": registros,
            "resumo": resumo,
        }

        if cruzar_local and cruzamento:
            if "erro" in cruzamento:
                resultado["cruzamento_erro"] = cruzamento["erro"]
            else:
                resultado["cruzamento"] = cruzamento

        return gerar_saida(True, **resultado)

    except RuntimeError as e:
        return gerar_saida(
            False,
            erro=str(e),
            requer_login="sessao" in str(e).lower() or "storage" in str(e).lower(),
            instrucao="Faca re-login interativo: python -m app.portal.atacadao.login_interativo",
        )

    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return gerar_saida(
            False,
            erro=f"Erro inesperado: {str(e)}",
            cnpj=cnpj,
        )

    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Consulta saldo disponivel para agendamento no portal Atacadao (export CSV)"
    )
    parser.add_argument(
        "--cnpj",
        default=None,
        help="CNPJ da filial para filtrar (14 digitos, com ou sem formatacao). Opcional.",
    )
    parser.add_argument(
        "--filial",
        default=None,
        help="Codigo de filial para filtrar (ex: 183, 111). Opcional.",
    )
    parser.add_argument(
        "--cruzar-local",
        action="store_true",
        help="Cruza EAN do CSV com CadastroPalletizacao.codigo_ean para identificar cod_produto",
    )

    args = parser.parse_args()

    resultado = consultar_saldo(
        cnpj=args.cnpj,
        filial=args.filial,
        cruzar_local=args.cruzar_local,
    )

    if not resultado.get("sucesso"):
        sys.exit(1)


if __name__ == "__main__":
    main()
