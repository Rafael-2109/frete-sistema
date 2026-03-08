#!/usr/bin/env python3
"""
consultar_agendamentos.py -- Consulta agendamentos futuros do portal Atacadao.

Exporta CSV de /relatorio/itens e opcionalmente cruza com dados locais
(Separacao, EntregaMonitorada) para detectar agendamentos disponiveis
e agendas perdidas.

Uso:
    python consultar_agendamentos.py --cnpj 75315333003043
    python consultar_agendamentos.py --cnpj 75315333003043 --dias 30
    python consultar_agendamentos.py --cnpj 75315333003043 --dry-run
    python consultar_agendamentos.py --cnpj 75315333003043 --cruzar-local

Saida:
    JSON padronizado com registros do CSV + resumo + caminho do CSV salvo.
"""
import argparse
import csv
import logging
import os
import re
import sys
from datetime import datetime, timedelta
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
    ATACADAO_BASE_URL,
    TIMEOUTS,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

CSV_DIR = Path("/tmp/agendamentos_atacadao")

URL_RELATORIO_ITENS = f"{ATACADAO_BASE_URL}/relatorio/itens"

SELETORES_RELATORIO = {
    "toggle_filtros": 'a[data-toggle="collapse"][data-target="#filtros-collapse"]',
    "abrir_modal_unidade": "#filtro-unidade > div.input-group.f_editando > span:nth-child(3) > button",
    "campo_cnpj_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-5.form-group > input",
    "botao_filtrar_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-1.form-group > button",
    "radio_unidade": 'input[name="m_unidades_modal-unidades"]',
    "botao_confirmar_modal": "#modal-unidades > div > div > div.modal-footer > div > div > button.btn.btn-primary.selecionar",
    "modal_unidades": "#modal-unidades",
    "botao_filtrar": "#enviarFiltros",
    "botao_exportar": "#exportarExcel",
    # Seletor do container de data de agendamento (6o filho dos filtros)
    "container_data_agendamento": "#filtros-collapse > div.filtros-body > div > div:nth-child(6)",
}

# Dias padrao para range futuro
DIAS_PADRAO = 45


# ──────────────────────────────────────────────
# Validacao de entradas
# ──────────────────────────────────────────────

def _validar_entradas(cnpj, dias):
    """Valida --cnpj e --dias.

    Args:
        cnpj: CNPJ da unidade (str)
        dias: Numero de dias futuros (int)

    Returns:
        tuple: (cnpj_limpo, dias_validado)

    Raises:
        ValueError: Se entradas invalidas
    """
    if not cnpj:
        raise ValueError("--cnpj e obrigatorio")

    # Limpar formatacao
    cnpj_limpo = re.sub(r"[.\-/]", "", cnpj.strip())
    if not cnpj_limpo.isdigit():
        raise ValueError(f"CNPJ invalido (deve conter apenas numeros): '{cnpj}'")
    if len(cnpj_limpo) != 14:
        raise ValueError(
            f"CNPJ invalido (deve ter 14 digitos, recebeu {len(cnpj_limpo)}): '{cnpj_limpo}'"
        )

    if dias is not None:
        if dias < 1:
            raise ValueError(f"--dias deve ser >= 1 (recebeu {dias})")
        if dias > 365:
            raise ValueError(f"--dias deve ser <= 365 (recebeu {dias})")
    else:
        dias = DIAS_PADRAO

    return cnpj_limpo, dias


# ──────────────────────────────────────────────
# Abrir area de filtros (reutiliza logica de imprimir_pedidos)
# ──────────────────────────────────────────────

def _abrir_filtros(page):
    """Abre a area de filtros colapsavel na pagina de relatorio.

    Estrategia em 3 niveis (mesma logica de imprimir_pedidos):
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
            page.wait_for_selector(
                "#filtros-collapse",
                state="visible",
                timeout=2000,
            )
            # Verificar se conteudo interno esta visivel (collapse aberto)
            collapse = page.locator("#filtros-collapse")
            if collapse.is_visible():
                # Verificar se tem altura > 0 (nao colapsado)
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

        # Verificar se funcionou
        height = page.evaluate("""() => {
            const el = document.querySelector('#filtros-collapse');
            return el ? el.offsetHeight : 0;
        }""")
        if height > 50:
            logger.info("Filtros abertos via JS")
            return True

        # 3. Fallback: clicar toggle
        logger.info("JS nao funcionou, tentando click no toggle...")
        toggle = page.locator(SELETORES_RELATORIO["toggle_filtros"])
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
# (mesma logica de imprimir_pedidos._filtrar_unidade)
# ──────────────────────────────────────────────

def _filtrar_unidade(page, cnpj):
    """Seleciona Unidade via modal de CNPJ.

    Fluxo: abrir modal → preencher CNPJ → filtrar → selecionar radio → confirmar.

    Args:
        page: Playwright Page (sync)
        cnpj: CNPJ limpo (14 digitos)

    Returns:
        str ou None: Texto da unidade selecionada
    """
    try:
        # 1. Abrir modal Unidade
        logger.info("Abrindo modal de Unidades...")
        btn_modal = page.locator(SELETORES_RELATORIO["abrir_modal_unidade"])
        btn_modal.click(timeout=TIMEOUTS["element_wait"])

        # 2. Aguardar modal visivel
        page.wait_for_selector(
            SELETORES_RELATORIO["modal_unidades"],
            state="visible",
            timeout=TIMEOUTS["modal_wait"],
        )
        page.wait_for_timeout(500)

        # 3. Preencher CNPJ
        logger.info(f"Preenchendo CNPJ: {cnpj}")
        campo_cnpj = page.locator(SELETORES_RELATORIO["campo_cnpj_modal"])
        campo_cnpj.fill(cnpj)

        # 4. Filtrar no modal
        logger.info("Filtrando no modal...")
        btn_filtrar = page.locator(SELETORES_RELATORIO["botao_filtrar_modal"])
        btn_filtrar.click()
        page.wait_for_timeout(2000)

        # 5. Selecionar primeiro radio
        radios = page.locator(SELETORES_RELATORIO["radio_unidade"])
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
        btn_confirmar = page.locator(SELETORES_RELATORIO["botao_confirmar_modal"])
        btn_confirmar.click()
        page.wait_for_timeout(1000)

        logger.info(f"Unidade selecionada: {unidade_texto}")
        return unidade_texto

    except Exception as e:
        logger.error(f"Erro ao filtrar unidade: {e}")
        return None


# ──────────────────────────────────────────────
# Selecionar datas (DateRangePicker)
# ──────────────────────────────────────────────

def _selecionar_datas(page, data_de, data_ate):
    """Seleciona range de datas de agendamento via DateRangePicker.

    Estrategia em 2 niveis:
    1. JS injection: seta datas diretamente no daterangepicker jQuery
    2. Fallback: tenta via input.value + trigger

    Args:
        page: Playwright Page (sync)
        data_de: Data inicio (DD/MM/YYYY)
        data_ate: Data fim (DD/MM/YYYY)

    Returns:
        bool: True se datas selecionadas
    """
    try:
        # Nivel 1: JS injection via jQuery daterangepicker
        logger.info(f"Selecionando datas: {data_de} a {data_ate}")
        resultado = page.evaluate(f"""() => {{
            // Estrategia 1: Buscar pelo container nth-child(6)
            const container = document.querySelector(
                '#filtros-collapse > div.filtros-body > div > div:nth-child(6)'
            );

            // Buscar qualquer input dentro do container que tenha daterangepicker
            let input = null;
            if (container) {{
                // Tentar inputs do container
                const inputs = container.querySelectorAll('input');
                for (const inp of inputs) {{
                    if ($ && $(inp).data && $(inp).data('daterangepicker')) {{
                        input = inp;
                        break;
                    }}
                }}
                // Fallback: qualquer elemento com daterangepicker
                if (!input) {{
                    const allEls = container.querySelectorAll('*');
                    for (const el of allEls) {{
                        try {{
                            if ($ && $(el).data && $(el).data('daterangepicker')) {{
                                input = el;
                                break;
                            }}
                        }} catch(e) {{}}
                    }}
                }}
            }}

            // Estrategia 2: buscar por todos daterangepickers na pagina
            if (!input) {{
                const allInputs = document.querySelectorAll('input');
                for (const inp of allInputs) {{
                    try {{
                        if ($ && $(inp).data && $(inp).data('daterangepicker')) {{
                            // Pular o de data de elaboracao (dthr_elaboracao)
                            const name = inp.name || inp.id || '';
                            if (name.includes('elaboracao')) continue;
                            // Usar o proximo daterangepicker encontrado
                            input = inp;
                        }}
                    }} catch(e) {{}}
                }}
            }}

            if (!input) {{
                return {{ ok: false, erro: 'Nenhum daterangepicker encontrado' }};
            }}

            try {{
                var picker = $(input).data('daterangepicker');
                if (!picker) {{
                    return {{ ok: false, erro: 'daterangepicker data nao encontrado no input' }};
                }}
                picker.setStartDate(moment('{data_de}', 'DD/MM/YYYY'));
                picker.setEndDate(moment('{data_ate}', 'DD/MM/YYYY'));
                $(input).trigger('apply.daterangepicker', picker);
                return {{
                    ok: true,
                    input_name: input.name || input.id || 'desconhecido',
                    start: picker.startDate.format('DD/MM/YYYY'),
                    end: picker.endDate.format('DD/MM/YYYY')
                }};
            }} catch(e) {{
                return {{ ok: false, erro: 'Erro ao setar datas: ' + e.message }};
            }}
        }}""")

        if resultado.get("ok"):
            logger.info(
                f"Datas selecionadas via JS: {resultado.get('start')} - {resultado.get('end')} "
                f"(input: {resultado.get('input_name')})"
            )
            return True

        logger.warning(f"JS daterangepicker falhou: {resultado.get('erro')}")

        # Nivel 2: Fallback — tentar abrir o picker e clicar
        logger.info("Tentando fallback: abrir daterangepicker por click...")
        container = page.locator(SELETORES_RELATORIO["container_data_agendamento"])
        if container.count() > 0:
            # Tentar clicar no botao/icone dentro do container
            botao = container.locator("button, span.input-group-btn button, i.fa-calendar").first
            if botao.count() > 0:
                botao.click()
                page.wait_for_timeout(500)

                # Tentar preencher diretamente o input visivel
                input_el = container.locator("input").first
                if input_el.count() > 0:
                    input_el.fill(f"{data_de} - {data_ate}")
                    # Disparar evento para que o picker atualize
                    page.evaluate("""(selector) => {
                        const input = document.querySelector(selector);
                        if (input) {
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }""", f"{SELETORES_RELATORIO['container_data_agendamento']} input")
                    page.wait_for_timeout(500)
                    logger.info("Datas preenchidas via input direto (fallback)")
                    return True

        logger.error("Nao foi possivel selecionar datas por nenhuma estrategia")
        return False

    except Exception as e:
        logger.error(f"Erro ao selecionar datas: {e}")
        return False


# ──────────────────────────────────────────────
# Exportar CSV
# ──────────────────────────────────────────────

def _exportar_csv(page, diretorio, cnpj):
    """Exporta CSV clicando em #exportarExcel e interceptando download.

    Args:
        page: Playwright Page (sync) — DEVE ter accept_downloads=True no context
        diretorio: Path de destino
        cnpj: CNPJ para nome do arquivo

    Returns:
        Path ou None: Caminho do CSV salvo
    """
    diretorio.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"relatorio_{cnpj}_{timestamp}.csv"
    csv_path = diretorio / csv_filename

    try:
        # Verificar se botao exportar existe
        btn_exportar = page.locator(SELETORES_RELATORIO["botao_exportar"])
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
# Parsing do CSV
# ──────────────────────────────────────────────

def _parsear_csv(csv_path):
    """Le CSV exportado do portal. Tenta UTF-8, fallback ISO-8859-1, Windows-1252.

    Detecta delimitador automaticamente (';' ou ',').

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
                registros = list(reader)

                if registros:
                    logger.info(
                        f"CSV parseado: {len(registros)} registros, "
                        f"encoding={encoding}, delimitador='{delimitador}', "
                        f"colunas={list(registros[0].keys())}"
                    )
                else:
                    logger.warning(f"CSV vazio (encoding={encoding})")

                return registros, encoding, delimitador

        except (UnicodeDecodeError, csv.Error):
            continue

    raise ValueError(f"Nao foi possivel ler CSV: {csv_path}")


# ──────────────────────────────────────────────
# Resumo dos registros
# ──────────────────────────────────────────────

def _gerar_resumo(registros):
    """Gera resumo estatistico dos registros do CSV.

    Args:
        registros: list[dict] do CSV parseado

    Returns:
        dict: Resumo com contadores por status, etc.
    """
    resumo = {
        "total": len(registros),
        "por_status": {},
    }

    # Detectar coluna de status (pode variar)
    col_status = None
    if registros:
        for possivel in ["Status", "status", "STATUS", "Situacao", "situacao"]:
            if possivel in registros[0]:
                col_status = possivel
                break

    if col_status:
        for reg in registros:
            status = reg.get(col_status, "Desconhecido").strip()
            resumo["por_status"][status] = resumo["por_status"].get(status, 0) + 1

    return resumo


# ──────────────────────────────────────────────
# Cruzamento com dados locais (opcional)
# ──────────────────────────────────────────────

def _cruzar_com_local(registros, cnpj):
    """Cruza registros do portal com Separacao e EntregaMonitorada locais.

    Classificacao:
    - agendamento_disponivel: protocolo no portal + Separacao.sincronizado_nf=False
    - agenda_perdida: data_agendamento < hoje + sem NF
    - em_dia: agendamento futuro, tudo ok
    - entregue: EntregaMonitorada.entregue=True

    Args:
        registros: list[dict] do CSV parseado
        cnpj: CNPJ limpo (14 digitos)

    Returns:
        dict: {registros_cruzados, resumo_cruzamento}
    """
    # Suprimir prints de import, create_app() e pool events para nao poluir stdout
    # (gerar_saida usa print para JSON output)
    # O pool event em app/__init__.py:136 imprime na primeira conexao,
    # por isso a supressao cobre tambem as queries do banco.
    import io as _io
    _old_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    try:
        from app import create_app, db
        app = create_app()

        with app.app_context():
            # Buscar separacoes com agendamento para o CNPJ
            separacoes = db.session.execute(
                db.text("""
                    SELECT DISTINCT ON (protocolo)
                        protocolo, agendamento, sincronizado_nf,
                        num_pedido, numero_nf, separacao_lote_id
                    FROM separacao
                    WHERE cnpj_cpf = :cnpj
                      AND protocolo IS NOT NULL
                      AND protocolo != ''
                    ORDER BY protocolo, id DESC
                """),
                {"cnpj": cnpj},
            ).fetchall()

            # Buscar entregas monitoradas
            entregas = db.session.execute(
                db.text("""
                    SELECT em.numero_nf, em.entregue, em.status_finalizacao,
                           ae.protocolo_agendamento, ae.data_agendada, ae.status
                    FROM entregas_monitoradas em
                    LEFT JOIN agendamentos_entrega ae ON ae.entrega_id = em.id
                    WHERE em.cnpj_cliente = :cnpj
                """),
                {"cnpj": cnpj},
            ).fetchall()
    finally:
        sys.stdout = _old_stdout

    # Indexar por protocolo (fora do bloco suprimido — sem I/O)
    sep_por_protocolo = {}
    for s in separacoes:
        sep_por_protocolo[s.protocolo.strip()] = {
            "sincronizado_nf": s.sincronizado_nf,
            "num_pedido": s.num_pedido,
            "numero_nf": s.numero_nf,
            "agendamento": str(s.agendamento) if s.agendamento else None,
            "separacao_lote_id": s.separacao_lote_id,
        }

    # Indexar entregas por protocolo
    entrega_por_protocolo = {}
    for e in entregas:
        if e.protocolo_agendamento:
            entrega_por_protocolo[e.protocolo_agendamento.strip()] = {
                "numero_nf": e.numero_nf,
                "entregue": e.entregue,
                "status_finalizacao": e.status_finalizacao,
                "data_agendada": str(e.data_agendada) if e.data_agendada else None,
                "status_agendamento": e.status,
            }

    # Detectar coluna de protocolo e data no CSV
    col_protocolo = None
    col_data = None
    if registros:
        chaves = registros[0].keys()
        for possivel in ["Protocolo", "protocolo", "PROTOCOLO", "Nr Protocolo", "Nro Protocolo"]:
            if possivel in chaves:
                col_protocolo = possivel
                break
        for possivel in ["Data Agendamento", "Data agendamento", "data_agendamento",
                         "Data", "DATA", "Dt Agendamento"]:
            if possivel in chaves:
                col_data = possivel
                break

    hoje = datetime.now().date()
    contadores = {
        "agendamento_disponivel": 0,
        "agenda_perdida": 0,
        "em_dia": 0,
        "entregue": 0,
        "sem_cruzamento": 0,
    }

    registros_cruzados = []
    for reg in registros:
        protocolo = reg.get(col_protocolo, "").strip() if col_protocolo else ""
        reg_cruzado = dict(reg)

        # Classificar
        sep = sep_por_protocolo.get(protocolo)
        ent = entrega_por_protocolo.get(protocolo)

        if ent and ent.get("entregue"):
            reg_cruzado["status_local"] = "entregue"
            contadores["entregue"] += 1
        elif sep and not sep.get("sincronizado_nf"):
            reg_cruzado["status_local"] = "agendamento_disponivel"
            contadores["agendamento_disponivel"] += 1
        elif col_data and reg.get(col_data):
            # Tentar parsear data para verificar se perdeu
            try:
                data_str = reg[col_data].strip()
                # Tentar formatos comuns
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M"]:
                    try:
                        data_agend = datetime.strptime(data_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    data_agend = None

                if data_agend and data_agend < hoje and not (sep and sep.get("sincronizado_nf")):
                    reg_cruzado["status_local"] = "agenda_perdida"
                    contadores["agenda_perdida"] += 1
                elif data_agend and data_agend >= hoje:
                    reg_cruzado["status_local"] = "em_dia"
                    contadores["em_dia"] += 1
                else:
                    reg_cruzado["status_local"] = "sem_cruzamento"
                    contadores["sem_cruzamento"] += 1
            except Exception:
                reg_cruzado["status_local"] = "sem_cruzamento"
                contadores["sem_cruzamento"] += 1
        else:
            reg_cruzado["status_local"] = "sem_cruzamento"
            contadores["sem_cruzamento"] += 1

        # Adicionar dados locais
        if sep:
            reg_cruzado["separacao"] = sep
        if ent:
            reg_cruzado["entrega_local"] = ent

        registros_cruzados.append(reg_cruzado)

    return {
        "registros": registros_cruzados,
        "resumo_cruzamento": contadores,
        "total_separacoes_local": len(sep_por_protocolo),
        "total_entregas_local": len(entrega_por_protocolo),
    }


# ──────────────────────────────────────────────
# Orquestrador principal
# ──────────────────────────────────────────────

def consultar_agendamentos(cnpj, dias=None, dry_run=False, cruzar_local=False):
    """Orquestra consulta de agendamentos do portal Atacadao.

    Args:
        cnpj: CNPJ da unidade (14 digitos)
        dias: Numero de dias futuros (default: 45)
        dry_run: Se True, apenas preview sem acessar portal
        cruzar_local: Se True, cruza com Separacao/EntregaMonitorada

    Returns:
        dict: Resultado JSON padronizado via gerar_saida()
    """
    # 1. Validar entradas
    try:
        cnpj, dias = _validar_entradas(cnpj, dias)
    except ValueError as e:
        return gerar_saida(False, erro=str(e))

    # Calcular range de datas
    hoje = datetime.now()
    data_de = hoje.strftime("%d/%m/%Y")
    data_ate = (hoje + timedelta(days=dias)).strftime("%d/%m/%Y")

    # 2. Dry-run
    if dry_run:
        info = {
            "modo": "dry-run",
            "cnpj": cnpj,
            "periodo": {
                "de": data_de,
                "ate": data_ate,
                "dias": dias,
            },
            "url": URL_RELATORIO_ITENS,
            "descricao": (
                f"Exportaria CSV de agendamentos do periodo {data_de} a {data_ate} "
                f"para CNPJ {cnpj}"
            ),
            "cruzar_local": cruzar_local,
        }
        return gerar_saida(True, **info)

    # 3. Execucao real
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

        # 4. Navegar para /relatorio/itens
        logger.info(f"Navegando para {URL_RELATORIO_ITENS}...")
        page.goto(
            URL_RELATORIO_ITENS,
            wait_until="domcontentloaded",
            timeout=TIMEOUTS["page_load"],
        )
        page.wait_for_timeout(2000)

        # Verificar se chegou na pagina correta
        url_atual = page.url.lower()
        if "login" in url_atual or "signin" in url_atual:
            return gerar_saida(
                False,
                erro="Redirecionado para login ao acessar /relatorio/itens",
                requer_login=True,
                instrucao="Faca re-login interativo: python -m app.portal.atacadao.login_interativo",
            )

        # 5. Abrir filtros
        if not _abrir_filtros(page):
            screenshot = capturar_screenshot(page, "erro_filtros_relatorio")
            return gerar_saida(
                False,
                erro="Nao foi possivel abrir area de filtros em /relatorio/itens",
                screenshot=screenshot,
            )

        # 6. Filtrar por Unidade
        unidade_texto = _filtrar_unidade(page, cnpj)
        if not unidade_texto:
            screenshot = capturar_screenshot(page, "erro_unidade_relatorio")
            return gerar_saida(
                False,
                erro=f"Nenhuma unidade encontrada para CNPJ {cnpj}",
                cnpj=cnpj,
                screenshot=screenshot,
            )

        # 7. Selecionar datas de agendamento
        if not _selecionar_datas(page, data_de, data_ate):
            # Nao bloquear — tentar sem filtro de data (capturara tudo)
            logger.warning(
                "Nao foi possivel selecionar datas. "
                "Prosseguindo sem filtro de data (pode trazer todos os registros)."
            )

        # 8. Aplicar filtros
        logger.info("Aplicando filtros...")
        page.evaluate("document.querySelector('#enviarFiltros').click()")
        page.wait_for_timeout(3000)

        # 9. Screenshot como evidencia
        screenshot = capturar_screenshot(page, f"relatorio_itens_{cnpj}")

        # 10. Exportar CSV
        csv_path = _exportar_csv(page, CSV_DIR, cnpj)
        if not csv_path:
            return gerar_saida(
                False,
                erro="Falha ao exportar CSV do relatorio",
                cnpj=cnpj,
                unidade=unidade_texto,
                screenshot=screenshot,
            )

        # 11. Parsear CSV
        try:
            registros, encoding, delimitador = _parsear_csv(csv_path)
        except ValueError as e:
            return gerar_saida(
                False,
                erro=str(e),
                csv_path=str(csv_path),
                screenshot=screenshot,
            )

        # 12. Gerar resumo
        resumo = _gerar_resumo(registros)

        # 13. Cruzamento local (opcional)
        cruzamento = None
        if cruzar_local and registros:
            try:
                cruzamento = _cruzar_com_local(registros, cnpj)
                resumo["agendamentos_disponiveis"] = cruzamento["resumo_cruzamento"]["agendamento_disponivel"]
                resumo["agendas_perdidas"] = cruzamento["resumo_cruzamento"]["agenda_perdida"]
                # Substituir registros pelos cruzados
                registros = cruzamento["registros"]
            except Exception as e:
                logger.error(f"Erro no cruzamento local: {e}")
                cruzamento = {"erro": str(e)}

        # 14. Montar resultado
        resultado = {
            "cnpj": cnpj,
            "unidade": unidade_texto,
            "periodo": {
                "de": data_de,
                "ate": data_ate,
                "dias": dias,
            },
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
                resultado["resumo_cruzamento"] = cruzamento["resumo_cruzamento"]
                resultado["total_separacoes_local"] = cruzamento["total_separacoes_local"]
                resultado["total_entregas_local"] = cruzamento["total_entregas_local"]

        # Logar colunas descobertas (util para primeira execucao)
        if registros:
            logger.info(f"Colunas do CSV: {list(registros[0].keys())}")

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
        description="Consulta agendamentos futuros do portal Atacadao (export CSV)"
    )
    parser.add_argument(
        "--cnpj",
        required=True,
        help="CNPJ da unidade (14 digitos, com ou sem formatacao). Ex: 75315333003043",
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=None,
        help=f"Numero de dias futuros para consultar (default: {DIAS_PADRAO})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas preview sem acessar portal",
    )
    parser.add_argument(
        "--cruzar-local",
        action="store_true",
        help="Cruza com Separacao/EntregaMonitorada locais",
    )

    args = parser.parse_args()

    resultado = consultar_agendamentos(
        cnpj=args.cnpj,
        dias=args.dias,
        dry_run=args.dry_run,
        cruzar_local=args.cruzar_local,
    )

    if not resultado.get("sucesso"):
        sys.exit(1)


if __name__ == "__main__":
    main()
