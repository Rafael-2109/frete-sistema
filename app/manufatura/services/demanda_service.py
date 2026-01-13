"""
Service para cálculo e gestão de demanda

ATUALIZADO: Fonte híbrida de dados históricos
- Até 30/06/2025: Odoo (sale.order) - dados legados
- A partir de 01/07/2025: CarteiraPrincipal (qtd_produto_pedido)
"""
from app import db
from app.manufatura.models import PrevisaoDemanda, HistoricoPedidos, GrupoEmpresarial
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.models import CarteiraPrincipal
from datetime import datetime, date
from sqlalchemy import func, extract, or_
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def extrair_prefixo_cnpj(campo_cnpj):
    """
    Extrai os 8 primeiros dígitos do CNPJ, removendo formatação.

    CNPJs podem estar formatados como '00.063.960/0015-04' ou apenas '00063960001504'.
    Esta função remove pontos, traços e barras antes de extrair o prefixo.

    Args:
        campo_cnpj: Campo SQLAlchemy do CNPJ

    Returns:
        Expressão SQLAlchemy com os 8 primeiros dígitos numéricos
    """
    # Remove formatação: pontos, traços e barras
    cnpj_limpo = func.replace(
        func.replace(
            func.replace(campo_cnpj, '.', ''),
            '-', ''
        ),
        '/', ''
    )
    # Extrai os 8 primeiros dígitos
    return func.substr(cnpj_limpo, 1, 8)

# Data de corte: antes desta data = Odoo, depois = CarteiraPrincipal
DATA_CORTE = date(2025, 7, 1)


class DemandaService:
    
    def calcular_demanda_realizada(self, cod_produto, mes, ano, grupo=None):
        """Calcula demanda realizada do FaturamentoProduto para um produto/mês/ano"""
        
        from app.faturamento.models import FaturamentoProduto
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== INÍCIO calcular_demanda_realizada ===")
        logger.info(f"Produto: {cod_produto}, Mês: {mes}, Ano: {ano}, Grupo: {grupo}")
        
        # Busca faturamentos do mês/ano
        query = db.session.query(
            func.sum(FaturamentoProduto.qtd_produto_faturado)
        ).filter(
            FaturamentoProduto.cod_produto == cod_produto,
            extract('month', FaturamentoProduto.data_fatura) == mes,
            extract('year', FaturamentoProduto.data_fatura) == ano,
            FaturamentoProduto.status_nf != 'Cancelado'  # Não contar NFs canceladas
        )
        
        # Filtro por grupo se especificado
        if grupo and grupo != '':
            if grupo == 'RESTANTE':
                # Busca todos os prefixos cadastrados
                from app.manufatura.models import GrupoEmpresarial
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()
                
                # Exclui CNPJs que pertencem a algum grupo
                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(FaturamentoProduto.cnpj_cliente) != prefixo
                        )
            else:
                # Busca prefixos do grupo específico
                from app.manufatura.models import GrupoEmpresarial
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()
                
                if prefixos_grupo:
                    from sqlalchemy import or_
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(FaturamentoProduto.cnpj_cliente) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))
        
        resultado = query.scalar()
        valor_final = float(resultado or 0)
        logger.info(f"Demanda realizada calculada: {valor_final}")
        logger.info(f"=== FIM calcular_demanda_realizada ===")
        return valor_final
    
    def calcular_demanda_ativa(self, cod_produto, grupo=None):
        """Calcula demanda ativa da carteira para um produto específico"""
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== INÍCIO calcular_demanda_ativa ===")
        logger.info(f"Produto: {cod_produto}, Grupo: {grupo}")
        
        # Debug: verificar se existe o produto na CarteiraPrincipal
        total_produto = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.cod_produto == cod_produto
        ).count()
        logger.info(f"Total de registros do produto {cod_produto} na CarteiraPrincipal: {total_produto}")
        
        # Debug: verificar se há saldo > 0
        com_saldo = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()
        logger.info(f"Registros com saldo > 0: {com_saldo}")
        
        # Busca na CarteiraPrincipal (pedidos não faturados)
        query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
        ).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        # Filtro por grupo se especificado
        if grupo and grupo != '':
            if grupo == 'RESTANTE':
                # Busca todos os prefixos cadastrados
                from app.manufatura.models import GrupoEmpresarial
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()
                
                # Exclui CNPJs que pertencem a algum grupo
                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) != prefixo
                        )
            else:
                # Busca prefixos do grupo específico
                from app.manufatura.models import GrupoEmpresarial
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()
                
                if prefixos_grupo:
                    from sqlalchemy import or_
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))
        
        resultado = query.scalar()
        valor_final = float(resultado or 0)
        logger.info(f"Resultado final da demanda ativa: {valor_final}")
        logger.info(f"=== FIM calcular_demanda_ativa ===")
        return valor_final
    
    
    def atualizar_demanda_realizada(self, mes, ano):
        """Atualiza qtd_demanda_realizada baseado no histórico"""
        
        # Buscar previsões do período
        previsoes = PrevisaoDemanda.query.filter_by(
            data_mes=mes,
            data_ano=ano
        ).all()
        
        for previsao in previsoes:
            # Calcular realizado do histórico
            realizado = db.session.query(
                func.sum(HistoricoPedidos.qtd_produto_pedido)
            ).filter(
                HistoricoPedidos.cod_produto == previsao.cod_produto,
                extract('month', HistoricoPedidos.data_pedido) == mes,
                extract('year', HistoricoPedidos.data_pedido) == ano
            )
            
            # Se tem grupo, filtrar por grupo
            if previsao.nome_grupo:
                realizado = realizado.filter(
                    HistoricoPedidos.nome_grupo == previsao.nome_grupo
                )
            
            total_realizado = realizado.scalar() or 0
            previsao.qtd_demanda_realizada = total_realizado
            previsao.atualizado_em = datetime.now()
        
        db.session.commit()
        return len(previsoes)
    
    def obter_pedidos_urgentes(self, dias_limite=7):
        """Obtém pedidos com expedição próxima que precisam produção"""
        
        from datetime import timedelta
        data_limite = datetime.now().date() + timedelta(days=dias_limite)
        
        # Pedidos em Separacao
        pedidos_separacao = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Separacao.cod_produto,
            Separacao.nome_produto,
            Separacao.qtd_saldo,
            Separacao.expedicao,
            Separacao.cnpj_cpf,
            Separacao.raz_social_red
        ).join(
            Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Pedido.status != 'FATURADO',
            Separacao.expedicao <= data_limite,
            Separacao.expedicao >= datetime.now().date()
        ).order_by(Separacao.expedicao).all()
        
        return [{
            'separacao_lote_id': p.separacao_lote_id,
            'num_pedido': p.num_pedido,
            'cod_produto': p.cod_produto,
            'nome_produto': p.nome_produto,
            'qtd_saldo': float(p.qtd_saldo or 0),
            'expedicao': p.expedicao.strftime('%d/%m/%Y') if p.expedicao else None,
            'dias_restantes': (p.expedicao - datetime.now().date()).days if p.expedicao else None,
            'cliente': f"{p.cnpj_cpf} - {p.raz_social_red}"
        } for p in pedidos_separacao]
    
    def criar_previsao_por_historico(self, mes, ano, multiplicador=1.0):
        """Cria previsão baseada no histórico do mesmo período ano anterior"""
        
        ano_anterior = ano - 1
        
        # Buscar histórico do período anterior
        historico = db.session.query(
            HistoricoPedidos.cod_produto,
            HistoricoPedidos.nome_produto,
            HistoricoPedidos.nome_grupo,
            func.sum(HistoricoPedidos.qtd_produto_pedido).label('qtd_total')
        ).filter(
            extract('month', HistoricoPedidos.data_pedido) == mes,
            extract('year', HistoricoPedidos.data_pedido) == ano_anterior
        ).group_by(
            HistoricoPedidos.cod_produto,
            HistoricoPedidos.nome_produto,
            HistoricoPedidos.nome_grupo
        ).all()
        
        previsoes_criadas = []
        
        for h in historico:
            # Verificar se já existe previsão
            existe = PrevisaoDemanda.query.filter_by(
                data_mes=mes,
                data_ano=ano,
                cod_produto=h.cod_produto,
                nome_grupo=h.nome_grupo
            ).first()
            
            if not existe:
                previsao = PrevisaoDemanda(
                    data_mes=mes,
                    data_ano=ano,
                    cod_produto=h.cod_produto,
                    nome_produto=h.nome_produto,
                    nome_grupo=h.nome_grupo,
                    qtd_demanda_prevista=Decimal(str(h.qtd_total)) * Decimal(str(multiplicador)),
                    qtd_demanda_realizada=0,
                    disparo_producao='MTS',  # Default
                    criado_por='Sistema'
                )
                db.session.add(previsao)
                previsoes_criadas.append(previsao)
        
        if previsoes_criadas:
            db.session.commit()
        
        return len(previsoes_criadas)
    
    def identificar_grupo_por_cnpj(self, cnpj):
        """
        Identifica grupo empresarial pelo prefixo do CNPJ (8 primeiros dígitos)
        Retorna 'RESTANTE' se não pertencer a nenhum grupo
        """
        # Remove caracteres não numéricos do CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        # Pega os 8 primeiros dígitos (prefixo)
        if len(cnpj_limpo) < 8:
            return 'RESTANTE'
        
        prefixo_cnpj = cnpj_limpo[:8]
        
        # Busca diretamente pelo prefixo (muito mais eficiente com a nova estrutura)
        grupo = GrupoEmpresarial.query.filter_by(
            prefixo_cnpj=prefixo_cnpj,
            ativo=True
        ).first()
        
        if grupo:
            return grupo.nome_grupo
        
        return 'RESTANTE'
    
    def calcular_media_historica(self, cod_produto, meses, mes_base, ano_base, grupo=None):
        """
        Calcula média dos últimos N meses para um produto
        HÍBRIDO: HistoricoPedidos (até 30/06/2025) + CarteiraPrincipal (a partir 01/07/2025)
        Se grupo for especificado, filtra por grupo (incluindo 'RESTANTE')
        """
        from dateutil.relativedelta import relativedelta

        # Data base para cálculo
        data_base = date(ano_base, mes_base, 1)

        # Calcula período de análise
        data_inicial = data_base - relativedelta(months=meses)
        data_final = data_base - relativedelta(days=1)  # Último dia do mês anterior

        total = 0

        # ============================================
        # PARTE 1: HistoricoPedidos (até 30/06/2025)
        # ============================================
        if data_inicial < DATA_CORTE:
            data_final_historico = min(data_final, date(2025, 6, 30))

            query_historico = db.session.query(
                func.sum(HistoricoPedidos.qtd_produto_pedido)
            ).filter(
                HistoricoPedidos.cod_produto == cod_produto,
                HistoricoPedidos.data_pedido >= data_inicial,
                HistoricoPedidos.data_pedido <= data_final_historico
            )

            # Filtro por grupo para HistoricoPedidos
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) == prefixo
                        )
                    if cnpj_filters:
                        query_historico = query_historico.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query_historico = query_historico.filter(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) != prefixo
                        )

            resultado_historico = query_historico.scalar() or 0
            total += float(resultado_historico)
            logger.debug(f"[HÍBRIDO] HistoricoPedidos: {resultado_historico}")

        # ============================================
        # PARTE 2: CarteiraPrincipal (a partir 01/07/2025)
        # ============================================
        if data_final >= DATA_CORTE:
            data_inicial_carteira = max(data_inicial, DATA_CORTE)

            query_carteira = db.session.query(
                func.sum(CarteiraPrincipal.qtd_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.data_pedido >= data_inicial_carteira,
                CarteiraPrincipal.data_pedido <= data_final
            )

            # Filtro por grupo para CarteiraPrincipal
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) == prefixo
                        )
                    if cnpj_filters:
                        query_carteira = query_carteira.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query_carteira = query_carteira.filter(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) != prefixo
                        )

            resultado_carteira = query_carteira.scalar() or 0
            total += float(resultado_carteira)
            logger.debug(f"[HÍBRIDO] CarteiraPrincipal: {resultado_carteira}")

        # Calcula média
        media = total / meses if meses > 0 else 0
        logger.debug(f"[HÍBRIDO] Total: {total}, Média: {media}")

        return round(media, 3)
    
    def calcular_mes_anterior(self, cod_produto, mes, ano, grupo=None):
        """
        Busca quantidade do mês anterior
        HÍBRIDO: HistoricoPedidos (até 30/06/2025) + CarteiraPrincipal (a partir 01/07/2025)
        """
        # Ajusta mês e ano para o mês anterior
        mes_anterior = mes - 1
        ano_anterior = ano
        if mes_anterior == 0:
            mes_anterior = 12
            ano_anterior = ano - 1

        # Verifica em qual período está o mês anterior
        data_mes_anterior = date(ano_anterior, mes_anterior, 1)

        total = 0

        # Se o mês anterior é antes de 01/07/2025, busca de HistoricoPedidos
        if data_mes_anterior < DATA_CORTE:
            query = db.session.query(
                func.sum(HistoricoPedidos.qtd_produto_pedido)
            ).filter(
                HistoricoPedidos.cod_produto == cod_produto,
                extract('month', HistoricoPedidos.data_pedido) == mes_anterior,
                extract('year', HistoricoPedidos.data_pedido) == ano_anterior
            )

            # Filtro por grupo
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) != prefixo
                        )

            total = float(query.scalar() or 0)

        # Se o mês anterior é a partir de 01/07/2025, busca de CarteiraPrincipal
        else:
            query = db.session.query(
                func.sum(CarteiraPrincipal.qtd_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                extract('month', CarteiraPrincipal.data_pedido) == mes_anterior,
                extract('year', CarteiraPrincipal.data_pedido) == ano_anterior
            )

            # Filtro por grupo
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) != prefixo
                        )

            total = float(query.scalar() or 0)

        return total
    
    def calcular_mesmo_mes_ano_anterior(self, cod_produto, mes, ano, grupo=None):
        """
        Busca quantidade do mesmo mês no ano anterior
        HÍBRIDO: HistoricoPedidos (até 30/06/2025) + CarteiraPrincipal (a partir 01/07/2025)
        """
        ano_anterior = ano - 1

        # Verifica em qual período está o mês do ano anterior
        data_mes_ano_anterior = date(ano_anterior, mes, 1)

        total = 0

        # Se o mês do ano anterior é antes de 01/07/2025, busca de HistoricoPedidos
        if data_mes_ano_anterior < DATA_CORTE:
            query = db.session.query(
                func.sum(HistoricoPedidos.qtd_produto_pedido)
            ).filter(
                HistoricoPedidos.cod_produto == cod_produto,
                extract('month', HistoricoPedidos.data_pedido) == mes,
                extract('year', HistoricoPedidos.data_pedido) == ano_anterior
            )

            # Filtro por grupo
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) != prefixo
                        )

            total = float(query.scalar() or 0)

        # Se o mês do ano anterior é a partir de 01/07/2025, busca de CarteiraPrincipal
        else:
            query = db.session.query(
                func.sum(CarteiraPrincipal.qtd_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                extract('month', CarteiraPrincipal.data_pedido) == mes,
                extract('year', CarteiraPrincipal.data_pedido) == ano_anterior
            )

            # Filtro por grupo
            if grupo and grupo != 'RESTANTE':
                prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.nome_grupo == grupo,
                    GrupoEmpresarial.ativo == True
                ).all()

                if prefixos_grupo:
                    prefixos = [p[0] for p in prefixos_grupo]
                    cnpj_filters = []
                    for prefixo in prefixos:
                        cnpj_filters.append(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))

            elif grupo == 'RESTANTE':
                todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                    GrupoEmpresarial.ativo == True
                ).all()

                if todos_prefixos:
                    for prefixo_tuple in todos_prefixos:
                        prefixo = prefixo_tuple[0]
                        query = query.filter(
                            extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) != prefixo
                        )

            total = float(query.scalar() or 0)

        return total