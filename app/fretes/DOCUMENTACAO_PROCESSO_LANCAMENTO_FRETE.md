# 📋 DOCUMENTAÇÃO COMPLETA: PROCESSO DE LANÇAMENTO DE FRETE

**Data de Criação:** 15/11/2025
**Autor:** Análise Profunda do Sistema
**Objetivo:** Documentar TODO o processo de lançamento de frete, vinculação a fatura e preenchimento de CT-e

---

## 📌 ÍNDICE

1. [Modelos e Relacionamentos](#modelos-e-relacionamentos)
2. [Fluxo de Lançamento de Frete](#fluxo-de-lancamento-de-frete)
3. [Vinculação à Fatura](#vinculacao-a-fatura)
4. [Preenchimento de CT-e](#preenchimento-de-cte)
5. [Regras de Negócio e Validações](#regras-de-negocio-e-validacoes)
6. [Status e Ciclo de Vida](#status-e-ciclo-de-vida)

---

## 1. MODELOS E RELACIONAMENTOS

### 1.1 Modelo FRETE (`fretes`)

**Definição Fundamental:**
```
1 Frete = 1 CTe = 1 Valor = 1 Vencimento = 1 CNPJ = 1 Embarque
Mas pode ter N pedidos e N NFs por frete
```

#### Campos Principais

| Campo | Tipo | Nullable | Descrição | Fonte |
|-------|------|----------|-----------|-------|
| `id` | Integer | ❌ | PK | Auto |
| `embarque_id` | Integer | ❌ | FK → embarques.id | Obrigatório |
| `cnpj_cliente` | String(20) | ❌ | CNPJ do cliente | Faturamento |
| `nome_cliente` | String(255) | ❌ | Nome do cliente | Faturamento |
| `transportadora_id` | Integer | ❌ | FK → transportadoras.id | Embarque |
| `tipo_carga` | String(20) | ❌ | FRACIONADA ou DIRETA | Embarque |
| `modalidade` | String(50) | ❌ | VALOR, PESO, VAN, etc | Tabela |

#### Totais das NFs

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `peso_total` | Float | ❌ Soma dos pesos das NFs |
| `valor_total_nfs` | Float | ❌ Soma dos valores das NFs |
| `quantidade_nfs` | Integer | ❌ Quantidade de NFs |
| `numeros_nfs` | Text | ❌ Lista de NFs (separadas por vírgula) |

#### OS 4 TIPOS DE VALORES DO FRETE

| Campo | Descrição | Quando é Preenchido |
|-------|-----------|---------------------|
| `valor_cotado` | ❌ Calculado pela tabela automaticamente | Na criação do frete |
| `valor_cte` | ✅ Valor cobrado pela transportadora | Na edição (CT-e) |
| `valor_considerado` | ✅ Valor que consideramos válido | Inicialmente = valor_cotado |
| `valor_pago` | ✅ Valor que efetivamente pagamos | Após conferência |

#### Dados do CT-e

| Campo | Tipo | Nullable | Quando Preenche |
|-------|------|----------|-----------------|
| `numero_cte` | String(255) | ✅ | Edição do frete |
| `data_emissao_cte` | Date | ✅ | Edição do frete |
| `vencimento` | Date | ✅ | Auto-preenchido da fatura ou manual |

#### Fatura de Frete

| Campo | Tipo | Nullable | Restrição |
|-------|------|----------|-----------|
| `fatura_frete_id` | Integer | ✅ | FK → faturas_frete.id |

**⚠️ REGRA CRÍTICA:** Para lançar CT-e é **OBRIGATÓRIO** ter fatura vinculada!

#### Vínculos com Odoo

| Campo | Tipo | Nullable | Quando Preenche |
|-------|------|----------|-----------------|
| `odoo_dfe_id` | Integer | ✅ | Após lançamento no Odoo (Etapa 1) |
| `odoo_purchase_order_id` | Integer | ✅ | Após criação do PO (Etapa 6) |
| `odoo_invoice_id` | Integer | ✅ | Após criação da Invoice (Etapa 11) |
| `lancado_odoo_em` | DateTime | ✅ | Timestamp do lançamento |
| `lancado_odoo_por` | String(100) | ✅ | Usuário que lançou |

#### Status e Aprovação

| Campo | Valores Possíveis | Padrão |
|-------|-------------------|--------|
| `status` | PENDENTE, EM_TRATATIVA, APROVADO, REJEITADO, PAGO, CANCELADO, LANCADO_ODOO | PENDENTE |
| `requer_aprovacao` | Boolean | False |
| `aprovado_por` | String(100) | null |
| `aprovado_em` | DateTime | null |

---

### 1.2 Modelo FATURAFRETE (`faturas_frete`)

**Definição:**
```
1 Fatura pode ter N CTes de N CNPJs
```

#### Campos Principais

| Campo | Tipo | Nullable | Descrição |
|-------|------|----------|-----------|
| `id` | Integer | ❌ | PK |
| `transportadora_id` | Integer | ❌ | FK → transportadoras.id |
| `numero_fatura` | String(50) | ❌ | Número da fatura (indexed) |
| `data_emissao` | Date | ❌ | Data de emissão |
| `valor_total_fatura` | Float | ❌ | Valor total da fatura |
| `vencimento` | Date | ✅ | Data de vencimento |
| `arquivo_pdf` | String(255) | ✅ | Caminho do PDF |

#### Status de Conferência

| Campo | Valores | Padrão |
|-------|---------|--------|
| `status_conferencia` | PENDENTE, EM_CONFERENCIA, CONFERIDO | PENDENTE |
| `conferido_por` | String(100) | null |
| `conferido_em` | DateTime | null |

#### Métodos Úteis

```python
def total_fretes(self) -> int
    # Retorna quantidade de fretes desta fatura

def valor_total_fretes(self) -> float
    # Soma dos valor_cte de todos os fretes

def total_despesas_extras(self) -> int
    # Quantidade de despesas extras vinculadas

def valor_total_despesas_extras(self) -> float
    # Soma das despesas extras
```

---

### 1.3 Modelo CONHECIMENTOTRANSPORTE (`conhecimento_transporte`)

**Definição:**
```
Registro de CTes importados do Odoo (modelo l10n_br_ciel_it_account.dfe com is_cte=True)
```

#### Vínculo com Odoo

| Campo | Tipo | Unique | Descrição |
|-------|------|--------|-----------|
| `dfe_id` | String(50) | ✅ | ID do DFe no Odoo (indexed) |
| `odoo_ativo` | Boolean | ❌ | Campo 'active' do Odoo |
| `odoo_name` | String(100) | ❌ | Ex: DFE/2025/15797 |
| `odoo_status_codigo` | String(2) | ❌ | 01-07 (indexed) |
| `odoo_status_descricao` | String(50) | ❌ | Ex: Concluído |

**Status Odoo:**
- 01 - Rascunho
- 02 - Sincronizado
- 03 - Ciência/Confirmado
- 04 - PO (Purchase Order criado)
- 05 - Rateio
- 06 - Concluído
- 07 - Rejeitado

#### Dados do CTe

| Campo | Tipo | Origem Odoo |
|-------|------|-------------|
| `chave_acesso` | String(44) | protnfe_infnfe_chnfe (unique, indexed) |
| `numero_cte` | String(20) | nfe_infnfe_ide_nnf (indexed) |
| `serie_cte` | String(10) | nfe_infnfe_ide_serie |
| `data_emissao` | Date | nfe_infnfe_ide_dhemi (indexed) |
| `valor_total` | Numeric(15,2) | nfe_infnfe_total_icmstot_vnf |
| `valor_frete` | Numeric(15,2) | nfe_infnfe_total_icms_vfrete |
| `vencimento` | Date | Preenchido posteriormente via fatura |

#### Partes Envolvidas

| Campo | Tipo | Origem Odoo | Indexed |
|-------|------|-------------|---------|
| `cnpj_emitente` | String(20) | nfe_infnfe_emit_cnpj | ✅ |
| `nome_emitente` | String(255) | nfe_infnfe_emit_xnome | ❌ |
| `cnpj_destinatario` | String(20) | nfe_infnfe_dest_cnpj | ✅ |
| `cnpj_remetente` | String(20) | nfe_infnfe_rem_cnpj | ✅ |
| `cnpj_expedidor` | String(20) | nfe_infnfe_exped_cnpj | ❌ |

#### Tomador

| Campo | Tipo | Valores | Indexed |
|-------|------|---------|---------|
| `tomador` | String(1) | 1-Remetente, 2-Expedidor, 3-Recebedor, 4-Destinatário | ❌ |
| `tomador_e_empresa` | Boolean | True se CNPJ começa com 61.724.241 | ✅ |

#### NFs do CTe

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `numeros_nfs` | Text | String separada por vírgula: "141768,141769,141770" |

#### Vínculo com Frete

| Campo | Tipo | Nullable | Indexed |
|-------|------|----------|---------|
| `frete_id` | Integer | ✅ | ✅ |
| `vinculado_manualmente` | Boolean | ❌ (default=False) | ❌ |
| `vinculado_em` | DateTime | ✅ | ❌ |
| `vinculado_por` | String(100) | ✅ | ❌ |

#### Arquivos

| Campo | Tipo | Origem Odoo |
|-------|------|-------------|
| `cte_pdf_path` | String(500) | Caminho S3/local |
| `cte_xml_path` | String(500) | Caminho S3/local |
| `cte_pdf_nome_arquivo` | String(255) | l10n_br_pdf_dfe_fname |
| `cte_xml_nome_arquivo` | String(255) | l10n_br_xml_dfe_fname |

---

## 2. FLUXO DE LANÇAMENTO DE FRETE

### 2.1 OPÇÃO 1: Criar Frete Novo por NF

**Rota:** `/fretes/criar_novo_frete_por_nf`
**Método:** GET
**Parâmetros:**
- `numero_nf` (required)
- `fatura_frete_id` (required)

#### Passos:

1. **Busca NF no Faturamento**
   ```python
   nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
   ```

2. **Busca Embarque que contém a NF**
   ```python
   embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).first()
   embarque = embarque_item.embarque
   ```

3. **Agrupa todas as NFs do MESMO CNPJ no embarque**
   ```python
   cnpj_cliente = nf_faturamento.cnpj_cliente
   itens_embarque_cnpj = EmbarqueItem.query.filter(
       embarque_id == embarque.id,
       nota_fiscal.in_(numeros_nfs_cnpj)
   ).all()
   ```

4. **Calcula totais**
   ```python
   total_peso = sum(nf.peso_bruto for nf in outras_nfs)
   total_valor = sum(nf.valor_total for nf in outras_nfs)
   numeros_nfs = ','.join([item.nota_fiscal for item in itens_embarque_cnpj])
   ```

5. **Renderiza formulário** (`criar_novo_frete.html`)

---

### 2.2 OPÇÃO 2: Processar Lançamento de Frete

**Rota:** `/fretes/processar_lancamento_frete`
**Método:** POST

#### Dados do Formulário:

| Campo | Tipo | Origem |
|-------|------|--------|
| `embarque_id` | Integer | Hidden field |
| `cnpj_cliente` | String | Hidden field |
| `nome_cliente` | String | Hidden field |
| `transportadora_id` | Integer | Do embarque |
| `tipo_carga` | String | Do embarque |
| `peso_total` | Float | Soma das NFs |
| `valor_total_nfs` | Float | Soma das NFs |
| `quantidade_nfs` | Integer | Contagem |
| `numeros_nfs` | String | Lista separada por vírgula |
| `fatura_frete_id` | Integer | **OBRIGATÓRIO** |

#### Passos:

1. **Busca Embarque**
   ```python
   embarque = Embarque.query.get_or_404(embarque_id)
   ```

2. **Prepara dados da tabela**
   - **Se DIRETA:** dados vêm do embarque
   - **Se FRACIONADA:** dados vêm de um item do CNPJ

   ```python
   if tipo_carga == 'DIRETA':
       tabela_dados = TabelaFreteManager.preparar_dados_tabela(embarque)
   else:
       item_referencia = EmbarqueItem.query.filter(...).first()
       tabela_dados = TabelaFreteManager.preparar_dados_tabela(item_referencia)
   ```

3. **Calcula valor_cotado**
   ```python
   valor_cotado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total, valor_total_nfs)
   ```

4. **Cria o Frete**
   ```python
   novo_frete = Frete(
       embarque_id=embarque_id,
       cnpj_cliente=cnpj_cliente,
       nome_cliente=nome_cliente,
       transportadora_id=transportadora_id,
       tipo_carga=tipo_carga,
       modalidade=tabela_dados['modalidade'],
       peso_total=peso_total,
       valor_total_nfs=valor_total_nfs,
       quantidade_nfs=quantidade_nfs,
       numeros_nfs=numeros_nfs,
       valor_cotado=valor_cotado,
       valor_considerado=valor_cotado,  # ✅ Inicialmente igual
       fatura_frete_id=fatura_frete_id,  # ✅ JÁ VINCULA
       criado_por=current_user.nome,
       lancado_em=datetime.utcnow(),
       lancado_por=current_user.nome
   )

   TabelaFreteManager.atribuir_campos_objeto(novo_frete, tabela_dados)
   db.session.add(novo_frete)
   db.session.commit()
   ```

5. **Redireciona** para visualização do frete

---

## 3. VINCULAÇÃO À FATURA

### 3.1 Quando Ocorre?

A vinculação do frete à fatura pode ocorrer em **2 momentos**:

#### Momento 1: NA CRIAÇÃO DO FRETE
```python
# routes.py:393
fatura_frete_id=fatura_frete_id,  # ✅ JÁ VÍNCULADO
```

**Fluxo:**
1. Usuário acessa "Lançar CT-e" → Seleciona Fatura
2. Busca pela NF
3. Cria frete → **JÁ vinculado à fatura**

#### Momento 2: EM FRETE EXISTENTE
**Rota:** `/fretes/processar_cte_frete_existente`
**Método:** POST

```python
# routes.py:305-318
# ✅ VALIDAÇÃO: Transportadora da fatura deve ser a mesma do frete
if frete.transportadora_id != fatura.transportadora_id:
    flash('Erro: Transportadoras diferentes!', 'error')
    return redirect(...)

# ✅ VINCULA A FATURA AO FRETE EXISTENTE
if not frete.fatura_frete_id:
    frete.fatura_frete_id = fatura_frete_id
    flash('Fatura vinculada', 'success')
elif frete.fatura_frete_id != fatura_frete_id:
    flash('Trocando fatura vinculada', 'warning')
    frete.fatura_frete_id = fatura_frete_id

# ✅ PRÉ-PREENCHE VENCIMENTO DA FATURA
if fatura.vencimento and not frete.vencimento:
    frete.vencimento = fatura.vencimento
    flash('Vencimento preenchido automaticamente', 'info')
```

---

### 3.2 Validações de Vinculação

| Validação | Código | Mensagem |
|-----------|--------|----------|
| **Fatura obrigatória para CT-e** | `routes.py:449-453` | "Este frete não possui fatura vinculada! Para lançar CTe é obrigatório ter fatura." |
| **Transportadora deve ser a mesma** | `routes.py:306-308` | "A transportadora da fatura (X) é diferente da transportadora do frete (Y)!" |
| **Auto-preencher vencimento** | `routes.py:321-323` | "Vencimento preenchido automaticamente: DD/MM/YYYY" |

---

### 3.3 Regra do Vencimento

**Auto-preenchimento:**
```python
# routes.py:458-460
if frete.fatura_frete and frete.fatura_frete.vencimento and not frete.vencimento:
    frete.vencimento = frete.fatura_frete.vencimento
    form.vencimento.data = frete.fatura_frete.vencimento
```

**Prioridade:**
1. ✅ Se fatura tem vencimento E frete não tem → **Auto-preenche**
2. ✅ Se frete já tem vencimento → **Mantém**
3. ✅ Se fatura não tem vencimento → **Usuário preenche manualmente**

---

## 4. PREENCHIMENTO DE CT-e

### 4.1 Onde Ocorre?

**Rota:** `/fretes/<int:frete_id>/editar`
**Método:** GET (formulário) / POST (salvar)

#### Validação Inicial:
```python
# routes.py:448-453
if not frete.fatura_frete_id:
    flash('❌ Este frete não possui fatura vinculada!', 'error')
    flash('💡 Fluxo correto: Fretes → Faturas → Criar Fatura → Lançar CTe', 'info')
    return redirect(...)
```

**⚠️ BLOQUEIO TOTAL:** Não permite editar frete sem fatura!

---

### 4.2 Campos Preenchidos no CT-e

#### Campos do Formulário (`FreteForm`):

| Campo | Tipo | Origem | Obrigatório |
|-------|------|--------|-------------|
| `numero_cte` | String(255) | Manual | ❌ |
| `vencimento` | Date | Auto (fatura) ou Manual | ✅ |
| `valor_cte` | String | Manual (aceita vírgula) | ✅ |
| `valor_considerado` | String | Manual (aceita vírgula) | ✅ |
| `valor_pago` | String | Manual (aceita vírgula) | ❌ |

#### Processamento no POST:

```python
# routes.py:463-480
frete.numero_cte = form.numero_cte.data
frete.vencimento = form.vencimento.data

# ✅ CONVERSÃO DE VALORES (aceita vírgula)
frete.valor_cte = converter_valor_brasileiro(form.valor_cte.data)
frete.valor_considerado = converter_valor_brasileiro(form.valor_considerado.data)
frete.valor_pago = converter_valor_brasileiro(form.valor_pago.data) if form.valor_pago.data else None
```

---

### 4.3 Busca de CTes Relacionados do Odoo

**Método:** `Frete.buscar_ctes_relacionados()`
**Localização:** `models.py:184-248`

#### Critérios de Busca:

1. **Pelo menos 1 NF em comum** entre frete e CTe
2. **Prefixo do CNPJ da transportadora** (primeiros 8 dígitos)
3. **Tomador deve ser a empresa** (CNPJ começa com 61.724.241)
4. **CTe ativo** (`ativo=True`)

#### Lógica:

```python
# Extrair prefixo CNPJ transportadora (8 primeiros dígitos)
cnpj_limpo = ''.join(filter(str.isdigit, cnpj_transportadora))
prefixo_cnpj = cnpj_limpo[:8]

# Buscar CTes
ctes_relacionados = ConhecimentoTransporte.query.filter(
    ativo == True,
    cnpj_emitente.isnot(None),
    numeros_nfs.isnot(None),
    tomador_e_empresa == True  # ✅ FILTRO CRÍTICO
).all()

# Filtrar em Python
for cte in ctes_relacionados:
    # Verificar prefixo CNPJ
    cnpj_cte_limpo = ''.join(filter(str.isdigit, cte.cnpj_emitente))
    if cnpj_cte_limpo[:8] != prefixo_cnpj:
        continue

    # Verificar NFs em comum
    nfs_frete = set(numeros_nfs.split(','))
    nfs_cte = set(cte.numeros_nfs.split(','))
    nfs_comuns = nfs_frete & nfs_cte

    if nfs_comuns:
        ctes_validos.append(cte)
```

---

## 5. REGRAS DE NEGÓCIO E VALIDAÇÕES

### 5.1 Regra dos R$ 5,00

**Método:** `Frete.requer_aprovacao_por_valor()`

#### Critérios:

| Condição | Ação |
|----------|------|
| `\|valor_considerado - valor_pago\| > R$ 5,00` | ✅ Requer aprovação (EM_TRATATIVA) |
| `\|valor_considerado - valor_cotado\| > R$ 5,00` | ✅ Requer aprovação (EM_TRATATIVA) |
| Diferença ≤ R$ 5,00 | ❌ Não requer aprovação |

#### Implementação:

```python
# models.py:130-159
requer = False
motivos = []

# Verifica considerado vs pago
if self.valor_considerado and self.valor_pago:
    diferenca = abs(self.valor_considerado - self.valor_pago)
    if diferenca > 5.00:
        requer = True
        motivos.append(f"Diferença de R$ {diferenca:.2f}")

# Verifica considerado vs cotado
if self.valor_considerado and self.valor_cotado:
    diferenca = abs(self.valor_considerado - self.valor_cotado)
    if diferenca > 5.00:
        requer = True
        motivos.append(f"Diferença de R$ {diferenca:.2f}")

return requer, motivos
```

---

### 5.2 Lançamento na Conta Corrente

**Método:** `Frete.deve_lancar_conta_corrente()`

#### Regras:

| Situação | Flag `considerar_diferenca` | Lança? |
|----------|----------------------------|--------|
| Diferença ≤ R$ 5,00 | ✅ True | ✅ SIM |
| Diferença ≤ R$ 5,00 | ❌ False | ❌ NÃO |
| Diferença > R$ 5,00 | Qualquer | ✅ SIM (se status=APROVADO) |
| Diferença > R$ 5,00 | Qualquer | ❌ NÃO (se status≠APROVADO) |

#### Implementação:

```python
# models.py:161-183
if not self.valor_considerado or not self.valor_pago:
    return False, "Valores não informados"

diferenca = abs(self.valor_considerado - self.valor_pago)

if diferenca <= 5.00:
    if self.considerar_diferenca:
        return True, f"Diferença de R$ {diferenca:.2f} será lançada (flag ativa)"
    else:
        return False, f"Diferença de R$ {diferenca:.2f} ignorada (flag inativa)"
else:
    if self.status == 'APROVADO':
        return True, f"Diferença de R$ {diferenca:.2f} aprovada"
    else:
        return False, f"Diferença de R$ {diferenca:.2f} requer aprovação"
```

---

## 6. STATUS E CICLO DE VIDA

### 6.1 Status Possíveis

| Status | Quando Ocorre |
|--------|---------------|
| `PENDENTE` | Frete criado, aguardando CT-e |
| `EM_TRATATIVA` | Diferença > R$ 5,00 detectada |
| `APROVADO` | Aprovado manualmente por usuário |
| `REJEITADO` | Rejeitado |
| `PAGO` | Pagamento confirmado |
| `CANCELADO` | Frete cancelado |
| `LANCADO_ODOO` | Lançado no Odoo com sucesso |

---

### 6.2 Ciclo de Vida Completo

```
┌─────────────────┐
│ CRIAR FATURA    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CRIAR FRETE     │ ← fatura_frete_id vinculado
│ status=PENDENTE │ ← valor_cotado calculado
└────────┬────────┘ ← valor_considerado = valor_cotado
         │
         ▼
┌─────────────────┐
│ EDITAR FRETE    │ ← ❌ Bloqueado se não tiver fatura
│ (Lançar CTe)    │ ← Preenche numero_cte, valor_cte, vencimento
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ VALIDAR VALORES │
└────────┬────────┘
         │
         ├──► Diferença ≤ R$ 5,00 ──► Pode prosseguir
         │
         └──► Diferença > R$ 5,00 ──► status = EM_TRATATIVA ──► Requer APROVAÇÃO
                                                                        │
                                                                        ▼
                                                             ┌─────────────────────┐
                                                             │ APROVAR/REJEITAR    │
                                                             └──────────┬──────────┘
                                                                        │
                ┌───────────────────────────────────────────────────────┴────┐
                ▼                                                            ▼
    ┌───────────────────┐                                        ┌──────────────────┐
    │ status = APROVADO │                                        │ status=REJEITADO │
    └─────────┬─────────┘                                        └──────────────────┘
              │
              ▼
    ┌───────────────────┐
    │ LANÇAR NO ODOO    │ ← 16 etapas auditadas
    │ (se aplicável)    │ ← Preenche odoo_dfe_id, odoo_purchase_order_id, odoo_invoice_id
    └─────────┬─────────┘ ← Preenche payment_reference nos 3 modelos
              │
              ▼
    ┌───────────────────┐
    │ status =          │
    │ LANCADO_ODOO      │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ CONTA CORRENTE    │ ← Lançamento baseado na flag considerar_diferenca
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ status = PAGO     │
    └───────────────────┘
```

---

## 7. RESUMO DE RESTRIÇÕES E VALIDAÇÕES

### ✅ OBRIGATÓRIOS

| Restrição | Local | Mensagem |
|-----------|-------|----------|
| Fatura vinculada para lançar CTe | `routes.py:449` | "Este frete não possui fatura vinculada!" |
| Transportadora da fatura = transportadora do frete | `routes.py:306` | "Transportadoras diferentes!" |
| Valores numéricos válidos | Formulário | Validação de tipo |

### ⚠️ ATENÇÕES

| Atenção | Comportamento |
|---------|---------------|
| Auto-preenche vencimento da fatura | Se frete não tiver vencimento |
| Diferença > R$ 5,00 | Muda status para EM_TRATATIVA |
| Flag `considerar_diferenca` | Controla lançamento na conta corrente |

### 🔒 BLOQUEIOS

| Bloqueio | Motivo |
|----------|--------|
| Editar frete sem fatura | Obrigatório ter fatura |
| CTe já lançado | Impede lançar novamente |
| Transportadoras diferentes | Inconsistência de dados |

---

## 8. CAMPOS QUE PROPAGAM PARA ODOO

Conforme implementação em `lancamento_odoo_service.py`:

| Modelo Odoo | Campo | Valor | Etapa |
|-------------|-------|-------|-------|
| `l10n_br_ciel_it_account.dfe` | `payment_reference` | `FATURA-{numero_fatura}` | 2 |
| `purchase.order` | `partner_ref` | `FATURA-{numero_fatura}` | 7 |
| `account.move` | `payment_reference` | `FATURA-{numero_fatura}` | 13 |

**Lógica:**
```python
if frete.fatura_frete_id and frete.fatura_frete:
    referencia_fatura = f"FATURA-{frete.fatura_frete.numero_fatura}"

    # Busca valor atual
    valor_atual = odoo.read(modelo, [id], [campo])

    # Só atualiza se diferente
    if valor_atual != referencia_fatura:
        odoo.write(modelo, [id], {campo: referencia_fatura})
```

---

## 9. PERGUNTAS E RESPOSTAS

### Q1: É possível criar frete sem fatura?
**R:** ✅ SIM, mas **NÃO é possível lançar CT-e** sem fatura vinculada.

### Q2: Pode trocar a fatura de um frete?
**R:** ✅ SIM, mas o sistema alerta com warning.

### Q3: O que acontece se diferença > R$ 5,00?
**R:** Status muda para `EM_TRATATIVA` e requer aprovação manual.

### Q4: Como funciona o auto-preenchimento do vencimento?
**R:** Se fatura tem vencimento e frete não tem, copia automaticamente.

### Q5: Pode lançar no Odoo sem ter CT-e preenchido?
**R:** ✅ SIM, mas precisa ter a **chave de acesso** do CT-e (44 dígitos).

### Q6: O que é o campo `considerar_diferenca`?
**R:** Flag booleana que controla se diferença ≤ R$ 5,00 é lançada na conta corrente.

---

**FIM DA DOCUMENTAÇÃO**
