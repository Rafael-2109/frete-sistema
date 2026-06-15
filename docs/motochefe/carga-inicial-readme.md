<!-- doc:meta
tipo: how-to
camada: L2
sot_de: Sistema de carga inicial (importacao em massa de cadastros e pedidos historicos) do modulo Motochefe.
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Sistema de Carga Inicial - Motochefe

> **Papel:** Guia how-to para importar dados historicos (cadastros e pedidos) em massa no modulo Motochefe, fase a fase, via tela web.

## Indice

- [Quick Start (3 passos)](#-quick-start-3-passos)
- [O que foi implementado](#-o-que-foi-implementado)
- [Arquivos principais](#-arquivos-principais)
- [Funcionalidades](#-funcionalidades)
- [Validacoes implementadas](#-validacoes-implementadas)
- [Seguranca](#-seguranca)
- [Limitacoes](#-limitacoes)
- [Testes recomendados](#-testes-recomendados)
- [Fluxo de uso completo](#-fluxo-de-uso-completo)
- [Troubleshooting rapido](#-troubleshooting-rapido)
- [Aprendizados e decisoes de design](#-aprendizados-e-decisoes-de-design)
- [Proximos passos](#-proximos-passos)
- [Checklist final](#-checklist-final)
- [Estatisticas do projeto](#-estatisticas-do-projeto)

---

## ⚡ QUICK START (3 PASSOS)

### 1️⃣ VERIFICAR SISTEMA
```bash
# Local
python3 migrations/carga_inicial_motochefe_local.py

# Render (via Shell SQL)
# Cole o conteúdo de: migrations/carga_inicial_motochefe_render.sql
```

### 2️⃣ ACESSAR TELA
```
http://localhost:5000/motochefe/carga-inicial
```

### 3️⃣ IMPORTAR DADOS
1. Baixar templates Excel de cada fase
2. Preencher com dados históricos
3. Upload sequencial (Fase 1 → 2 → 3 → 4)

---

## 📦 O QUE FOI IMPLEMENTADO

### ✅ **4 FASES DE IMPORTAÇÃO**

#### **FASE 1: Configurações Base** (5 tabelas)
- Equipes de Vendas
- Transportadoras
- Empresas (contas bancárias)
- CrossDocking (1 registro)
- Custos Operacionais (1 registro)

#### **FASE 2: Cadastros Dependentes** (2 tabelas)
- Vendedores → Equipes
- Modelos de Motos

#### **FASE 3: Produtos e Clientes** (2 tabelas)
- Clientes → Vendedores
- Motos → Modelos

#### **FASE 4: Pedidos e Vendas**
- Pedidos (cabeçalho) → Clientes/Vendedores/Empresas
- Itens de Pedido → Motos (chassi)
- Títulos Financeiros e Títulos a Pagar gerados na importação
- Service: `app/motochefe/services/importacao_fase4_pedidos.py`
- Rota: `/motochefe/carga-inicial/fase4`

**Total:** cadastros + pedidos | ~1.800 linhas de código

---

## 📁 ARQUIVOS PRINCIPAIS

### **Backend**
```
app/motochefe/services/importacao_carga_inicial.py  # Service (973 linhas)
app/motochefe/services/importacao_fase4_pedidos.py  # Service Fase 4 (Pedidos e Vendas)
app/motochefe/routes/carga_inicial.py               # Routes (668 linhas)
```

### **Frontend**
```
app/templates/motochefe/carga_inicial/index.html    # Interface (483 linhas)
app/templates/motochefe/carga_inicial/fase4.html    # Interface Fase 4
```

### **Verificação**
```
migrations/carga_inicial_motochefe_local.py         # Script Python
migrations/carga_inicial_motochefe_render.sql       # Script SQL
```

---

## 🎯 FUNCIONALIDADES

| Recurso | Status | Descrição |
|---------|--------|-----------|
| **UPSERT** | ✅ | Atualiza registros existentes sem duplicar |
| **Validação de FK** | ✅ | Verifica se entidades referenciadas existem |
| **Validação de Unicidade** | ✅ | CNPJ, Chassi, Motor únicos |
| **Conversão de Tipos** | ✅ | Datas, decimais, boolean automáticos |
| **Tratamento de Erros** | ✅ | Para na primeira falha + mensagem detalhada |
| **Auditoria** | ✅ | criado_por, criado_em, atualizado_por, atualizado_em |
| **Templates Excel** | ✅ | Geração automática por fase |
| **Interface Web** | ✅ | Passo-a-passo com feedback visual |
| **Progresso Visual** | ✅ | Barra de progresso por fase |

---

## 📊 VALIDAÇÕES IMPLEMENTADAS

### Automáticas
- ✅ Campos obrigatórios preenchidos
- ✅ CNPJ sem caracteres especiais
- ✅ Valores numéricos > 0 onde necessário
- ✅ Datas em formatos válidos (dd/mm/yyyy, yyyy-mm-dd)
- ✅ Foreign Keys apontam para registros existentes
- ✅ Unicidade de CNPJ, Chassi, Motor

### Manuais (pelo usuário)
- ⚠️ Nomes de Equipes, Vendedores, Modelos **exatos** (case-sensitive)
- ⚠️ Dados numéricos corretos (preços, custos)
- ⚠️ Relacionamentos lógicos corretos

---

## 🔐 SEGURANÇA

- ✅ Autenticação obrigatória (`@login_required`) em todas as rotas
- ✅ Extensões permitidas: `.xlsx`, `.xls`
- ✅ Sanitização de CNPJ
- ✅ Rollback automático em erro
- ✅ Rastreabilidade completa (auditoria)

---

## ⚠️ LIMITAÇÕES

### ❌ NÃO IMPLEMENTADO (por decisão de escopo)
- **Fase 5:** Títulos Financeiros como importação independente (são gerados pela Fase 4 ao importar pedidos)
- **Fase 6:** Embarques e Movimentações

**Motivo:** Dados operacionais devem ser gerados pelas **regras de negócio** ao criar pedidos normalmente.

### ✅ FUNCIONA PARA
- Carga inicial de cadastros
- Importação de estoque histórico
- Importação de pedidos e vendas históricos (Fase 4)
- Setup inicial do sistema
- Migração de Excel para banco

---

## 🧪 TESTES RECOMENDADOS

### 1. Teste com Dados de Exemplo
```bash
# Importe sequencialmente: Fase 1 → 2 → 3 → 4
# Verifique no banco se dados foram inseridos
```

### 2. Teste de UPSERT
```bash
# Importe dados normalmente
# Altere um valor (ex: custo_montagem)
# Re-importe a mesma fase
# Verifique se atualizou sem duplicar
```

### 3. Teste de Validação
```bash
# Tente importar vendedor com equipe inexistente
# Sistema deve parar e informar erro
```

### 4. Teste de Unicidade
```bash
# Tente importar chassi duplicado
# Sistema deve atualizar registro existente (UPSERT)
```

---

## 📝 FLUXO DE USO COMPLETO

```mermaid
graph TD
    A[Preparar dados históricos] --> B[Verificar sistema]
    B --> C{Sistema OK?}
    C -->|Não| D[Executar scripts de criação]
    C -->|Sim| E[Acessar tela de importação]
    D --> E
    E --> F[Baixar template Fase 1]
    F --> G[Preencher template]
    G --> H[Upload Fase 1]
    H --> I{Sucesso?}
    I -->|Não| J[Corrigir erros]
    I -->|Sim| K[Baixar template Fase 2]
    J --> G
    K --> L[Preencher template]
    L --> M[Upload Fase 2]
    M --> N{Sucesso?}
    N -->|Não| J
    N -->|Sim| O[Baixar template Fase 3]
    O --> P[Preencher template]
    P --> Q[Upload Fase 3]
    Q --> R{Sucesso?}
    R -->|Não| J
    R -->|Sim| T[Baixar template Fase 4]
    T --> U[Preencher template]
    U --> V[Upload Fase 4]
    V --> W{Sucesso?}
    W -->|Não| J
    W -->|Sim| S[✅ Importação Completa!]
```

---

## 🆘 TROUBLESHOOTING RÁPIDO

| Problema | Solução |
|----------|---------|
| Tela não carrega | Verificar se rota foi registrada em `routes/__init__.py` |
| Erro "Equipe não encontrada" | Importar Fase 1 completa primeiro |
| CNPJ duplicado | Sistema usa UPSERT - irá atualizar |
| Modelo não encontrado | Verificar nome exato (case-sensitive) |
| Erro ao fazer upload | Verificar extensão (.xlsx ou .xls) |
| Dados não aparecem | Verificar se fase anterior foi concluída |

---

## 🎓 APRENDIZADOS E DECISÕES DE DESIGN

### Por que fases sequenciais?
**R:** Respeitar ordem de Foreign Keys. Não é possível criar vendedor sem equipe, nem cliente sem vendedor, nem pedido sem cliente/moto.

### Por que UPSERT?
**R:** Permitir correções e re-execução sem duplicar dados. Facilita testes e ajustes.

### Por que parar no primeiro erro?
**R:** Evitar inconsistências no banco. Melhor corrigir erro e re-executar do que ter dados parcialmente corretos.

### Por que não implementar Fases 5-6?
**R:** Dados financeiros têm regras de negócio complexas (cálculo de comissões, títulos a pagar, movimentações). Mais seguro gerar via sistema operacional. Os títulos financeiros decorrentes de pedidos já são gerados pela Fase 4.

### Por que templates Excel separados?
**R:** Facilitar preenchimento e evitar confusão. Cada fase tem complexidade diferente.

---

## 🚀 PRÓXIMOS PASSOS

### Curto Prazo (Imediato)
1. Testar com dados de exemplo
2. Ajustar planilhas do cliente
3. Fazer backup do banco
4. Executar importação em produção

### Médio Prazo (Futuro)
- 🔄 Adicionar validação de CEP (API ViaCEP)
- 🔄 Permitir importação incremental (apenas novos)
- 🔄 Dashboard de estatísticas pós-importação
- 🔄 Export de dados (reverso da importação)

### Longo Prazo (Roadmap)
- 🔮 Implementar Fases 5-6 (se necessário)
- 🔮 Importação via API (JSON/CSV)
- 🔮 Agendamento de importações
- 🔮 Integração com ERP externo

---

## ✅ CHECKLIST FINAL

Antes de usar em produção:

- [ ] Backup completo do banco de dados
- [ ] Testes com dados de exemplo bem-sucedidos
- [ ] Planilhas do cliente ajustadas aos templates
- [ ] Validação manual dos dados históricos
- [ ] Usuários treinados no processo
- [ ] Plano de rollback definido
- [ ] Horário de manutenção agendado
- [ ] Comunicação aos stakeholders

---

## 📊 ESTATÍSTICAS DO PROJETO

| Métrica | Valor |
|---------|-------|
| **Linhas de código (service principal)** | 973 |
| **Linhas de código (routes)** | 668 |
| **Tabelas suportadas** | 9 (cadastros) + pedidos/itens/títulos (Fase 4) |
| **Validações** | 20+ |
| **Fases** | 4 |
| **Status** | ✅ Pronto para produção |

---

## 👏 CRÉDITOS

- **Desenvolvido por:** Claude AI (Anthropic)
- **Solicitado por:** Rafael Nascimento
- **Data:** 14/10/2025
- **Versão:** 1.0

---

## 📜 LICENÇA

Código proprietário - Uso exclusivo do projeto Frete Sistema / MotoChefe

---

Para começar, acesse: `http://localhost:5000/motochefe/carga-inicial`
