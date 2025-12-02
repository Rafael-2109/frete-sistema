# DFE - Documentos Fiscais Eletronicos

Documentacao completa dos campos do modelo DFE no Odoo, com foco em campos fiscais e tributarios.

## Visao Geral

O DFE (Documento Fiscal Eletronico) eh o modelo que armazena NFe, NFSe, CTe e outros documentos fiscais recebidos no Odoo. Ele eh a porta de entrada para todas as notas fiscais emitidas contra a empresa.

**Tipos de Documentos:**
- **NFe** (mod=55): Nota Fiscal Eletronica de mercadorias
- **CTe** (mod=57): Conhecimento de Transporte Eletronico (frete)
- **NFSe** (mod=99): Nota Fiscal de Servicos Eletronica

---

## Modelo Principal

**Modelo Odoo:** `l10n_br_ciel_it_account.dfe`

### Campos de Identificacao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID do registro |
| `protnfe_infnfe_chnfe` | char | Chave de acesso (44 digitos) |
| `nfe_infnfe_ide_nnf` | char | Numero da NF |
| `nfe_infnfe_ide_serie` | char | Serie |
| `nfe_infnfe_ide_mod` | char | Modelo (55=NFe, 57=CTe) |
| `company_id` | many2one | Empresa destinataria (obrigatorio) |

### Campos de Finalidade e Tipo

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_ide_finnfe` | selection | Finalidade da NF |
| `is_cte` | boolean | Indica se eh CTe |
| `l10n_br_tipo_pedido` | selection | Tipo de Pedido (servico, mercadoria, etc) |
| `l10n_br_situacao_dfe` | selection | Situacao do DFe |

**Valores de finnfe (Finalidade):**
| Codigo | Descricao | Uso |
|--------|-----------|-----|
| 1 | Normal | Venda, compra, entrada |
| 2 | Complementar | Ajuste de valor/imposto |
| 3 | Ajuste | Correcao fiscal |
| 4 | Devolucao | Retorno de mercadoria |

### Campos de Datas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_ide_dhemi` | datetime | Data/hora emissao |
| `nfe_infnfe_ide_dhsaient` | datetime | Data/hora saida/entrada |
| `l10n_br_date_in` | date | Data entrada (lancamento no sistema) |
| `l10n_br_data_entrada` | date | Data de lancamento |

### Campos do Emitente (Fornecedor)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Parceiro emitente (res.partner) |
| `nfe_infnfe_emit_cnpj` | char | CNPJ emitente (COM pontuacao: XX.XXX.XXX/XXXX-XX) |
| `nfe_infnfe_emit_cpf` | char | CPF emitente |
| `nfe_infnfe_emit_xnome` | char | Razao social |
| `nfe_infnfe_emit_xfant` | char | Nome fantasia |
| `nfe_infnfe_emit_ie` | char | Inscricao estadual |
| `nfe_infnfe_emit_ender_xlgr` | char | Logradouro |
| `nfe_infnfe_emit_ender_xmun` | char | Municipio |
| `nfe_infnfe_emit_ender_uf` | char | UF |

> **NOTA**: O script `consultando_conhecidas.py` aceita CNPJ com ou sem pontuacao e converte automaticamente.

### Campos do Destinatario (Empresa)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_dest_id` | many2one | Parceiro destinatario (res.partner) |
| `nfe_infnfe_dest_cnpj` | char | CNPJ destinatario (SEM pontuacao) |
| `nfe_infnfe_dest_cpf` | char | CPF destinatario |
| `nfe_infnfe_dest_uf` | char | UF destinatario |

> **NOTA**: O campo `nfe_infnfe_dest_xnome` NAO existe. Use `partner_dest_id` para obter dados do destinatario.

---

## Campos Fiscais - Totais do Documento {#totais-fiscais}

### Totais Gerais

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icmstot_vnf` | float | **Valor Total da NF** |
| `nfe_infnfe_total_icmstot_vprod` | float | Valor Total dos Produtos |
| `nfe_infnfe_total_icms_vdesc` | float | Valor Total do Desconto |
| `nfe_infnfe_total_icms_vfrete` | float | Valor do Frete |
| `nfe_infnfe_total_icms_vseg` | float | Valor do Seguro |
| `nfe_infnfe_total_icms_voutro` | float | Outras Despesas Acessorias |

### Totais de ICMS

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vbc` | float | Base de Calculo do ICMS |
| `nfe_infnfe_total_icms_vicms` | float | **Valor do ICMS** |
| `nfe_infnfe_total_icms_vicmsdeson` | char | Valor ICMS Desonerado |

### Totais de ICMS-ST (Substituicao Tributaria)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vbcst` | float | Base de Calculo do ICMS-ST |
| `nfe_infnfe_total_icms_vst` | float | **Valor do ICMS-ST** |

### Totais de PIS

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vpis` | float | **Valor do PIS** |

### Totais de COFINS

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vcofins` | float | **Valor do COFINS** |

### Totais de IPI

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vipi` | float | **Valor do IPI** |

---

## Campos Especificos de CTe {#cte}

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `is_cte` | boolean | Indica se eh CTe |
| `cte_infcte_ide_cmunini` | char | Codigo Municipio de Origem |
| `cte_infcte_ide_cmunfim` | char | Codigo Municipio de Destino |
| `cte_infcte_ide_toma3_toma` | char | Tomador do Servico |

**Valores do Tomador (toma):**
| Codigo | Descricao |
|--------|-----------|
| 0 | Remetente |
| 1 | Expedidor |
| 2 | Recebedor |
| 3 | Destinatario |

---

## Campos de Status e Fluxo

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_status` | selection | Status do DFE |
| `state` | selection | Estado do registro |
| `active` | boolean | Ativo/inativo |

**Valores de l10n_br_status:**
| Codigo | Descricao | Uso |
|--------|-----------|-----|
| 01 | Novo | Documento recem importado |
| 02 | Manifestado | Manifestacao realizada |
| 03 | Ciencia | Ciencia da operacao |
| 04 | PO (Purchase Order) | **Pronto para lancamento** |
| 05 | Faturado | Invoice gerada |
| 06 | Cancelado | Documento cancelado |
| 07 | Denegado | Uso denegado |

> **IMPORTANTE**: Para lancamento no Odoo via integracao, o status deve ser '04' (PO).

---

## Campos de Relacionamento e Integracao {#relacionamentos}

### Relacionamentos Principais

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Parceiro emitente (fornecedor) |
| `partner_dest_id` | many2one | Parceiro destinatario |
| `purchase_id` | many2one | Pedido de Compra vinculado |
| `purchase_fiscal_id` | many2one | Pedido de Compra (Escrituracao) |
| `invoice_ids` | one2many | Faturas/Invoices vinculadas |
| `refs_ids` | one2many | Referencias (NF referenciadas) |

### Referencias e Rastreabilidade

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `payment_reference` | char | Referencia de Pagamento |
| `x_studio_pedido_de_venda_referncia` | char | Pedido de Venda (Referencia) |

### Arquivos do Documento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pdf_dfe` | binary | DANFE em PDF (base64) |
| `l10n_br_pdf_dfe_fname` | char | Nome do arquivo PDF |
| `l10n_br_xml_dfe` | binary | XML do documento (base64) |
| `l10n_br_xml_dfe_fname` | char | Nome do arquivo XML |
| `l10n_br_body_xml_dfe` | text | Conteudo XML (texto) |
| `l10n_br_xml_body_dfe` | text | Body XML (texto) |

---

## Linhas do DFE (Itens) {#linhas}

**Modelo Odoo:** `l10n_br_ciel_it_account.dfe.line`

### Campos de Produto

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID da linha |
| `dfe_id` | many2one | ID do DFE pai |
| `product_id` | many2one | Produto vinculado (product.product) |
| `det_prod_cprod` | char | Codigo do produto (fornecedor) |
| `det_prod_xprod` | char | Descricao do produto |
| `det_prod_ncm` | char | NCM (Nomenclatura Comum Mercosul) |
| `det_prod_cfop` | char | CFOP (Codigo Fiscal Operacoes) |
| `det_infadprod` | char | Dados Adicionais do Produto |

### Campos de Quantidade e Valor

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_prod_qcom` | float | Quantidade comercial |
| `det_prod_ucom` | char | Unidade comercial |
| `det_prod_vuncom` | float | Valor unitario comercial |
| `det_prod_vprod` | float | Valor total do item |
| `det_prod_vdesc` | float | Valor do desconto |
| `det_prod_vfrete` | float | Valor do frete (rateio) |
| `det_prod_vseg` | float | Valor do seguro (rateio) |
| `det_prod_voutro` | float | Outras despesas (rateio) |
| `product_uom_id` | many2one | Unidade de medida estoque |

### Campos de Pedido do Cliente

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_prod_xped` | char | Numero Pedido do Cliente |
| `det_prod_nitemped` | char | Item do Pedido do Cliente |

### Campos de Centro de Custo

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `account_analytic_id` | many2one | Conta Analitica |
| `analytic_distribution` | json | Distribuicao Analitica |

---

## Tributos por Linha (Detalhados) {#tributos-linha}

### ICMS (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_cst` | char | **CST ICMS** (Codigo Situacao Tributaria) |
| `det_imposto_icms_orig` | char | Origem da Mercadoria (0-8) |
| `det_imposto_icms_vbc` | float | Base de Calculo ICMS |
| `det_imposto_icms_picms` | float | **Aliquota ICMS (%)** |
| `det_imposto_icms_vicms` | float | **Valor ICMS** |
| `det_imposto_icms_predbc` | float | % Reducao Base ICMS |

### ICMS Simples Nacional (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_pcredsn` | float | % Credito ICMS Simples Nacional |
| `det_imposto_icms_vcredicmssn` | float | Valor Credito ICMS SN |

### ICMS-ST Substituicao Tributaria (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_vbcst` | float | Base de Calculo ICMS-ST |
| `det_imposto_icms_vicmsst` | float | **Valor ICMS-ST** |
| `det_imposto_icms_vbcstret` | float | Base ICMS-ST Retido |
| `det_imposto_icms_vicmsstret` | float | Valor ICMS-ST Retido |
| `det_imposto_icms_vicmssubstituto` | float | Valor ICMS Substituto |

### PIS (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_pis_cst` | char | **CST PIS** |
| `det_imposto_pis_vbc` | float | Base de Calculo PIS |
| `det_imposto_pis_ppis` | float | **Aliquota PIS (%)** |
| `det_imposto_pis_vpis` | float | **Valor PIS** |

### COFINS (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_cofins_cst` | char | **CST COFINS** |
| `det_imposto_cofins_vbc` | float | Base de Calculo COFINS |
| `det_imposto_cofins_pcofins` | float | **Aliquota COFINS (%)** |
| `det_imposto_cofins_vcofins` | float | **Valor COFINS** |

### IPI (Linha)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_ipi_cst` | char | **CST IPI** |
| `det_imposto_ipi_vbc` | float | Base de Calculo IPI |
| `det_imposto_ipi_pipi` | float | **Aliquota IPI (%)** |
| `det_imposto_ipi_vipi` | float | **Valor IPI** |

---

## Pagamentos do DFE (Duplicatas) {#pagamentos}

**Modelo Odoo:** `l10n_br_ciel_it_account.dfe.pagamento`

### Campos Principais

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `dfe_id` | many2one | DFE vinculado |
| `company_id` | many2one | Empresa |

### Campos da Duplicata

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cobr_dup_ndup` | char | Numero da Parcela |
| `cobr_dup_dvenc` | date | **Data de Vencimento** |
| `cobr_dup_vdup` | float | **Valor da Parcela** |

---

## Relacionamento com Contas a Receber/Pagar

### Fluxo de Integracao

```
DFE (Documento Entrada)
    |
    v
purchase.order (Pedido de Compra)
    |
    v
account.move (Invoice/Fatura)
    |
    v
account.move.line (Parcelas - Contas a Pagar)
```

### Campos de Vinculo em account.move.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `dfe_line_id` | many2one | Vinculo com linha do DFE |

---

## Tabelas de CST (Codigo Situacao Tributaria)

### CST ICMS

| CST | Descricao |
|-----|-----------|
| 00 | Tributada integralmente |
| 10 | Tributada com cobranca ICMS-ST |
| 20 | Com reducao de base de calculo |
| 30 | Isenta/nao tributada com cobranca ICMS-ST |
| 40 | Isenta |
| 41 | Nao tributada |
| 50 | Suspensao |
| 51 | Diferimento |
| 60 | Cobrado anteriormente por ST |
| 70 | Com reducao e cobranca ICMS-ST |
| 90 | Outras |

### CST PIS/COFINS

| CST | Descricao |
|-----|-----------|
| 01 | Operacao tributavel aliquota basica |
| 02 | Operacao tributavel aliquota diferenciada |
| 04 | Operacao tributavel monofasica revenda aliquota zero |
| 05 | Operacao tributavel ST |
| 06 | Operacao tributavel aliquota zero |
| 07 | Operacao isenta |
| 08 | Operacao sem incidencia |
| 09 | Operacao com suspensao |
| 49 | Outras operacoes de saida |
| 50-56 | Operacoes com direito a credito |
| 70-75 | Operacoes de aquisicao sem direito a credito |
| 98-99 | Outras operacoes |

### CST IPI

| CST | Descricao |
|-----|-----------|
| 00 | Entrada com recuperacao de credito |
| 01 | Entrada tributada aliquota zero |
| 02 | Entrada isenta |
| 03 | Entrada nao tributada |
| 04 | Entrada imune |
| 05 | Entrada com suspensao |
| 49 | Outras entradas |
| 50 | Saida tributada |
| 51 | Saida tributada aliquota zero |
| 52 | Saida isenta |
| 53 | Saida nao tributada |
| 54 | Saida imune |
| 55 | Saida com suspensao |
| 99 | Outras saidas |

---

## Consultas Frequentes

### Buscar devolucoes
```python
filtros = [
    '|', ('active', '=', True), ('active', '=', False),
    ('nfe_infnfe_ide_finnfe', '=', '4')  # finnfe=4 = devolucao
]
```

### Buscar CTe
```python
filtros = [
    '|', ('active', '=', True), ('active', '=', False),
    ('is_cte', '=', True)
]
```

### Buscar por CNPJ emitente
```python
# Com formatacao parcial
filtros.append(('nfe_infnfe_emit_cnpj', 'ilike', '18.467.441'))
```

### Buscar por periodo
```python
filtros.append(('nfe_infnfe_ide_dhemi', '>=', '2025-01-01'))
filtros.append(('nfe_infnfe_ide_dhemi', '<=', '2025-12-31 23:59:59'))
```

### Buscar por valor
```python
# Notas acima de 10.000
filtros.append(('nfe_infnfe_total_icmstot_vnf', '>=', 10000))
```

### Buscar por status pronto para lancamento
```python
filtros.append(('l10n_br_status', '=', '04'))  # PO
```

---

## Exemplos de Script

### Buscar devolucao por cliente
```bash
python consultando_conhecidas.py \
  --tipo dfe \
  --subtipo devolucao \
  --cliente "atacadao"
```

### Buscar CTe por transportadora
```bash
python consultando_conhecidas.py \
  --tipo dfe \
  --subtipo cte \
  --cliente "18467441"  # CNPJ formatado ou nao
```

### Buscar devolucao por quantidade e produto
```bash
python consultando_conhecidas.py \
  --tipo dfe \
  --subtipo devolucao \
  --produto "pimenta" \
  --quantidade 784 \
  --detalhes
```

### Descobrir novos campos
```bash
# Buscar campos de um termo especifico
python consultando_desconhecidas.py \
  --modelo l10n_br_ciel_it_account.dfe \
  --buscar-campo referencia

# Listar todos os campos
python consultando_desconhecidas.py \
  --modelo l10n_br_ciel_it_account.dfe.line \
  --listar-campos
```

---

## Diagrama de Relacionamentos

```
                    +------------------+
                    |   res.partner    |
                    | (Emitente/Dest)  |
                    +--------+---------+
                             |
              +--------------+----------------+
              |                               |
              v                               v
+-------------+-----------+     +-------------+-----------+
| l10n_br_ciel_it_account |     |     purchase.order      |
|          .dfe           |---->|   (Pedido de Compra)    |
+-------------+-----------+     +-------------+-----------+
              |                               |
              |                               v
              |                 +-------------+-----------+
              |                 |      account.move       |
              |                 |    (Invoice/Fatura)     |
              |                 +-------------+-----------+
              |                               |
              v                               v
+-------------+-----------+     +-------------+-----------+
| l10n_br_ciel_it_account |     |    account.move.line    |
|       .dfe.line         |---->|  (Linhas/Parcelas)      |
+-------------+-----------+     +-------------------------+
              |
              v
+-------------+-----------+
| l10n_br_ciel_it_account |
|      .dfe.pagamento     |
|      (Duplicatas)       |
+-------------------------+
```

---

## Notas Importantes

1. **CNPJ do Emitente**: Armazenado COM pontuacao (XX.XXX.XXX/XXXX-XX)
2. **CNPJ do Destinatario**: Armazenado SEM pontuacao
3. **Status '04'**: Documento pronto para lancamento (gerar PO/Invoice)
4. **CST vs CSOSN**: Empresas do Simples Nacional usam CSOSN ao inves de CST
5. **Campos de totais**: Prefixo `nfe_infnfe_total_icms_` para valores consolidados
6. **Campos de linha**: Prefixo `det_imposto_` para tributos por item
