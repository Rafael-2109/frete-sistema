"""
Serviços de ETL e processamento para o módulo BI
"""
from app import db
from app.bi.models import (
    BiFreteAgregado, BiDespesaDetalhada, 
    BiPerformanceTransportadora, BiAnaliseRegional,
    BiIndicadorMensal, get_regiao_by_uf
)
from app.bi.services_helpers import BiCalculosReais
from app.fretes.models import Frete, DespesaExtra, ContaCorrenteTransportadora
from app.transportadoras.models import Transportadora
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, case, distinct
import logging

logger = logging.getLogger(__name__)

class BiETLService:
    """Serviço de ETL para popular as tabelas do BI"""
    
    @staticmethod
    def processar_frete_agregado(data_inicio=None, data_fim=None):
        """
        Processa e agrega dados de fretes para a tabela bi_frete_agregado
        """
        try:
            # Define período padrão (último mês) se não especificado
            if not data_fim:
                data_fim = date.today()
            if not data_inicio:
                data_inicio = data_fim - timedelta(days=30)
            
            logger.info(f"Processando fretes de {data_inicio} até {data_fim}")
            
            # Query otimizada para agregação
            query = db.session.query(
                func.date(Frete.criado_em).label('data_referencia'),
                Frete.transportadora_id,
                Frete.cnpj_cliente,
                Frete.nome_cliente,
                Frete.uf_destino,
                Frete.cidade_destino,
                Frete.tipo_carga,
                Frete.modalidade,
                func.count(distinct(Frete.id)).label('qtd_fretes'),
                func.count(distinct(Frete.numero_cte)).label('qtd_ctes'),
                func.sum(Frete.peso_total).label('peso_total'),
                func.sum(Frete.valor_total_nfs).label('valor_faturado'),
                func.sum(Frete.valor_cotado).label('valor_cotado'),
                func.sum(Frete.valor_cte).label('valor_cte'),
                func.sum(Frete.valor_considerado).label('valor_considerado'),
                func.sum(Frete.valor_pago).label('valor_pago'),
                func.sum(case((Frete.status == 'APROVADO', 1), else_=0)).label('qtd_aprovacoes'),
                func.sum(case((Frete.status == 'REJEITADO', 1), else_=0)).label('qtd_rejeicoes'),
                func.sum(case((Frete.status == 'EM_TRATATIVA', 1), else_=0)).label('qtd_em_tratativa')
            ).join(
                Transportadora, Transportadora.id == Frete.transportadora_id
            ).filter(
                and_(
                    func.date(Frete.criado_em) >= data_inicio,
                    func.date(Frete.criado_em) <= data_fim,
                    Frete.status != 'CANCELADO'
                )
            ).group_by(
                func.date(Frete.criado_em),
                Frete.transportadora_id,
                Frete.cnpj_cliente,
                Frete.nome_cliente,
                Frete.uf_destino,
                Frete.cidade_destino,
                Frete.tipo_carga,
                Frete.modalidade
            )
            
            resultados = query.all()
            
            for r in resultados:
                # Busca dados complementares
                transportadora = db.session.get(Transportadora,r.transportadora_id) if r.transportadora_id else None
                
                # Calcula despesas extras
                despesas = db.session.query(
                    func.count(DespesaExtra.id).label('qtd'),
                    func.sum(DespesaExtra.valor_despesa).label('total'),
                    func.sum(case((DespesaExtra.tipo_despesa == 'REENTREGA', DespesaExtra.valor_despesa), else_=0)).label('reentrega'),
                    func.sum(case((DespesaExtra.tipo_despesa == 'TDE', DespesaExtra.valor_despesa), else_=0)).label('tde'),
                    func.sum(case((DespesaExtra.tipo_despesa == 'DEVOLUÇÃO', DespesaExtra.valor_despesa), else_=0)).label('devolucao'),
                    func.sum(case((DespesaExtra.tipo_despesa == 'COMPLEMENTO DE FRETE', DespesaExtra.valor_despesa), else_=0)).label('complemento')
                ).join(
                    Frete, Frete.id == DespesaExtra.frete_id
                ).filter(
                    and_(
                        func.date(Frete.criado_em) == r.data_referencia,
                        Frete.transportadora_id == r.transportadora_id,
                        Frete.cnpj_cliente == r.cnpj_cliente
                    )
                ).first()
                
                # Verifica se já existe registro
                bi_frete = BiFreteAgregado.query.filter_by(
                    data_referencia=r.data_referencia,
                    transportadora_id=r.transportadora_id,
                    cliente_cnpj=r.cnpj_cliente,
                    destino_uf=r.uf_destino,
                    destino_cidade=r.cidade_destino
                ).first()
                
                if not bi_frete:
                    bi_frete = BiFreteAgregado()
                
                # Popula campos
                bi_frete.data_referencia = r.data_referencia
                bi_frete.ano = r.data_referencia.year
                bi_frete.mes = r.data_referencia.month
                bi_frete.trimestre = (r.data_referencia.month - 1) // 3 + 1
                bi_frete.semana_ano = r.data_referencia.isocalendar()[1]
                bi_frete.dia_semana = r.data_referencia.weekday()
                
                # Transportadora
                bi_frete.transportadora_id = r.transportadora_id
                bi_frete.transportadora_nome = transportadora.razao_social if transportadora else None
                bi_frete.transportadora_cnpj = transportadora.cnpj if transportadora else None
                bi_frete.transportadora_uf = transportadora.uf if transportadora else None
                bi_frete.transportadora_optante = transportadora.optante if transportadora else False
                
                # Cliente
                bi_frete.cliente_cnpj = r.cnpj_cliente
                bi_frete.cliente_nome = r.nome_cliente
                bi_frete.destino_uf = r.uf_destino
                bi_frete.destino_cidade = r.cidade_destino
                bi_frete.destino_regiao = get_regiao_by_uf(r.uf_destino)
                
                # Carga
                bi_frete.tipo_carga = r.tipo_carga
                bi_frete.modalidade = r.modalidade
                
                # Volumes
                bi_frete.qtd_embarques = r.qtd_fretes
                bi_frete.qtd_ctes = r.qtd_ctes
                bi_frete.peso_total_kg = float(r.peso_total or 0)
                bi_frete.valor_total_nf = float(r.valor_faturado or 0)
                
                # Valores
                bi_frete.valor_cotado_total = float(r.valor_cotado or 0)
                bi_frete.valor_cte_total = float(r.valor_cte or 0)
                bi_frete.valor_considerado_total = float(r.valor_considerado or 0)
                bi_frete.valor_pago_total = float(r.valor_pago or 0)
                
                # Despesas extras
                if despesas:
                    bi_frete.qtd_despesas_extras = despesas.qtd or 0
                    bi_frete.valor_despesas_extras = float(despesas.total or 0)
                    bi_frete.valor_reentrega = float(despesas.reentrega or 0)
                    bi_frete.valor_tde = float(despesas.tde or 0)
                    bi_frete.valor_devolucao = float(despesas.devolucao or 0)
                    bi_frete.valor_complemento = float(despesas.complemento or 0)
                
                # Divergências
                bi_frete.divergencia_cotado_cte = bi_frete.valor_cte_total - bi_frete.valor_cotado_total
                bi_frete.divergencia_considerado_pago = bi_frete.valor_pago_total - bi_frete.valor_considerado_total
                bi_frete.qtd_aprovacoes = r.qtd_aprovacoes or 0
                bi_frete.qtd_rejeicoes = r.qtd_rejeicoes or 0
                bi_frete.qtd_em_tratativa = r.qtd_em_tratativa or 0
                
                # KPIs calculados
                if bi_frete.peso_total_kg > 0:
                    bi_frete.custo_por_kg = bi_frete.valor_pago_total / bi_frete.peso_total_kg
                
                if bi_frete.valor_total_nf > 0:
                    bi_frete.custo_por_real_faturado = bi_frete.valor_pago_total / bi_frete.valor_total_nf
                
                if bi_frete.valor_pago_total > 0:
                    bi_frete.percentual_despesa_extra = (bi_frete.valor_despesas_extras / bi_frete.valor_pago_total) * 100
                
                if bi_frete.valor_cotado_total > 0:
                    bi_frete.percentual_divergencia = abs(bi_frete.divergencia_cotado_cte / bi_frete.valor_cotado_total) * 100

                # Calcula lead time médio real
                bi_frete.lead_time_medio = BiCalculosReais.calcular_lead_time(
                    r.data_referencia, r.data_referencia, r.transportadora_id, r.uf_destino
                )

                # Calcula distância aproximada
                bi_frete.distancia_km = BiCalculosReais.calcular_distancia_aproximada('SP', r.uf_destino)

                # Calcula custo por km se houver distância
                if bi_frete.distancia_km and bi_frete.distancia_km > 0:
                    bi_frete.custo_por_km = bi_frete.valor_pago_total / bi_frete.distancia_km

                bi_frete.processado_em = datetime.now()
                bi_frete.versao_etl = '2.0'
                
                db.session.add(bi_frete)
            
            db.session.commit()
            logger.info(f"Processados {len(resultados)} registros de frete agregado")
            return True
            
        except Exception as e:
            logger.error(f"Erro no ETL de frete agregado: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def processar_despesas_detalhadas(data_inicio=None, data_fim=None):
        """
        Processa análise detalhada de despesas extras
        """
        try:
            if not data_fim:
                data_fim = date.today()
            if not data_inicio:
                data_inicio = data_fim - timedelta(days=30)
            
            # Agregação de despesas por tipo/setor/motivo
            query = db.session.query(
                func.date(DespesaExtra.criado_em).label('data_referencia'),
                DespesaExtra.tipo_despesa,
                DespesaExtra.setor_responsavel,
                DespesaExtra.motivo_despesa,
                Frete.transportadora_id,
                Frete.cnpj_cliente,
                Frete.nome_cliente,
                Frete.uf_destino,
                Frete.cidade_destino,
                func.count(DespesaExtra.id).label('qtd'),
                func.sum(DespesaExtra.valor_despesa).label('total'),
                func.avg(DespesaExtra.valor_despesa).label('media'),
                func.min(DespesaExtra.valor_despesa).label('minimo'),
                func.max(DespesaExtra.valor_despesa).label('maximo')
            ).join(
                Frete, Frete.id == DespesaExtra.frete_id
            ).filter(
                and_(
                    func.date(DespesaExtra.criado_em) >= data_inicio,
                    func.date(DespesaExtra.criado_em) <= data_fim
                )
            ).group_by(
                func.date(DespesaExtra.criado_em),
                DespesaExtra.tipo_despesa,
                DespesaExtra.setor_responsavel,
                DespesaExtra.motivo_despesa,
                Frete.transportadora_id,
                Frete.cnpj_cliente,
                Frete.nome_cliente,
                Frete.uf_destino,
                Frete.cidade_destino
            )
            
            resultados = query.all()
            
            for r in resultados:
                transportadora = db.session.get(Transportadora,r.transportadora_id) if r.transportadora_id else None
                
                # Verifica se já existe
                bi_despesa = BiDespesaDetalhada.query.filter_by(
                    data_referencia=r.data_referencia,
                    tipo_despesa=r.tipo_despesa,
                    setor_responsavel=r.setor_responsavel,
                    motivo_despesa=r.motivo_despesa,
                    transportadora_id=r.transportadora_id,
                    cliente_cnpj=r.cnpj_cliente
                ).first()
                
                if not bi_despesa:
                    bi_despesa = BiDespesaDetalhada()
                
                # Popula campos
                bi_despesa.data_referencia = r.data_referencia
                bi_despesa.ano = r.data_referencia.year
                bi_despesa.mes = r.data_referencia.month
                
                bi_despesa.tipo_despesa = r.tipo_despesa
                bi_despesa.setor_responsavel = r.setor_responsavel
                bi_despesa.motivo_despesa = r.motivo_despesa
                
                bi_despesa.transportadora_id = r.transportadora_id
                bi_despesa.transportadora_nome = transportadora.razao_social if transportadora else None
                bi_despesa.cliente_cnpj = r.cnpj_cliente
                bi_despesa.cliente_nome = r.nome_cliente
                bi_despesa.destino_uf = r.uf_destino
                bi_despesa.destino_cidade = r.cidade_destino
                
                bi_despesa.qtd_ocorrencias = r.qtd
                bi_despesa.valor_total = float(r.total or 0)
                bi_despesa.valor_medio = float(r.media or 0)
                bi_despesa.valor_minimo = float(r.minimo or 0)
                bi_despesa.valor_maximo = float(r.maximo or 0)
                
                # Calcula tendência real
                periodo_atual = (r.data_referencia, r.data_referencia)
                periodo_anterior = (r.data_referencia - timedelta(days=30), r.data_referencia - timedelta(days=1))
                bi_despesa.tendencia = BiCalculosReais.analisar_tendencia(
                    r.tipo_despesa, r.setor_responsavel, periodo_atual, periodo_anterior
                )
                
                bi_despesa.processado_em = datetime.now()
                
                db.session.add(bi_despesa)
            
            db.session.commit()
            logger.info(f"Processados {len(resultados)} registros de despesas detalhadas")
            return True
            
        except Exception as e:
            logger.error(f"Erro no ETL de despesas: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def calcular_performance_transportadora(mes=None, ano=None):
        """
        Calcula performance mensal das transportadoras
        """
        try:
            if not ano:
                ano = date.today().year
            if not mes:
                mes = date.today().month
            
            periodo_inicio = date(ano, mes, 1)
            if mes == 12:
                periodo_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                periodo_fim = date(ano, mes + 1, 1) - timedelta(days=1)
            
            # Busca todas transportadoras ativas
            transportadoras = Transportadora.query.filter_by(ativo=True).all()
            
            for transp in transportadoras:
                # Busca ou cria registro
                bi_perf = BiPerformanceTransportadora.query.filter_by(
                    transportadora_id=transp.id,
                    periodo_inicio=periodo_inicio,
                    periodo_fim=periodo_fim,
                    tipo_periodo='MENSAL'
                ).first()
                
                if not bi_perf:
                    bi_perf = BiPerformanceTransportadora()
                    bi_perf.transportadora_id = transp.id
                    bi_perf.periodo_inicio = periodo_inicio
                    bi_perf.periodo_fim = periodo_fim
                    bi_perf.tipo_periodo = 'MENSAL'
                
                bi_perf.transportadora_nome = transp.razao_social
                bi_perf.transportadora_cnpj = transp.cnpj
                
                # Calcula métricas de volume
                fretes = Frete.query.filter(
                    and_(
                        Frete.transportadora_id == transp.id,
                        func.date(Frete.criado_em) >= periodo_inicio,
                        func.date(Frete.criado_em) <= periodo_fim,
                        Frete.status != 'CANCELADO'
                    )
                ).all()
                
                bi_perf.total_embarques = len(fretes)
                bi_perf.total_nfs = sum(f.quantidade_nfs or 0 for f in fretes)
                bi_perf.total_peso_kg = sum(f.peso_total or 0 for f in fretes)
                bi_perf.total_valor_faturado = sum(f.valor_total_nfs or 0 for f in fretes)
                
                # Calcula valores
                bi_perf.valor_total_frete = sum(f.valor_pago or 0 for f in fretes)
                
                # Calcula despesas extras
                despesas = DespesaExtra.query.join(
                    Frete, Frete.id == DespesaExtra.frete_id
                ).filter(
                    and_(
                        Frete.transportadora_id == transp.id,
                        func.date(DespesaExtra.criado_em) >= periodo_inicio,
                        func.date(DespesaExtra.criado_em) <= periodo_fim
                    )
                ).all()
                
                bi_perf.valor_total_despesas = sum(d.valor_despesa or 0 for d in despesas)
                
                # Calcula médias
                if bi_perf.total_peso_kg > 0:
                    bi_perf.custo_medio_por_kg = bi_perf.valor_total_frete / bi_perf.total_peso_kg
                
                if bi_perf.total_nfs > 0:
                    bi_perf.custo_medio_por_nf = bi_perf.valor_total_frete / bi_perf.total_nfs
                
                # Calcula conta corrente
                conta_corrente = ContaCorrenteTransportadora.query.filter(
                    and_(
                        ContaCorrenteTransportadora.transportadora_id == transp.id,
                        ContaCorrenteTransportadora.status == 'ATIVO'
                    )
                ).all()
                
                bi_perf.saldo_conta_corrente = sum(
                    cc.valor_credito - cc.valor_debito for cc in conta_corrente
                )
                bi_perf.qtd_creditos = sum(1 for cc in conta_corrente if cc.valor_credito > 0)
                bi_perf.qtd_debitos = sum(1 for cc in conta_corrente if cc.valor_debito > 0)
                
                # Calcula qualidade
                if bi_perf.total_embarques > 0:
                    bi_perf.percentual_com_despesa_extra = (len(despesas) / bi_perf.total_embarques) * 100
                
                # Score de qualidade REAL usando o helper
                bi_perf.score_qualidade = BiCalculosReais.calcular_score_transportadora(
                    transp.id, periodo_inicio, periodo_fim
                )

                # Calcula percentual de entregas no prazo
                bi_perf.percentual_entregas_prazo = BiCalculosReais.calcular_percentual_no_prazo(
                    transp.id, periodo_inicio, periodo_fim
                )
                
                bi_perf.calculado_em = datetime.now()
                
                db.session.add(bi_perf)
            
            # Calcula rankings
            db.session.flush()
            
            todas_perf = BiPerformanceTransportadora.query.filter_by(
                periodo_inicio=periodo_inicio,
                periodo_fim=periodo_fim,
                tipo_periodo='MENSAL'
            ).order_by(BiPerformanceTransportadora.custo_medio_por_kg.asc()).all()
            
            for idx, perf in enumerate(todas_perf, 1):
                perf.ranking_custo = idx
            
            db.session.commit()
            logger.info(f"Calculada performance para {len(transportadoras)} transportadoras")
            return True
            
        except Exception as e:
            logger.error(f"Erro no cálculo de performance: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def processar_analise_regional(data_inicio=None, data_fim=None):
        """
        Processa análise regional de custos e performance
        """
        try:
            if not data_fim:
                data_fim = date.today()
            if not data_inicio:
                data_inicio = data_fim - timedelta(days=30)

            logger.info(f"Processando análise regional de {data_inicio} até {data_fim}")

            # Query para agregar dados por região/UF/cidade
            query = db.session.query(
                Frete.uf_destino,
                Frete.cidade_destino,
                func.count(distinct(Frete.id)).label('qtd_entregas'),
                func.sum(Frete.peso_total).label('peso_total'),
                func.sum(Frete.valor_total_nfs).label('valor_faturado'),
                func.sum(Frete.valor_pago).label('custo_total'),
                func.avg(Frete.valor_pago / func.nullif(Frete.peso_total, 0)).label('custo_medio_kg'),
                func.count(distinct(Frete.transportadora_id)).label('qtd_transportadoras')
            ).filter(
                and_(
                    func.date(Frete.criado_em) >= data_inicio,
                    func.date(Frete.criado_em) <= data_fim,
                    Frete.status != 'CANCELADO'
                )
            ).group_by(
                Frete.uf_destino,
                Frete.cidade_destino
            )

            resultados = query.all()

            for r in resultados:
                # Verifica se já existe registro
                bi_regional = BiAnaliseRegional.query.filter_by(
                    data_referencia=data_fim,
                    uf=r.uf_destino,
                    cidade=r.cidade_destino
                ).first()

                if not bi_regional:
                    bi_regional = BiAnaliseRegional()

                # Popula campos
                bi_regional.data_referencia = data_fim
                bi_regional.ano = data_fim.year
                bi_regional.mes = data_fim.month
                bi_regional.regiao = get_regiao_by_uf(r.uf_destino)
                bi_regional.uf = r.uf_destino
                bi_regional.cidade = r.cidade_destino

                # Volumes e custos
                bi_regional.qtd_entregas = r.qtd_entregas or 0
                bi_regional.peso_total_kg = float(r.peso_total or 0)
                bi_regional.valor_total_faturado = float(r.valor_faturado or 0)
                bi_regional.custo_total_frete = float(r.custo_total or 0)
                bi_regional.custo_medio_por_kg = float(r.custo_medio_kg or 0)

                if bi_regional.qtd_entregas > 0:
                    bi_regional.custo_medio_por_entrega = bi_regional.custo_total_frete / bi_regional.qtd_entregas

                # Transportadoras
                bi_regional.qtd_transportadoras_ativas = r.qtd_transportadoras or 0

                # Identifica transportadora principal
                transp_principal = BiCalculosReais.identificar_transportadora_principal(
                    r.uf_destino, data_inicio, data_fim
                )
                if transp_principal:
                    bi_regional.transportadora_principal_id = transp_principal['id']
                    bi_regional.transportadora_principal_nome = transp_principal['nome']
                    if bi_regional.peso_total_kg > 0:
                        bi_regional.percentual_transportadora_principal = (
                            transp_principal['peso_total'] / bi_regional.peso_total_kg * 100
                        )

                # Lead time médio
                bi_regional.lead_time_medio = BiCalculosReais.calcular_lead_time(
                    data_inicio, data_fim, uf_destino=r.uf_destino
                )

                # TODO: Calcular percentual no prazo e com problema
                bi_regional.percentual_no_prazo = 95.0  # Placeholder
                bi_regional.percentual_com_problema = 5.0  # Placeholder

                bi_regional.processado_em = datetime.now()

                db.session.add(bi_regional)

            db.session.commit()
            logger.info(f"Processados {len(resultados)} registros de análise regional")
            return True

        except Exception as e:
            logger.error(f"Erro no ETL de análise regional: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def processar_indicadores_mensais(mes=None, ano=None):
        """
        Processa indicadores mensais consolidados
        """
        try:
            if not ano:
                ano = date.today().year
            if not mes:
                mes = date.today().month

            periodo_inicio = date(ano, mes, 1)
            if mes == 12:
                periodo_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                periodo_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            logger.info(f"Processando indicadores mensais de {mes}/{ano}")

            # Verifica se já existe
            bi_indicador = BiIndicadorMensal.query.filter_by(ano=ano, mes=mes).first()

            if not bi_indicador:
                bi_indicador = BiIndicadorMensal()
                bi_indicador.ano = ano
                bi_indicador.mes = mes

            # KPIs principais - busca dos dados agregados
            kpis = db.session.query(
                func.sum(BiFreteAgregado.valor_pago_total).label('custo_total'),
                func.sum(BiFreteAgregado.valor_despesas_extras).label('despesas_total'),
                func.sum(BiFreteAgregado.valor_cotado_total - BiFreteAgregado.valor_pago_total).label('economia'),
                func.sum(BiFreteAgregado.qtd_embarques).label('total_embarques'),
                func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
                func.sum(BiFreteAgregado.valor_total_nf).label('valor_faturado'),
                func.avg(BiFreteAgregado.custo_por_kg).label('custo_medio_kg')
            ).filter(
                and_(
                    BiFreteAgregado.ano == ano,
                    BiFreteAgregado.mes == mes
                )
            ).first()

            if kpis:
                bi_indicador.custo_total_frete = float(kpis.custo_total or 0)
                bi_indicador.custo_total_despesas = float(kpis.despesas_total or 0)
                bi_indicador.economia_realizada = float(kpis.economia or 0)
                bi_indicador.total_embarques = kpis.total_embarques or 0
                bi_indicador.total_peso_kg = float(kpis.peso_total or 0)
                bi_indicador.total_valor_faturado = float(kpis.valor_faturado or 0)
                bi_indicador.custo_medio_por_kg = float(kpis.custo_medio_kg or 0)

                if bi_indicador.total_embarques > 0:
                    bi_indicador.custo_medio_por_embarque = bi_indicador.custo_total_frete / bi_indicador.total_embarques
                    bi_indicador.ticket_medio_embarque = bi_indicador.total_valor_faturado / bi_indicador.total_embarques

            # Top performers
            top_transp_volume = db.session.query(
                BiFreteAgregado.transportadora_nome
            ).filter(
                and_(
                    BiFreteAgregado.ano == ano,
                    BiFreteAgregado.mes == mes
                )
            ).group_by(
                BiFreteAgregado.transportadora_nome
            ).order_by(
                func.sum(BiFreteAgregado.peso_total_kg).desc()
            ).first()

            if top_transp_volume:
                bi_indicador.top_transportadora_volume = top_transp_volume.transportadora_nome

            top_transp_custo = db.session.query(
                BiFreteAgregado.transportadora_nome
            ).filter(
                and_(
                    BiFreteAgregado.ano == ano,
                    BiFreteAgregado.mes == mes,
                    BiFreteAgregado.custo_por_kg.isnot(None)
                )
            ).group_by(
                BiFreteAgregado.transportadora_nome
            ).order_by(
                func.avg(BiFreteAgregado.custo_por_kg).asc()
            ).first()

            if top_transp_custo:
                bi_indicador.top_transportadora_custo = top_transp_custo.transportadora_nome

            # Top regiões
            top_regiao_volume = db.session.query(
                BiFreteAgregado.destino_regiao
            ).filter(
                and_(
                    BiFreteAgregado.ano == ano,
                    BiFreteAgregado.mes == mes
                )
            ).group_by(
                BiFreteAgregado.destino_regiao
            ).order_by(
                func.sum(BiFreteAgregado.peso_total_kg).desc()
            ).first()

            if top_regiao_volume:
                bi_indicador.top_regiao_volume = top_regiao_volume.destino_regiao

            # Variações (comparação com mês anterior)
            if mes == 1:
                mes_anterior = 12
                ano_anterior = ano - 1
            else:
                mes_anterior = mes - 1
                ano_anterior = ano

            kpis_anterior = db.session.query(
                func.sum(BiFreteAgregado.valor_pago_total).label('custo_total')
            ).filter(
                and_(
                    BiFreteAgregado.ano == ano_anterior,
                    BiFreteAgregado.mes == mes_anterior
                )
            ).first()

            if kpis_anterior and kpis_anterior.custo_total and bi_indicador.custo_total_frete:
                bi_indicador.variacao_mes_anterior = (
                    (bi_indicador.custo_total_frete - float(kpis_anterior.custo_total)) /
                    float(kpis_anterior.custo_total) * 100
                )

            # Performance
            bi_indicador.percentual_no_prazo = 90.0  # TODO: Calcular real
            bi_indicador.percentual_com_divergencia = 10.0  # TODO: Calcular real
            bi_indicador.percentual_aprovado = 85.0  # TODO: Calcular real

            bi_indicador.calculado_em = datetime.now()

            db.session.add(bi_indicador)
            db.session.commit()

            logger.info(f"Indicadores mensais de {mes}/{ano} processados com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro no processamento de indicadores mensais: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def executar_etl_completo():
        """
        Executa todo o processo de ETL
        """
        logger.info("Iniciando ETL completo do BI")

        # Processa últimos 90 dias por padrão
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=90)

        sucesso = True

        # 1. Processa fretes agregados
        if not BiETLService.processar_frete_agregado(data_inicio, data_fim):
            sucesso = False
            logger.error("Falha no processamento de fretes agregados")

        # 2. Processa despesas detalhadas
        if not BiETLService.processar_despesas_detalhadas(data_inicio, data_fim):
            sucesso = False
            logger.error("Falha no processamento de despesas")

        # 3. Calcula performance das transportadoras
        if not BiETLService.calcular_performance_transportadora():
            sucesso = False
            logger.error("Falha no cálculo de performance")

        # 4. Processa análise regional
        if not BiETLService.processar_analise_regional(data_inicio, data_fim):
            sucesso = False
            logger.error("Falha no processamento de análise regional")

        # 5. Processa indicadores mensais
        if not BiETLService.processar_indicadores_mensais():
            sucesso = False
            logger.error("Falha no processamento de indicadores mensais")

        if sucesso:
            logger.info("ETL completo executado com sucesso")
        else:
            logger.warning("ETL completo executado com algumas falhas")

        return sucesso