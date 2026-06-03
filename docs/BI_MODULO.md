<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# 📊 Módulo BI (Business Intelligence) - Documentação

> **Papel:** 📊 Módulo BI (Business Intelligence) - Documentação.

## Indice

- [📋 Visão Geral](#visão-geral)
- [🎯 Objetivos](#objetivos)
- [🏗️ Arquitetura](#arquitetura)
  - [Estrutura de Camadas](#estrutura-de-camadas)
- [📁 Estrutura de Arquivos](#estrutura-de-arquivos)
- [🔄 Processo ETL](#processo-etl)
  - [Execução Manual](#execução-manual)
  - [Execução via Interface](#execução-via-interface)
  - [Agendamento Automático (Cron)](#agendamento-automático-cron)
- [📊 KPIs Principais](#kpis-principais)
  - [1. Custo por KG](#1-custo-por-kg)
  - [2. Custo por R$ Faturado](#2-custo-por-r-faturado)
  - [3. Taxa de Despesas Extras](#3-taxa-de-despesas-extras)
  - [4. Divergência Cotado vs Pago](#4-divergência-cotado-vs-pago)
  - [5. Eficiência da Transportadora](#5-eficiência-da-transportadora)
- [🎨 Dashboards Disponíveis](#dashboards-disponíveis)
  - [Dashboard Principal (`/bi/dashboard`)](#dashboard-principal-bidashboard)
  - [Dashboard de Transportadoras (`/bi/transportadoras`)](#dashboard-de-transportadoras-bitransportadoras)
  - [Dashboard Regional (`/bi/regional`)](#dashboard-regional-biregional)
  - [Dashboard de Despesas (`/bi/despesas`)](#dashboard-de-despesas-bidespesas)
- [🔌 APIs Disponíveis](#apis-disponíveis)
  - [Indicadores Principais](#indicadores-principais)
  - [Evolução Mensal](#evolução-mensal)
  - [Ranking Transportadoras](#ranking-transportadoras)
  - [Análise Regional](#análise-regional)
  - [Despesas por Tipo](#despesas-por-tipo)
  - [Executar ETL](#executar-etl)
- [🗄️ Tabelas do Data Warehouse](#tabelas-do-data-warehouse)
  - [bi_frete_agregado](#bi_frete_agregado)
  - [bi_despesa_detalhada](#bi_despesa_detalhada)
  - [bi_performance_transportadora](#bi_performance_transportadora)
  - [bi_analise_regional](#bi_analise_regional)
  - [bi_indicador_mensal](#bi_indicador_mensal)
- [🔧 Configuração](#configuração)
  - [Instalação das Tabelas](#instalação-das-tabelas)
  - [Primeira Carga de Dados](#primeira-carga-de-dados)
  - [Permissões Necessárias](#permissões-necessárias)
- [📈 Otimizações Implementadas](#otimizações-implementadas)
  - [Índices](#índices)
  - [Performance](#performance)
  - [Queries Otimizadas](#queries-otimizadas)
- [🚀 Melhorias Futuras](#melhorias-futuras)
  - [Fase 2](#fase-2)
  - [Fase 3](#fase-3)
- [📝 Notas Importantes](#notas-importantes)
- [🆘 Suporte](#suporte)

## 📋 Visão Geral

O módulo BI foi desenvolvido para fornecer análises detalhadas e visualizações interativas dos dados de frete, permitindo tomada de decisões baseadas em dados concretos e KPIs estratégicos.

## 🎯 Objetivos

- **Análise de Custos**: Visualizar custos por kg, por R$ faturado, por região e transportadora
- **Gestão de Despesas**: Identificar tipos de despesas extras e seus responsáveis
- **Performance de Transportadoras**: Ranking e avaliação de eficiência
- **Análise Regional**: Mapear custos e volumes por região/UF
- **Economia Realizada**: Comparar valores cotados vs pagos

## 🏗️ Arquitetura

### Estrutura de Camadas

```
CAMADA 1: DADOS TRANSACIONAIS (Fonte)
├── fretes                 # Registros de CTes e pagamentos
├── despesas_extras        # Despesas adicionais
├── embarques             # Agrupamento de pedidos
└── transportadoras       # Cadastro de transportadoras

    ↓ ETL DIÁRIO ↓

CAMADA 2: DATA WAREHOUSE (Agregação)
├── bi_frete_agregado           # Fatos agregados por período
├── bi_despesa_detalhada        # Análise de despesas
├── bi_performance_transportadora # Performance consolidada
├── bi_analise_regional         # Análise por região
└── bi_indicador_mensal         # KPIs mensais

    ↓ APIs REST ↓

CAMADA 3: APRESENTAÇÃO (Visualização)
├── Dashboard Principal     # Visão executiva
├── Transportadoras        # Análise por transportadora
├── Regional              # Mapa de custos
└── Despesas             # Breakdown de despesas
```

## 📁 Estrutura de Arquivos

```
app/bi/
├── __init__.py          # Blueprint do módulo
├── models.py           # Modelos do Data Warehouse
├── services.py         # Serviços de ETL
└── routes.py          # APIs e rotas

app/templates/bi/
├── dashboard.html      # Dashboard principal
├── transportadoras.html # Análise de transportadoras
├── regional.html       # Análise regional
└── despesas.html      # Análise de despesas

Scripts:
├── create_bi_tables.sql # DDL das tabelas
└── run_bi_etl.py       # Script de ETL
```

## 🔄 Processo ETL

### Execução Manual
```bash
# Executar ETL completo
python run_bi_etl.py
```

### Execução via Interface
- Acesse o dashboard do BI
- Clique em "Atualizar Dados"
- Aguarde o processamento

### Agendamento Automático (Cron)
```bash
# Adicionar ao crontab para execução diária às 2h
0 2 * * * /usr/bin/python3 /caminho/run_bi_etl.py
```

## 📊 KPIs Principais

### 1. Custo por KG
```
Fórmula: valor_pago_total / peso_total_kg
Objetivo: Identificar eficiência no transporte de carga
Meta sugerida: < R$ 0,50/kg
```

### 2. Custo por R$ Faturado
```
Fórmula: valor_pago_total / valor_total_nfs
Objetivo: Medir impacto do frete no faturamento
Meta sugerida: < 5% do faturamento
```

### 3. Taxa de Despesas Extras
```
Fórmula: (valor_despesas_extras / valor_pago_total) * 100
Objetivo: Controlar custos adicionais
Meta sugerida: < 3% do frete total
```

### 4. Divergência Cotado vs Pago
```
Fórmula: valor_pago - valor_cotado
Objetivo: Controlar variações de custo
Meta sugerida: < 5% de divergência
```

### 5. Eficiência da Transportadora
```
Score = 100 - (penalidades por divergências + despesas + rejeições)
Objetivo: Avaliar performance geral
Meta sugerida: > 80 pontos
```

## 🎨 Dashboards Disponíveis

### Dashboard Principal (`/bi/dashboard`)
- **KPIs em tempo real**: Custo total, custo/kg, despesas, economia
- **Evolução mensal**: Gráfico de linha com histórico 12 meses
- **Top transportadoras**: Ranking por volume e custo
- **Distribuição regional**: Mapa de custos por região
- **Tipos de despesas**: Pizza com breakdown de despesas

### Dashboard de Transportadoras (`/bi/transportadoras`)
- **Ranking completo**: Todas transportadoras com métricas
- **Comparativo**: Benchmarking entre transportadoras
- **Conta corrente**: Saldo de débitos/créditos
- **Score de qualidade**: Avaliação de performance

### Dashboard Regional (`/bi/regional`)
- **Mapa de calor**: Visualização geográfica de custos
- **Análise por UF**: Detalhamento por estado
- **Rotas principais**: Origem-destino mais frequentes
- **Lead time**: Tempo médio de entrega por região

### Dashboard de Despesas (`/bi/despesas`)
- **Por tipo**: Reentrega, TDE, devolução, etc.
- **Por setor**: Comercial, Qualidade, Fiscal, etc.
- **Por motivo**: Causas raiz das despesas
- **Tendências**: Evolução temporal

## 🔌 APIs Disponíveis

### Indicadores Principais
```
GET /bi/api/indicadores-principais
Retorna: KPIs do período atual
```

### Evolução Mensal
```
GET /bi/api/evolucao-mensal
Retorna: Série temporal últimos 12 meses
```

### Ranking Transportadoras
```
GET /bi/api/ranking-transportadoras?periodo={mes|trimestre|ano}
Retorna: Top 10 transportadoras
```

### Análise Regional
```
GET /bi/api/analise-regional
Retorna: Dados agregados por região/UF
```

### Despesas por Tipo
```
GET /bi/api/despesas-por-tipo
Retorna: Breakdown de despesas extras
```

### Executar ETL
```
POST /bi/api/executar-etl
Executa: Processo completo de ETL
```

## 🗄️ Tabelas do Data Warehouse

### bi_frete_agregado
Tabela fato principal com agregações diárias de frete por transportadora/cliente/região

### bi_despesa_detalhada
Análise granular de despesas extras com classificação por tipo/setor/motivo

### bi_performance_transportadora
Consolidação mensal de performance com rankings e scores

### bi_analise_regional
Métricas agregadas por região geográfica

### bi_indicador_mensal
KPIs executivos consolidados mensalmente

## 🔧 Configuração

### Instalação das Tabelas
```bash
# Executar script SQL
psql -U usuario -d database -f create_bi_tables.sql
```

### Primeira Carga de Dados
```bash
# Executar ETL inicial (processa últimos 90 dias)
python run_bi_etl.py
```

### Permissões Necessárias
- Leitura: tabelas transacionais (fretes, embarques, etc.)
- Escrita: tabelas bi_* do Data Warehouse
- Execução: procedures e functions do PostgreSQL

## 📈 Otimizações Implementadas

### Índices
- Índices compostos por período + dimensão principal
- Índices únicos para evitar duplicação
- Índices de busca textual para nomes

### Performance
- Views materializadas para queries complexas
- Agregações pré-calculadas no ETL
- Cache de 15 minutos nas APIs
- Paginação em listagens grandes

### Queries Otimizadas
- CTEs (Common Table Expressions) para reuso
- Window functions para rankings
- Aggregate functions com GROUP BY eficiente

## 🚀 Melhorias Futuras

### Fase 2
- [ ] Integração com PowerBI/Tableau
- [ ] Alertas automáticos por e-mail
- [ ] Previsão de custos com ML
- [ ] API GraphQL

### Fase 3
- [ ] Dashboard mobile responsivo
- [ ] Exportação para Excel/PDF
- [ ] Simulador de custos
- [ ] Análise preditiva

## 📝 Notas Importantes

1. **ETL deve rodar diariamente** para manter dados atualizados
2. **Backup das tabelas BI** antes de grandes alterações
3. **Monitorar espaço em disco** - tabelas crescem rapidamente
4. **Revisar índices mensalmente** para otimização

## 🆘 Suporte

Para dúvidas ou problemas:
1. Verificar logs em `/var/log/bi_etl.log`
2. Consultar status do ETL no dashboard
3. Verificar permissões do banco de dados
4. Contatar equipe de desenvolvimento

---

**Versão**: 1.0.0  
**Data**: Janeiro 2025  
**Autor**: Sistema de Fretes - Módulo BI
