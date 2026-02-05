#!/usr/bin/env python3
"""
Script para consultar frete de pedidos existentes.

Uso:
    python consultar_pedido_frete.py --pedido VCD2565291
    python consultar_pedido_frete.py --separacao SEP-2025-001
    python consultar_pedido_frete.py --nf 144533
    python consultar_pedido_frete.py --pedido VCD2565291 --recalcular
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def consultar_pedido_frete(
    pedido: str = None,
    separacao: str = None,
    nf: str = None,
    recalcular: bool = False
) -> dict:
    """
    Consulta dados de frete de pedidos existentes na CarteiraPrincipal,
    Separacao ou FaturamentoProduto.

    Args:
        pedido: Numero do pedido (VCD/VFB)
        separacao: Lote de separacao
        nf: Numero da NF
        recalcular: Se True, recalcula com tabelas atuais

    Returns:
        dict: {sucesso, fonte, pedidos, frete_recalculado}
    """
    from app import create_app, db
    from sqlalchemy import text

    resultado = {
        'sucesso': False,
        'fonte': None,
        'pedidos': [],
        'total': 0
    }

    if not pedido and not separacao and not nf:
        resultado['erro'] = 'Informe --pedido, --separacao ou --nf'
        return resultado

    app = create_app()
    with app.app_context():
        try:
            if pedido:
                resultado['fonte'] = 'pedido_unificado'
                resultado = _consultar_pedido_unificado(pedido, recalcular, resultado)
            elif separacao:
                resultado['fonte'] = 'separacao'
                resultado = _consultar_separacao(separacao, recalcular, resultado)
            elif nf:
                resultado['fonte'] = 'faturamento'
                resultado = _consultar_faturamento(nf, recalcular, resultado)

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            import traceback
            resultado['traceback'] = traceback.format_exc()
            return resultado


def _consultar_pedido_unificado(pedido: str, recalcular: bool, resultado: dict) -> dict:
    """
    Busca pedido em separacao E carteira simultaneamente.

    Retorna todos os 'contextos' encontrados:
    - Cada separacao_lote_id com sincronizado_nf=False (dados ricos)
    - Saldo remanescente na carteira (se houver parte nao separada)

    O agente usa 'resumo.requer_clarificacao' para decidir se precisa
    perguntar ao usuario qual contexto ele quer.
    """
    from app import db
    from sqlalchemy import text

    contextos = []

    # === 1. Buscar na separacao (dados ricos: codigo_ibge, peso real) ===
    sql_sep = """
        SELECT
            separacao_lote_id,
            num_pedido,
            cnpj_cpf,
            raz_social_red,
            COALESCE(cidade_normalizada, nome_cidade) as cidade,
            COALESCE(uf_normalizada, cod_uf) as uf,
            codigo_ibge,
            SUM(valor_saldo) as valor_total,
            SUM(peso) as peso_total,
            SUM(pallet) as pallet_total,
            expedicao,
            agendamento
        FROM separacao
        WHERE num_pedido ILIKE :pedido
          AND sincronizado_nf = false
          AND qtd_saldo > 0
        GROUP BY separacao_lote_id, num_pedido, cnpj_cpf, raz_social_red,
                 cidade, uf, codigo_ibge, expedicao, agendamento
    """
    rows_sep = db.session.execute(text(sql_sep), {'pedido': f'%{pedido}%'}).fetchall()

    for row in rows_sep:
        contextos.append({
            'tipo': 'separacao',
            'separacao_lote_id': row[0],
            'num_pedido': row[1],
            'cnpj': row[2],
            'cliente': row[3],
            'cidade': row[4],
            'uf': row[5],
            'codigo_ibge': row[6],
            'valor_total': float(row[7]) if row[7] else 0,
            'peso_total': float(row[8]) if row[8] else 0,
            'pallet_total': float(row[9]) if row[9] else 0,
            'expedicao': str(row[10]) if row[10] else None,
            'agendamento': str(row[11]) if row[11] else None,
            'peso_fonte': 'separacao'
        })

    # === 2. Buscar saldo remanescente na carteira ===
    sql_cart = """
        SELECT
            num_pedido,
            cnpj_cpf,
            raz_social_red,
            nome_cidade,
            cod_uf,
            SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_total,
            incoterm,
            data_entrega_pedido
        FROM carteira_principal
        WHERE num_pedido ILIKE :pedido
          AND qtd_saldo_produto_pedido > 0
        GROUP BY num_pedido, cnpj_cpf, raz_social_red, nome_cidade,
                 cod_uf, incoterm, data_entrega_pedido
    """
    rows_cart = db.session.execute(text(sql_cart), {'pedido': f'%{pedido}%'}).fetchall()

    for row in rows_cart:
        info_cart = {
            'tipo': 'carteira',
            'num_pedido': row[0],
            'cnpj': row[1],
            'cliente': row[2],
            'cidade': row[3],
            'uf': row[4],
            'valor_total': float(row[5]) if row[5] else 0,
            'incoterm': row[6],
            'data_entrega': str(row[7]) if row[7] else None,
            'peso_total': 0,
            'peso_fonte': None
        }

        # Buscar peso via palletizacao (carteira nao tem peso direto)
        sql_peso_pall = """
            SELECT COALESCE(SUM(cp.qtd_saldo_produto_pedido * p.peso_bruto), 0)
            FROM carteira_principal cp
            LEFT JOIN cadastro_palletizacao p ON p.cod_produto = cp.cod_produto
            WHERE cp.num_pedido = :pedido
              AND cp.qtd_saldo_produto_pedido > 0
        """
        peso_pall = db.session.execute(text(sql_peso_pall), {'pedido': info_cart['num_pedido']}).fetchone()
        info_cart['peso_total'] = float(peso_pall[0]) if peso_pall and peso_pall[0] else 0
        info_cart['peso_fonte'] = 'palletizacao_estimado'

        contextos.append(info_cart)

    # === 3. Montar resultado ===
    if not contextos:
        resultado['erro'] = f"Pedido '{pedido}' nao encontrado na separacao nem na carteira"
        return resultado

    resultado['sucesso'] = True
    resultado['pedidos'] = contextos
    resultado['total'] = len(contextos)

    # Indicadores para o agente decidir
    tipos = set(c['tipo'] for c in contextos)
    sep_ids = [c['separacao_lote_id'] for c in contextos if c['tipo'] == 'separacao']

    resultado['resumo'] = {
        'tem_separacao': 'separacao' in tipos,
        'tem_carteira': 'carteira' in tipos,
        'qtd_separacoes': len(sep_ids),
        'separacoes': sep_ids,
        'qtd_carteira': sum(1 for c in contextos if c['tipo'] == 'carteira'),
        'requer_clarificacao': len(contextos) > 1
    }

    # Recalcular se solicitado (para todos os contextos)
    if recalcular:
        resultado['frete_recalculado'] = _recalcular_fretes(contextos)

    return resultado


def _consultar_carteira(pedido: str, recalcular: bool, resultado: dict) -> dict:
    """Busca dados de frete na CarteiraPrincipal."""
    from app import db
    from sqlalchemy import text

    sql = """
        SELECT
            num_pedido,
            cnpj_cpf,
            raz_social_red,
            nome_cidade,
            cod_uf,
            SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_total,
            incoterm,
            data_entrega_pedido
        FROM carteira_principal
        WHERE num_pedido ILIKE :pedido
          AND qtd_saldo_produto_pedido > 0
        GROUP BY num_pedido, cnpj_cpf, raz_social_red, nome_cidade,
                 cod_uf, incoterm, data_entrega_pedido
    """

    rows = db.session.execute(text(sql), {'pedido': f'%{pedido}%'}).fetchall()

    if not rows:
        resultado['erro'] = f"Pedido '{pedido}' nao encontrado na carteira com saldo"
        return resultado

    pedidos_info = []
    for row in rows:
        info = {
            'num_pedido': row[0],
            'cnpj': row[1],
            'cliente': row[2],
            'cidade': row[3],
            'uf': row[4],
            'valor_total': float(row[5]) if row[5] else 0,
            'incoterm': row[6],
            'data_entrega': str(row[7]) if row[7] else None
        }
        pedidos_info.append(info)

    # Buscar peso da separacao ou palletizacao
    for info in pedidos_info:
        sql_peso = """
            SELECT COALESCE(SUM(peso), 0) as peso_total
            FROM separacao
            WHERE num_pedido = :pedido
              AND sincronizado_nf = false
              AND qtd_saldo > 0
        """
        peso_row = db.session.execute(text(sql_peso), {'pedido': info['num_pedido']}).fetchone()
        info['peso_total'] = float(peso_row[0]) if peso_row and peso_row[0] else 0

        # Se nao tem peso na separacao, estimar via palletizacao
        if info['peso_total'] == 0:
            sql_peso_pall = """
                SELECT COALESCE(SUM(cp.qtd_saldo_produto_pedido * p.peso_bruto), 0)
                FROM carteira_principal cp
                LEFT JOIN cadastro_palletizacao p ON p.cod_produto = cp.cod_produto
                WHERE cp.num_pedido = :pedido
                  AND cp.qtd_saldo_produto_pedido > 0
            """
            peso_pall = db.session.execute(text(sql_peso_pall), {'pedido': info['num_pedido']}).fetchone()
            info['peso_total'] = float(peso_pall[0]) if peso_pall and peso_pall[0] else 0
            info['peso_fonte'] = 'palletizacao_estimado'
        else:
            info['peso_fonte'] = 'separacao'

    resultado['sucesso'] = True
    resultado['pedidos'] = pedidos_info
    resultado['total'] = len(pedidos_info)

    # Recalcular se solicitado
    if recalcular:
        resultado['frete_recalculado'] = _recalcular_fretes(pedidos_info)

    return resultado


def _consultar_separacao(separacao: str, recalcular: bool, resultado: dict) -> dict:
    """Busca dados de frete na Separacao."""
    from app import db
    from sqlalchemy import text

    sql = """
        SELECT
            separacao_lote_id,
            num_pedido,
            cnpj_cpf,
            raz_social_red,
            COALESCE(cidade_normalizada, nome_cidade) as cidade,
            COALESCE(uf_normalizada, cod_uf) as uf,
            codigo_ibge,
            SUM(valor_saldo) as valor_total,
            SUM(peso) as peso_total,
            SUM(pallet) as pallet_total,
            expedicao,
            agendamento
        FROM separacao
        WHERE (separacao_lote_id ILIKE :sep OR num_pedido ILIKE :sep)
          AND sincronizado_nf = false
          AND qtd_saldo > 0
        GROUP BY separacao_lote_id, num_pedido, cnpj_cpf, raz_social_red,
                 cidade, uf, codigo_ibge, expedicao, agendamento
    """

    rows = db.session.execute(text(sql), {'sep': f'%{separacao}%'}).fetchall()

    if not rows:
        resultado['erro'] = f"Separacao '{separacao}' nao encontrada com saldo ativo"
        return resultado

    pedidos_info = []
    for row in rows:
        info = {
            'separacao_lote_id': row[0],
            'num_pedido': row[1],
            'cnpj': row[2],
            'cliente': row[3],
            'cidade': row[4],
            'uf': row[5],
            'codigo_ibge': row[6],
            'valor_total': float(row[7]) if row[7] else 0,
            'peso_total': float(row[8]) if row[8] else 0,
            'pallet_total': float(row[9]) if row[9] else 0,
            'expedicao': str(row[10]) if row[10] else None,
            'agendamento': str(row[11]) if row[11] else None,
            'peso_fonte': 'separacao'
        }
        pedidos_info.append(info)

    resultado['sucesso'] = True
    resultado['pedidos'] = pedidos_info
    resultado['total'] = len(pedidos_info)

    if recalcular:
        resultado['frete_recalculado'] = _recalcular_fretes(pedidos_info)

    return resultado


def _consultar_faturamento(nf: str, recalcular: bool, resultado: dict) -> dict:
    """Busca dados de frete no FaturamentoProduto."""
    from app import db
    from sqlalchemy import text

    sql = """
        SELECT
            numero_nf,
            cnpj_cliente,
            nome_cliente,
            municipio,
            estado,
            SUM(peso_total) as peso_total,
            SUM(qtd_produto_faturado * preco_produto_faturado) as valor_total,
            data_fatura,
            origem
        FROM faturamento_produto
        WHERE numero_nf ILIKE :nf
        GROUP BY numero_nf, cnpj_cliente, nome_cliente, municipio, estado,
                 data_fatura, origem
    """

    rows = db.session.execute(text(sql), {'nf': f'%{nf}%'}).fetchall()

    if not rows:
        resultado['erro'] = f"NF '{nf}' nao encontrada no faturamento"
        return resultado

    pedidos_info = []
    for row in rows:
        info = {
            'numero_nf': row[0],
            'cnpj': row[1],
            'cliente': row[2],
            'cidade': row[3],
            'uf': row[4],
            'peso_total': float(row[5]) if row[5] else 0,
            'valor_total': float(row[6]) if row[6] else 0,
            'data_fatura': str(row[7]) if row[7] else None,
            'pedido_origem': row[8],
            'peso_fonte': 'faturamento'
        }
        pedidos_info.append(info)

    resultado['sucesso'] = True
    resultado['pedidos'] = pedidos_info
    resultado['total'] = len(pedidos_info)

    if recalcular:
        resultado['frete_recalculado'] = _recalcular_fretes(pedidos_info)

    return resultado


def _recalcular_fretes(pedidos_info: list) -> list:
    """Recalcula fretes para lista de pedidos usando tabelas atuais."""
    from app.utils.frete_simulador import calcular_fretes_possiveis
    from app.localidades.models import Cidade
    from app.utils.string_utils import remover_acentos
    from sqlalchemy import func

    resultados_recalculo = []

    for info in pedidos_info:
        cidade_nome = info.get('cidade', '')
        uf = info.get('uf', '')
        peso = info.get('peso_total', 0)
        valor = info.get('valor_total', 0)
        codigo_ibge = info.get('codigo_ibge')

        if not peso or peso <= 0 or not valor or valor <= 0:
            resultados_recalculo.append({
                'referencia': info.get('num_pedido') or info.get('separacao_lote_id') or info.get('numero_nf'),
                'erro': 'Peso ou valor insuficiente para calculo'
            })
            continue

        # Resolver cidade
        cidade_obj = None
        if codigo_ibge:
            cidade_obj = Cidade.query.filter_by(codigo_ibge=codigo_ibge).first()

        if not cidade_obj and cidade_nome and uf:
            cidade_normalizada = remover_acentos(cidade_nome.strip()).upper()
            cidades_uf = Cidade.query.filter(func.upper(Cidade.uf) == uf.upper()).all()
            for c in cidades_uf:
                if remover_acentos(c.nome.strip()).upper() == cidade_normalizada:
                    cidade_obj = c
                    break

        if not cidade_obj:
            resultados_recalculo.append({
                'referencia': info.get('num_pedido') or info.get('separacao_lote_id') or info.get('numero_nf'),
                'erro': f"Cidade '{cidade_nome}/{uf}' nao encontrada para recalculo"
            })
            continue

        # Calcular fretes
        fretes = calcular_fretes_possiveis(
            cidade_destino_id=cidade_obj.id,
            peso_utilizado=peso,
            valor_carga=valor
        )

        opcoes = []
        for frete in fretes[:5]:  # Top 5
            opcoes.append({
                'transportadora': frete.get('transportadora', ''),
                'nome_tabela': frete.get('nome_tabela', ''),
                'tipo_carga': frete.get('tipo_carga', ''),
                'valor_com_icms': frete.get('valor_total', 0),
                'valor_liquido': frete.get('valor_liquido', 0)
            })

        resultados_recalculo.append({
            'referencia': info.get('num_pedido') or info.get('separacao_lote_id') or info.get('numero_nf'),
            'cidade': cidade_obj.nome,
            'uf': cidade_obj.uf,
            'peso': peso,
            'valor': valor,
            'opcoes': opcoes,
            'total_opcoes': len(opcoes)
        })

    return resultados_recalculo


def main():
    parser = argparse.ArgumentParser(
        description='Consulta frete de pedidos existentes'
    )
    parser.add_argument('--pedido', type=str, default=None,
                        help='Numero do pedido (VCD/VFB)')
    parser.add_argument('--separacao', type=str, default=None,
                        help='Lote de separacao')
    parser.add_argument('--nf', type=str, default=None,
                        help='Numero da NF')
    parser.add_argument('--recalcular', action='store_true',
                        help='Recalcular com tabelas atuais')

    args = parser.parse_args()

    resultado = consultar_pedido_frete(
        pedido=args.pedido,
        separacao=args.separacao,
        nf=args.nf,
        recalcular=args.recalcular
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
