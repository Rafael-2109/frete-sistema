# 📊 Sistema de Análises de Fretes

## 📋 Visão Geral

Sistema completo de análises de custos de fretes com gráficos interativos e filtros configuráveis.

## 🎯 Funcionalidades

### 1. **Gráficos Principais** (sempre visíveis)
- **Gráfico por UF**: Barras duplas com % sobre valor NF e R$/KG
- **Gráfico por Transportadora**: Barras duplas com % sobre valor NF e R$/KG

### 2. **Análises Detalhadas** (opcionais)
- **Por UF**: Análise agregada por estado
- **Por Cidade**: Análise detalhada por cidade + UF
- **Por Sub-rota**: Análise por UF + sub-rota (JOIN com `cadastro_sub_rota`)
- **Por Transportadora**: Análise por transportadora
- **Por Cliente**: Análise por CNPJ + nome do cliente
- **Por Mês**: Análise temporal (mês/ano)
- **Por Veículo (Modalidade)**: Análise por tipo de veículo (VAN, TRUCK, etc.)

### 3. **Filtros Disponíveis**
- **Período**: Data início e data fim
- **Transportadora**: Filtro por transportadora específica
- **UF**: Filtro por estado
- **Status**: Filtro por status do frete (futuro)

## 🏗️ Arquitetura

### Arquivos Criados

1. **Service Layer**: `app/fretes/services/analises_service.py`
   - Funções puras de agregação de dados
   - Queries otimizadas com SQLAlchemy
   - Cálculo de métricas (% valor, R$/KG)

2. **Rota**: `app/fretes/routes.py:68-213`
   - Endpoint: `/fretes/analises`
   - Método: GET
   - Filtros via query params
   - Proteção: `@require_financeiro()`

3. **Template**: `app/templates/fretes/analises.html`
   - 2 gráficos Chart.js v4.4.0
   - Formulário de filtros
   - Tabela de dados detalhados
   - Responsivo (Bootstrap 5)

4. **Dashboard**: Link adicionado em `app/templates/fretes/dashboard.html:169-174`

### Modelos Utilizados

```python
# Modelo Frete (app/fretes/models.py)
Frete:
  - uf_destino: str(2)              # Para análise por UF
  - cidade_destino: str(100)        # Para análise por cidade
  - modalidade: str(50)             # Para análise por veículo
  - peso_total: float               # Para cálculo R$/KG
  - valor_total_nfs: float          # Para cálculo % valor
  - valor_considerado: float        # Valor do frete
  - transportadora_id: int          # Para análise por transportadora
  - cnpj_cliente: str(20)           # Para análise por cliente
  - criado_em: datetime             # Para filtro de período

# Modelo DespesaExtra (app/fretes/models.py)
DespesaExtra:
  - frete_id: int                   # FK para Frete
  - valor_despesa: float            # Somado ao custo total

# Modelo CadastroSubRota (app/localidades/models.py)
CadastroSubRota:
  - cod_uf: str(2)                  # JOIN com Frete.uf_destino
  - nome_cidade: str(100)           # JOIN com Frete.cidade_destino
  - sub_rota: str(50)               # Nome da sub-rota
  - ativa: bool                     # Filtro
```

## 📊 Métricas Calculadas

### 1. **Percentual sobre Valor NF**
```python
percentual_valor = (valor_frete + valor_despesa) / valor_nf * 100
```

- **Verde** (< 5%): Custo baixo
- **Amarelo** (5-10%): Custo médio
- **Vermelho** (> 10%): Custo alto

### 2. **Valor por KG**
```python
valor_por_kg = (valor_frete + valor_despesa) / peso_total
```

Indica custo de transporte por quilograma.

### 3. **Custo Total**
```python
total_custo = valor_considerado + sum(despesas_extras)
```

## 🔍 Queries Otimizadas

### Estrutura das Queries

Todas as funções de análise seguem o mesmo padrão:

```python
# 1. Subquery para agregar despesas extras
subq_despesas = db.session.query(
    DespesaExtra.frete_id,
    func.sum(DespesaExtra.valor_despesa).label('total_despesas')
).group_by(DespesaExtra.frete_id).subquery()

# 2. Query principal com JOIN e agregações
query = db.session.query(
    Frete.campo_agrupamento,
    func.count(Frete.id).label('qtd_fretes'),
    func.sum(Frete.valor_considerado).label('total_frete'),
    func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
    func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
    func.sum(Frete.peso_total).label('total_peso')
).outerjoin(
    subq_despesas,
    Frete.id == subq_despesas.c.frete_id
)

# 3. Aplicar filtros dinâmicos
if data_inicio:
    query = query.filter(Frete.criado_em >= data_inicio)
if data_fim:
    # Adicionar 1 dia para incluir todo o dia final
    query = query.filter(Frete.criado_em < data_fim + timedelta(days=1))

# 4. Agrupar e ordenar
query = query.group_by(Frete.campo_agrupamento).order_by(...)
```

### JOIN com Sub-rota

Para análise por sub-rota, fazemos LEFT JOIN com `cadastro_sub_rota`:

```python
.outerjoin(
    CadastroSubRota,
    db.and_(
        Frete.uf_destino == CadastroSubRota.cod_uf,
        Frete.cidade_destino == CadastroSubRota.nome_cidade,
        CadastroSubRota.ativa == True
    )
)
```

## 🎨 Frontend

### Tecnologias

- **Chart.js v4.4.0**: Gráficos de barras duplas
- **Bootstrap 5**: Layout responsivo
- **Font Awesome**: Ícones

### Gráficos

Ambos os gráficos usam:
- **Tipo**: `bar` (barras verticais)
- **2 eixos Y**: Um para % valor (esquerda), outro para R$/KG (direita)
- **Tooltip customizado**: Exibe qtd fretes, custo, valor NF e peso

### Interatividade

- **Auto-submit**: Ao trocar tipo de análise, o formulário é enviado automaticamente
- **Filtros persistentes**: Valores ficam preenchidos após submit
- **Tabela dinâmica**: Colunas adaptam-se ao tipo de análise

## 📡 API Endpoints

### GET `/fretes/analises`

**Query Parameters:**
- `data_inicio` (opcional): AAAA-MM-DD
- `data_fim` (opcional): AAAA-MM-DD
- `transportadora_id` (opcional): ID da transportadora
- `uf` (opcional): Sigla do estado (ex: ES, RJ)
- `status` (opcional): Status do frete
- `tipo_analise` (opcional): uf | cidade | subrota | transportadora | cliente | mes | modalidade

**Resposta**: HTML renderizado

**Exemplo**:
```
GET /fretes/analises?data_inicio=2025-01-01&data_fim=2025-01-31&tipo_analise=uf&transportadora_id=5
```

## 🚀 Como Usar

### 1. Acessar Análises

- **Via Dashboard**: Clique no botão "Análises" no dashboard de fretes
- **Via URL**: Acesse `/fretes/analises`

### 2. Aplicar Filtros

1. **Definir período**: Escolha data início e fim
2. **Filtrar transportadora**: Selecione uma transportadora específica (opcional)
3. **Filtrar UF**: Selecione um estado (opcional)
4. **Clicar em "Filtrar"**: Aplicar filtros

### 3. Escolher Tipo de Análise

Clique em um dos botões:
- **UF**: Ver dados por estado
- **Cidade**: Ver dados por cidade
- **Sub-rota**: Ver dados por sub-rota (requer cadastro de sub-rotas)
- **Transportadora**: Ver dados por transportadora
- **Cliente**: Ver dados por cliente
- **Mês**: Ver evolução temporal
- **Veículo**: Ver dados por tipo de veículo

## 🔮 Melhorias Futuras

### Backend
- [ ] Export para Excel/CSV
- [ ] API REST para consumo externo
- [ ] Cache de queries pesadas
- [ ] Análises combinadas (ex: Transportadora + UF + Veículo)
- [ ] Comparação entre períodos (atual vs anterior)

### Frontend
- [ ] Gráficos de linha para evolução temporal
- [ ] Gráficos de pizza para distribuição percentual
- [ ] Filtro de status funcional
- [ ] Download de gráficos como imagem
- [ ] Impressão de relatórios

### Análises Adicionais
- [ ] Por rota (campo `rota` em Separacao)
- [ ] Por tipo de carga (FRACIONADA vs DIRETA)
- [ ] Por vendedor/equipe de vendas (via NF)
- [ ] Por produto (via NF detalhada)
- [ ] Análise de despesas extras por tipo

## 📝 Notas Técnicas

### Performance

- **Índices recomendados**:
  - `fretes(uf_destino)`
  - `fretes(cidade_destino)`
  - `fretes(transportadora_id)`
  - `fretes(criado_em)`
  - `despesas_extras(frete_id)`

- **Otimização de queries**:
  - Uso de subquery para despesas (evita N+1)
  - Agregações no banco (não em Python)
  - LEFT JOIN (não trava se sub-rota não existir)

### Segurança

- **Proteção**: Apenas usuários do financeiro podem acessar (`@require_financeiro()`)
- **SQL Injection**: Protegido (uso de SQLAlchemy ORM)
- **XSS**: Protegido (Jinja2 auto-escape)

### Tratamento de Erros

- **Datas inválidas**: Flash message + ignora filtro
- **IDs inválidos**: Trata exceção + ignora filtro
- **Dados vazios**: Exibe mensagem "Nenhum dado encontrado"
- **Sub-rota não cadastrada**: Exibe "SEM SUB-ROTA"

## 🧪 Como Testar

### 1. Testar Sintaxe
```bash
python3 -m py_compile app/fretes/services/analises_service.py
python3 -m py_compile app/fretes/routes.py
```

### 2. Testar no Navegador
1. Acesse: `http://localhost:5000/fretes/`
2. Clique em "Análises"
3. Verifique se os gráficos aparecem
4. Teste cada tipo de análise
5. Teste os filtros

### 3. Testar Queries SQL
```python
from app.fretes.services.analises_service import analise_por_uf
dados = analise_por_uf()
print(dados)
```

## 📚 Referências

- **Chart.js**: https://www.chartjs.org/docs/latest/
- **SQLAlchemy Aggregations**: https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html
- **Bootstrap 5**: https://getbootstrap.com/docs/5.3/

---

**Data de Criação**: 2025-01-16
**Última Atualização**: 2025-01-16
**Autor**: Claude AI + Rafael Nascimento
