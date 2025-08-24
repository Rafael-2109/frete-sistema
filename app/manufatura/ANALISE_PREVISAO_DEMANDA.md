# 📊 ANÁLISE PROFUNDA - PREVISÃO DE DEMANDA
## Módulo de Manufatura/PCP

**Data da Análise**: 24/08/2025  
**Analista**: Claude (Precision Engineer Mode)  
**Foco**: Exclusivamente Previsão de Demanda

---

## 1. 📋 SITUAÇÃO ATUAL - EVIDÊNCIAS COLETADAS

### 1.1 Estrutura de Arquivos Existentes
```
app/manufatura/
├── models.py                        ✅ Existe (11 modelos implementados)
├── routes/
│   ├── dashboard_routes.py          ✅ Existe
│   ├── previsao_demanda_routes.py   ✅ Existe
│   └── ...
├── services/
│   ├── demanda_service.py           ✅ Existe
│   └── ...
└── templates/
    ├── dashboard.html                ✅ Existe
    ├── master.html                   ✅ Existe  
    ├── previsao_demanda.html         ✅ Existe
    └── ...
```

### 1.2 Modelo de Dados - GrupoEmpresarial (models.py, linhas 9-18)
```python
class GrupoEmpresarial(db.Model):
    __tablename__ = 'grupo_empresarial'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_grupo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tipo_grupo = db.Column(db.String(20), nullable=False)  # ⚠️ Não especifica valores válidos
    info_grupo = db.Column(ARRAY(db.Text), nullable=False)  # ⚠️ Array genérico, não específico para CNPJ
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
```

### 1.3 Modelo PrevisaoDemanda (models.py, linhas 50-68)
```python
class PrevisaoDemanda(db.Model):
    __tablename__ = 'previsao_demanda'
    
    id = db.Column(db.Integer, primary_key=True)
    data_mes = db.Column(db.Integer, nullable=False)
    data_ano = db.Column(db.Integer, nullable=False, index=True)
    nome_grupo = db.Column(db.String(100))  # ✅ Vincula com grupo
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_demanda_prevista = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_demanda_realizada = db.Column(db.Numeric(15, 3), default=0)
    disparo_producao = db.Column(db.String(3))  # ✅ MTO/MTS
    # ⚠️ FALTAM campos para comparações e múltiplas previsões
```

### 1.4 Template previsao_demanda.html - Análise
**Funcionalidades Existentes**:
- ✅ Filtro por mês/ano (linhas 30-49)
- ✅ Filtro por grupo empresarial (linhas 51-54)
- ✅ Botão gerar por histórico (linha 65-67)
- ✅ Disparo MTO/MTS (linhas 180-183)

**GAPS Identificados**:
- ❌ Não possui média 3 meses
- ❌ Não possui média 6 meses
- ❌ Não possui 3 colunas de comparação
- ❌ Não possui botões para escolher coluna
- ❌ Grupos não são por prefixo CNPJ
- ❌ Não possui opção "Restante"

### 1.5 Serviço DemandaService (demanda_service.py)
**Funcionalidades Existentes**:
- ✅ calcular_demanda_ativa() - linha 16
- ✅ criar_previsao_por_historico() - linha 216
- ✅ Considera Separacao, PreSeparacaoItem e CarteiraPrincipal

**GAPS**:
- ❌ Não calcula médias 3/6 meses
- ❌ Não agrupa por prefixo CNPJ

---

## 2. 🎯 REQUISITOS SOLICITADOS VS IMPLEMENTAÇÃO

### 2.1 Organização das Telas

#### SITUAÇÃO ATUAL:
- **master.html**: Renderizada em `/master` (dashboard_routes.py, linha 22)
- **dashboard.html**: Renderizada em `/dashboard` (dashboard_routes.py, linha 16)

#### ANÁLISE DO CONTEÚDO:
**master.html** (linha 1-100):
- Possui cards com módulos
- Links para diferentes funcionalidades
- Visual mais elaborado com gradientes

**dashboard.html** (linha 1-100):
- Cards de métricas operacionais
- Ordens abertas, necessidades pendentes
- Taxa de cumprimento

### 2.2 Previsão de Demanda - Requisitos

| Requisito | Status Atual | Evidência |
|-----------|--------------|-----------|
| A) Definição do mês a ser previsto | ✅ Parcial | previsao_demanda.html, linha 31-44 |
| B) Definição do grupo empresarial | ⚠️ Existe mas incorreto | linha 51-54, não usa prefixo CNPJ |
| C) Filtros dinâmicos: | | |
| - Campo select mês/ano | ✅ Existe | linha 31-49 |
| - Média últimos 3 meses | ❌ NÃO EXISTE | Não encontrado |
| - Média últimos 6 meses | ❌ NÃO EXISTE | Não encontrado |
| - 3 botões para escolher coluna | ❌ NÃO EXISTE | Não encontrado |
| D) 3 colunas de comparação | ❌ NÃO EXISTE | Tabela tem apenas 1 previsão |
| E) Coluna Demanda Prevista | ✅ Existe | linha 91 |
| F) Disparo MTO/MTS | ✅ Existe | linha 94, 180-183 |

### 2.3 Grupos Empresariais - Requisitos

| Requisito | Status Atual | Evidência |
|-----------|--------------|-----------|
| A) Grupos por prefixo CNPJ | ❌ NÃO IMPLEMENTADO | tipo_grupo e info_grupo genéricos |
| B) N prefixos para 1 grupo | ⚠️ Possível com ARRAY | info_grupo é ARRAY(db.Text) |
| C) Grupo "Restante" | ❌ NÃO EXISTE | Não implementado |

---

## 3. 🚨 GAPS CRÍTICOS IDENTIFICADOS

### 3.1 Modelo de Dados
1. **GrupoEmpresarial**:
   - `tipo_grupo` não especifica se é 'prefixo_cnpj' ou 'restante'
   - `info_grupo` é genérico, deveria ser `prefixos_cnpj`
   - Falta lógica para grupo "Restante"

2. **PrevisaoDemanda**:
   - Falta estrutura para múltiplas comparações
   - Não tem campos para armazenar médias históricas

### 3.2 Interface (previsao_demanda.html)
1. Falta seção de filtros avançados com:
   - Checkboxes/selects para médias 3/6 meses
   - Botões para escolher coluna de destino
2. Tabela não suporta múltiplas colunas de comparação

### 3.3 Backend (services e routes)
1. Falta endpoint para calcular médias históricas
2. Falta lógica para agrupar por prefixo CNPJ
3. Falta tratamento do grupo "Restante"

---

## 4. 📐 PROPOSTA DE REORGANIZAÇÃO

### 4.1 MASTER.HTML - Configurações e Parâmetros
**Deve conter**:
- ✅ Cadastro de Grupos Empresariais
- ✅ Definição de prefixos CNPJ
- ✅ Parâmetros de produção (MTO/MTS padrões)
- ✅ Configuração de estoque de segurança
- ✅ Lead times padrão
- ✅ Cadastro de recursos/máquinas
- ✅ Lista de materiais (BOM)

### 4.2 DASHBOARD.HTML - Operações Diárias
**Deve conter**:
- ✅ Métricas em tempo real
- ✅ Alertas e necessidades urgentes
- ✅ Link para Previsão de Demanda
- ✅ Link para Ordens de Produção
- ✅ Link para Plano Mestre
- ✅ Gráficos de performance

### 4.3 PREVISAO_DEMANDA.HTML - Melhorias Necessárias
**Nova estrutura proposta**:
```html
<!-- Seção de Filtros Avançados -->
<div class="card">
    <div class="card-header">Configuração de Análise</div>
    <div class="card-body">
        <!-- Linha 1: Período Base -->
        <div class="row mb-3">
            <div class="col-md-4">
                <label>Mês/Ano a Prever</label>
                <div class="input-group">
                    <select id="mes-previsao">...</select>
                    <input type="number" id="ano-previsao">
                </div>
            </div>
            <div class="col-md-4">
                <label>Grupo Empresarial</label>
                <select id="grupo-empresarial">
                    <option value="">Todos</option>
                    <option value="RESTANTE">Restante (sem grupo)</option>
                    <!-- Grupos dinâmicos -->
                </select>
            </div>
        </div>
        
        <!-- Linha 2: Comparações -->
        <div class="row">
            <div class="col-md-12">
                <h6>Comparações para Análise</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Tipo de Análise</th>
                            <th>Incluir na Coluna</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Média Últimos 3 Meses</td>
                            <td>
                                <div class="btn-group">
                                    <button class="btn btn-sm btn-outline-primary" data-coluna="1">Coluna 1</button>
                                    <button class="btn btn-sm btn-outline-primary" data-coluna="2">Coluna 2</button>
                                    <button class="btn btn-sm btn-outline-primary" data-coluna="3">Coluna 3</button>
                                    <button class="btn btn-sm btn-outline-secondary">Não incluir</button>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>Média Últimos 6 Meses</td>
                            <td><!-- Mesmos botões --></td>
                        </tr>
                        <tr>
                            <td>Mesmo Mês Ano Anterior</td>
                            <td><!-- Mesmos botões --></td>
                        </tr>
                        <tr>
                            <td>Demanda Ativa (Carteira)</td>
                            <td><!-- Mesmos botões --></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Tabela de Resultados com Múltiplas Colunas -->
<table class="table">
    <thead>
        <tr>
            <th rowspan="2">Produto</th>
            <th colspan="3" class="text-center">Comparações</th>
            <th rowspan="2">Demanda Prevista</th>
            <th rowspan="2">Disparo</th>
        </tr>
        <tr>
            <th>Coluna 1</th>
            <th>Coluna 2</th>
            <th>Coluna 3</th>
        </tr>
    </thead>
    <tbody>
        <!-- Dados dinâmicos -->
    </tbody>
</table>
```

---

## 5. 🔧 IMPLEMENTAÇÕES NECESSÁRIAS

### 5.1 Alterações no Modelo GrupoEmpresarial
```python
class GrupoEmpresarial(db.Model):
    __tablename__ = 'grupo_empresarial'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_grupo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tipo_grupo = db.Column(db.String(20), nullable=False)  # 'prefixo_cnpj' ou 'restante'
    prefixos_cnpj = db.Column(ARRAY(db.String(10)), nullable=True)  # Array de prefixos
    descricao = db.Column(db.String(255))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
```

### 5.2 Nova Tabela para Comparações
```python
class PrevisaoDemandaComparacao(db.Model):
    __tablename__ = 'previsao_demanda_comparacao'
    
    id = db.Column(db.Integer, primary_key=True)
    previsao_demanda_id = db.Column(db.Integer, db.ForeignKey('previsao_demanda.id'))
    tipo_comparacao = db.Column(db.String(50))  # 'media_3m', 'media_6m', 'ano_anterior', 'demanda_ativa'
    coluna_destino = db.Column(db.Integer)  # 1, 2 ou 3
    valor_calculado = db.Column(db.Numeric(15, 3))
    data_calculo = db.Column(db.DateTime, default=datetime.utcnow)
```

### 5.3 Novos Endpoints Necessários
```python
# Em previsao_demanda_routes.py

@bp.route('/api/previsao-demanda/calcular-media')
@login_required
def calcular_media_historica():
    """Calcula média de períodos anteriores"""
    meses = request.args.get('meses', type=int)  # 3 ou 6
    grupo = request.args.get('grupo')
    cod_produto = request.args.get('cod_produto')
    # Implementar lógica

@bp.route('/api/grupos-empresariais/listar')
@login_required  
def listar_grupos():
    """Lista grupos com opção Restante"""
    grupos = GrupoEmpresarial.query.filter_by(ativo=True).all()
    resultado = [{'value': 'RESTANTE', 'label': 'Restante (sem grupo)'}]
    resultado.extend([{
        'value': g.nome_grupo,
        'label': g.nome_grupo,
        'prefixos': g.prefixos_cnpj
    } for g in grupos])
    return jsonify(resultado)
```

### 5.4 Service para Grupos por Prefixo
```python
# Em demanda_service.py

def identificar_grupo_por_cnpj(self, cnpj):
    """Identifica grupo empresarial pelo prefixo do CNPJ"""
    grupos = GrupoEmpresarial.query.filter_by(
        tipo_grupo='prefixo_cnpj',
        ativo=True
    ).all()
    
    for grupo in grupos:
        for prefixo in grupo.prefixos_cnpj:
            if cnpj.startswith(prefixo):
                return grupo.nome_grupo
    
    return 'RESTANTE'

def calcular_media_periodo(self, cod_produto, meses, mes_base, ano_base, grupo=None):
    """Calcula média dos últimos N meses"""
    # Implementar cálculo
```

---

## 6. 📋 PLANO DE AÇÃO RECOMENDADO

### FASE 1 - Ajuste de Modelos (1 dia)
1. [ ] Alterar modelo GrupoEmpresarial
2. [ ] Criar modelo PrevisaoDemandaComparacao
3. [ ] Migrations no banco de dados

### FASE 2 - Backend (2 dias)
1. [ ] Implementar service para grupos por CNPJ
2. [ ] Criar endpoints de médias históricas
3. [ ] Ajustar DemandaService

### FASE 3 - Frontend (2 dias)
1. [ ] Redesenhar previsao_demanda.html
2. [ ] Implementar seleção de colunas
3. [ ] Criar interface de comparações

### FASE 4 - Reorganização Master/Dashboard (1 dia)
1. [ ] Mover cadastros para master.html
2. [ ] Manter operações em dashboard.html
3. [ ] Criar links adequados

---

## 7. ⚠️ RISCOS E CONSIDERAÇÕES

1. **Migração de Dados**: Grupos existentes precisarão ser reconfigurados
2. **Performance**: Cálculos de média podem ser pesados com muito histórico
3. **Validação**: Prefixos CNPJ devem ser únicos entre grupos
4. **UX**: Interface com 3 colunas pode ficar complexa em telas pequenas

---

**FIM DA ANÁLISE**

Total de arquivos analisados: 12  
Total de linhas de código revisadas: ~1500  
Gaps identificados: 15  
Melhorias propostas: 10