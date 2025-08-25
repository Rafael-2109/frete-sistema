"""
Service para cálculo e gestão de demanda
"""
from app import db
from app.manufatura.models import PrevisaoDemanda, HistoricoPedidos, GrupoEmpresarial
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.models import PreSeparacaoItem, CarteiraPrincipal
from datetime import datetime
from sqlalchemy import func, extract, or_
from decimal import Decimal


class DemandaService:
    
    def calcular_demanda_ativa(self, cod_produto, grupo=None):
        """Calcula demanda ativa da carteira para um produto específico"""
        
        from app.carteira.models import CarteiraPrincipal
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
                            func.substr(CarteiraPrincipal.cnpj_cpf, 1, 8) != prefixo
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
                            func.substr(CarteiraPrincipal.cnpj_cpf, 1, 8) == prefixo
                        )
                    if cnpj_filters:
                        query = query.filter(or_(*cnpj_filters))
        
        resultado = query.scalar()
        valor_final = float(resultado or 0)
        logger.info(f"Resultado final da demanda ativa: {valor_final}")
        logger.info(f"=== FIM calcular_demanda_ativa ===")
        return valor_final
    
    def calcular_demanda_ativa_OLD(self, mes=None, ano=None, cod_produto=None):
        """Método antigo mantido para compatibilidade"""
        
        query_filters = []
        if mes:
            query_filters.append(extract('month', Separacao.expedicao) == mes)
        if ano:
            query_filters.append(extract('year', Separacao.expedicao) == ano)
        if cod_produto:
            query_filters.append(Separacao.cod_produto == cod_produto)
        
        # Demanda de Separacao (prioridade)
        demanda_separacao = db.session.query(
            Separacao.cod_produto,
            Separacao.nome_produto,
            extract('month', Separacao.expedicao).label('mes'),
            extract('year', Separacao.expedicao).label('ano'),
            func.sum(Separacao.qtd_saldo).label('qtd_demanda')
        ).join(
            Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Pedido.status != 'FATURADO',
            *query_filters
        ).group_by(
            Separacao.cod_produto,
            Separacao.nome_produto,
            'mes',
            'ano'
        )
        
        # Demanda de PreSeparacaoItem (só se não existe em Separacao)
        subquery_separacao = db.session.query(Separacao.separacao_lote_id).subquery()
        
        query_filters_psi = []
        if mes:
            query_filters_psi.append(extract('month', PreSeparacaoItem.data_expedicao_editada) == mes)
        if ano:
            query_filters_psi.append(extract('year', PreSeparacaoItem.data_expedicao_editada) == ano)
        if cod_produto:
            query_filters_psi.append(PreSeparacaoItem.cod_produto == cod_produto)
        
        demanda_pre_separacao = db.session.query(
            PreSeparacaoItem.cod_produto,
            PreSeparacaoItem.nome_produto,
            extract('month', PreSeparacaoItem.data_expedicao_editada).label('mes'),
            extract('year', PreSeparacaoItem.data_expedicao_editada).label('ano'),
            func.sum(PreSeparacaoItem.qtd_selecionada_usuario).label('qtd_demanda')
        ).filter(
            ~PreSeparacaoItem.separacao_lote_id.in_(subquery_separacao),
            *query_filters_psi
        ).group_by(
            PreSeparacaoItem.cod_produto,
            PreSeparacaoItem.nome_produto,
            'mes',
            'ano'
        )
        
        # Demanda de CarteiraPrincipal (saldo sem separação)
        # Subqueries para excluir itens já em Separacao ou PreSeparacaoItem
        subquery_sep_pedidos = db.session.query(Separacao.num_pedido).distinct().subquery()
        subquery_psi_pedidos = db.session.query(PreSeparacaoItem.num_pedido).distinct().subquery()
        
        query_filters_cp = []
        if mes:
            query_filters_cp.append(extract('month', CarteiraPrincipal.expedicao) == mes)
        if ano:
            query_filters_cp.append(extract('year', CarteiraPrincipal.expedicao) == ano)
        if cod_produto:
            query_filters_cp.append(CarteiraPrincipal.cod_produto == cod_produto)
        
        demanda_carteira = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            extract('month', CarteiraPrincipal.expedicao).label('mes'),
            extract('year', CarteiraPrincipal.expedicao).label('ano'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_demanda')
        ).filter(
            ~CarteiraPrincipal.num_pedido.in_(subquery_sep_pedidos),
            ~CarteiraPrincipal.num_pedido.in_(subquery_psi_pedidos),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
            *query_filters_cp
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            'mes',
            'ano'
        )
        
        # Combinar resultados
        resultado = {}
        for item in demanda_separacao.all():
            key = (item.cod_produto, item.mes, item.ano)
            resultado[key] = {
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'mes': item.mes,
                'ano': item.ano,
                'qtd_demanda': float(item.qtd_demanda or 0),
                'fonte': 'Separacao'
            }
        
        for item in demanda_pre_separacao.all():
            key = (item.cod_produto, item.mes, item.ano)
            if key in resultado:
                resultado[key]['qtd_demanda'] += float(item.qtd_demanda or 0)
                resultado[key]['fonte'] = 'Separacao+PreSeparacao'
            else:
                resultado[key] = {
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'mes': item.mes,
                    'ano': item.ano,
                    'qtd_demanda': float(item.qtd_demanda or 0),
                    'fonte': 'PreSeparacao'
                }
        
        for item in demanda_carteira.all():
            key = (item.cod_produto, item.mes, item.ano)
            if key in resultado:
                resultado[key]['qtd_demanda'] += float(item.qtd_demanda or 0)
                resultado[key]['fonte'] += '+Carteira'
            else:
                resultado[key] = {
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'mes': item.mes,
                    'ano': item.ano,
                    'qtd_demanda': float(item.qtd_demanda or 0),
                    'fonte': 'Carteira'
                }
        
        return list(resultado.values())
    
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
        Se grupo for especificado, filtra por grupo (incluindo 'RESTANTE')
        """
        from dateutil.relativedelta import relativedelta
        from datetime import date
        
        # Data base para cálculo
        data_base = date(ano_base, mes_base, 1)
        
        # Calcula período de análise
        data_inicial = data_base - relativedelta(months=meses)
        data_final = data_base - relativedelta(days=1)  # Último dia do mês anterior
        
        # Query base
        query = db.session.query(
            func.sum(HistoricoPedidos.qtd_produto_pedido).label('qtd_total')
        ).filter(
            HistoricoPedidos.cod_produto == cod_produto,
            HistoricoPedidos.data_pedido >= data_inicial,
            HistoricoPedidos.data_pedido <= data_final
        )
        
        # Filtro por grupo
        if grupo and grupo != 'RESTANTE':
            # Busca todos os prefixos do grupo
            prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.nome_grupo == grupo,
                GrupoEmpresarial.ativo == True
            ).all()
            
            if prefixos_grupo:
                # Lista de prefixos do grupo
                prefixos = [p[0] for p in prefixos_grupo]
                
                # Filtra CNPJs que começam com os prefixos
                cnpj_filters = []
                for prefixo in prefixos:
                    cnpj_filters.append(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
                    )
                if cnpj_filters:
                    query = query.filter(or_(*cnpj_filters))
            else:
                # Grupo não encontrado, retorna 0
                return 0
                
        elif grupo == 'RESTANTE':
            # Busca todos os prefixos cadastrados
            todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.ativo == True
            ).all()
            
            # Exclui CNPJs que pertencem a algum grupo
            if todos_prefixos:
                for prefixo_tuple in todos_prefixos:
                    prefixo = prefixo_tuple[0]
                    query = query.filter(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
                    )
        
        # Executa query
        resultado = query.scalar() or 0
        
        # Calcula média
        media = float(resultado) / meses if meses > 0 else 0
        
        return round(media, 3)
    
    def calcular_mes_anterior(self, cod_produto, mes, ano, grupo=None):
        """
        Busca quantidade do mês anterior
        """
        # Ajusta mês e ano para o mês anterior
        mes_anterior = mes - 1
        ano_anterior = ano
        if mes_anterior == 0:
            mes_anterior = 12
            ano_anterior = ano - 1
        
        # Query base
        query = db.session.query(
            func.sum(HistoricoPedidos.qtd_produto_pedido).label('qtd_total')
        ).filter(
            HistoricoPedidos.cod_produto == cod_produto,
            extract('month', HistoricoPedidos.data_pedido) == mes_anterior,
            extract('year', HistoricoPedidos.data_pedido) == ano_anterior
        )
        
        # Aplica mesma lógica de grupo
        if grupo and grupo != 'RESTANTE':
            # Busca todos os prefixos do grupo
            prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.nome_grupo == grupo,
                GrupoEmpresarial.ativo == True
            ).all()
            
            if prefixos_grupo:
                prefixos = [p[0] for p in prefixos_grupo]
                cnpj_filters = []
                for prefixo in prefixos:
                    cnpj_filters.append(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
                    )
                if cnpj_filters:
                    query = query.filter(or_(*cnpj_filters))
                    
        elif grupo == 'RESTANTE':
            # Busca todos os prefixos cadastrados
            todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.ativo == True
            ).all()
            
            if todos_prefixos:
                for prefixo_tuple in todos_prefixos:
                    prefixo = prefixo_tuple[0]
                    query = query.filter(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
                    )
        
        resultado = query.scalar() or 0
        return float(resultado)
    
    def calcular_mesmo_mes_ano_anterior(self, cod_produto, mes, ano, grupo=None):
        """
        Busca quantidade do mesmo mês no ano anterior
        """
        ano_anterior = ano - 1
        
        # Query base
        query = db.session.query(
            func.sum(HistoricoPedidos.qtd_produto_pedido).label('qtd_total')
        ).filter(
            HistoricoPedidos.cod_produto == cod_produto,
            extract('month', HistoricoPedidos.data_pedido) == mes,
            extract('year', HistoricoPedidos.data_pedido) == ano_anterior
        )
        
        # Aplica mesma lógica de grupo da função anterior
        if grupo and grupo != 'RESTANTE':
            # Busca todos os prefixos do grupo
            prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.nome_grupo == grupo,
                GrupoEmpresarial.ativo == True
            ).all()
            
            if prefixos_grupo:
                prefixos = [p[0] for p in prefixos_grupo]
                cnpj_filters = []
                for prefixo in prefixos:
                    cnpj_filters.append(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
                    )
                if cnpj_filters:
                    query = query.filter(or_(*cnpj_filters))
                    
        elif grupo == 'RESTANTE':
            # Busca todos os prefixos cadastrados
            todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                GrupoEmpresarial.ativo == True
            ).all()
            
            if todos_prefixos:
                for prefixo_tuple in todos_prefixos:
                    prefixo = prefixo_tuple[0]
                    query = query.filter(
                        func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
                    )
        
        resultado = query.scalar() or 0
        return float(resultado)