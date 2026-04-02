"""
Conferencia Service — Conferencia de CTe Subcontratado via TabelaFrete
=====================================================================

Permite conferir individualmente cada CTe de subcontratado contra as tabelas
de frete Nacom (TabelaFrete + CidadeAtendida), usando o mesmo fluxo de
calculo da CotacaoService.

Reutiliza (R1 — permitidos por isolamento):
- app/utils/calculadora_frete.py: CalculadoraFrete.calcular_frete_unificado()
- app/utils/tabela_frete_manager.py: TabelaFreteManager.preparar_dados_tabela()
- app/utils/grupo_empresarial.py: GrupoEmpresarialService.obter_transportadoras_grupo()
- app/utils/frete_simulador.py: buscar_cidade_unificada()
- app/vinculos/models.py: CidadeAtendida
"""

import logging
from typing import Dict

from app import db

logger = logging.getLogger(__name__)


class ConferenciaService:
    """Servico de conferencia de CTe subcontratado contra tabelas de frete."""

    def calcular_opcoes_conferencia(self, subcontrato_id: int) -> Dict:
        """
        Calcula TODAS as opcoes de frete para um subcontrato,
        para o conferente comparar com o cte_valor cobrado.

        Fluxo:
        1. Carrega sub + operacao
        2. GrupoEmpresarialService → grupo_ids
        3. buscar_cidade_unificada → codigo_ibge
        4. CidadeAtendida.filter(codigo_ibge, transportadora_id.in_(grupo_ids))
        5. TabelaFrete.filter(grupo_ids, uf_origem, uf_destino, nome_tabela)
        6. CalculadoraFrete.calcular_frete_unificado() para cada tabela
        7. CotacaoService._montar_descritivo() para breakdown legivel

        Args:
            subcontrato_id: ID do CarviaSubcontrato

        Returns:
            Dict com:
            - sucesso: bool
            - subcontrato_info: {id, cte_numero, cte_valor, valor_cotado, valor_final, status}
            - operacao_info: {id, cidade_destino, uf_destino, uf_origem, peso, valor_mercadoria}
            - opcoes: [{tabela_nome, tipo_carga, modalidade, valor_frete, descritivo, ...}]
            - total_opcoes: int
            - erro: str (se falhou)
        """
        from app.carvia.models import CarviaSubcontrato, CarviaOperacao

        sub = db.session.get(CarviaSubcontrato, subcontrato_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        operacao = db.session.get(CarviaOperacao, sub.operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada'}

        # Fallback defensivo: max(bruto, cubado) — consistente com CotacaoService
        peso_bruto = float(operacao.peso_bruto or 0)
        peso_cubado = float(operacao.peso_cubado or 0)
        peso = max(peso_bruto, peso_cubado)
        valor_mercadoria = float(operacao.valor_mercadoria or 0)
        uf_destino = operacao.uf_destino
        uf_origem = operacao.uf_origem
        cidade_destino = operacao.cidade_destino

        if peso <= 0:
            return {'sucesso': False, 'erro': 'Peso nao informado na operacao'}
        if not uf_destino:
            return {'sucesso': False, 'erro': 'UF destino nao informada'}

        subcontrato_info = {
            'id': sub.id,
            'cte_numero': sub.cte_numero,
            'cte_valor': float(sub.cte_valor) if sub.cte_valor else None,
            'valor_cotado': float(sub.valor_cotado) if sub.valor_cotado else None,
            'valor_acertado': float(sub.valor_acertado) if sub.valor_acertado else None,
            'valor_final': float(sub.valor_final) if sub.valor_final else None,
            'status': sub.status,
            'status_conferencia': sub.status_conferencia,
            'valor_considerado': float(sub.valor_considerado) if sub.valor_considerado else None,
        }

        operacao_info = {
            'id': operacao.id,
            'cidade_destino': cidade_destino,
            'uf_destino': uf_destino,
            'uf_origem': uf_origem,
            'peso': peso,
            'valor_mercadoria': valor_mercadoria,
            'nome_cliente': operacao.nome_cliente,
        }

        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao_svc = CotacaoService()

            # Buscar todas opcoes para a transportadora do subcontrato
            opcoes = self._buscar_opcoes_transportadora(
                cotacao_svc, sub.transportadora_id,
                peso, valor_mercadoria,
                uf_destino, uf_origem, cidade_destino,
            )

            return {
                'sucesso': True,
                'subcontrato_info': subcontrato_info,
                'operacao_info': operacao_info,
                'opcoes': opcoes,
                'total_opcoes': len(opcoes),
            }

        except Exception as e:
            logger.error(f"Erro ao calcular opcoes conferencia sub {subcontrato_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _buscar_opcoes_transportadora(self, cotacao_svc, transportadora_id: int,
                                       peso: float, valor_mercadoria: float,
                                       uf_destino: str, uf_origem: str,
                                       cidade_destino: str) -> list:
        """
        Busca todas tabelas de frete para a transportadora do subcontrato
        e calcula frete com cada uma.

        Reutiliza metodos privados da CotacaoService (mesmo modulo CarVia,
        nao viola R1).
        """
        from app.tabelas.models import TabelaFrete
        from app.transportadoras.models import Transportadora

        grupo_ids = cotacao_svc._obter_grupo_transportadora(transportadora_id)
        transportadora = db.session.get(Transportadora, transportadora_id)
        transportadora_nome = transportadora.razao_social if transportadora else '?'

        opcoes = []

        # Resolver cidade para IBGE
        cidade_obj = None
        if cidade_destino:
            cidade_obj = cotacao_svc._resolver_cidade(cidade_destino, uf_destino)

        # Via CidadeAtendida (preciso)
        tabelas_encontradas = {}
        if cidade_obj:
            vinculos = cotacao_svc._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
            for vinculo in vinculos:
                if vinculo.transportadora_id not in grupo_ids:
                    continue

                query = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_destino == uf_destino,
                    TabelaFrete.nome_tabela == vinculo.nome_tabela,
                )
                if uf_origem:
                    query = query.filter(TabelaFrete.uf_origem == uf_origem)

                for tf in query.all():
                    tabelas_encontradas[tf.id] = tf

        # Fallback: busca direta por transportadora + UF
        if not tabelas_encontradas:
            query = TabelaFrete.query.filter(
                TabelaFrete.transportadora_id.in_(grupo_ids),
                TabelaFrete.uf_destino == uf_destino,
            )
            if uf_origem:
                query = query.filter(TabelaFrete.uf_origem == uf_origem)
            for tf in query.all():
                tabelas_encontradas[tf.id] = tf

        # Calcular com cada tabela
        for tabela in tabelas_encontradas.values():
            try:
                resultado = cotacao_svc._calcular_com_tabela(
                    tabela, peso, valor_mercadoria,
                    uf_destino, cidade_destino,
                )
                if not resultado:
                    continue

                tabela_dados = resultado.get('tabela_dados', {})
                detalhes = resultado.get('detalhes', {})
                descritivo = cotacao_svc._montar_descritivo(
                    tabela_dados, detalhes, peso, valor_mercadoria,
                )

                # Buscar transportadora real da tabela
                transp_tabela = db.session.get(Transportadora, tabela.transportadora_id)

                opcoes.append({
                    'tabela_frete_id': tabela.id,
                    'tabela_nome': tabela.nome_tabela,
                    'tipo_carga': tabela.tipo_carga,
                    'modalidade': tabela.modalidade,
                    'transportadora_id': tabela.transportadora_id,
                    'transportadora_nome': (
                        transp_tabela.razao_social if transp_tabela
                        else transportadora_nome
                    ),
                    'valor_frete': round(resultado['valor'], 2),
                    'detalhes': detalhes,
                    'descritivo': descritivo,
                })
            except Exception as e:
                logger.warning(f"Erro ao calcular com tabela {tabela.id}: {e}")
                continue

        # Ordenar por valor
        opcoes.sort(key=lambda x: x['valor_frete'])
        return opcoes

    def registrar_conferencia(self, subcontrato_id: int, valor_considerado: float,
                               status: str, usuario: str,
                               observacoes: str = None) -> Dict:
        """
        Registra conferencia de um subcontrato.

        Args:
            subcontrato_id: ID do CarviaSubcontrato
            valor_considerado: Valor registrado pelo conferente
            status: APROVADO ou DIVERGENTE
            usuario: Email do conferente
            observacoes: Texto opcional

        Returns:
            Dict com sucesso, fatura_atualizada, fatura_status
        """
        from app.carvia.models import CarviaSubcontrato
        from app.utils.timezone import agora_utc_naive

        if status not in ('APROVADO', 'DIVERGENTE'):
            return {'sucesso': False, 'erro': 'Status deve ser APROVADO ou DIVERGENTE'}

        sub = db.session.get(CarviaSubcontrato, subcontrato_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        if sub.status not in ('FATURADO', 'CONFERIDO'):
            return {
                'sucesso': False,
                'erro': f'Subcontrato deve estar FATURADO ou CONFERIDO '
                        f'para conferencia (atual: {sub.status})',
            }

        try:
            # Gravar snapshot dos calculos no momento da conferencia
            snapshot = None
            try:
                resultado = self.calcular_opcoes_conferencia(subcontrato_id)
                if resultado.get('sucesso'):
                    snapshot = {
                        'opcoes': resultado.get('opcoes', []),
                        'operacao_info': resultado.get('operacao_info'),
                        'conferido_em': str(agora_utc_naive()),
                    }
            except Exception as e:
                logger.warning(f"Erro ao gerar snapshot conferencia: {e}")

            sub.valor_considerado = valor_considerado
            sub.status_conferencia = status
            sub.conferido_por = usuario
            sub.conferido_em = agora_utc_naive()
            sub.detalhes_conferencia = snapshot

            if observacoes:
                sub.observacoes = (sub.observacoes or '') + f'\n[Conferencia] {observacoes}'

            # Verificar cascade para fatura
            fatura_atualizada = False
            fatura_status = None
            if sub.fatura_transportadora_id:
                fatura_atualizada, fatura_status = self._verificar_fatura_completa(
                    sub.fatura_transportadora_id, usuario,
                )

            db.session.commit()

            logger.info(
                f"Conferencia registrada | sub_id={subcontrato_id} | "
                f"valor_considerado={valor_considerado} | status={status} | "
                f"usuario={usuario}"
            )

            return {
                'sucesso': True,
                'status_conferencia': status,
                'valor_considerado': float(valor_considerado),
                'fatura_atualizada': fatura_atualizada,
                'fatura_status': fatura_status,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar conferencia sub {subcontrato_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _verificar_fatura_completa(self, fatura_id: int, usuario: str):
        """
        Verifica se todos os subcontratos de uma fatura foram conferidos
        e atualiza o status_conferencia da fatura.

        Returns:
            Tuple (fatura_atualizada: bool, novo_status: str)
        """
        from app.carvia.models import CarviaFaturaTransportadora, CarviaSubcontrato
        from app.utils.timezone import agora_utc_naive

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return False, None

        subs = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.fatura_transportadora_id == fatura_id,
        ).all()

        if not subs:
            return False, fatura.status_conferencia

        contagem = {'APROVADO': 0, 'DIVERGENTE': 0, 'PENDENTE': 0}
        for s in subs:
            sc = s.status_conferencia or 'PENDENTE'
            contagem[sc] = contagem.get(sc, 0) + 1

        total = len(subs)
        status_anterior = fatura.status_conferencia

        if contagem['APROVADO'] == total:
            # Todos aprovados → fatura CONFERIDO + subs CONFERIDO
            fatura.status_conferencia = 'CONFERIDO'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
            for s in subs:
                if s.status == 'FATURADO':
                    s.status = 'CONFERIDO'
        elif contagem['DIVERGENTE'] > 0:
            fatura.status_conferencia = 'DIVERGENTE'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
        elif contagem['APROVADO'] > 0 or contagem['DIVERGENTE'] > 0:
            # Mix de aprovados e pendentes
            fatura.status_conferencia = 'EM_CONFERENCIA'
        # Se todos pendentes, manter status atual

        novo_status = fatura.status_conferencia
        atualizado = novo_status != status_anterior

        if atualizado:
            logger.info(
                f"Fatura transportadora #{fatura_id}: conferencia "
                f"{status_anterior} -> {novo_status} | "
                f"aprovados={contagem['APROVADO']}/{total} "
                f"divergentes={contagem['DIVERGENTE']}/{total}"
            )

        return atualizado, novo_status

    def resumo_conferencia_fatura(self, fatura_id: int) -> Dict:
        """
        Retorna resumo da conferencia de uma fatura.

        Returns:
            Dict com total, aprovados, divergentes, pendentes,
            soma_cte_valor, soma_considerado, diferenca
        """
        from app.carvia.models import CarviaSubcontrato

        subs = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.fatura_transportadora_id == fatura_id,
        ).all()

        total = len(subs)
        aprovados = sum(1 for s in subs if s.status_conferencia == 'APROVADO')
        divergentes = sum(1 for s in subs if s.status_conferencia == 'DIVERGENTE')
        pendentes = total - aprovados - divergentes

        soma_cte_valor = sum(float(s.cte_valor or 0) for s in subs)
        soma_considerado = sum(float(s.valor_considerado or 0) for s in subs if s.valor_considerado)

        return {
            'total': total,
            'aprovados': aprovados,
            'divergentes': divergentes,
            'pendentes': pendentes,
            'soma_cte_valor': round(soma_cte_valor, 2),
            'soma_considerado': round(soma_considerado, 2),
            'diferenca': round(soma_cte_valor - soma_considerado, 2) if soma_considerado else None,
            'percentual_conferido': round((aprovados + divergentes) / total * 100) if total else 0,
        }
