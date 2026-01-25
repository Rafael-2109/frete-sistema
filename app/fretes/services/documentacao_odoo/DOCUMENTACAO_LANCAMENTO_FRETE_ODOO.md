# 📋 DOCUMENTAÇÃO COMPLETA - LANÇAMENTO AUTOMÁTICO DE FRETE NO ODOO

**Data:** 14/11/2025
**Autor:** Sistema de Fretes
**Status:** Script completo e funcional ✅

---

## 🎯 RESUMO EXECUTIVO

Foi criado um **sistema completo de lançamento automático de CTe no Odoo**, que executa **16 etapas** de forma totalmente automatizada, desde a busca do CTe até a confirmação final da fatura.

---

## 📂 ARQUIVOS CRIADOS

### 1. **Script Principal - COMPLETO E FUNCIONAL**
**Arquivo:** `/home/rafaelnascimento/projetos/frete_sistema/scripts/lancamento_frete_completo.py`

**Uso:**
```bash
python3 scripts/lancamento_frete_completo.py <CHAVE_CTE> [DATA_VENCIMENTO]
```

**Exemplo:**
```bash
python3 scripts/lancamento_frete_completo.py 33251120341933000150570010000281801000319398 2025-12-31
```

### 2. **Scripts de Suporte (para debug/testes)**
- `scripts/investigar_dfe_32639_standalone.py` - Investiga estrutura de DFe
- `scripts/investigar_purchase_order_31085.py` - Investiga PO
- `scripts/aprovar_purchase_order.py` - Aprova PO standalone
- `scripts/criar_fatura_po.py` - Cria fatura standalone
- `scripts/descobrir_empresa_cd.py` - Descobre ID da empresa
- `scripts/investigar_operacao_fiscal_po.py` - Investiga operação fiscal
- `scripts/investigar_invoice_campos.py` - Investiga campos da invoice

---

## 🔧 IDS FIXOS DESCOBERTOS E CONFIGURADOS

```python
# IDs usados no script (NÃO MUDAR!)
PRODUTO_SERVICO_FRETE_ID = 29993          # "SERVIÇO DE FRETE" (código 800000025)
CONTA_ANALITICA_LOGISTICA_ID = 1186       # "LOGISTICA TRANSPORTE" (código 119009)
TEAM_LANCAMENTO_FRETE_ID = 119            # "Lançamento Frete"
PAYMENT_PROVIDER_TRANSFERENCIA_ID = 30    # "Transferência Bancária"
COMPANY_NACOM_GOYA_CD_ID = 4              # "NACOM GOYA - CD"
```

---

## 📊 PROCESSO COMPLETO - 16 ETAPAS AUTOMATIZADAS

### **ETAPA 1: LANÇAMENTO NO DF-e** (6 passos)

**Modelo Odoo:** `l10n_br_ciel_it_account.dfe`

1. **Conectar no Odoo** - Autenticação via XML-RPC
2. **Buscar DFe pela chave** - Campo: `protnfe_infnfe_chnfe`
3. **Atualizar data de entrada** - Campo: `l10n_br_data_entrada` = hoje
4. **Atualizar tipo pedido** - Campo: `l10n_br_tipo_pedido` = 'servico'
5. **Atualizar linha com produto** - Modelo: `l10n_br_ciel_it_account.dfe.line`
   - `product_id` = 29993 (SERVIÇO DE FRETE)
   - `l10n_br_quantidade` = 1.0
   - `product_uom_id` = 1 (UN)
6. **Atualizar vencimento** - Modelo: `l10n_br_ciel_it_account.dfe.pagamento`
   - Campo: `cobr_dup_dvenc` = data_vencimento
7. **Gerar Purchase Order** - Método: `action_gerar_po_dfe`
   - Contexto: `{'validate_analytic': True}`

---

### **ETAPA 2: CONFIRMAÇÃO DO PURCHASE ORDER** (5 passos)

**Modelo Odoo:** `purchase.order`

8. **Buscar PO gerado** - Extrair `res_id` do resultado de `action_gerar_po_dfe`
9. **Atualizar campos obrigatórios:**
   - `team_id` = 119 (Lançamento Frete)
   - `payment_provider_id` = 30 (Transferência Bancária)
   - **`company_id` = 4 (NACOM GOYA - CD)** ← CRÍTICO!
10. **Atualizar impostos do PO** - Método: `onchange_l10n_br_calcular_imposto`
    - ⚠️ Retorna None (erro de serialização, mas executa corretamente)
11. **Confirmar pedido** - Método: `button_confirm`
    - Contexto: `{'validate_analytic': True}`
12. **Aprovar pedido** (se state='to approve') - Método: `button_approve`

---

### **ETAPA 3: CRIAÇÃO DA FATURA** (2 passos)

**Modelo Odoo:** `account.move`

13. **Criar fatura** - Método: `action_create_invoice` no PO
    - Extrair `invoice_id` do resultado ou buscar em `invoice_ids` do PO
14. **Atualizar impostos da fatura** - Método: `onchange_l10n_br_calcular_imposto`
    - ⚠️ Retorna None (erro de serialização, mas executa)

---

### **ETAPA 4: CONFIRMAÇÃO DA FATURA** (3 passos + 3 campos)

**Modelo Odoo:** `account.move`

15. **Configurar 3 campos da fatura:**
    - `l10n_br_compra_indcom` = 'out' (Outros)
    - `l10n_br_situacao_nf` = 'autorizado' (Autorizado)
    - `invoice_date_due` = data_vencimento
16. **Atualizar impostos novamente** - Método: `onchange_l10n_br_calcular_imposto_btn`
    - ⚠️ Retorna None (normal)
17. **Confirmar fatura** - Método: `action_post`
    - Contexto: `{'validate_analytic': True}`

---

## ✅ TESTE REALIZADO COM SUCESSO

**CTe Cobaia:** 33251120341933000150570010000281801000319398
**DFe ID:** 32639

**Resultados dos Testes:**
- PO 31085 (C2512194) - Primeiro teste completo
- PO 31086 (C2512195) - Erro de empresa incompatível (antes de adicionar company_id)
- PO 31087 (C2512196) - Funcionou, mas sem situacao_nf
- PO 31088 (C2512197) - Funcionou completo
- **PO 31089 (C2512198) + Invoice 405941** - ✅ **PERFEITO!** Todos os campos corretos

---

## 🔴 PROBLEMAS CONHECIDOS E SOLUÇÕES

### 1. **Erro "cannot marshal None"**
- **Causa:** Métodos Odoo retornam None, XML-RPC não serializa
- **Solução:** Catch exception e continuar (método executa corretamente)
- **Métodos afetados:**
  - `onchange_l10n_br_calcular_imposto`
  - `onchange_l10n_br_calcular_imposto_btn`
  - `button_approve`

### 2. **Erro "Empresas incompatíveis"**
- **Causa:** Operação fiscal não pertence à empresa CD
- **Solução:** SEMPRE setar `company_id = 4` ANTES de confirmar PO
- **Ordem correta:**
  1. Atualizar company_id
  2. Atualizar impostos (ajusta operação fiscal)
  3. Confirmar PO

### 3. **Permissões de acesso**
- **Usuário:** rafael@conservascampobelo.com.br (ID 42)
- Se falhar por permissão, liberar acesso ao modelo no Odoo

---

## 📝 CAMPOS IMPORTANTES DOS MODELOS

### **DFe (l10n_br_ciel_it_account.dfe)**
```python
protnfe_infnfe_chnfe      # Chave de acesso do CTe
l10n_br_data_entrada      # Data de entrada
l10n_br_tipo_pedido       # 'servico' para frete
l10n_br_status            # Status do DFe ('04' = pronto para gerar PO)
lines_ids                 # IDs das linhas
dups_ids                  # IDs dos pagamentos
```

### **DFe Line (l10n_br_ciel_it_account.dfe.line)**
```python
product_id                # ID do produto
l10n_br_quantidade        # Quantidade
product_uom_id            # Unidade de medida
analytic_distribution     # Distribuição analítica (pode ser preenchida por trigger)
```

### **DFe Pagamento (l10n_br_ciel_it_account.dfe.pagamento)**
```python
cobr_dup_dvenc           # Data de vencimento
cobr_dup_ndup            # Número da duplicata
cobr_dup_vdup            # Valor da duplicata
```

### **Purchase Order (purchase.order)**
```python
team_id                  # Equipe (119 = Lançamento Frete)
payment_provider_id      # Fornecedor de pagamento (30 = Transferência)
company_id               # Empresa (4 = NACOM GOYA - CD) ← CRÍTICO!
l10n_br_operacao_id      # Operação fiscal (ajustada por onchange)
state                    # draft, to approve, purchase
invoice_status           # no, to invoice, invoiced
invoice_ids              # IDs das invoices geradas
```

### **Invoice (account.move)**
```python
l10n_br_compra_indcom    # Destinação: 'out' (Outros)
l10n_br_situacao_nf      # Situação: 'autorizado' (Autorizado)
invoice_date_due         # Data de vencimento
state                    # draft, posted
```

---

## 🚀 PRÓXIMOS PASSOS (APÓS COMPACTAÇÃO)

### 1. **Criar Tabela de Auditoria**
- Gravar TODOS os campos antes e depois de cada etapa
- Incluir: usuario, data_hora, etapa, modelo, campo, valor_antes, valor_depois
- Modelo sugerido: `LancamentoFreteAuditoria`

### 2. **Vincular CTe com Frete do Sistema**
- **Validação:** `Frete.valor_cte` = `ConhecimentoTransporte.valor_total`
- Criar relacionamento: `ConhecimentoTransporte.frete_id` ↔ `Frete.cte_id`
- Modelo de Frete: preciso investigar qual é (não foi trabalhado ainda)
- **IMPORTANTE:** Validar APENAS o campo `valor_cte` do Frete com `valor_total` do CTe

### 3. **Exibir Vinculações**
- No CTe: mostrar frete vinculado
- No Frete: mostrar CTe vinculado
- Templates a criar/modificar

### 4. **Criar Service de Lançamento**
- Local: `app/fretes/services/lancamento_odoo_service.py`
- Método: `lancar_frete_odoo(cte_chave, data_vencimento, usuario_id)`
- Retornar: resultado completo com auditoria

### 5. **Criar Botão na Tela de Fretes**
- Adicionar botão "Lançar no Odoo"
- Modal para confirmar e escolher data de vencimento
- Chamar service
- Mostrar resultado (sucesso/erro)

---

## 📦 ESTRUTURA DO SISTEMA DE FRETES (ATUAL)

```
app/fretes/
├── __init__.py
├── models.py              # ConhecimentoTransporte, etc
├── routes.py              # Rotas web
├── cte_routes.py          # Rotas específicas de CTe
├── forms.py               # Formulários
├── email_models.py        # Modelos de email
├── email_routes.py        # Rotas de email
└── lancamento.md          # ← ESTA DOCUMENTAÇÃO DO PROCESSO MANUAL
```

---

## 🔗 MODELOS RELACIONADOS (INVESTIGAR)

**Preciso entender:**
1. Qual modelo representa "Frete" no sistema?
   - Verificar `app/fretes/models.py`
   - Campos: `valor_pago`, `valor_cte`, relação com transportadora

2. Como CTe se relaciona com Frete atualmente?
   - Já existe vinculação?
   - ConhecimentoTransporte tem campo `frete_id`?

3. Onde ficam os fretes na UI?
   - Templates em `app/templates/fretes/`?
   - Qual rota mostra lista de fretes?

---

## 🔍 COMANDOS ÚTEIS PARA INVESTIGAÇÃO

### Ver estrutura do modelo Frete:
```bash
grep -r "class.*Frete" app/fretes/models.py
```

### Ver rotas de fretes:
```bash
cat app/fretes/routes.py | grep "@"
```

### Buscar campos valor_pago, valor_cte:
```bash
grep -r "valor_pago\|valor_cte" app/fretes/
```

---

## ⚙️ CONFIGURAÇÃO ODOO

**Arquivo de Config:** `app/odoo/config/odoo_config.py`

```python
import os

ODOO_CONFIG = {
    'url': os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br'),
    'database': os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd'),
    'username': os.environ.get('ODOO_USERNAME', ''),
    'api_key': os.environ.get('ODOO_API_KEY', ''),  # Configure via variável de ambiente!
    'timeout': 120,
    'retry_attempts': 3
}
```

**Helper de Conexão:** `app/odoo/utils/connection.py`
- Classe: `OdooConnection`
- Método: `get_odoo_connection()`

---

## 📚 REFERÊNCIAS IMPORTANTES

1. **CLAUDE.md** - Mapeamento de campos dos modelos do sistema
2. **REGRAS_NEGOCIO.md** - Regras de negócio (se existir)
3. **app/fretes/lancamento.md** - Este arquivo com processo manual detalhado

---

## ✅ CHECKLIST ANTES DE CONTINUAR

Após compactação, verificar:

- [ ] Modelos de Frete existentes no sistema
- [ ] Campos `valor_pago` e `valor_cte`
- [ ] Relacionamento CTe ↔ Frete (se existe)
- [ ] Templates de visualização de fretes
- [ ] Onde adicionar botão de lançamento
- [ ] Estrutura de auditoria existente (se houver)

---

## 🎯 OBJETIVO FINAL

**Sistema Completo de Lançamento de Frete:**

1. ✅ Script standalone funcional (PRONTO)
2. ⏳ Auditoria completa de todas as operações
3. ⏳ Vinculação CTe ↔ Frete com validação
4. ⏳ Visualização de vínculos
5. ⏳ Service integrado ao sistema Flask
6. ⏳ Interface web com botão de lançamento

---

**FIM DA DOCUMENTAÇÃO**

Esta documentação contém TUDO necessário para continuar o desenvolvimento após a compactação da conversa.
