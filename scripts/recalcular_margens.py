"""
Script para recalcular margens de pedidos pendentes.

Busca custo do CustoConsiderado e aplica a nova lógica:
- Margem Bruta: apenas custo_material (sem custo_producao)
- Margem Líquida: inclui custo_producao com perda

Executar uma única vez após a correção da fórmula.

Uso:
    source .venv/bin/activate
    python scripts/recalcular_margens.py
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.custeio.models import CustoFrete, ParametroCusteio, RegraComissao, CustoConsiderado
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def recalcular_margens():
    """
    Recalcula margens de todos os pedidos com saldo pendente.
    """
    resultado = {
        'total_itens': 0,
        'atualizados': 0,
        'sem_custo': 0,
        'erros': []
    }

    try:
        # Buscar parâmetros globais
        percentual_perda = ParametroCusteio.obter_valor('PERCENTUAL_PERDA', 0.0)
        custo_financeiro_percentual = ParametroCusteio.obter_valor('CUSTO_FINANCEIRO_PERCENTUAL', 0.0)
        custo_operacao_percentual = ParametroCusteio.obter_valor('CUSTO_OPERACAO_PERCENTUAL', 0.0)

        logger.info(f"Parâmetros: Perda={percentual_perda}%, Financeiro={custo_financeiro_percentual}%, Operação={custo_operacao_percentual}%")

        # Carregar cache de custos considerados
        logger.info("Carregando custos considerados...")
        custos_cache = {}
        custos = CustoConsiderado.query.filter_by(custo_atual=True).all()
        for c in custos:
            custos_cache[c.cod_produto] = {
                'custo_considerado': float(c.custo_considerado) if c.custo_considerado else 0,
                'custo_producao': float(c.custo_producao) if c.custo_producao else 0
            }
        logger.info(f"Carregados {len(custos_cache)} custos")

        # Buscar itens com saldo pendente
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
        ).all()

        resultado['total_itens'] = len(itens)
        logger.info(f"Encontrados {len(itens)} itens para recalcular")

        for i, item in enumerate(itens):
            try:
                # Verificar se tem preço
                if not item.preco_produto_pedido:
                    resultado['sem_custo'] += 1
                    continue

                preco = float(item.preco_produto_pedido)
                qtd = float(item.qtd_produto_pedido or 1)

                if preco <= 0 or qtd <= 0:
                    resultado['sem_custo'] += 1
                    continue

                # Buscar custo: prioridade snapshot, senão CustoConsiderado
                if item.custo_unitario_snapshot:
                    custo_unitario = float(item.custo_unitario_snapshot)
                    custo_producao = float(item.custo_producao_snapshot) if item.custo_producao_snapshot else 0.0
                else:
                    custo_info = custos_cache.get(item.cod_produto)
                    if not custo_info or not custo_info['custo_considerado']:
                        resultado['sem_custo'] += 1
                        continue
                    custo_unitario = custo_info['custo_considerado']
                    custo_producao = custo_info['custo_producao']

                    # Atualizar snapshot para próximas consultas
                    item.custo_unitario_snapshot = custo_unitario
                    item.custo_producao_snapshot = custo_producao if custo_producao else None

                # Custos com perda (separados)
                custo_material_com_perda = custo_unitario * (1 + percentual_perda / 100)
                custo_producao_com_perda = custo_producao * (1 + percentual_perda / 100) if custo_producao else 0.0

                # Impostos por unidade
                icms_unit = float(item.icms_valor) / qtd if item.icms_valor else 0.0
                pis_unit = float(item.pis_valor) / qtd if item.pis_valor else 0.0
                cofins_unit = float(item.cofins_valor) / qtd if item.cofins_valor else 0.0

                # Frete
                frete_percentual = 0.0
                if item.incoterm and item.cod_uf:
                    frete_percentual = CustoFrete.buscar_percentual_vigente(item.incoterm, item.cod_uf)
                frete_valor = (frete_percentual / 100) * preco

                # Custo financeiro
                custo_financeiro_valor = (custo_financeiro_percentual / 100) * preco

                # Verificar bonificação
                forma_pgto = item.forma_pgto_pedido or ''
                eh_bonificacao = forma_pgto.upper() == 'SEM PAGAMENTO'

                if eh_bonificacao:
                    # Margem bruta bonificação
                    margem_bruta = -custo_material_com_perda - icms_unit - custo_financeiro_valor - frete_valor
                    comissao_percentual = 0.0
                else:
                    # Desconto contratual
                    desconto_valor = (float(item.desconto_percentual) / 100) * preco if item.desconto_percentual else 0.0

                    # Comissão
                    comissao_percentual = RegraComissao.calcular_comissao_total(
                        cnpj=item.cnpj_cpf or '',
                        raz_social_red=item.raz_social_red or '',
                        cod_produto=item.cod_produto or '',
                        cod_uf=item.cod_uf or '',
                        vendedor=item.vendedor or '',
                        equipe=item.equipe_vendas or ''
                    )
                    comissao_valor = (comissao_percentual / 100) * preco

                    # Margem bruta normal (SEM custo_producao)
                    margem_bruta = (preco - icms_unit - pis_unit - cofins_unit -
                                   custo_material_com_perda - desconto_valor -
                                   frete_valor - custo_financeiro_valor - comissao_valor)

                margem_bruta_percentual = (margem_bruta / preco * 100) if preco > 0 else 0.0

                # Custo operação
                custo_operacao_valor = (custo_operacao_percentual / 100) * preco

                # Margem líquida (COM custo_producao)
                margem_liquida = margem_bruta - custo_operacao_valor - custo_producao_com_perda
                margem_liquida_percentual = (margem_liquida / preco * 100) if preco > 0 else 0.0

                # Atualizar item
                item.margem_bruta = round(margem_bruta, 2)
                item.margem_bruta_percentual = round(margem_bruta_percentual, 2)
                item.margem_liquida = round(margem_liquida, 2)
                item.margem_liquida_percentual = round(margem_liquida_percentual, 2)
                item.comissao_percentual = round(comissao_percentual, 2)

                resultado['atualizados'] += 1

                # Log a cada 100 itens
                if (i + 1) % 100 == 0:
                    logger.info(f"Processados {i + 1}/{len(itens)} itens...")

            except Exception as e:
                resultado['erros'].append(f"{item.num_pedido}/{item.cod_produto}: {str(e)}")

        db.session.commit()

        logger.info("=" * 60)
        logger.info("RECÁLCULO CONCLUÍDO")
        logger.info("=" * 60)
        logger.info(f"Total de itens: {resultado['total_itens']}")
        logger.info(f"Atualizados: {resultado['atualizados']}")
        logger.info(f"Sem custo: {resultado['sem_custo']}")
        logger.info(f"Erros: {len(resultado['erros'])}")

        if resultado['erros']:
            logger.warning("Erros encontrados:")
            for erro in resultado['erros'][:10]:  # Mostrar só os 10 primeiros
                logger.warning(f"  - {erro}")
            if len(resultado['erros']) > 10:
                logger.warning(f"  ... e mais {len(resultado['erros']) - 10} erros")

        return resultado

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro fatal no recálculo: {e}")
        raise


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        recalcular_margens()
