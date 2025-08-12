# 📦 MÓDULO MANUFATURA - SISTEMA PCP

## 📋 Visão Geral
Sistema completo de Planejamento e Controle de Produção (PCP) integrado com Odoo.

**Status**: ✅ 72% Implementado | 100% Funcional para operações básicas

## 🚀 Acesso Rápido

### Central de Controle
```
http://localhost:5000/manufatura/master
```
Template master com acesso a todas as funcionalidades do módulo.

### Templates Disponíveis
- `/manufatura/master` - Central de controle unificada
- `/manufatura/dashboard` - Dashboard operacional  
- `/manufatura/previsao-demanda` - Gestão de previsões
- `/manufatura/ordens-producao` - Gestão de ordens MTO/MTS
- `/manufatura/plano-mestre` - Plano mestre visual completo

## 📊 Funcionalidades Principais

### ✅ 100% Implementado
1. **Previsão de Demanda** - Com histórico e grupos empresariais
2. **Plano Mestre** - Cálculos automáticos de reposição
3. **Ordens de Produção** - MTO automático, MTS manual
4. **Explosão BOM** - Multi-nível com ordens filhas automáticas
5. **Necessidades de Compra** - Sistema To-Do List
6. **Integração Odoo** - Bidirecional com mapeamento completo
7. **Dashboard** - Métricas e KPIs em tempo real
8. **Lead Time** - Cálculos considerando dias úteis

### ⚠️ Funcional via API (falta template)
- Sequenciamento de produção
- Requisições de compras
- Pedidos de compra
- Gestão de grupos empresariais

### ❌ Pendente Implementação
- Quebra de ordem de produção
- Gestão visual de BOM
- Gestão de recursos/capacidade
- Visualização Gantt interativa

## 🔧 Arquitetura

```
app/manufatura/
├── models.py              # 11 modelos SQLAlchemy
├── routes/                # 6 blueprints de rotas
│   ├── dashboard_routes.py
│   ├── ordem_producao_routes.py
│   ├── plano_mestre_routes.py
│   ├── previsao_demanda_routes.py
│   ├── requisicao_compras_routes.py
│   └── integracao_routes.py
├── services/              # Lógica de negócio
│   ├── dashboard_service.py
│   ├── demanda_service.py
│   ├── ordem_producao_service.py
│   └── plano_mestre_service.py
└── templates/manufatura/  # Templates HTML
    ├── master.html        # Central de controle
    ├── dashboard.html
    ├── plano_mestre.html
    ├── previsao_demanda.html
    └── ordens_producao.html
```

## 🔗 Integração Odoo

### Estrutura Padronizada
```
app/odoo/
├── utils/manufatura_mapper.py    # Mapeamentos hardcoded
├── services/manufatura_service.py # Service com mapper
└── routes/manufatura_routes.py   # Rotas de integração
```

### Endpoints de Integração
- `/odoo/manufatura/` - Dashboard de integração
- `/odoo/manufatura/importar/requisicoes` - Importar requisições
- `/odoo/manufatura/importar/pedidos` - Importar pedidos
- `/odoo/manufatura/sincronizar/producao` - Sincronizar produção
- `/odoo/manufatura/gerar/ordens-mto` - Gerar ordens MTO
- `/odoo/manufatura/sincronizacao-completa` - Sync completa

## 📚 Documentação

### Essenciais
- `escopo.md` - Definição do escopo original (IMUTÁVEL)
- `README.md` - Este arquivo (visão geral)
- `IMPLEMENTACAO_STATUS.md` - Status detalhado de implementação

### Referência Técnica
- `fluxo_processo_pcp.md` - Fluxo operacional do PCP
- `implementacao_*.md` - Guias técnicos de implementação (4 arquivos)

## 🎯 Regras de Ouro

1. **Separacao tem PRIORIDADE sobre PreSeparacaoItem**
2. **EXCLUIR pedidos com status = 'FATURADO'** 
3. **Necessidades são TO-DO LIST** (não cria requisição automática)
4. **PCP cria requisições NO ODOO manualmente**
5. **Sistema IMPORTA do Odoo** (não exporta requisições)

## 🚦 Próximos Passos

### Fase 1 - Urgente (1-2 dias)
1. Template `requisicoes_compras.html`
2. Template `lista_materiais.html`
3. Funcionalidade de quebra de ordem

### Fase 2 - Importante (3-5 dias)
1. Template `sequenciamento_gantt.html`
2. Template `recursos_producao.html`
3. Template `pedidos_compras.html`

### Fase 3 - Desejável (1 semana)
1. Templates restantes
2. Relatórios PDF/Excel
3. Dashboard BI

## 📈 Métricas de Implementação

| Categoria | Status | Percentual |
|-----------|--------|------------|
| Modelos/Backend | ✅ Excelente | 95% |
| Services/Lógica | ✅ Excelente | 90% |
| Rotas/APIs | ✅ Muito Bom | 85% |
| Templates/Frontend | ⚠️ Em Progresso | 40% |
| Integração Odoo | ✅ Excelente | 95% |
| **TOTAL** | ✅ Funcional | **72%** |

## 🛠️ Comandos Úteis

```python
# Testar módulo
python run.py

# Acessar central de controle
http://localhost:5000/manufatura/master

# Sincronização Odoo completa
POST /odoo/manufatura/sincronizacao-completa

# Gerar Plano Mestre
POST /manufatura/api/plano-mestre/gerar
```

## 📞 Suporte

Para dúvidas ou problemas, consulte:
1. `IMPLEMENTACAO_STATUS.md` - Status detalhado
2. `fluxo_processo_pcp.md` - Fluxo operacional
3. Código fonte em `app/manufatura/`

---
**Última Atualização**: 11/08/2025 | **Versão**: 1.0