# IMPLEMENTAÇÃO - QUERIES SQL E TEMPLATES

## 1. QUERIES SQL CRÍTICAS

### 1.1 Demanda Ativa (Excluindo Faturados)
```sql
-- Demanda por produto excluindo pedidos faturados
-- IMPORTANTE: Separacao tem prioridade sobre PreSeparacaoItem
CREATE OR REPLACE VIEW v_demanda_ativa AS
SELECT 
    s.cod_produto,
    s.nome_produto,
    EXTRACT(MONTH FROM s.expedicao) as mes,
    EXTRACT(YEAR FROM s.expedicao) as ano,
    SUM(s.qtd_saldo) as qtd_demanda
FROM separacao s
JOIN pedido p ON s.separacao_lote_id = p.separacao_lote_id
WHERE p.status != 'FATURADO'
GROUP BY s.cod_produto, s.nome_produto, mes, ano

UNION ALL

-- PreSeparacaoItem só se NÃO existe em Separacao
SELECT 
    psi.cod_produto,
    psi.nome_produto,
    EXTRACT(MONTH FROM psi.data_expedicao_editada) as mes,
    EXTRACT(YEAR FROM psi.data_expedicao_editada) as ano,
    SUM(psi.qtd_selecionada_usuario) as qtd_demanda
FROM pre_separacao_item psi
WHERE NOT EXISTS (
    SELECT 1 FROM separacao s
    WHERE s.separacao_lote_id = psi.separacao_lote_id
)
GROUP BY psi.cod_produto, psi.nome_produto, mes, ano;
```

### 1.2 Estoque Disponível por Produto
```sql
-- Estoque atual considerando todas movimentações
CREATE OR REPLACE VIEW v_estoque_atual AS
SELECT 
    cod_produto,
    SUM(CASE 
        WHEN tipo_movimentacao IN ('ENTRADA_COMPRA', 'PRODUCAO', 'AJUSTE_POSITIVO') 
        THEN qtd_movimentacao
        WHEN tipo_movimentacao IN ('SAIDA_VENDA', 'CONSUMO_BOM', 'AJUSTE_NEGATIVO', 'REFUGO')
        THEN -qtd_movimentacao
        ELSE 0
    END) as estoque_atual
FROM movimentacao_estoque
GROUP BY cod_produto;
```

### 1.3 Explosão de Materiais Recursiva
```sql
-- BOM multi-nível
WITH RECURSIVE bom_explodida AS (
    -- Nível 0: produto principal
    SELECT 
        :cod_produto as cod_produto_pai,
        cod_produto_componente,
        nome_produto_componente,
        qtd_utilizada * :qtd_base as qtd_necessaria,
        0 as nivel
    FROM lista_materiais
    WHERE cod_produto_produzido = :cod_produto
    AND status = 'ativo'
    
    UNION ALL
    
    -- Níveis subsequentes
    SELECT 
        be.cod_produto_componente as cod_produto_pai,
        lm.cod_produto_componente,
        lm.nome_produto_componente,
        be.qtd_necessaria * lm.qtd_utilizada as qtd_necessaria,
        be.nivel + 1
    FROM bom_explodida be
    JOIN lista_materiais lm ON lm.cod_produto_produzido = be.cod_produto_componente
    WHERE lm.status = 'ativo'
    AND be.nivel < 10  -- Limitar recursão
)
SELECT 
    cod_produto_componente,
    nome_produto_componente,
    SUM(qtd_necessaria) as qtd_total_necessaria
FROM bom_explodida
GROUP BY cod_produto_componente, nome_produto_componente;
```

### 1.4 Disponibilidade de Linha de Produção
```sql
-- Verificar conflitos de linha
CREATE OR REPLACE FUNCTION verificar_disponibilidade_linha(
    p_linha VARCHAR(50),
    p_data_inicio DATE,
    p_data_fim DATE,
    p_ordem_excluir VARCHAR(20) DEFAULT NULL
) RETURNS TABLE(
    disponivel BOOLEAN,
    ordens_conflito VARCHAR[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) = 0 as disponivel,
        ARRAY_AGG(numero_ordem) as ordens_conflito
    FROM ordem_producao
    WHERE linha_producao = p_linha
    AND status NOT IN ('Concluída', 'Cancelada')
    AND (p_ordem_excluir IS NULL OR numero_ordem != p_ordem_excluir)
    AND (
        (data_inicio_prevista, data_fim_prevista) OVERLAPS (p_data_inicio, p_data_fim)
        OR (data_inicio_real, data_fim_real) OVERLAPS (p_data_inicio, p_data_fim)
    );
END;
$$ LANGUAGE plpgsql;
```

### 1.5 Cálculo de Necessidades de Compra
```sql
-- Necessidades consolidadas
CREATE OR REPLACE VIEW v_necessidades_compra AS
SELECT 
    om.cod_produto,
    om.nome_produto,
    SUM(om.qtd_necessaria) as qtd_total_necessaria,
    COALESCE(ea.estoque_atual, 0) as estoque_disponivel,
    GREATEST(0, SUM(om.qtd_necessaria) - COALESCE(ea.estoque_atual, 0)) as qtd_comprar,
    MIN(op.data_inicio_prevista) as data_necessidade,
    ARRAY_AGG(DISTINCT op.numero_ordem) as ordens_impactadas
FROM (
    SELECT 
        jsonb_array_elements(materiais_necessarios)->>'cod_produto' as cod_produto,
        jsonb_array_elements(materiais_necessarios)->>'nome_produto' as nome_produto,
        (jsonb_array_elements(materiais_necessarios)->>'qtd_necessaria')::NUMERIC as qtd_necessaria,
        id as ordem_id
    FROM ordem_producao
    WHERE status IN ('Planejada', 'Liberada')
) om
JOIN ordem_producao op ON op.id = om.ordem_id
LEFT JOIN v_estoque_atual ea ON ea.cod_produto = om.cod_produto
JOIN cadastro_palletizacao cp ON cp.cod_produto = om.cod_produto
WHERE cp.produto_comprado = true
GROUP BY om.cod_produto, om.nome_produto, ea.estoque_atual
HAVING GREATEST(0, SUM(om.qtd_necessaria) - COALESCE(ea.estoque_atual, 0)) > 0;
```

### 1.6 Dashboard - Indicadores
```sql
-- KPIs do módulo
CREATE OR REPLACE VIEW v_dashboard_manufatura AS
SELECT 
    -- Ordens atrasadas
    (SELECT COUNT(*) FROM ordem_producao 
     WHERE status IN ('Planejada', 'Liberada', 'Em Produção')
     AND data_fim_prevista < CURRENT_DATE) as ordens_atrasadas,
    
    -- Taxa ocupação linhas
    (SELECT 
        AVG(ocupacao) as taxa_ocupacao_media
     FROM (
        SELECT 
            linha_producao,
            SUM(EXTRACT(EPOCH FROM (data_fim_prevista - data_inicio_prevista))/3600) / 
            (8 * 22) * 100 as ocupacao -- 8h/dia, 22 dias/mês
        FROM ordem_producao
        WHERE status IN ('Liberada', 'Em Produção')
        AND EXTRACT(MONTH FROM data_inicio_prevista) = EXTRACT(MONTH FROM CURRENT_DATE)
        GROUP BY linha_producao
     ) t) as taxa_ocupacao_linhas,
    
    -- Aderência ao plano
    (SELECT 
        CASE WHEN SUM(qtd_planejada) > 0 
        THEN SUM(qtd_produzida) / SUM(qtd_planejada) * 100
        ELSE 0 END
     FROM ordem_producao
     WHERE EXTRACT(MONTH FROM data_inicio_prevista) = EXTRACT(MONTH FROM CURRENT_DATE)
    ) as aderencia_plano,
    
    -- Materiais críticos (estoque < 3 dias)
    (SELECT COUNT(DISTINCT cod_produto)
     FROM v_necessidades_compra
     WHERE data_necessidade <= CURRENT_DATE + INTERVAL '3 days'
    ) as materiais_criticos;
```

## 2. TEMPLATES HTML

### 2.1 Dashboard Principal
```html
<!-- app/manufatura/templates/dashboard.html -->
{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <h2>Dashboard PCP</h2>
    
    <!-- Indicadores -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-white bg-danger">
                <div class="card-body">
                    <h5 class="card-title">Ordens Atrasadas</h5>
                    <h2 id="ordens-atrasadas">0</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-white bg-info">
                <div class="card-body">
                    <h5 class="card-title">Taxa Ocupação</h5>
                    <h2 id="taxa-ocupacao">0%</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-white bg-success">
                <div class="card-body">
                    <h5 class="card-title">Aderência Plano</h5>
                    <h2 id="aderencia-plano">0%</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-white bg-warning">
                <div class="card-body">
                    <h5 class="card-title">Materiais Críticos</h5>
                    <h2 id="materiais-criticos">0</h2>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Tabs -->
    <ul class="nav nav-tabs" role="tablist">
        <li class="nav-item">
            <a class="nav-link active" data-toggle="tab" href="#ordens">Ordens Produção</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-toggle="tab" href="#necessidades">Necessidades Compra</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-toggle="tab" href="#sequenciamento">Sequenciamento</a>
        </li>
    </ul>
    
    <div class="tab-content mt-3">
        <div id="ordens" class="tab-pane active">
            <table class="table table-striped" id="tabela-ordens">
                <thead>
                    <tr>
                        <th>Número</th>
                        <th>Produto</th>
                        <th>Qtd Plan.</th>
                        <th>Qtd Prod.</th>
                        <th>Status</th>
                        <th>Início</th>
                        <th>Fim</th>
                        <th>Linha</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div id="necessidades" class="tab-pane">
            <table class="table table-striped" id="tabela-necessidades">
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th>Qtd Necessária</th>
                        <th>Estoque</th>
                        <th>Comprar</th>
                        <th>Data Necessidade</th>
                        <th>Ordens</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div id="sequenciamento" class="tab-pane">
            <div id="gantt-producao"></div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Carregar indicadores
    $.get('/manufatura/api/dashboard/indicadores', function(data) {
        $('#ordens-atrasadas').text(data.ordens_atrasadas);
        $('#taxa-ocupacao').text(data.taxa_ocupacao_linhas.toFixed(1) + '%');
        $('#aderencia-plano').text(data.aderencia_plano.toFixed(1) + '%');
        $('#materiais-criticos').text(data.materiais_criticos);
    });
    
    // DataTables
    $('#tabela-ordens').DataTable({
        ajax: '/manufatura/api/ordens-producao/listar',
        columns: [
            {data: 'numero_ordem'},
            {data: 'nome_produto'},
            {data: 'qtd_planejada'},
            {data: 'qtd_produzida'},
            {data: 'status'},
            {data: 'data_inicio_prevista'},
            {data: 'data_fim_prevista'},
            {data: 'linha_producao'},
            {data: 'acoes', orderable: false}
        ]
    });
    
    $('#tabela-necessidades').DataTable({
        ajax: '/manufatura/api/necessidades-compra/listar',
        columns: [
            {data: 'nome_produto'},
            {data: 'qtd_total_necessaria'},
            {data: 'estoque_disponivel'},
            {data: 'qtd_comprar'},
            {data: 'data_necessidade'},
            {data: 'ordens_impactadas'},
            {data: 'status'},
            {data: 'acoes', orderable: false}
        ]
    });
    
    // Gantt de sequenciamento
    carregarGantt();
});

function carregarGantt() {
    $.get('/manufatura/api/ordens-producao/gantt', function(data) {
        // Usar biblioteca como dhtmlxGantt ou Google Charts
    });
}
</script>
{% endblock %}
```

### 2.2 Formulário Ordem de Produção
```html
<!-- app/manufatura/templates/ordem_form.html -->
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h2>{{ 'Editar' if ordem else 'Nova' }} Ordem de Produção</h2>
    
    <form method="POST" id="form-ordem">
        {{ form.hidden_tag() }}
        
        <div class="row">
            <div class="col-md-6">
                <div class="form-group">
                    <label>Produto</label>
                    <select class="form-control select2" name="cod_produto" required>
                        <option value="">Selecione...</option>
                        {% for produto in produtos %}
                            <option value="{{ produto.cod_produto }}" 
                                    data-mto="{{ produto.disparo_producao }}"
                                    data-lead="{{ produto.lead_time_mto }}">
                                {{ produto.cod_produto }} - {{ produto.nome_produto }}
                            </option>
                        {% endfor %}
                    </select>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="form-group">
                    <label>Quantidade</label>
                    <input type="number" class="form-control" name="qtd_planejada" 
                           step="0.001" required>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="form-group">
                    <label>Origem</label>
                    <select class="form-control" name="origem_ordem">
                        <option value="PMP">Plano Mestre</option>
                        <option value="MTO">Make to Order</option>
                        <option value="Manual">Manual</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-3">
                <div class="form-group">
                    <label>Data Início</label>
                    <input type="date" class="form-control" name="data_inicio_prevista" required>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="form-group">
                    <label>Data Fim</label>
                    <input type="date" class="form-control" name="data_fim_prevista" required>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="form-group">
                    <label>Linha Produção</label>
                    <select class="form-control" name="linha_producao" id="linha_producao">
                        <option value="">Selecione...</option>
                    </select>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="form-group">
                    <label>Lote</label>
                    <input type="text" class="form-control" name="lote_producao">
                </div>
            </div>
        </div>
        
        <!-- Explosão de Materiais -->
        <div class="card mt-3">
            <div class="card-header">
                <h5>Materiais Necessários</h5>
                <button type="button" class="btn btn-sm btn-info" onclick="explodirMateriais()">
                    Calcular Materiais
                </button>
            </div>
            <div class="card-body">
                <table class="table table-sm" id="tabela-materiais">
                    <thead>
                        <tr>
                            <th>Componente</th>
                            <th>Qtd Necessária</th>
                            <th>Estoque</th>
                            <th>Comprar</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        
        <div class="form-group mt-3">
            <button type="button" class="btn btn-primary" onclick="verificarConflitos()">
                Verificar Disponibilidade
            </button>
            <button type="submit" class="btn btn-success">Salvar</button>
            <a href="{{ url_for('manufatura.listar_ordens') }}" class="btn btn-secondary">
                Cancelar
            </a>
        </div>
    </form>
</div>

<script>
function explodirMateriais() {
    const cod_produto = $('[name="cod_produto"]').val();
    const qtd_planejada = $('[name="qtd_planejada"]').val();
    
    if (!cod_produto || !qtd_planejada) {
        alert('Selecione produto e quantidade');
        return;
    }
    
    $.post('/manufatura/api/ordens-producao/explodir-materiais', {
        cod_produto: cod_produto,
        qtd_planejada: qtd_planejada
    }, function(data) {
        const tbody = $('#tabela-materiais tbody');
        tbody.empty();
        
        data.materiais_necessarios.forEach(function(mat) {
            tbody.append(`
                <tr class="${mat.qtd_comprar > 0 ? 'table-warning' : ''}">
                    <td>${mat.nome_produto}</td>
                    <td>${mat.qtd_necessaria}</td>
                    <td>${mat.qtd_disponivel}</td>
                    <td>${mat.qtd_comprar}</td>
                </tr>
            `);
        });
        
        // Salvar no campo hidden
        $('<input>').attr({
            type: 'hidden',
            name: 'materiais_necessarios',
            value: JSON.stringify(data.materiais_necessarios)
        }).appendTo('#form-ordem');
    });
}

function verificarConflitos() {
    const linha = $('#linha_producao').val();
    const data_inicio = $('[name="data_inicio_prevista"]').val();
    const data_fim = $('[name="data_fim_prevista"]').val();
    
    if (!linha || !data_inicio || !data_fim) {
        alert('Preencha linha e datas');
        return;
    }
    
    $.post('/manufatura/api/ordens-producao/verificar-conflito', {
        linha_producao: linha,
        data_inicio: data_inicio,
        data_fim: data_fim
    }, function(data) {
        if (data.conflito) {
            alert('Conflito com ordens: ' + data.ordens_conflitantes.join(', '));
        } else {
            alert('Linha disponível no período');
        }
    });
}

// Carregar linhas baseado no produto
$('[name="cod_produto"]').change(function() {
    const cod_produto = $(this).val();
    
    $.get('/manufatura/api/recursos-producao/linhas/' + cod_produto, function(data) {
        const select = $('#linha_producao');
        select.empty();
        select.append('<option value="">Selecione...</option>');
        
        data.linhas.forEach(function(linha) {
            select.append(`
                <option value="${linha.linha_producao}">
                    ${linha.linha_producao} (Cap: ${linha.capacidade_unidade_minuto}/min)
                </option>
            `);
        });
    });
});
</script>
{% endblock %}
```

## 3. ARQUIVO DE CONFIGURAÇÃO PRINCIPAL

### Arquivo: app/__init__.py (adicionar)
```python
# Registrar blueprint manufatura
from app.manufatura import manufatura_bp
app.register_blueprint(manufatura_bp)

# Inicializar scheduler
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    from app.scheduler_manufatura import scheduler
    # Scheduler já está iniciado no arquivo
```

## 4. REQUIREMENTS.TXT (adicionar)
```
APScheduler==3.10.4
holidays==0.35
```

## 5. COMANDOS FLASK CLI

### Arquivo: app/manufatura/commands.py
```python
import click
from flask.cli import with_appcontext
from app import db

@click.command()
@with_appcontext
def init_manufatura():
    """Inicializa módulo manufatura"""
    # Criar tabelas
    from app.manufatura import models
    db.create_all()
    
    # Inserir dados iniciais
    print("Módulo manufatura inicializado")

@click.command()
@click.argument('mes', type=int)
@click.argument('ano', type=int)
@with_appcontext
def gerar_pmp(mes, ano):
    """Gera Plano Mestre de Produção"""
    from app.manufatura.services.pmp_service import gerar_plano_mestre
    resultado = gerar_plano_mestre(mes, ano)
    print(f"PMP gerado: {resultado}")

# Registrar comandos
def register_commands(app):
    app.cli.add_command(init_manufatura)
    app.cli.add_command(gerar_pmp)
```

## 6. TESTES UNITÁRIOS

### Arquivo: tests/test_manufatura.py
```python
import unittest
from datetime import date, timedelta
from app import create_app, db
from app.manufatura.models import OrdemProducao, ListaMateriais
from app.manufatura.services.explosao_materiais_service import explodir_materiais

class TestManufatura(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_criar_ordem_producao(self):
        ordem = OrdemProducao(
            numero_ordem='OP-000001',
            origem_ordem='PMP',
            cod_produto='PROD001',
            nome_produto='Produto Teste',
            qtd_planejada=100,
            data_inicio_prevista=date.today(),
            data_fim_prevista=date.today() + timedelta(days=5)
        )
        db.session.add(ordem)
        db.session.commit()
        
        self.assertEqual(ordem.status, 'Planejada')
        self.assertEqual(ordem.qtd_produzida, 0)
    
    def test_explosao_materiais(self):
        # Criar BOM
        bom = ListaMateriais(
            cod_produto_produzido='PROD001',
            nome_produto_produzido='Produto Final',
            cod_produto_componente='COMP001',
            nome_produto_componente='Componente 1',
            qtd_utilizada=2.5,
            status='ativo'
        )
        db.session.add(bom)
        db.session.commit()
        
        # Testar explosão
        materiais = explodir_materiais('PROD001', 100)
        
        self.assertEqual(len(materiais), 1)
        self.assertEqual(materiais[0]['qtd_necessaria'], 250)
```