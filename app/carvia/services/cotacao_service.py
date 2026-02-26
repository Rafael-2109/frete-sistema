"""
Cotacao Service — Wrapper de CalculadoraFrete para CarVia
==========================================================

Reutiliza:
- app/utils/calculadora_frete.py: CalculadoraFrete.calcular_frete_unificado()
- app/utils/frete_simulador.py: calcular_fretes_possiveis()
- app/utils/tabela_frete_manager.py: TabelaFreteManager

Fluxo por subcontrato:
1. Buscar peso_utilizado da operacao pai
2. Resolver cidade destino -> Cidade (localidades)
3. Buscar tabelas_frete para a transportadora + UF/cidade
4. Chamar CalculadoraFrete.calcular_frete_unificado()
5. Gravar valor_cotado e tabela_frete_id no subcontrato
"""

import logging
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class CotacaoService:
    """Servico de cotacao de frete para subcontratos CarVia"""

    def cotar_subcontrato(self, operacao_id: int,
                          transportadora_id: int) -> Dict:
        """
        Calcula cotacao de frete para um subcontrato.

        Args:
            operacao_id: ID da operacao CarVia
            transportadora_id: ID da transportadora subcontratada

        Returns:
            Dict com resultado da cotacao:
            - sucesso: bool
            - valor_cotado: float
            - tabela_frete_id: int
            - detalhes: dict com breakdown do calculo
            - erro: str (se falhou)
        """
        from app.carvia.models import CarviaOperacao
        from app.transportadoras.models import Transportadora

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada'}

        transportadora = db.session.get(Transportadora, transportadora_id)
        if not transportadora:
            return {'sucesso': False, 'erro': 'Transportadora nao encontrada'}

        peso = float(operacao.peso_utilizado or operacao.peso_bruto or 0)
        valor_mercadoria = float(operacao.valor_mercadoria or 0)
        uf_destino = operacao.uf_destino
        cidade_destino = operacao.cidade_destino

        if peso <= 0:
            return {'sucesso': False, 'erro': 'Peso nao informado na operacao'}

        if not uf_destino:
            return {'sucesso': False, 'erro': 'UF destino nao informada'}

        try:
            # Buscar tabelas de frete da transportadora para o destino
            from app.tabelas.models import TabelaFrete
            tabelas = db.session.query(TabelaFrete).filter(
                TabelaFrete.transportadora_id == transportadora_id,
                TabelaFrete.uf_destino == uf_destino,
                TabelaFrete.ativo == True,  # noqa: E712
            ).all()

            if not tabelas:
                return {
                    'sucesso': False,
                    'erro': f'Nenhuma tabela de frete ativa para '
                            f'{transportadora.razao_social} -> {uf_destino}',
                }

            # Tentar calcular com cada tabela e retornar a melhor
            melhor = None
            for tabela in tabelas:
                try:
                    resultado = self._calcular_com_tabela(
                        tabela, peso, valor_mercadoria, uf_destino, cidade_destino
                    )
                    if resultado and (melhor is None or resultado['valor'] < melhor['valor']):
                        melhor = resultado
                        melhor['tabela_frete_id'] = tabela.id
                        melhor['tabela_nome'] = tabela.nome_tabela
                except Exception as e:
                    logger.warning(f"Erro ao calcular com tabela {tabela.id}: {e}")
                    continue

            if melhor:
                return {
                    'sucesso': True,
                    'valor_cotado': round(melhor['valor'], 2),
                    'tabela_frete_id': melhor['tabela_frete_id'],
                    'tabela_nome': melhor.get('tabela_nome'),
                    'detalhes': melhor.get('detalhes', {}),
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma tabela conseguiu calcular o frete',
                }

        except Exception as e:
            logger.error(f"Erro na cotacao: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _calcular_com_tabela(self, tabela, peso: float,
                              valor_mercadoria: float,
                              uf_destino: str,
                              cidade_destino: str) -> Optional[Dict]:
        """Calcula frete usando uma tabela especifica"""
        try:
            from app.utils.calculadora_frete import CalculadoraFrete

            calc = CalculadoraFrete()

            # Preparar dados da tabela no formato esperado
            tabela_dados = {
                'valor_kg': float(tabela.valor_kg or 0),
                'percentual_valor': float(tabela.percentual_valor or 0),
                'frete_minimo_valor': float(tabela.frete_minimo_valor or 0),
                'frete_minimo_peso': float(tabela.frete_minimo_peso or 0),
                'icms': float(tabela.icms or 0),
                'percentual_gris': float(tabela.percentual_gris or 0),
                'pedagio_por_100kg': float(tabela.pedagio_por_100kg or 0),
                'valor_tas': float(tabela.valor_tas or 0),
                'percentual_adv': float(tabela.percentual_adv or 0),
                'percentual_rca': float(tabela.percentual_rca or 0),
                'valor_despacho': float(tabela.valor_despacho or 0),
                'valor_cte': float(tabela.valor_cte or 0),
                'icms_incluso': bool(tabela.icms_incluso),
            }

            resultado = calc.calcular_frete_unificado(
                peso=peso,
                valor_nf=valor_mercadoria,
                tabela_dados=tabela_dados,
            )

            if resultado and 'valor_total' in resultado:
                return {
                    'valor': resultado['valor_total'],
                    'detalhes': resultado,
                }

            return None
        except Exception as e:
            logger.warning(f"Erro ao calcular frete: {e}")
            return None

    def listar_opcoes_transportadora(self, uf_destino: str,
                                      cidade_destino: str = None) -> List[Dict]:
        """
        Lista transportadoras com tabelas ativas para o destino.

        Returns:
            Lista de dicts com transportadora_id, nome, tem_tabela
        """
        try:
            from app.transportadoras.models import Transportadora
            from app.tabelas.models import TabelaFrete

            # Buscar transportadoras que tem tabela para a UF
            subquery = db.session.query(
                TabelaFrete.transportadora_id
            ).filter(
                TabelaFrete.uf_destino == uf_destino,
                TabelaFrete.ativo == True,  # noqa: E712
            ).distinct().subquery()

            transportadoras = db.session.query(Transportadora).filter(
                Transportadora.id.in_(subquery),
                Transportadora.ativo == True,  # noqa: E712
            ).order_by(Transportadora.razao_social).all()

            return [{
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
                'freteiro': t.freteiro,
            } for t in transportadoras]

        except Exception as e:
            logger.error(f"Erro ao listar opcoes: {e}")
            return []
