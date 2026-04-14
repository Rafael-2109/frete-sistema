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

        # Phase C (2026-04-14): status_conferencia/valor_considerado lidos
        # via sub.frete (campos migrados para CarviaFrete)
        subcontrato_info = {
            'id': sub.id,
            'cte_numero': sub.cte_numero,
            'cte_valor': float(sub.cte_valor) if sub.cte_valor else None,
            'valor_cotado': float(sub.valor_cotado) if sub.valor_cotado else None,
            'valor_acertado': float(sub.valor_acertado) if sub.valor_acertado else None,
            'valor_final': float(sub.valor_final) if sub.valor_final else None,
            'status': sub.status,
            'status_conferencia': (
                sub.frete.status_conferencia if sub.frete else 'PENDENTE'
            ),
            'valor_considerado': (
                float(sub.frete.valor_considerado)
                if sub.frete and sub.frete.valor_considerado else None
            ),
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

    def registrar_conferencia(self, frete_id: int, valor_considerado: float,
                               status: str, usuario: str,
                               observacoes: str = None,
                               valor_pago: float = None) -> Dict:
        """
        Registra conferencia de um CarviaFrete (unidade de analise — paridade Nacom).

        Paridade Nacom: equivalente a editar_frete com valor_considerado/pago
        (app/fretes/routes.py:editar_frete linhas ~750-900).

        REFATOR D4 (.claude/plans/wobbly-tumbling-treasure.md):
        Quando o conferente decide DIVERGENTE, uma CarviaAprovacaoFrete
        PENDENTE e criada via AprovacaoFreteService, e o frete fica com
        status_conferencia='PENDENTE' + requer_aprovacao=True ate o aprovador
        decidir. APROVADO continua sendo gravado direto (se dentro da tolerancia).

        Args:
            frete_id: ID do CarviaFrete
            valor_considerado: Valor registrado pelo conferente
            status: APROVADO ou DIVERGENTE (decisao inicial)
            usuario: Email do conferente
            observacoes: Texto opcional
            valor_pago: Valor efetivamente pago (opcional)

        Returns:
            Dict com sucesso, status_conferencia, fatura_atualizada,
            fatura_status, tratativa_aberta, aprovacao_id.
        """
        from app.carvia.models import CarviaFrete
        from app.utils.timezone import agora_utc_naive

        if status not in ('APROVADO', 'DIVERGENTE'):
            return {'sucesso': False, 'erro': 'Status deve ser APROVADO ou DIVERGENTE'}

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        if frete.status == 'CANCELADO':
            return {'sucesso': False, 'erro': 'Frete cancelado — sem conferencia'}

        try:
            # Snapshot dos calculos (opcional — usar primary sub como proxy)
            snapshot = None
            primary_sub = frete.subcontratos.first()
            if primary_sub:
                try:
                    resultado = self.calcular_opcoes_conferencia(primary_sub.id)
                    if resultado.get('sucesso'):
                        snapshot = {
                            'opcoes': resultado.get('opcoes', []),
                            'operacao_info': resultado.get('operacao_info'),
                            'conferido_em': str(agora_utc_naive()),
                        }
                except Exception as e:
                    logger.warning(f"Erro ao gerar snapshot frete {frete_id}: {e}")

            frete.valor_considerado = valor_considerado
            if valor_pago is not None:
                frete.valor_pago = valor_pago
            frete.conferido_por = usuario
            frete.conferido_em = agora_utc_naive()
            frete.detalhes_conferencia = snapshot

            if observacoes:
                frete.observacoes = (frete.observacoes or '') + f'\n[Conferencia] {observacoes}'

            # REFATOR D4: roteamento entre APROVADO direto ou abrir tratativa
            from app.carvia.services.documentos.aprovacao_frete_service import (
                AprovacaoFreteService,
            )
            aprov_svc = AprovacaoFreteService()

            tratativa_aberta = False
            aprovacao_id = None

            if status == 'DIVERGENTE':
                frete.status_conferencia = 'PENDENTE'
                resultado_trat = aprov_svc.verificar_e_solicitar_se_necessario(
                    frete_id=frete_id, usuario=usuario,
                )
                if resultado_trat.get('sucesso') and resultado_trat.get('tratativa_aberta'):
                    tratativa_aberta = True
                    aprovacao_id = resultado_trat.get('aprovacao_id')
                else:
                    frete.status_conferencia = 'DIVERGENTE'
            else:  # APROVADO
                resultado_trat = aprov_svc.verificar_e_solicitar_se_necessario(
                    frete_id=frete_id, usuario=usuario,
                )
                if resultado_trat.get('sucesso') and resultado_trat.get('tratativa_aberta'):
                    frete.status_conferencia = 'PENDENTE'
                    tratativa_aberta = True
                    aprovacao_id = resultado_trat.get('aprovacao_id')
                else:
                    frete.status_conferencia = 'APROVADO'

            # Cascade para fatura
            fatura_atualizada = False
            fatura_status = None
            if frete.fatura_transportadora_id:
                fatura_atualizada, fatura_status = self._verificar_fatura_completa(
                    frete.fatura_transportadora_id, usuario,
                )

            db.session.commit()

            logger.info(
                f"Conferencia registrada | frete_id={frete_id} | "
                f"considerado={valor_considerado} | pago={valor_pago} | "
                f"solicitado={status} | final={frete.status_conferencia} | "
                f"tratativa={tratativa_aberta} | usuario={usuario}"
            )

            return {
                'sucesso': True,
                'status_conferencia': frete.status_conferencia,
                'valor_considerado': float(valor_considerado),
                'valor_pago': float(valor_pago) if valor_pago is not None else None,
                'fatura_atualizada': fatura_atualizada,
                'fatura_status': fatura_status,
                'tratativa_aberta': tratativa_aberta,
                'aprovacao_id': aprovacao_id,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar conferencia frete {frete_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _verificar_fatura_completa(self, fatura_id: int, usuario: str):
        """Verifica se todos fretes da fatura foram conferidos.

        Paridade Nacom: itera CarviaFrete (nao Sub).

        Returns:
            Tuple (fatura_atualizada: bool, novo_status: str)
        """
        from app.carvia.models import CarviaFaturaTransportadora, CarviaFrete
        from app.utils.timezone import agora_utc_naive

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return False, None

        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        if not fretes:
            return False, fatura.status_conferencia

        contagem = {'APROVADO': 0, 'DIVERGENTE': 0, 'PENDENTE': 0}
        for f in fretes:
            sc = f.status_conferencia or 'PENDENTE'
            contagem[sc] = contagem.get(sc, 0) + 1

        total = len(fretes)
        status_anterior = fatura.status_conferencia

        if contagem['APROVADO'] == total:
            fatura.status_conferencia = 'CONFERIDO'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
            for f in fretes:
                if f.status == 'FATURADO':
                    f.status = 'CONFERIDO'
        elif contagem['DIVERGENTE'] > 0:
            fatura.status_conferencia = 'DIVERGENTE'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
        elif contagem['APROVADO'] > 0:
            fatura.status_conferencia = 'EM_CONFERENCIA'

        novo_status = fatura.status_conferencia
        atualizado = novo_status != status_anterior

        if atualizado:
            logger.info(
                f"Fatura #{fatura_id}: {status_anterior} → {novo_status} | "
                f"aprovados={contagem['APROVADO']}/{total} "
                f"divergentes={contagem['DIVERGENTE']}/{total}"
            )

        return atualizado, novo_status

    def resumo_conferencia_fatura(self, fatura_id: int) -> Dict:
        """Retorna resumo da conferencia de uma fatura.

        Paridade Nacom: itera CarviaFrete (unidade de analise).

        Returns:
            Dict com total, aprovados, divergentes, pendentes,
            soma_cte_valor, soma_considerado, soma_valor_pago,
            soma_custos_entrega, valor_conferido_total, valor_pago_total.
        """
        from app.carvia.models import CarviaFrete, CarviaCustoEntrega

        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        total = len(fretes)
        aprovados = sum(1 for f in fretes if f.status_conferencia == 'APROVADO')
        divergentes = sum(1 for f in fretes if f.status_conferencia == 'DIVERGENTE')
        pendentes = total - aprovados - divergentes

        soma_cte_valor = sum(float(f.valor_cte or 0) for f in fretes)
        soma_considerado = sum(float(f.valor_considerado or 0) for f in fretes)
        soma_valor_pago = sum(float(f.valor_pago or 0) for f in fretes)

        ces = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_id,
            CarviaCustoEntrega.status != 'CANCELADO',
        ).all()
        soma_custos_entrega = sum(float(ce.valor or 0) for ce in ces)
        total_ces = len(ces)
        valor_conferido_total = soma_considerado + soma_custos_entrega
        valor_pago_total = soma_valor_pago + soma_custos_entrega

        return {
            'total': total,
            'aprovados': aprovados,
            'divergentes': divergentes,
            'pendentes': pendentes,
            'soma_cte_valor': round(soma_cte_valor, 2),
            'soma_considerado': round(soma_considerado, 2),
            'soma_valor_pago': round(soma_valor_pago, 2),
            'soma_custos_entrega': round(soma_custos_entrega, 2),
            'total_ces': total_ces,
            'valor_conferido_total': round(valor_conferido_total, 2),
            'valor_pago_total': round(valor_pago_total, 2),
            'diferenca': round(soma_cte_valor - soma_considerado, 2) if total else None,
            'percentual_conferido': round((aprovados + divergentes) / total * 100) if total else 0,
        }
