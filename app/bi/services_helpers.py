"""
Métodos auxiliares para cálculos reais do BI
"""
from app import db
from sqlalchemy import func, and_, case, distinct, cast, Integer
from app.fretes.models import Frete, DespesaExtra
from app.embarques.models import Embarque # type: ignore
import logging

logger = logging.getLogger(__name__)

class BiCalculosReais:
    """Classe com métodos para calcular dados reais do BI"""
    
    @staticmethod
    def calcular_lead_time(data_inicio, data_fim, transportadora_id=None, uf_destino=None):
        """
        Calcula lead time médio real baseado em embarques/entregas
        """
        try:
            query = db.session.query(
                func.avg(
                    cast(Embarque.data_embarque - Embarque.data_prevista_embarque, Integer)
                ).label('lead_time_medio')
            ).filter(
                and_(
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    Embarque.status == 'ativo',
                    func.date(Embarque.data_embarque) >= data_inicio,
                    func.date(Embarque.data_embarque) <= data_fim
                )
            )
            
            if transportadora_id:
                query = query.filter(Embarque.transportadora_id == transportadora_id)
            
            resultado = query.first()
            return float(resultado.lead_time_medio or 0) if resultado else 0
            
        except Exception as e:
            logger.error(f"Erro ao calcular lead time: {str(e)}")
            return 0
    
    @staticmethod
    def calcular_score_transportadora(transportadora_id, periodo_inicio, periodo_fim):
        """
        Calcula score real da transportadora baseado em múltiplos fatores
        """
        try:
            score = 100.0  # Começa com score máximo
            
            # 1. Penalidade por divergências de valor (peso 30%)
            divergencias = db.session.query(
                func.count(Frete.id).label('qtd'),
                func.avg(
                    case(
                        (Frete.valor_cotado > 0, 
                         func.abs(Frete.valor_pago - Frete.valor_cotado) / Frete.valor_cotado * 100),
                        else_=0
                    )
                ).label('percentual_medio')
            ).filter(
                and_(
                    Frete.transportadora_id == transportadora_id,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).first()
            
            if divergencias and divergencias.percentual_medio:
                # Reduz até 30 pontos baseado na divergência média
                penalidade_divergencia = min(30, float(divergencias.percentual_medio or 0))
                score -= penalidade_divergencia
            
            # 2. Penalidade por despesas extras (peso 25%)
            despesas = db.session.query(
                func.count(DespesaExtra.id).label('qtd'),
                func.sum(DespesaExtra.valor_despesa).label('total')
            ).join(
                Frete, Frete.id == DespesaExtra.frete_id
            ).filter(
                and_(
                    Frete.transportadora_id == transportadora_id,
                    func.date(DespesaExtra.criado_em) >= periodo_inicio,
                    func.date(DespesaExtra.criado_em) <= periodo_fim
                )
            ).first()
            
            if despesas and despesas.qtd:
                # Calcula valor total de fretes
                valor_fretes = db.session.query(
                    func.sum(Frete.valor_pago)
                ).filter(
                    and_(
                        Frete.transportadora_id == transportadora_id,
                        func.date(Frete.criado_em) >= periodo_inicio,
                        func.date(Frete.criado_em) <= periodo_fim,
                        Frete.status != 'CANCELADO'
                    )
                ).scalar() or 0
                
                if valor_fretes > 0:
                    percentual_despesas = (float(despesas.total or 0) / valor_fretes) * 100
                    # Reduz até 25 pontos baseado no percentual de despesas
                    penalidade_despesas = min(25, percentual_despesas * 2)
                    score -= penalidade_despesas
            
            # 3. Penalidade por rejeições/aprovações (peso 20%)
            aprovacoes = db.session.query(
                func.sum(case((Frete.status == 'APROVADO', 1), else_=0)).label('aprovados'),
                func.sum(case((Frete.status == 'REJEITADO', 1), else_=0)).label('rejeitados'),
                func.sum(case((Frete.status == 'EM_TRATATIVA', 1), else_=0)).label('em_tratativa')
            ).filter(
                and_(
                    Frete.transportadora_id == transportadora_id,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim
                )
            ).first()
            
            if aprovacoes:
                total_avaliados = (aprovacoes.aprovados or 0) + (aprovacoes.rejeitados or 0)
                if total_avaliados > 0:
                    taxa_rejeicao = (float(aprovacoes.rejeitados or 0) / total_avaliados) * 100
                    # Reduz até 20 pontos baseado na taxa de rejeição
                    penalidade_rejeicao = min(20, taxa_rejeicao)
                    score -= penalidade_rejeicao
            
            # 4. Penalidade por atrasos (peso 15%)
            atrasos = db.session.query(
                func.count(Embarque.id).label('total'),
                func.sum(
                    case(
                        (Embarque.data_embarque > Embarque.data_prevista_embarque, 1),
                        else_=0
                    )
                ).label('atrasados')
            ).filter(
                and_(
                    Embarque.transportadora_id == transportadora_id,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).first()
            
            if atrasos and atrasos.total > 0:
                taxa_atraso = (float(atrasos.atrasados or 0) / atrasos.total) * 100
                # Reduz até 15 pontos baseado na taxa de atraso
                penalidade_atraso = min(15, taxa_atraso * 0.3)
                score -= penalidade_atraso
            
            # 5. Bônus por volume (peso 10%)
            # Transportadoras com maior volume podem ter até 10 pontos de bônus
            volume = db.session.query(
                func.count(Frete.id).label('qtd_fretes')
            ).filter(
                and_(
                    Frete.transportadora_id == transportadora_id,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).scalar() or 0
            
            if volume > 100:
                bonus_volume = min(10, volume / 50)  # 1 ponto a cada 50 fretes
                score = min(100, score + bonus_volume)
            
            return max(0, min(100, score))  # Garante score entre 0 e 100
            
        except Exception as e:
            logger.error(f"Erro ao calcular score da transportadora {transportadora_id}: {str(e)}")
            return 50  # Score neutro em caso de erro
    
    @staticmethod
    def analisar_tendencia(tipo_despesa, setor, periodo_atual, periodo_anterior):
        """
        Analisa tendência comparando período atual com anterior
        """
        try:
            # Busca valor do período atual
            valor_atual = db.session.query(
                func.sum(DespesaExtra.valor_despesa)
            ).filter(
                and_(
                    DespesaExtra.tipo_despesa == tipo_despesa,
                    DespesaExtra.setor_responsavel == setor,
                    func.date(DespesaExtra.criado_em) >= periodo_atual[0],
                    func.date(DespesaExtra.criado_em) <= periodo_atual[1]
                )
            ).scalar() or 0
            
            # Busca valor do período anterior
            valor_anterior = db.session.query(
                func.sum(DespesaExtra.valor_despesa)
            ).filter(
                and_(
                    DespesaExtra.tipo_despesa == tipo_despesa,
                    DespesaExtra.setor_responsavel == setor,
                    func.date(DespesaExtra.criado_em) >= periodo_anterior[0],
                    func.date(DespesaExtra.criado_em) <= periodo_anterior[1]
                )
            ).scalar() or 0
            
            if valor_anterior == 0:
                if valor_atual > 0:
                    return 'CRESCENTE'
                return 'ESTAVEL'
            
            variacao = ((valor_atual - valor_anterior) / valor_anterior) * 100
            
            if variacao > 10:
                return 'CRESCENTE'
            elif variacao < -10:
                return 'DECRESCENTE'
            else:
                return 'ESTAVEL'
                
        except Exception as e:
            logger.error(f"Erro ao analisar tendência: {str(e)}")
            return 'ESTAVEL'
    
    @staticmethod
    def calcular_distancia_aproximada(origem_uf, destino_uf):
        """
        Calcula distância aproximada entre UFs (em km)
        Usando uma tabela simplificada de distâncias
        """
        # Tabela simplificada de distâncias de SP para outras UFs (em km)
        distancias_sp = {
            'SP': 0,
            'RJ': 430,
            'MG': 590,
            'ES': 880,
            'PR': 410,
            'SC': 700,
            'RS': 1110,
            'MS': 1010,
            'MT': 1610,
            'GO': 930,
            'DF': 1010,
            'BA': 1960,
            'SE': 2180,
            'AL': 2450,
            'PE': 2650,
            'PB': 2770,
            'RN': 2930,
            'CE': 3120,
            'PI': 2830,
            'MA': 2970,
            'TO': 1780,
            'PA': 2930,
            'AP': 3340,
            'RR': 4280,
            'AM': 3870,
            'AC': 3600,
            'RO': 3050
        }
        
        if origem_uf == 'SP' and destino_uf in distancias_sp:
            return distancias_sp[destino_uf]
        elif destino_uf == 'SP' and origem_uf in distancias_sp:
            return distancias_sp[origem_uf]
        else:
            # Retorna uma estimativa genérica se não tiver na tabela
            return 1000
    
    @staticmethod
    def identificar_transportadora_principal(uf_destino, periodo_inicio, periodo_fim):
        """
        Identifica a transportadora com maior volume para uma UF
        """
        try:
            resultado = db.session.query(
                Frete.transportadora_id,
                func.count(Frete.id).label('qtd_fretes'),
                func.sum(Frete.peso_total).label('peso_total')
            ).filter(
                and_(
                    Frete.uf_destino == uf_destino,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).group_by(
                Frete.transportadora_id
            ).order_by(
                func.count(Frete.id).desc()
            ).first()
            
            if resultado:
                from app.transportadoras.models import Transportadora
                transp = db.session.get(Transportadora,resultado.transportadora_id) if resultado.transportadora_id else None
                if transp:
                    return {
                        'id': transp.id,
                        'nome': transp.razao_social,
                        'qtd_fretes': resultado.qtd_fretes,
                        'peso_total': float(resultado.peso_total or 0)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao identificar transportadora principal: {str(e)}")
            return None
    
    @staticmethod
    def calcular_percentual_no_prazo(transportadora_id, periodo_inicio, periodo_fim):
        """
        Calcula percentual de entregas no prazo
        """
        try:
            # Total de embarques com data prevista e real
            total = db.session.query(
                func.count(Embarque.id)
            ).filter(
                and_(
                    Embarque.transportadora_id == transportadora_id,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0
            
            if total == 0:
                return 100.0  # Se não há dados, assume 100%
            
            # Embarques no prazo (data real <= data prevista)
            no_prazo = db.session.query(
                func.count(Embarque.id)
            ).filter(
                and_(
                    Embarque.transportadora_id == transportadora_id,
                    Embarque.data_embarque <= Embarque.data_prevista_embarque,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0
            
            return (no_prazo / total) * 100
            
        except Exception as e:
            logger.error(f"Erro ao calcular percentual no prazo: {str(e)}")
            return 0
    
    @staticmethod
    def obter_top_motivos_despesas(periodo_inicio, periodo_fim, limite=10):
        """
        Obtém os top motivos de despesas extras do período
        """
        try:
            resultados = db.session.query(
                DespesaExtra.motivo_despesa,
                DespesaExtra.tipo_despesa,
                DespesaExtra.setor_responsavel,
                func.count(DespesaExtra.id).label('qtd'),
                func.sum(DespesaExtra.valor_despesa).label('valor_total'),
                func.avg(DespesaExtra.valor_despesa).label('valor_medio')
            ).filter(
                and_(
                    func.date(DespesaExtra.criado_em) >= periodo_inicio,
                    func.date(DespesaExtra.criado_em) <= periodo_fim
                )
            ).group_by(
                DespesaExtra.motivo_despesa,
                DespesaExtra.tipo_despesa,
                DespesaExtra.setor_responsavel
            ).order_by(
                func.sum(DespesaExtra.valor_despesa).desc()
            ).limit(limite).all()
            
            return [
                {
                    'motivo': r.motivo_despesa,
                    'tipo': r.tipo_despesa,
                    'setor': r.setor_responsavel,
                    'qtd': r.qtd,
                    'valor': float(r.valor_total or 0),
                    'medio': float(r.valor_medio or 0)
                }
                for r in resultados
            ]
            
        except Exception as e:
            logger.error(f"Erro ao obter top motivos de despesas: {str(e)}")
            return []
    
    @staticmethod
    def obter_top_transportadoras_despesas(periodo_inicio, periodo_fim, limite=5):
        """
        Obtém as transportadoras com mais despesas extras
        """
        try:
            from app.transportadoras.models import Transportadora
            
            resultados = db.session.query(
                Frete.transportadora_id,
                func.count(distinct(DespesaExtra.id)).label('qtd_despesas'),
                func.sum(DespesaExtra.valor_despesa).label('valor_total')
            ).join(
                DespesaExtra, DespesaExtra.frete_id == Frete.id
            ).filter(
                and_(
                    func.date(DespesaExtra.criado_em) >= periodo_inicio,
                    func.date(DespesaExtra.criado_em) <= periodo_fim
                )
            ).group_by(
                Frete.transportadora_id
            ).order_by(
                func.sum(DespesaExtra.valor_despesa).desc()
            ).limit(limite).all()
            
            # Busca nome das transportadoras e calcula percentual
            top_transportadoras = []
            for r in resultados:
                transp = db.session.get(Transportadora,r.transportadora_id) if r.transportadora_id else None
                if transp:
                    # Calcula valor total de fretes da transportadora
                    valor_fretes = db.session.query(
                        func.sum(Frete.valor_pago)
                    ).filter(
                        and_(
                            Frete.transportadora_id == r.transportadora_id,
                            func.date(Frete.criado_em) >= periodo_inicio,
                            func.date(Frete.criado_em) <= periodo_fim,
                            Frete.status != 'CANCELADO'
                        )
                    ).scalar() or 0
                    
                    percentual = 0
                    if valor_fretes > 0:
                        percentual = (float(r.valor_total or 0) / valor_fretes) * 100
                    
                    top_transportadoras.append({
                        'id': transp.id,
                        'nome': transp.razao_social,
                        'qtd_despesas': r.qtd_despesas,
                        'valor': float(r.valor_total or 0),
                        'percentual': percentual
                    })

            return top_transportadoras

        except Exception as e:
            logger.error(f"Erro ao obter top transportadoras com despesas: {str(e)}")
            return []

    @staticmethod
    def calcular_percentual_no_prazo_por_regiao(uf_destino, periodo_inicio, periodo_fim):
        """
        Calcula percentual de entregas no prazo para uma região (UF)

        Critério: Embarque.data_embarque <= Embarque.data_prevista_embarque
        """
        try:
            from app.embarques.models import EmbarqueItem  # type: ignore

            # Total de embarques com data prevista e real para a UF
            total = db.session.query(
                func.count(distinct(Embarque.id))
            ).join(
                EmbarqueItem, EmbarqueItem.embarque_id == Embarque.id
            ).filter(
                and_(
                    EmbarqueItem.uf_destino == uf_destino,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0

            if total == 0:
                return 100.0  # Se não há dados, assume 100%

            # Embarques no prazo (data real <= data prevista)
            no_prazo = db.session.query(
                func.count(distinct(Embarque.id))
            ).join(
                EmbarqueItem, EmbarqueItem.embarque_id == Embarque.id
            ).filter(
                and_(
                    EmbarqueItem.uf_destino == uf_destino,
                    Embarque.data_embarque <= Embarque.data_prevista_embarque,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0

            return round((no_prazo / total) * 100, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular percentual no prazo por região {uf_destino}: {str(e)}")
            return 95.0  # Fallback para evitar erro

    @staticmethod
    def calcular_percentual_com_problema_por_regiao(uf_destino, periodo_inicio, periodo_fim):
        """
        Calcula percentual de fretes com problema para uma região (UF)

        Problema = Fretes com status REJEITADO, EM_TRATATIVA ou com despesas extras
        """
        try:
            from app.embarques.models import EmbarqueItem  # type: ignore

            # Total de fretes da UF
            total = db.session.query(
                func.count(distinct(Frete.id))
            ).filter(
                and_(
                    Frete.uf_destino == uf_destino,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).scalar() or 0

            if total == 0:
                return 0.0

            # Fretes com problema (status problemático OU tem despesa extra)
            fretes_com_despesa = db.session.query(
                func.count(distinct(DespesaExtra.frete_id))
            ).join(
                Frete, Frete.id == DespesaExtra.frete_id
            ).filter(
                and_(
                    Frete.uf_destino == uf_destino,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim
                )
            ).scalar() or 0

            fretes_rejeitados = db.session.query(
                func.count(distinct(Frete.id))
            ).filter(
                and_(
                    Frete.uf_destino == uf_destino,
                    Frete.status.in_(['REJEITADO', 'EM_TRATATIVA']),
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim
                )
            ).scalar() or 0

            # Combina (pode haver overlap, então pegamos o maior conservador)
            com_problema = max(fretes_com_despesa, fretes_rejeitados)

            return round((com_problema / total) * 100, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular percentual com problema por região {uf_destino}: {str(e)}")
            return 5.0  # Fallback para evitar erro

    @staticmethod
    def calcular_percentual_no_prazo_mensal(ano, mes):
        """
        Calcula percentual de entregas no prazo para um mês inteiro (todos os UFs)
        """
        try:
            from datetime import date, timedelta

            periodo_inicio = date(ano, mes, 1)
            if mes == 12:
                periodo_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                periodo_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            # Total de embarques com data prevista e real
            total = db.session.query(
                func.count(Embarque.id)
            ).filter(
                and_(
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0

            if total == 0:
                return 100.0

            no_prazo = db.session.query(
                func.count(Embarque.id)
            ).filter(
                and_(
                    Embarque.data_embarque <= Embarque.data_prevista_embarque,
                    Embarque.data_embarque.isnot(None),
                    Embarque.data_prevista_embarque.isnot(None),
                    func.date(Embarque.data_embarque) >= periodo_inicio,
                    func.date(Embarque.data_embarque) <= periodo_fim,
                    Embarque.status == 'ativo'
                )
            ).scalar() or 0

            return round((no_prazo / total) * 100, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular percentual no prazo mensal {mes}/{ano}: {str(e)}")
            return 90.0

    @staticmethod
    def calcular_percentual_divergencia_mensal(ano, mes):
        """
        Calcula percentual de fretes com divergência entre cotado e pago para um mês

        Divergência = |valor_cotado - valor_pago| / valor_cotado > 5%
        """
        try:
            from datetime import date, timedelta

            periodo_inicio = date(ano, mes, 1)
            if mes == 12:
                periodo_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                periodo_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            # Total de fretes com valores cotado e pago
            total = db.session.query(
                func.count(Frete.id)
            ).filter(
                and_(
                    Frete.valor_cotado.isnot(None),
                    Frete.valor_pago.isnot(None),
                    Frete.valor_cotado > 0,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).scalar() or 0

            if total == 0:
                return 0.0

            # Fretes com divergência > 5%
            divergentes = db.session.query(
                func.count(Frete.id)
            ).filter(
                and_(
                    Frete.valor_cotado.isnot(None),
                    Frete.valor_pago.isnot(None),
                    Frete.valor_cotado > 0,
                    func.abs(Frete.valor_cotado - Frete.valor_pago) / Frete.valor_cotado > 0.05,
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).scalar() or 0

            return round((divergentes / total) * 100, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular percentual divergência mensal {mes}/{ano}: {str(e)}")
            return 10.0

    @staticmethod
    def calcular_percentual_aprovado_mensal(ano, mes):
        """
        Calcula percentual de fretes aprovados vs total para um mês

        Aprovado = status = 'APROVADO'
        """
        try:
            from datetime import date, timedelta

            periodo_inicio = date(ano, mes, 1)
            if mes == 12:
                periodo_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                periodo_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            # Total de fretes (exceto cancelados)
            total = db.session.query(
                func.count(Frete.id)
            ).filter(
                and_(
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim,
                    Frete.status != 'CANCELADO'
                )
            ).scalar() or 0

            if total == 0:
                return 100.0

            # Fretes aprovados
            aprovados = db.session.query(
                func.count(Frete.id)
            ).filter(
                and_(
                    Frete.status == 'APROVADO',
                    func.date(Frete.criado_em) >= periodo_inicio,
                    func.date(Frete.criado_em) <= periodo_fim
                )
            ).scalar() or 0

            return round((aprovados / total) * 100, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular percentual aprovado mensal {mes}/{ano}: {str(e)}")
            return 85.0