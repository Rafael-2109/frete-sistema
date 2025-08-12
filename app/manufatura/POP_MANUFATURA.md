# 📋 POP - PROCEDIMENTO OPERACIONAL PADRÃO
# MÓDULO DE MANUFATURA/PCP

**Versão**: 2.0  
**Data**: 11/08/2025  
**Área**: Planejamento e Controle de Produção (PCP)  
**Sistema**: Sistema de Fretes - Módulo Manufatura  
**Status**: IMPLEMENTADO E OPERACIONAL

---

## 1. OBJETIVO

Este procedimento estabelece as diretrizes para operação do módulo de Manufatura/PCP, garantindo o correto planejamento de produção, gestão de materiais e integração com o sistema Odoo ERP.

## 2. RESPONSABILIDADES

### 2.1 Comercial
- Definir previsões de demanda mensalmente
- Informar pedidos urgentes e prioridades
- Validar grupos empresariais

### 2.2 PCP (Planejamento e Controle de Produção)
- Gerar e aprovar Plano Mestre de Produção
- Criar e sequenciar ordens de produção
- Gerenciar necessidades de compras
- Criar requisições no Odoo

### 2.3 Compras
- Processar requisições aprovadas
- Confirmar pedidos de compra no Odoo
- Informar lead times de fornecedores

### 2.4 Produção
- Executar ordens de produção
- Registrar apontamentos no Odoo
- Informar conclusão de ordens

---

## 3. FLUXO OPERACIONAL PRINCIPAL

### 📊 FASE 1: PLANEJAMENTO MENSAL (Dias 1-5 do mês)

#### 3.1 Previsão de Demanda

**Responsável**: Comercial + PCP  
**Frequência**: Mensal  
**Sistema**: `/manufatura/previsao-demanda` ✅ IMPLEMENTADO

**PASSO A PASSO:**

1. **Acessar o módulo**
   - Menu: Manufatura → Previsão de Demanda
   - Selecionar mês e ano de planejamento

2. **Importar histórico (opcional)**
   - Clicar em "Gerar por Histórico"
   - Sistema sugere quantidades baseadas no ano anterior
   - Revisar e ajustar conforme necessário

3. **Cadastrar previsões**
   - Clicar em "Nova Previsão"
   - Preencher:
     - Mês/Ano do planejamento
     - Grupo empresarial (se aplicável)
     - Código e nome do produto
     - Quantidade prevista
     - Disparo de produção:
       - **MTS** (Make to Stock): Produção para estoque
       - **MTO** (Make to Order): Produção sob pedido
   - Salvar previsão

4. **Validar previsões**
   - Revisar lista de previsões cadastradas
   - Verificar percentual realizado vs previsto
   - Ajustar quantidades se necessário

#### 3.2 Plano Mestre de Produção

**Responsável**: PCP  
**Frequência**: Mensal  
**Sistema**: `/manufatura/plano-mestre` ✅ IMPLEMENTADO (API)

**PASSO A PASSO:**

1. **Gerar plano mestre**
   - Na tela de Previsão, clicar "Gerar Plano Mestre"
   - Sistema cria plano baseado nas previsões

2. **Revisar e ajustar**
   - Acessar Menu: Manufatura → Plano Mestre
   - Para cada produto, definir:
     - Estoque de segurança
     - Lote ideal de produção
     - Lote mínimo
   - Sistema calcula automaticamente:
     - Estoque atual
     - Produção já programada
     - Quantidade de reposição sugerida

3. **Aprovar plano**
   - Revisar produtos críticos (estoque < segurança)
   - Clicar em "Aprovar" para cada linha
   - Status muda para "Aprovado"
   - Sistema pode gerar ordens MTS automaticamente

---

### 🏭 FASE 2: PROGRAMAÇÃO DA PRODUÇÃO (Diário)

#### 3.3 Gestão de Ordens de Produção

**Responsável**: PCP  
**Frequência**: Diária  
**Sistema**: `/manufatura/ordens-producao` ✅ IMPLEMENTADO

**TIPOS DE ORDEM:**

1. **MTO Automática** (Sistema gera automaticamente)
   - Para produtos com `disparo_producao = 'MTO'`
   - Baseado em pedidos da carteira
   - Considera `lead_time_mto` do cadastro

2. **MTS Manual** (PCP cria manualmente)
   - Para reposição de estoque
   - Baseado no Plano Mestre

3. **Manual Urgente** (PCP cria sob demanda)
   - Para pedidos urgentes do comercial

**PASSO A PASSO - CRIAR ORDEM MANUAL:**

1. **Nova ordem**
   - Clicar em "Nova Ordem"
   - Selecionar origem:
     - Manual: Ordem avulsa
     - PMP: Do Plano Mestre
     - MTO: Para pedido específico

2. **Preencher dados**
   - Código do produto
   - Quantidade planejada
   - Data início prevista
   - Data fim prevista
   - Linha de produção
   - Marcar "Explodir BOM" para calcular materiais

3. **Verificar materiais (BOM)**
   - Sistema mostra lista de materiais necessários
   - Para cada material:
     - Quantidade necessária
     - Quantidade disponível em estoque
     - Quantidade a comprar
   - Se faltar material, sistema cria necessidade de compra

4. **Salvar ordem**
   - Status inicial: "Planejada"
   - Número gerado: OP-2025-000001

#### 3.4 Sequenciamento de Produção

**Responsável**: PCP  
**Frequência**: Diária  
**Sistema**: `/manufatura/sequenciamento` ✅ IMPLEMENTADO (API)

**CRITÉRIOS DE PRIORIZAÇÃO:**

1. **Prioridade 1**: Ordens MTO com expedição próxima
2. **Prioridade 2**: Pedidos puxados pelo comercial
3. **Prioridade 3**: Produtos com ruptura iminente
4. **Prioridade 4**: Ordens MTS para reposição

**PASSO A PASSO:**

1. **Visualizar sequência**
   - Selecionar linha de produção
   - Definir período (ex: próximos 7 dias)
   - Sistema mostra sequência sugerida

2. **Ajustar sequência**
   - Arrastar e soltar ordens para reordenar
   - Verificar conflitos de horário
   - Considerar:
     - Disponibilidade de materiais
     - Capacidade da linha (unidades/minuto)
     - Tempo de setup entre produtos

3. **Liberar ordens**
   - Selecionar ordem sequenciada
   - Clicar em "Liberar para Produção"
   - Status muda para "Liberada"

#### 3.5 Atualização de Status

**FLUXO DE STATUS:**
```
Planejada → Liberada → Em Produção → Concluída
                ↓
            Cancelada
```

**AÇÕES POR STATUS:**

- **Planejada**: Aguardando liberação do PCP
- **Liberada**: Pronta para iniciar produção
- **Em Produção**: Sistema registra data início real
- **Concluída**: Sistema registra data fim real e quantidade produzida
- **Cancelada**: Ordem cancelada (libera materiais reservados)

---

### 📦 FASE 3: GESTÃO DE COMPRAS (Diário)

#### 3.6 Necessidades de Compras

**Responsável**: PCP  
**Frequência**: Diária  
**Sistema**: `/manufatura/requisicoes-compras` ✅ IMPLEMENTADO (API)

**ORIGEM DAS NECESSIDADES:**

1. **Automática**: Sistema gera ao explodir BOM das ordens
2. **Manual**: PCP identifica necessidade adicional
3. **Reposição**: Baseado em estoque mínimo

**PASSO A PASSO:**

1. **Visualizar necessidades**
   - Menu: Manufatura → Requisições de Compras
   - Aba "Necessidades" mostra To-Do list
   - Itens urgentes destacados em vermelho

2. **Analisar necessidade**
   - Verificar:
     - Produto e quantidade necessária
     - Data de necessidade
     - Ordens impactadas
     - Lead time do fornecedor

3. **Criar requisição no Odoo**
   - ⚠️ **IMPORTANTE**: Requisições são criadas MANUALMENTE no Odoo
   - Acessar Odoo ERP
   - Criar requisição de compra
   - Informar dados da necessidade

4. **Marcar como requisitada**
   - No sistema, clicar "Marcar como Criada no Odoo"
   - Status muda para "Requisitada"
   - Necessidade sai da lista To-Do

#### 3.7 Acompanhamento de Requisições

**FLUXO DE STATUS:**
```
Pendente → Requisitada → Em Cotação → Pedido Colocado
```

**MONITORAMENTO:**

1. **Requisições pendentes**: Aguardando criação no Odoo
2. **Requisições em andamento**: Criadas no Odoo
3. **Pedidos confirmados**: Importados do Odoo automaticamente

---

### 🔄 FASE 4: INTEGRAÇÃO ODOO ✅ IMPLEMENTADA

#### 3.8 Sincronizações (Manual ou Agendada)

**ENDPOINTS DISPONÍVEIS EM `/odoo/manufatura/`:**

| Função | Endpoint | Status | Descrição |
|--------|----------|--------|-----------|
| Importar Requisições | `/importar/requisicoes` | ✅ | Importa requisições do Odoo |
| Importar Pedidos | `/importar/pedidos` | ✅ | Importa pedidos confirmados |
| Sincronizar Produção | `/sincronizar/producao` | ✅ | Atualiza status e quantidades |
| Gerar Ordens MTO | `/gerar/ordens-mto` | ✅ | Cria ordens automáticas |
| Importar Histórico | `/importar/historico` | ✅ | Histórico para análise |
| Sincronização Completa | `/sincronizacao-completa` | ✅ | Executa todas as etapas |

#### 3.9 Dashboard de Integração Odoo

**Acesso ao Dashboard Completo:**

1. **URL**: `/odoo/manufatura/`
2. **Funcionalidades**:
   - Cards com estatísticas de sincronização
   - Botões para cada tipo de importação
   - Histórico de sincronizações
   - Botão de Sincronização Completa
3. **Execução**: Clicar no botão desejado
4. **Monitoramento**: Tabela com logs em tempo real

---

## 4. INDICADORES E MÉTRICAS

### 4.1 Dashboard Principal ✅ IMPLEMENTADO

**Acesso**: `/manufatura/dashboard` 

**MÉTRICAS DISPONÍVEIS:**

- **Ordens Abertas**: Total de ordens não concluídas
- **Necessidades Pendentes**: Itens aguardando compra
- **Taxa de Cumprimento**: % realizado vs previsto
- **Ordens Concluídas/Mês**: Produtividade mensal
- **Produtos em Ruptura**: Estoque < segurança
- **Pedidos MTO Pendentes**: Aguardando produção

### 4.2 KPIs Operacionais

| Indicador | Fórmula | Meta |
|-----------|---------|------|
| Aderência ao Plano | (Produzido / Planejado) × 100 | > 95% |
| Lead Time Produção | Data Fim Real - Data Início Real | < Previsto |
| Taxa de Retrabalho | (Refugo / Produzido) × 100 | < 2% |
| Giro de Estoque | Consumo / Estoque Médio | > 12x/ano |

---

## 5. REGRAS DE NEGÓCIO CRÍTICAS

### ⚠️ ATENÇÃO - NUNCA ESQUECER:

1. **Prioridade de Dados** ✅ IMPLEMENTADO
   - `Separacao` tem SEMPRE prioridade sobre `PreSeparacaoItem`
   - Quando mesmo `separacao_lote_id` existe em ambas, considerar APENAS Separacao

2. **Exclusões Automáticas** ✅ IMPLEMENTADO
   - Sistema EXCLUI pedidos com `status = 'FATURADO'` de todos os cálculos
   - Pedidos faturados não geram demanda nem ordens

3. **Fluxo de Requisições** ✅ IMPLEMENTADO
   - Necessidades são apenas TO-DO LIST
   - NÃO cria requisições automáticas no Odoo
   - PCP deve criar manualmente no Odoo

4. **Direção da Integração** ✅ IMPLEMENTADO
   - Sistema IMPORTA do Odoo (requisições, pedidos, produção)
   - Sistema NÃO EXPORTA requisições para Odoo

5. **MTO Automático** ✅ IMPLEMENTADO
   - Vinculação via `separacao_lote_id` (não CarteiraPrincipal diretamente)
   - Apenas para produtos com `lead_time_mto` cadastrado
   - Calcula: Data Expedição - Lead Time = Data Início Produção
   - Considera apenas dias úteis

---

## 6. TROUBLESHOOTING

### 6.1 Problemas Comuns

| Problema | Causa Provável | Solução |
|----------|---------------|---------|
| Ordem MTO não criada | Falta lead_time_mto | Cadastrar lead time no produto |
| Necessidade duplicada | Requisição já existe | Verificar requisições pendentes |
| Plano não gera ordem | Quantidade < lote mínimo | Ajustar lote mínimo |
| Sincronização falhou | Conexão Odoo | Verificar credenciais |
| Demanda incorreta | Pedido faturado incluído | Aguardar próxima sincronização |

### 6.2 Verificações Diárias

**CHECKLIST PCP:**
- [ ] Verificar ordens MTO geradas automaticamente
- [ ] Revisar necessidades urgentes (< 7 dias)
- [ ] Liberar ordens sequenciadas
- [ ] Verificar logs de integração
- [ ] Monitorar ordens em produção

---

## 7. CONTROLE DE ACESSO

### 7.1 Perfis e Permissões

| Perfil | Visualizar | Criar | Editar | Aprovar | Deletar |
|--------|------------|-------|--------|---------|---------|
| Comercial | ✓ | Previsão | Previsão | - | - |
| PCP | ✓ | ✓ | ✓ | ✓ | Ordens |
| Compras | ✓ | - | Requisições | - | - |
| Produção | ✓ | - | Status | - | - |
| Gerência | ✓ | ✓ | ✓ | ✓ | ✓ |

### 7.2 Auditoria

**REGISTROS MANTIDOS:**
- Criação e alteração de previsões
- Aprovação de planos mestres
- Liberação de ordens
- Alterações de status
- Logs de integração

---

## 8. ANEXOS

### Anexo A - Fluxograma do Processo
```
[Previsão Demanda] → [Plano Mestre] → [Ordens Produção]
                                            ↓
[Necessidades] ← [Explosão BOM] ← [Sequenciamento]
      ↓
[Requisição Odoo] → [Pedido Compra] → [Recebimento]
                                            ↓
                                      [Produção]
```

### Anexo B - Campos Obrigatórios por Tela

**Previsão de Demanda:**
- Mês/Ano
- Código Produto
- Quantidade Prevista
- Disparo Produção

**Ordem de Produção:**
- Código Produto
- Quantidade Planejada
- Data Início
- Data Fim

**Plano Mestre:**
- Estoque Segurança
- Status Aprovação

---

## 9. HISTÓRICO DE REVISÕES

| Versão | Data | Responsável | Alterações |
|--------|------|------------|------------|
| 1.0 | 10/08/2025 | Sistema | Versão inicial - Planejamento |
| 2.0 | 11/08/2025 | Sistema | Atualização pós-implementação completa |

---

## 10. APROVAÇÕES

| Cargo | Nome | Assinatura | Data |
|-------|------|------------|------|
| Gerente PCP | | | |
| Coordenador Produção | | | |
| Gerente TI | | | |

---

**FIM DO DOCUMENTO**

Para dúvidas ou sugestões sobre este POP, contatar:
- PCP: pcp@empresa.com
- TI: suporte@empresa.com