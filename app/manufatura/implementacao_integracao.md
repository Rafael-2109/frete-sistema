# IMPLEMENTAÇÃO - INTEGRAÇÃO ODOO E JOBS

## 1. CONFIGURAÇÃO APSCHEDULER

### Arquivo: app/scheduler_manufatura.py
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

scheduler = BackgroundScheduler()

# Jobs de integração
scheduler.add_job(
    func='app.manufatura.jobs.odoo_integration:importar_requisicoes_odoo',
    trigger=IntervalTrigger(minutes=30),
    id='importar_requisicoes',
    name='Importar Requisições do Odoo',
    replace_existing=True
)

scheduler.add_job(
    func='app.manufatura.jobs.odoo_integration:importar_pedidos_compra_odoo',
    trigger=IntervalTrigger(minutes=30),
    id='importar_pedidos_compra',
    name='Importar Pedidos de Compra do Odoo',
    replace_existing=True
)

scheduler.add_job(
    func='app.manufatura.jobs.odoo_integration:importar_apontamentos_producao',
    trigger=IntervalTrigger(hours=1),
    id='importar_apontamentos',
    name='Importar Apontamentos de Produção',
    replace_existing=True
)

scheduler.add_job(
    func='app.manufatura.jobs.odoo_integration:importar_entradas_material',
    trigger=IntervalTrigger(minutes=30),
    id='importar_entradas',
    name='Importar Entradas de Material',
    replace_existing=True
)

scheduler.add_job(
    func='app.manufatura.jobs.calculo_demanda:atualizar_demanda_realizada',
    trigger=IntervalTrigger(hours=24),
    id='atualizar_demanda',
    name='Atualizar Demanda Realizada',
    replace_existing=True
)

scheduler.add_job(
    func='app.manufatura.jobs.ordem_producao:gerar_ordens_mto_automaticas',
    trigger=IntervalTrigger(hours=1),
    id='gerar_ordens_mto',
    name='Gerar Ordens MTO Automáticas',
    replace_existing=True
)

scheduler.start()
atexit.register(lambda: scheduler.shutdown())
```

## 2. JOBS DE INTEGRAÇÃO ODOO

### Arquivo: app/manufatura/jobs/odoo_integration.py
```python
import xmlrpc.client
from datetime import datetime, timedelta
from app import db
from app.manufatura.models import (
    RequisicaoCompras, PedidoCompras, OrdemProducao, 
    MovimentacaoEstoque, LeadTimeFornecedor
)

class OdooIntegration:
    def __init__(self):
        self.url = os.environ.get('ODOO_URL')
        self.db_name = os.environ.get('ODOO_DB')
        self.username = os.environ.get('ODOO_USER')
        self.password = os.environ.get('ODOO_PASSWORD')
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = self.common.authenticate(self.db_name, self.username, self.password, {})
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

def importar_requisicoes_odoo():
    """
    Job: Importa requisições de compra do Odoo
    Frequência: 30 minutos
    """
    odoo = OdooIntegration()
    
    # Buscar requisições criadas nas últimas 24h
    domain = [
        ('create_date', '>=', (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')),
        ('state', 'in', ['draft', 'sent', 'purchase'])
    ]
    
    requisicoes_odoo = odoo.models.execute_kw(
        odoo.db_name, odoo.uid, odoo.password,
        'purchase.requisition', 'search_read',
        [domain],
        {'fields': ['name', 'create_date', 'user_id', 'line_ids']}
    )
    
    for req_odoo in requisicoes_odoo:
        # Verificar se já existe
        requisicao = RequisicaoCompras.query.filter_by(
            odoo_id=str(req_odoo['id'])
        ).first()
        
        if not requisicao:
            # Buscar linhas da requisição
            linhas = odoo.models.execute_kw(
                odoo.db_name, odoo.uid, odoo.password,
                'purchase.requisition.line', 'read',
                [req_odoo['line_ids']],
                {'fields': ['product_id', 'product_qty', 'schedule_date']}
            )
            
            for linha in linhas:
                produto = odoo.models.execute_kw(
                    odoo.db_name, odoo.uid, odoo.password,
                    'product.product', 'read',
                    [linha['product_id'][0]],
                    {'fields': ['default_code', 'name']}
                )[0]
                
                nova_requisicao = RequisicaoCompras(
                    num_requisicao=req_odoo['name'],
                    data_requisicao_criacao=datetime.strptime(req_odoo['create_date'], '%Y-%m-%d %H:%M:%S').date(),
                    usuario_requisicao_criacao=req_odoo['user_id'][1] if req_odoo['user_id'] else None,
                    cod_produto=produto['default_code'],
                    nome_produto=produto['name'],
                    qtd_produto_requisicao=linha['product_qty'],
                    data_requisicao_solicitada=datetime.strptime(linha['schedule_date'], '%Y-%m-%d').date() if linha['schedule_date'] else None,
                    status='Requisitada',
                    importado_odoo=True,
                    odoo_id=str(req_odoo['id'])
                )
                db.session.add(nova_requisicao)
    
    db.session.commit()

def importar_pedidos_compra_odoo():
    """
    Job: Importa pedidos de compra do Odoo
    Frequência: 30 minutos
    """
    odoo = OdooIntegration()
    
    domain = [
        ('create_date', '>=', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),
        ('state', 'in', ['purchase', 'done'])
    ]
    
    pedidos_odoo = odoo.models.execute_kw(
        odoo.db_name, odoo.uid, odoo.password,
        'purchase.order', 'search_read',
        [domain],
        {'fields': ['name', 'partner_id', 'date_order', 'date_planned', 'order_line', 'requisition_id']}
    )
    
    for ped_odoo in pedidos_odoo:
        # Buscar linhas do pedido
        linhas = odoo.models.execute_kw(
            odoo.db_name, odoo.uid, odoo.password,
            'purchase.order.line', 'read',
            [ped_odoo['order_line']],
            {'fields': ['product_id', 'product_qty', 'price_unit', 'date_planned']}
        )
        
        for linha in linhas:
            produto = odoo.models.execute_kw(
                odoo.db_name, odoo.uid, odoo.password,
                'product.product', 'read',
                [linha['product_id'][0]],
                {'fields': ['default_code', 'name']}
            )[0]
            
            fornecedor = odoo.models.execute_kw(
                odoo.db_name, odoo.uid, odoo.password,
                'res.partner', 'read',
                [ped_odoo['partner_id'][0]],
                {'fields': ['vat', 'name']}
            )[0]
            
            # Verificar se já existe
            pedido = PedidoCompras.query.filter_by(
                odoo_id=str(ped_odoo['id']),
                cod_produto=produto['default_code']
            ).first()
            
            if not pedido:
                pedido = PedidoCompras(
                    num_pedido=ped_odoo['name'],
                    num_requisicao=ped_odoo['requisition_id'][1] if ped_odoo.get('requisition_id') else None,
                    cnpj_fornecedor=fornecedor['vat'],
                    raz_social=fornecedor['name'],
                    data_pedido_criacao=datetime.strptime(ped_odoo['date_order'], '%Y-%m-%d %H:%M:%S').date(),
                    data_pedido_previsao=datetime.strptime(linha['date_planned'], '%Y-%m-%d %H:%M:%S').date(),
                    cod_produto=produto['default_code'],
                    nome_produto=produto['name'],
                    qtd_produto_pedido=linha['product_qty'],
                    preco_produto_pedido=linha['price_unit'],
                    confirmacao_pedido=ped_odoo['state'] == 'done',
                    importado_odoo=True,
                    odoo_id=str(ped_odoo['id'])
                )
                db.session.add(pedido)
            else:
                # Atualizar status
                pedido.confirmacao_pedido = ped_odoo['state'] == 'done'
                pedido.data_pedido_previsao = datetime.strptime(linha['date_planned'], '%Y-%m-%d %H:%M:%S').date()
    
    db.session.commit()

def importar_apontamentos_producao():
    """
    Job: Importa apontamentos de produção do Odoo
    Frequência: 1 hora
    """
    odoo = OdooIntegration()
    
    # Buscar ordens em produção no sistema
    ordens_producao = OrdemProducao.query.filter(
        OrdemProducao.status.in_(['Em Produção', 'Liberada'])
    ).all()
    
    for ordem in ordens_producao:
        # Buscar ordem no Odoo pelo número
        domain = [('name', '=', ordem.numero_ordem)]
        
        ordem_odoo = odoo.models.execute_kw(
            odoo.db_name, odoo.uid, odoo.password,
            'mrp.production', 'search_read',
            [domain],
            {'fields': ['state', 'qty_produced', 'date_finished']}
        )
        
        if ordem_odoo:
            ordem_odoo = ordem_odoo[0]
            
            # Se tem quantidade produzida nova
            if ordem_odoo['qty_produced'] > float(ordem.qtd_produzida or 0):
                qtd_nova = ordem_odoo['qty_produced'] - float(ordem.qtd_produzida or 0)
                
                # Criar movimentação
                mov = MovimentacaoEstoque(
                    tipo_movimentacao='PRODUCAO',
                    cod_produto=ordem.cod_produto,
                    qtd_movimentacao=qtd_nova,
                    data_movimentacao=datetime.now(),
                    ordem_producao_id=ordem.id,
                    origem='Odoo',
                    usuario='Sistema'
                )
                db.session.add(mov)
                
                # Atualizar ordem
                ordem.qtd_produzida = ordem_odoo['qty_produced']
                
                if ordem_odoo['state'] == 'done':
                    ordem.status = 'Concluída'
                    ordem.data_fim_real = datetime.strptime(ordem_odoo['date_finished'], '%Y-%m-%d %H:%M:%S').date()
                elif ordem_odoo['state'] == 'progress' and ordem.status != 'Em Produção':
                    ordem.status = 'Em Produção'
                    ordem.data_inicio_real = datetime.now().date()
    
    db.session.commit()

def importar_entradas_material():
    """
    Job: Importa entradas de material do Odoo
    Frequência: 30 minutos
    """
    odoo = OdooIntegration()
    
    # Buscar recebimentos dos últimos 2 dias
    domain = [
        ('create_date', '>=', (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')),
        ('state', '=', 'done'),
        ('picking_type_code', '=', 'incoming')
    ]
    
    recebimentos = odoo.models.execute_kw(
        odoo.db_name, odoo.uid, odoo.password,
        'stock.picking', 'search_read',
        [domain],
        {'fields': ['name', 'partner_id', 'origin', 'date_done', 'move_lines']}
    )
    
    for receb in recebimentos:
        # Buscar movimentos
        movimentos = odoo.models.execute_kw(
            odoo.db_name, odoo.uid, odoo.password,
            'stock.move', 'read',
            [receb['move_lines']],
            {'fields': ['product_id', 'product_uom_qty', 'origin']}
        )
        
        for mov_odoo in movimentos:
            produto = odoo.models.execute_kw(
                odoo.db_name, odoo.uid, odoo.password,
                'product.product', 'read',
                [mov_odoo['product_id'][0]],
                {'fields': ['default_code', 'name']}
            )[0]
            
            # Verificar se produto é comprado
            from app.estoque.models import CadastroPalletizacao
            cad_produto = CadastroPalletizacao.query.filter_by(
                cod_produto=produto['default_code']
            ).first()
            
            if cad_produto and cad_produto.produto_comprado:
                # Verificar se já foi importado
                mov_existe = MovimentacaoEstoque.query.filter_by(
                    origem='Odoo',
                    referencia=receb['name'],
                    cod_produto=produto['default_code']
                ).first()
                
                if not mov_existe:
                    mov = MovimentacaoEstoque(
                        tipo_movimentacao='ENTRADA_COMPRA',
                        cod_produto=produto['default_code'],
                        qtd_movimentacao=mov_odoo['product_uom_qty'],
                        data_movimentacao=datetime.strptime(receb['date_done'], '%Y-%m-%d %H:%M:%S'),
                        num_pedido=mov_odoo['origin'],
                        origem='Odoo',
                        referencia=receb['name'],
                        usuario='Sistema'
                    )
                    db.session.add(mov)
                    
                    # Atualizar pedido de compra se existir
                    if mov_odoo['origin']:
                        pedido = PedidoCompras.query.filter_by(
                            num_pedido=mov_odoo['origin'],
                            cod_produto=produto['default_code']
                        ).first()
                        
                        if pedido:
                            pedido.data_pedido_entrega = datetime.strptime(receb['date_done'], '%Y-%m-%d %H:%M:%S').date()
                            pedido.confirmacao_pedido = True
                            
                            # Atualizar lead time histórico
                            if pedido.data_pedido_criacao and pedido.data_pedido_entrega:
                                dias_lead = (pedido.data_pedido_entrega - pedido.data_pedido_criacao).days
                                
                                lead_time = LeadTimeFornecedor.query.filter_by(
                                    cnpj_fornecedor=pedido.cnpj_fornecedor,
                                    cod_produto=pedido.cod_produto
                                ).first()
                                
                                if lead_time:
                                    # Média móvel
                                    if lead_time.lead_time_historico:
                                        lead_time.lead_time_historico = (lead_time.lead_time_historico + dias_lead) / 2
                                    else:
                                        lead_time.lead_time_historico = dias_lead
                                else:
                                    # Criar novo
                                    lead_time = LeadTimeFornecedor(
                                        cnpj_fornecedor=pedido.cnpj_fornecedor,
                                        nome_fornecedor=pedido.raz_social,
                                        cod_produto=pedido.cod_produto,
                                        nome_produto=pedido.nome_produto,
                                        lead_time_previsto=dias_lead,
                                        lead_time_historico=dias_lead
                                    )
                                    db.session.add(lead_time)
    
    db.session.commit()
```

## 3. JOBS DE CÁLCULO E AUTOMAÇÃO

### Arquivo: app/manufatura/jobs/calculo_demanda.py
```python
from datetime import datetime
from sqlalchemy import text
from app import db
from app.manufatura.models import PrevisaoDemanda, HistoricoPedidos

def atualizar_demanda_realizada():
    """
    Job: Atualiza demanda realizada baseada em histórico
    Frequência: Diária
    """
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    # Atualizar previsões do mês atual
    previsoes = PrevisaoDemanda.query.filter_by(
        data_mes=mes_atual,
        data_ano=ano_atual
    ).all()
    
    for previsao in previsoes:
        # Calcular demanda realizada
        query = text("""
            SELECT COALESCE(SUM(qtd_produto_pedido), 0) as total
            FROM historico_pedidos
            WHERE cod_produto = :cod_produto
            AND EXTRACT(MONTH FROM data_pedido) = :mes
            AND EXTRACT(YEAR FROM data_pedido) = :ano
            AND (:grupo IS NULL OR nome_grupo = :grupo)
        """)
        
        result = db.session.execute(query, {
            'cod_produto': previsao.cod_produto,
            'mes': previsao.data_mes,
            'ano': previsao.data_ano,
            'grupo': previsao.nome_grupo
        }).fetchone()
        
        previsao.qtd_demanda_realizada = result.total
        previsao.atualizado_em = datetime.now()
    
    db.session.commit()
```

### Arquivo: app/manufatura/jobs/ordem_producao.py
```python
from datetime import datetime, timedelta
from app import db
from app.manufatura.models import OrdemProducao
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.estoque.models import CadastroPalletizacao
from app.manufatura.services.explosao_materiais_service import explodir_materiais
import holidays

def gerar_ordens_mto_automaticas():
    """
    Job: Gera ordens MTO para pedidos novos
    Frequência: 1 hora
    """
    # Buscar separações sem ordem de produção
    # IMPORTANTE: Separacao tem prioridade sobre PreSeparacaoItem
    query = text("""
        SELECT DISTINCT s.separacao_lote_id, s.cod_produto, s.expedicao, 
               SUM(s.qtd_saldo) as qtd_total
        FROM separacao s
        JOIN pedido p ON s.separacao_lote_id = p.separacao_lote_id
        JOIN cadastro_palletizacao cp ON s.cod_produto = cp.cod_produto
        LEFT JOIN carteira_principal cart ON cart.separacao_lote_id = s.separacao_lote_id
        WHERE p.status NOT IN ('FATURADO', 'CANCELADO')
        AND cp.disparo_producao = 'MTO'
        AND cp.produto_produzido = true
        AND cp.lead_time_mto IS NOT NULL
        AND cart.ordem_producao_id IS NULL
        GROUP BY s.separacao_lote_id, s.cod_produto, s.expedicao
        
        UNION ALL
        
        SELECT DISTINCT psi.separacao_lote_id, psi.cod_produto, 
               psi.data_expedicao_editada as expedicao,
               SUM(psi.qtd_selecionada_usuario) as qtd_total
        FROM pre_separacao_item psi
        JOIN cadastro_palletizacao cp ON psi.cod_produto = cp.cod_produto
        WHERE cp.disparo_producao = 'MTO'
        AND cp.produto_produzido = true
        AND cp.lead_time_mto IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM separacao s
            WHERE s.separacao_lote_id = psi.separacao_lote_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM carteira_principal cart
            WHERE cart.separacao_lote_id = psi.separacao_lote_id
            AND cart.ordem_producao_id IS NOT NULL
        )
        GROUP BY psi.separacao_lote_id, psi.cod_produto, psi.data_expedicao_editada
    """)
    
    pedidos_mto = db.session.execute(query).fetchall()
    
    br_holidays = holidays.Brazil()
    
    for pedido in pedidos_mto:
        # Buscar informações do produto
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=pedido.cod_produto
        ).first()
        
        if produto:
            # Calcular data início (considerando dias úteis)
            data_expedicao = pedido.expedicao
            dias_uteis = produto.lead_time_mto
            data_inicio = calcular_data_util_retroativa(data_expedicao, dias_uteis, br_holidays)
            
            # Gerar número da ordem
            numero_ordem = gerar_numero_ordem()
            
            # Explodir materiais
            materiais = explodir_materiais(pedido.cod_produto, pedido.qtd_total)
            
            # Criar ordem
            ordem = OrdemProducao(
                numero_ordem=numero_ordem,
                origem_ordem='MTO',
                status='Planejada',
                cod_produto=pedido.cod_produto,
                nome_produto=produto.nome_produto,
                materiais_necessarios=materiais,
                qtd_planejada=pedido.qtd_total,
                data_inicio_prevista=data_inicio,
                data_fim_prevista=data_expedicao - timedelta(days=1),
                criado_por='Sistema MTO'
            )
            db.session.add(ordem)
            db.session.flush()
            
            # Atualizar CarteiraPrincipal
            db.session.execute(
                text("""
                    UPDATE carteira_principal 
                    SET ordem_producao_id = :ordem_id,
                        disparo_producao = 'MTO'
                    WHERE separacao_lote_id = :lote_id
                    AND cod_produto = :cod_produto
                """),
                {
                    'ordem_id': ordem.id,
                    'lote_id': pedido.separacao_lote_id,
                    'cod_produto': pedido.cod_produto
                }
            )
    
    db.session.commit()

def calcular_data_util_retroativa(data_fim, dias_uteis, feriados):
    """
    Calcula data retroativa considerando apenas dias úteis
    """
    data = data_fim
    dias_contados = 0
    
    while dias_contados < dias_uteis:
        data = data - timedelta(days=1)
        # Se não é fim de semana nem feriado
        if data.weekday() < 5 and data not in feriados:
            dias_contados += 1
    
    return data

def gerar_numero_ordem():
    """
    Gera número sequencial para ordem
    """
    ultimo = db.session.query(
        db.func.max(OrdemProducao.numero_ordem)
    ).scalar()
    
    if ultimo:
        numero = int(ultimo.split('-')[1]) + 1
    else:
        numero = 1
    
    return f"OP-{numero:06d}"
```

## 4. CONFIGURAÇÃO DE VARIÁVEIS DE AMBIENTE

### Arquivo: .env
```
# Odoo Integration
ODOO_URL=http://odoo.empresa.com.br
ODOO_DB=producao
ODOO_USER=integracao_pcp
ODOO_PASSWORD=senha_segura_aqui

# Scheduler
SCHEDULER_API_ENABLED=true
SCHEDULER_TIMEZONE=America/Sao_Paulo
```

## 5. ENDPOINTS DE CONTROLE DOS JOBS

### Arquivo: app/manufatura/routes/jobs_routes.py
```python
@manufatura_bp.route('/jobs/status')
@login_required
def status_jobs():
    """
    GET: Status de todos os jobs
    """
    from app.scheduler_manufatura import scheduler
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time,
            'trigger': str(job.trigger)
        })
    
    return jsonify(jobs)

@manufatura_bp.route('/jobs/<job_id>/executar', methods=['POST'])
@login_required
def executar_job(job_id):
    """
    POST: Executa job manualmente
    """
    from app.scheduler_manufatura import scheduler
    
    job = scheduler.get_job(job_id)
    if job:
        job.func()
        return jsonify({'status': 'executado'})
    
    return jsonify({'erro': 'Job não encontrado'}), 404

@manufatura_bp.route('/jobs/<job_id>/pausar', methods=['POST'])
@login_required
def pausar_job(job_id):
    """
    POST: Pausa job
    """
    from app.scheduler_manufatura import scheduler
    
    scheduler.pause_job(job_id)
    return jsonify({'status': 'pausado'})

@manufatura_bp.route('/jobs/<job_id>/retomar', methods=['POST'])
@login_required
def retomar_job(job_id):
    """
    POST: Retoma job
    """
    from app.scheduler_manufatura import scheduler
    
    scheduler.resume_job(job_id)
    return jsonify({'status': 'retomado'})
```

## 6. LOGS DE INTEGRAÇÃO

### Arquivo: app/manufatura/models.py (adicionar)
```python
class LogIntegracao(db.Model):
    __tablename__ = 'log_integracao'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo_integracao = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text)
    registros_processados = db.Column(db.Integer, default=0)
    registros_erro = db.Column(db.Integer, default=0)
    data_execucao = db.Column(db.DateTime, default=datetime.utcnow)
    tempo_execucao = db.Column(db.Float)
    detalhes = db.Column(JSONB)
```

## 7. TRATAMENTO DE ERROS NOS JOBS

### Arquivo: app/manufatura/jobs/base_job.py
```python
import functools
import time
from app import db
from app.manufatura.models import LogIntegracao

def log_job_execution(tipo_integracao):
    """
    Decorator para logar execução de jobs
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            inicio = time.time()
            log = LogIntegracao(
                tipo_integracao=tipo_integracao,
                status='executando'
            )
            
            try:
                resultado = func(*args, **kwargs)
                log.status = 'sucesso'
                log.registros_processados = resultado.get('processados', 0) if isinstance(resultado, dict) else 0
                return resultado
                
            except Exception as e:
                log.status = 'erro'
                log.mensagem = str(e)
                log.registros_erro = 1
                db.session.rollback()
                raise
                
            finally:
                log.tempo_execucao = time.time() - inicio
                db.session.add(log)
                db.session.commit()
        
        return wrapper
    return decorator

# Uso nos jobs:
@log_job_execution('importar_requisicoes')
def importar_requisicoes_odoo():
    # código do job
    pass
```