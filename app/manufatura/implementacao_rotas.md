# IMPLEMENTAÇÃO - ROTAS E ENDPOINTS

## 1. ESTRUTURA DE ARQUIVOS

```
app/manufatura/
├── __init__.py
├── models.py
├── routes/
│   ├── __init__.py
│   ├── previsao_demanda_routes.py
│   ├── plano_mestre_routes.py
│   ├── ordem_producao_routes.py
│   ├── requisicao_compras_routes.py
│   └── dashboard_routes.py
├── services/
│   ├── __init__.py
│   ├── previsao_service.py
│   ├── pmp_service.py
│   ├── ordem_service.py
│   ├── explosao_materiais_service.py
│   └── integracao_odoo_service.py
├── utils/
│   ├── __init__.py
│   ├── calculo_demanda.py
│   ├── sequenciamento.py
│   └── validacoes.py
└── templates/
    ├── dashboard.html
    ├── previsao_demanda.html
    ├── plano_mestre.html
    ├── ordens_producao.html
    └── necessidades_compra.html
```

## 2. BLUEPRINT PRINCIPAL

### Arquivo: app/manufatura/__init__.py
```python
from flask import Blueprint

manufatura_bp = Blueprint('manufatura', __name__, url_prefix='/manufatura')

from app.manufatura.routes import (
    previsao_demanda_routes,
    plano_mestre_routes,
    ordem_producao_routes,
    requisicao_compras_routes,
    dashboard_routes
)
```

## 3. ROTAS DE PREVISÃO DE DEMANDA

### Arquivo: app/manufatura/routes/previsao_demanda_routes.py
```python
@manufatura_bp.route('/previsao-demanda')
@login_required
def listar_previsao():
    # GET /manufatura/previsao-demanda
    # Query params: mes, ano, grupo
    pass

@manufatura_bp.route('/previsao-demanda/criar', methods=['GET', 'POST'])
@login_required
def criar_previsao():
    # GET: Formulário
    # POST: Criar previsão
    # Campos: data_mes, data_ano, nome_grupo, cod_produto, qtd_demanda_prevista, disparo_producao
    pass

@manufatura_bp.route('/previsao-demanda/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_previsao(id):
    # GET: Formulário com dados
    # POST: Atualizar previsão
    pass

@manufatura_bp.route('/api/previsao-demanda/calcular-realizado', methods=['POST'])
@login_required
def calcular_demanda_realizada():
    # POST body: {mes, ano, cod_produto, nome_grupo}
    # Retorna: {qtd_demanda_realizada}
    pass

@manufatura_bp.route('/api/previsao-demanda/importar-historico', methods=['POST'])
@login_required
def importar_historico():
    # POST: Importa HistoricoPedidos do período
    pass
```

## 4. ROTAS DO PLANO MESTRE

### Arquivo: app/manufatura/routes/plano_mestre_routes.py
```python
@manufatura_bp.route('/plano-mestre')
@login_required
def listar_plano_mestre():
    # GET /manufatura/plano-mestre
    # Query params: mes, ano, status_geracao
    pass

@manufatura_bp.route('/plano-mestre/gerar', methods=['POST'])
@login_required
def gerar_plano_mestre():
    # POST body: {data_mes, data_ano}
    # Gera PMP baseado em PrevisaoDemanda
    pass

@manufatura_bp.route('/plano-mestre/<int:id>/aprovar', methods=['POST'])
@login_required
def aprovar_plano_mestre(id):
    # POST: Muda status_geracao para 'aprovado'
    pass

@manufatura_bp.route('/api/plano-mestre/calcular-reposicao', methods=['POST'])
@login_required
def calcular_reposicao():
    # POST body: {cod_produto, mes, ano}
    # Retorna: {qtd_reposicao_sugerida, qtd_lote_ideal, qtd_lote_minimo}
    pass

@manufatura_bp.route('/plano-mestre/<int:id>/definir-seguranca', methods=['POST'])
@login_required
def definir_estoque_seguranca(id):
    # POST body: {qtd_estoque_seguranca}
    pass
```

## 5. ROTAS DE ORDEM DE PRODUÇÃO

### Arquivo: app/manufatura/routes/ordem_producao_routes.py
```python
@manufatura_bp.route('/ordens-producao')
@login_required
def listar_ordens():
    # GET /manufatura/ordens-producao
    # Query params: status, linha_producao, data_inicio, data_fim
    pass

@manufatura_bp.route('/ordens-producao/criar', methods=['GET', 'POST'])
@login_required
def criar_ordem():
    # GET: Formulário
    # POST: Criar ordem
    # Campos: cod_produto, qtd_planejada, data_inicio_prevista, data_fim_prevista, linha_producao, origem_ordem
    pass

@manufatura_bp.route('/ordens-producao/<numero_ordem>')
@login_required
def visualizar_ordem(numero_ordem):
    # GET: Detalhes da ordem incluindo materiais_necessarios
    pass

@manufatura_bp.route('/ordens-producao/<numero_ordem>/liberar', methods=['POST'])
@login_required
def liberar_ordem(numero_ordem):
    # POST: Muda status para 'Liberada'
    pass

@manufatura_bp.route('/ordens-producao/<numero_ordem>/iniciar', methods=['POST'])
@login_required
def iniciar_ordem(numero_ordem):
    # POST: Muda status para 'Em Produção', define data_inicio_real
    pass

@manufatura_bp.route('/api/ordens-producao/criar-mto', methods=['POST'])
@login_required
def criar_ordem_mto():
    # POST body: {separacao_lote_id}
    # Cria ordem automática para produtos MTO
    pass

@manufatura_bp.route('/api/ordens-producao/explodir-materiais', methods=['POST'])
@login_required
def explodir_materiais():
    # POST body: {cod_produto, qtd_planejada}
    # Retorna: {materiais_necessarios: [{cod_produto, qtd_necessaria, qtd_disponivel, qtd_comprar}]}
    pass

@manufatura_bp.route('/ordens-producao/sequenciamento')
@login_required
def tela_sequenciamento():
    # GET: Tela de sequenciamento (kanban/gantt)
    pass

@manufatura_bp.route('/api/ordens-producao/verificar-conflito', methods=['POST'])
@login_required
def verificar_conflito():
    # POST body: {linha_producao, data_inicio, data_fim}
    # Retorna: {conflito: bool, ordens_conflitantes: []}
    pass

@manufatura_bp.route('/api/ordens-producao/atualizar-sequencia', methods=['POST'])
@login_required
def atualizar_sequencia():
    # POST body: {ordens: [{numero_ordem, prioridade, data_inicio_prevista, data_fim_prevista}]}
    pass
```

## 6. ROTAS DE REQUISIÇÃO DE COMPRAS

### Arquivo: app/manufatura/routes/requisicao_compras_routes.py
```python
@manufatura_bp.route('/necessidades-compra')
@login_required
def listar_necessidades():
    # GET: Lista necessidades pendentes (To-Do List)
    # Sistema gera automaticamente baseado em ordens de produção
    # PCP visualiza e usa como guia para criar requisições no Odoo
    pass

@manufatura_bp.route('/api/necessidades-compra/gerar', methods=['POST'])
@login_required
def gerar_necessidades():
    # POST: Analisa ordens e gera lista de necessidades
    # Cria registros de necessidade com status "Pendente"
    # Agrupa por produto e calcula data_necessidade
    pass

@manufatura_bp.route('/necessidades-compra/<int:id>/marcar-requisitada', methods=['POST'])
@login_required
def marcar_como_requisitada(id):
    # POST: PCP marca que criou requisição no Odoo
    # Atualiza status da necessidade para "Requisitada"
    # Não cria requisição, apenas marca como feito
    pass

@manufatura_bp.route('/requisicoes-compra')
@login_required
def listar_requisicoes():
    # GET: Lista requisições IMPORTADAS do Odoo
    # Jobs automáticos trazem requisições criadas no Odoo
    pass

@manufatura_bp.route('/pedidos-compra')
@login_required
def listar_pedidos_compra():
    # GET: Lista pedidos IMPORTADOS do Odoo
    # Jobs automáticos trazem pedidos criados no Odoo
    pass

@manufatura_bp.route('/api/requisicoes/sincronizar-odoo', methods=['POST'])
@login_required
def sincronizar_requisicoes_odoo():
    # POST: Força sincronização manual com Odoo
    # Importa requisições e pedidos novos/atualizados
    pass

@manufatura_bp.route('/api/lead-time/consultar', methods=['POST'])
@login_required
def consultar_lead_time():
    # POST body: {cod_produto, cnpj_fornecedor}
    # Retorna: {lead_time_previsto, lead_time_historico}
    pass
```

## 7. ROTAS DO DASHBOARD

### Arquivo: app/manufatura/routes/dashboard_routes.py
```python
@manufatura_bp.route('/dashboard')
@login_required
def dashboard():
    # GET: Dashboard principal
    pass

@manufatura_bp.route('/api/dashboard/indicadores')
@login_required
def indicadores_dashboard():
    # GET: Retorna JSON com indicadores
    # {
    #   ordens_atrasadas: int,
    #   taxa_ocupacao_linhas: float,
    #   materiais_criticos: [],
    #   aderencia_plano: float
    # }
    pass

@manufatura_bp.route('/api/dashboard/demanda-vs-capacidade')
@login_required
def demanda_vs_capacidade():
    # GET: Dados para gráfico
    pass

@manufatura_bp.route('/api/dashboard/materiais-faltantes')
@login_required
def materiais_faltantes():
    # GET: Lista materiais com estoque crítico
    pass
```

## 8. SERVIÇOS PRINCIPAIS

### Arquivo: app/manufatura/services/explosao_materiais_service.py
```python
def explodir_materiais(cod_produto, qtd_planejada):
    """
    Retorna lista de materiais necessários
    """
    # Query ListaMateriais WHERE cod_produto_produzido = cod_produto AND status = 'ativo'
    # Para cada componente:
    #   qtd_necessaria = qtd_planejada * qtd_utilizada
    #   qtd_disponivel = query MovimentacaoEstoque
    #   qtd_comprar = max(0, qtd_necessaria - qtd_disponivel)
    return materiais_necessarios

def calcular_data_necessidade(data_inicio_producao, cod_produto):
    """
    Calcula quando material precisa estar disponível
    """
    # Query LeadTimeFornecedor
    # data_necessidade = data_inicio_producao - lead_time_previsto
    return data_necessidade
```

### Arquivo: app/manufatura/services/ordem_service.py
```python
def criar_ordem_mto(separacao_lote_id):
    """
    Cria ordem automática para produto MTO
    """
    # 1. Query Separacao/PreSeparacaoItem
    # 2. Verificar CadastroPalletizacao.disparo_producao = 'MTO'
    # 3. Calcular data_inicio = expedicao - lead_time_mto
    # 4. Criar OrdemProducao
    # 5. Explodir materiais
    # 6. Atualizar CarteiraPrincipal.ordem_producao_id
    pass

def sequenciar_ordens(linha_producao, data_inicio, data_fim):
    """
    Retorna ordens sequenciadas sem conflito
    """
    # Query ordens na linha e período
    # Ordenar por prioridade e data
    # Ajustar datas para evitar sobreposição
    pass

def calcular_prioridade_ordem(ordem):
    """
    Calcula prioridade baseada em critérios
    """
    # 1. Pedidos com expedicao próxima (Separacao)
    # 2. Estoque de segurança baixo
    # 3. Lead time componentes
    # 4. Disponibilidade linha
    return prioridade
```

## 9. QUERIES CRÍTICAS

### Arquivo: app/manufatura/utils/calculo_demanda.py
```python
def calcular_demanda_pedidos_ativos(cod_produto, mes, ano):
    """
    Calcula demanda excluindo pedidos faturados
    """
    query = """
        SELECT SUM(s.qtd_saldo) as demanda
        FROM separacao s
        JOIN pedido p ON s.separacao_lote_id = p.separacao_lote_id
        WHERE s.cod_produto = :cod_produto
        AND EXTRACT(MONTH FROM s.expedicao) = :mes
        AND EXTRACT(YEAR FROM s.expedicao) = :ano
        AND p.status != 'FATURADO'
        AND NOT EXISTS (
            SELECT 1 FROM pre_separacao_item psi
            WHERE psi.separacao_lote_id = s.separacao_lote_id
        )
    """
    return query

def verificar_disponibilidade_linha(linha_producao, data_inicio, data_fim):
    """
    Verifica se linha está disponível no período
    """
    query = """
        SELECT COUNT(*) as conflitos
        FROM ordem_producao
        WHERE linha_producao = :linha
        AND status NOT IN ('Concluída', 'Cancelada')
        AND (
            (data_inicio_prevista <= :data_fim AND data_fim_prevista >= :data_inicio)
            OR (data_inicio_real <= :data_fim AND data_fim_real >= :data_inicio)
        )
    """
    return query
```

## 10. VALIDAÇÕES

### Arquivo: app/manufatura/utils/validacoes.py
```python
def validar_ordem_producao(cod_produto):
    """
    Valida se produto pode ter ordem
    """
    # Query CadastroPalletizacao.produto_produzido = True
    pass

def validar_requisicao_compra(cod_produto):
    """
    Valida se produto pode ser comprado
    """
    # Query CadastroPalletizacao.produto_comprado = True
    pass

def validar_pedido_nao_faturado(separacao_lote_id):
    """
    Valida que pedido não está faturado
    """
    # Query Pedido.status != 'FATURADO'
    # join Pedido.separacao_lote_id com Separacao.separacao_lote_id
    pass

def evitar_duplicacao_separacao(separacao_lote_id):
    """
    Garante que não duplica PreSeparacao e Separacao
    """
    # Se mesmo separacao_lote_id existe em ambas tabelas,
    # usar APENAS Separacao (tem prioridade)
    # PreSeparacaoItem só é considerada se não existe em Separacao
    pass
```