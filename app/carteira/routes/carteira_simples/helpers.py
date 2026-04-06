"""
Funcoes auxiliares da Carteira Simplificada

- validar_numero_json: sanitizacao de numeros para JSON (NaN/Infinity)
- converter_entradas_para_frontend: Dict[date, float] → List[Dict] para JS
- atualizar_embarque_item_por_separacao: sync EmbarqueItem ao editar separacao
- calcular_saidas_nao_visiveis: saidas TODAS - FILTRADAS para projecao de estoque
"""

from datetime import date
import logging

from app import db
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem

logger = logging.getLogger(__name__)


def validar_numero_json(valor, padrao, permitir_zero=True):
    """
    Valida um numero para garantir que e JSON-serializavel (nao NaN/Infinity)

    Args:
        valor: Valor a validar
        padrao: Valor padrao caso validacao falhe
        permitir_zero: Se True, aceita 0 como valor valido

    Returns:
        float valido ou valor padrao
    """
    try:
        numero = float(valor) if valor is not None else padrao
        # Verificar se e um numero valido (nao NaN, nao Infinity)
        if numero != numero or numero == float('inf') or numero == float('-inf'):
            return padrao
        # Verificar se e negativo
        if numero < 0:
            return padrao
        # Verificar se e zero quando nao permitido
        if not permitir_zero and numero == 0:
            return padrao
        return numero
    except (ValueError, TypeError, AttributeError):
        return padrao


def converter_entradas_para_frontend(entradas_dict):
    """
    Converte Dict[date, float] para List[Dict[str, Any]] esperado pelo frontend.

    Formato esperado pelo frontend:
    [
        {'data': '2025-01-07', 'qtd': 100.0},
        {'data': '2025-01-08', 'qtd': 200.0}
    ]

    Args:
        entradas_dict: Dict[date, float] retornado por ServicoEstoqueSimples

    Returns:
        List[Dict[str, Any]] no formato esperado pelo frontend
    """
    try:
        if not entradas_dict:
            return []

        programacao = []
        for data_entrada, qtd in entradas_dict.items():
            # Validar data
            if not isinstance(data_entrada, date):
                logger.warning(f"Data invalida ignorada: {data_entrada}")
                continue

            # Validar quantidade
            qtd_validada = validar_numero_json(qtd, 0, permitir_zero=True)

            if qtd_validada > 0:  # So incluir se qtd > 0
                programacao.append({
                    'data': data_entrada.isoformat(),
                    'qtd': qtd_validada
                })

        # Ordenar por data (garantir ordem cronologica)
        programacao.sort(key=lambda x: x['data'])

        return programacao

    except Exception as e:
        logger.error(f"Erro ao converter entradas para frontend: {e}")
        return []


def atualizar_embarque_item_por_separacao(separacao_lote_id):
    """
    Atualiza EmbarqueItem quando uma Separacao do lote e modificada
    Recalcula peso, valor e pallets somando todas as Separacoes do lote

    Args:
        separacao_lote_id: ID do lote de separacao

    Returns:
        bool: True se atualizou, False se nao encontrou EmbarqueItem
    """
    try:
        if not separacao_lote_id:
            return False

        # Buscar EmbarqueItem correspondente (apenas ativos)
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=separacao_lote_id,
            status='ativo'
        ).first()

        if not embarque_item:
            logger.debug(f"[EMBARQUE] Lote {separacao_lote_id} nao esta embarcado")
            return False

        # Buscar TODAS as Separacoes deste lote
        separacoes_lote = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        if not separacoes_lote:
            logger.warning(f"[EMBARQUE] Lote {separacao_lote_id} sem separacoes - zerando EmbarqueItem")
            embarque_item.peso = 0
            embarque_item.valor = 0
            embarque_item.pallets = 0
        else:
            # Recalcular totais somando todas as separacoes do lote
            embarque_item.peso = sum(float(s.peso or 0) for s in separacoes_lote)
            embarque_item.valor = sum(float(s.valor_saldo or 0) for s in separacoes_lote)
            embarque_item.pallets = sum(float(s.pallet or 0) for s in separacoes_lote)

            logger.info(
                f"[EMBARQUE] EmbarqueItem ID={embarque_item.id} atualizado: "
                f"Peso={embarque_item.peso:.2f}, Valor={embarque_item.valor:.2f}, "
                f"Pallets={embarque_item.pallets:.2f} (baseado em {len(separacoes_lote)} separacoes)"
            )

        # Commit das alteracoes (o trigger do banco atualizara o Embarque automaticamente)
        db.session.commit()

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"[EMBARQUE] Erro ao atualizar EmbarqueItem do lote {separacao_lote_id}: {e}", exc_info=True)
        return False


def calcular_saidas_nao_visiveis(
    codigos_produtos,
    separacoes_todas,
    separacoes_filtradas,
    mapa_unificacao=None
):
    """
    Calcula saidas NAO visiveis usando: TODAS - FILTRADAS

    LOGICA:
    1. Recebe separacoes_todas (todas as separacoes dos pedidos da pagina)
    2. Recebe separacoes_filtradas (separacoes que passaram pelos filtros)
    3. Calcula: NAO VISIVEIS = TODAS - FILTRADAS
    4. Agrupa por produto + data

    Args:
        codigos_produtos (list): Lista de codigos de produtos
        separacoes_todas (list): TODAS as separacoes dos pedidos (sem filtros)
        separacoes_filtradas (list): Separacoes FILTRADAS (visiveis)
        mapa_unificacao (dict): Mapa pre-computado {cod: [cod1, cod2, ...]}

    Returns:
        dict: {cod_produto: [{'data': '2025-10-23', 'qtd': 100.0}]}
    """
    try:
        logger.info(f"Calculando saidas NAO visiveis (TODAS - FILTRADAS)...")

        # 1. Criar SET de IDs das separacoes FILTRADAS (visiveis)
        ids_filtradas = set(sep.id for sep in separacoes_filtradas)

        logger.info(f"   Total separacoes: {len(separacoes_todas)}")
        logger.info(f"   Separacoes filtradas (visiveis): {len(ids_filtradas)}")

        # 2. Filtrar separacoes NAO VISIVEIS = TODAS - FILTRADAS
        # Incluir separacoes sem data (expedicao is None) - serao agrupadas em hoje
        separacoes_nao_visiveis = [
            sep for sep in separacoes_todas
            if sep.id not in ids_filtradas
        ]

        logger.info(f"   Separacoes NAO visiveis: {len(separacoes_nao_visiveis)}")

        # 3. Agrupar por produto + data COM UNIFICACAO
        hoje = date.today()
        saidas_por_produto_data = {}

        # Construir lookup reverso ANTES do loop (O(1) por separacao)
        codigo_to_grupo = {}
        if mapa_unificacao:
            for cod, grupo in mapa_unificacao.items():
                for related_cod in grupo:
                    codigo_to_grupo[related_cod] = grupo

        for sep in separacoes_nao_visiveis:
            cod_prod_original = sep.cod_produto
            qtd = float(sep.qtd_saldo or 0)

            if qtd <= 0:
                continue

            # Agrupar separacoes sem data ou atrasadas em hoje
            if not sep.expedicao or sep.expedicao < hoje:
                data_exp = hoje.isoformat()
            else:
                data_exp = sep.expedicao.isoformat()

            # ADICIONAR apenas para o "codigo representante" do grupo (menor codigo)
            # Isso evita duplicacao quando multiplos codigos do mesmo grupo estao na pagina
            if codigo_to_grupo and cod_prod_original in codigo_to_grupo:
                codigos_relacionados = codigo_to_grupo[cod_prod_original]
            else:
                # Fallback: codigo isolado ou mapa nao disponivel
                codigos_relacionados = [cod_prod_original]

            # Encontrar quais codigos do grupo estao na pagina
            codigos_na_pagina = [c for c in codigos_relacionados if c in codigos_produtos]

            if codigos_na_pagina:
                # Usar o MENOR codigo como representante (para consistencia)
                codigo_representante = min(codigos_na_pagina)

                chave = (codigo_representante, data_exp)
                if chave in saidas_por_produto_data:
                    saidas_por_produto_data[chave] += qtd
                else:
                    saidas_por_produto_data[chave] = qtd

        # 4. Converter para formato final
        saidas_consolidadas = {}

        for cod_prod in codigos_produtos:
            saidas_consolidadas[cod_prod] = []

        for (cod_prod, data_exp), qtd in saidas_por_produto_data.items():
            if cod_prod in codigos_produtos:
                saidas_consolidadas[cod_prod].append({
                    'data': data_exp,
                    'qtd': qtd
                })

        # 5. Ordenar por data
        for cod_prod in saidas_consolidadas:
            saidas_consolidadas[cod_prod].sort(key=lambda x: x['data'])

        # Log final
        total_saidas = sum(len(s) for s in saidas_consolidadas.values())
        logger.info(f"Saidas NAO visiveis: {total_saidas} saidas calculadas")

        return saidas_consolidadas

    except Exception as e:
        logger.error(f"Erro ao calcular saidas nao visiveis: {e}", exc_info=True)
        return {cod_prod: [] for cod_prod in codigos_produtos}
