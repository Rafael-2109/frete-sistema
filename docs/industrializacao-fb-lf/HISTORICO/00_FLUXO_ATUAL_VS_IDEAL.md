# Fluxo de Industrialização FB ↔ LF — Estado Atual × Estado Ideal

**Elaboração**: Time interno (operações + dados)
**Objetivo**: Submeter para validação Fiscal/Contábil
**Empresas envolvidas**:
- NACOM GOYA – FB (CNPJ 61.724.241/0001-78) — encomendante
- LA FAMIGLIA – LF (CNPJ 18.467.441/0001-63) — industrializadora

**Produto de referência utilizado na análise**:
- 4870112 MOLHO SHOYU PET 12X1,01L CAMPO BELO — produto acabado (industrializado pela LF)
- 210030322 ROTULO MOLHO SHOYU PET 1,01L (e demais 14 componentes/MPs)

---

## 1. Resumo executivo

O fluxo de retorno de industrialização LF → FB está, hoje, **somando o Produto Acabado E os componentes na mesma entrada de estoque na FB**. Os componentes, que já foram fisicamente consumidos pela LF na ordem de produção, **deveriam apenas ser baixados de uma conta transitória/de terceiros** — não somados de novo ao Ativo Estoque.

Como o método de valoração no Odoo é **AVCO (custo médio) em tempo real**, cada `stock.move` gera um `account.move` automaticamente. Logo, o erro de movimentação física **já está postado no razão contábil** das empresas, há vários exercícios.

Pedido ao Fiscal/Contábil: **validar o desenho correto** (item 3 abaixo) e **definir o tratamento contábil** do passivo acumulado (item 4 abaixo).

---

## 2. Como é HOJE

### 2.1. Fluxo físico (Odoo — stock.picking)

| Etapa | Empresa | Picking type usado | Origem → Destino | Status |
|---|---|---|---|---|
| Remessa de componentes FB → LF | FB | **53 FB/SAI/IND** (Expedição Industrialização) | FB/Estoque → Estoque Virtual / Em Trânsito (Industrialização) | ✅ Correto |
| Recebimento da remessa em LF | LF | **64 LF/RECEB/IND** (Recebimentos Industrialização) | Em Trânsito Industrialização → LF/Estoque | ❌ Abandonado (último uso: ago/2024 — só 5 pickings na história) |
| Compra direta de componentes pela LF | LF | 19 LF/IN (Recebimento) | Fornecedor → LF/Estoque | ✅ Usado em paralelo |
| Ordem de Produção LF (consumo) | LF | 34 LF/PC + 36 LF/MO | LF/Estoque → Virtual/Produção → LF/Pós-Produção | ✅ Funcionando |
| Retorno LF → FB (NF de retorno + PA) | FB | **1 RECEB/FB** (Recebimento genérico de fornecedor) | Parceiros / Estoque LF → FB/Estoque | ❌ Tipo errado |

**Comprovação no Odoo (banco de produção, consulta em 28/05/2026)**:
- 105 dos 200 pickings de retorno LF → FB (state=done) usam `picking_type_id=1` (genérico).
- 0 desses pickings usam `picking_type_id=52 RECEB/FB/IND` (que é o que existe especificamente para Recebimento de Industrialização).
- O picking_type 52 tem `default_location_src_id = Estoque Virtual / Em Trânsito (Industrialização)` — projetado para BAIXAR o que foi remetido. Está ocioso.

### 2.2. O que entra fisicamente na FB pela NF de retorno

Exemplo: picking FB/IN/01541 (01/Out/2024, partner LA FAMIGLIA – LF, origin C2401915), 17 linhas, todas entrando em FB/Estoque:

| Código | Produto | Qty entrada | Tipo |
|---|---|---:|---|
| 4870112 | MOLHO SHOYU PET 12X1,01L | 336 cx | **PA** |
| X105000022 | MOLHO SHOYU TRADICIONAL | 933,15 | semi-acabado |
| 104000002 | ÁCIDO CÍTRICO | 4,31 | MP |
| 104000004 | BENZOATO DE SÓDIO | 4,31 | MP |
| 104000007 | CORANTE CARAMELO | 64,60 | MP |
| 104000015 | SAL SEM IODO | 244,06 | MP |
| 104000018 | SORBATO POTÁSSIO | 4,31 | MP |
| 105000023 | ANTIESPUMANTE | 0,86 | MP |
| 105000024 | AÇÚCAR CRISTAL | 43,07 | MP |
| 105000039 | AROMA SHOYU | 19,64 | MP |
| 207210014 | ETIQUETA BRANCA | 336 | EMB |
| 208000008 | FILME STRETCH | 3,90 | EMB |
| 208000010 | FITA ADESIVA | 288,96 | EMB |
| 210030010 | FRASCO INCOLOR 1,01L | 4.032 | EMB |
| 210030110 | TAMPA PLÁSTICA | 4.032 | EMB |
| 210030203 | CAIXA PAPELÃO | 336 | EMB |
| 210030322 | RÓTULO SHOYU | 4.032 | EMB |

Matemática: 336 cx PA × 12 = 4.032 frascos = 4.032 tampas = 4.032 rótulos = 1 lote de produção. **Os componentes consumidos pela MO da LF retornam fisicamente no picking de entrada da FB e somam ao Ativo Estoque.**

### 2.3. Lançamento contábil automático gerado hoje

Pela categoria de produto (parâmetros do `product.category`):
- Método: **AVCO** (`cost_method=average`)
- Valoração: **Tempo real** (`valuation=real_time`)
- Contas (exemplo para a categoria ROTULO):
  - Estoque: **1150100002 MATERIAL DE EMBALAGEM** (Ativo Circulante)
  - Entrada (transitória fiscal): **1150100011 RECEBIMENTO FÍSICO FISCAL**
  - Saída (transitória fiscal): 1150100012 FATURAMENTO FÍSICO FISCAL
  - Despesa/CMV: 3202010001 CUSTOS DAS MERCADORIAS VENDIDAS
- Diário: 8 ESTOQUE

**Cada linha de componente que entra na FB hoje gera**:

```
D 1150100002 MATERIAL DE EMBALAGEM     (Ativo Estoque)             +X
C 1150100011 RECEBIMENTO FÍSICO FISCAL (Conta transitória)         −X
```

Como **a NF de retorno LF→FB não é processada como Compra**, a conta transitória 1150100011 **não recebe a contrapartida fechadora** (que viria de "C Fornecedor / D 1150100011" no fechamento financeiro de uma compra normal). Ela acumula saldo credor.

### 2.4. Sintomas contábeis observáveis (consulta em 28/05/2026, FB, postados)

| Conta | Saldo |
|---|---:|
| 1150100002 MATERIAL DE EMBALAGEM (Estoque) | R$ 21.938.384,94 |
| 1150100011 RECEBIMENTO FÍSICO FISCAL (transitória) | **R$ −1.488.150.962,96** |
| 1150200001 MATERIAL EM TERCEIROS | **R$ 0,00** |
| 1150200002 (−) MATERIAL DE TERCEIROS | R$ 0,00 |
| 1150200003 AJUSTES PREÇO MATERIAL TERCEIROS | R$ 0,00 |

> **Atenção**: O saldo negativo de R$ 1,49 bi na transitória 1150100011 é histórico acumulado e provavelmente reflete outros fluxos além da industrialização. A conta MATERIAL EM TERCEIROS estar zerada confirma que **as remessas FB→LF (CFOP 5901) nunca foram contabilizadas como remessa para industrialização** — o material continua, contabilmente, como estoque normal da FB.

### 2.5. Quantificação do efeito específico da industrialização (produto MOLHO SHOYU PET, todos os componentes, todos os retornos LF→FB)

| Métrica | Valor |
|---|---:|
| Pickings de retorno LF→FB analisados (com PA + componentes juntos) | 66 |
| Stock.moves de **componentes** indevidamente somados ao estoque FB | 1.057 |
| SVLs (camadas de valoração) gerados | 1.057 |
| **Valor somado ao Ativo Estoque da FB indevidamente** | **R$ 785.569,62** |

> Este é o **valor do passivo apenas para um único produto industrializado**. Existem outros (vinagre, azeitona, etc.) com o mesmo fluxo. **Total geral pode ser múltiplo deste**.

### 2.6. Sintomas físicos (saldos de estoque pendurados)

| Location | Empresa | Saldo (rótulo 210030322) | Observação |
|---|---|---:|---|
| Estoque Virtual / Em Trânsito (Industrialização) | (virtual/cmp 0) | 350.800 un | Remessas FB→LF que nunca foram baixadas pelo lado LF (picking_type 64 abandonado) |
| FB/Indisponível | FB | 546.001 un | Saldo movido manualmente para Indisponível durante projeto de inventário (escondido para não distorcer relatórios operacionais, mas continua no Ativo) |
| FB/Estoque | FB | 21.180 un | Saldo "real" operacional |
| LF/Estoque | LF | 20.170 un | Saldo "real" operacional |

---

## 3. Como DEVERIA SER (proposta para validação)

### 3.1. Premissa fiscal (CFOPs aplicáveis a industrialização por encomenda)

| CFOP | Operação | Quem emite |
|---|---|---|
| 5901 / 6901 | Remessa para industrialização por encomenda | FB (encomendante) |
| 1901 / 2901 | Retorno simbólico (visão do encomendante recebendo de volta) | FB recebe |
| 5902 / 6902 | Retorno de mercadoria utilizada na industrialização | LF emite |
| 5903 / 6903 | Retorno de mercadoria não utilizada (sobra) | LF emite |
| 5124 / 6124 | Industrialização efetuada para outra empresa | LF emite |
| 1124 / 2124 | Recebimento da industrialização efetuada por encomenda | FB recebe |

### 3.2. Fluxo físico ideal (stock.picking)

| Etapa | Empresa | Picking type | Origem → Destino | NF/CFOP relacionado |
|---|---|---|---|---|
| 1. Remessa de componentes FB → LF | FB | 53 FB/SAI/IND | FB/Estoque → Em Trânsito Industrialização | NF saída FB CFOP 5901 |
| 2. Recebimento da remessa em LF | LF | **64 LF/RECEB/IND (reativar)** | Em Trânsito Industrialização → LF/Estoque (ou "Materiais de Terceiros") | DFe entrada LF CFOP 1901 |
| 3. Ordem de Produção LF | LF | 34 LF/PC + 36 LF/MO | LF/Estoque → Virtual/Produção → LF/Pós-Produção | — (interno) |
| 4. Retorno LF → FB | LF | **NOVO LF/SAI/RETIND/IND** (CRIAR) | LF/Estoque → Em Trânsito Industrialização | NF saída LF CFOP 5124 (PA) + 5902 (componentes consumidos) + 5903 (sobras) |
| 5. Recebimento do retorno em FB | FB | **52 RECEB/FB/IND** (USAR) | Em Trânsito Industrialização → FB/Estoque | DFe entrada FB CFOP 1124 + 1902 + 1903 |

**O par "Em Trânsito Industrialização" é a chave**: tudo que sai pela etapa 1 deve ser baixado pela etapa 2; tudo que sai pela etapa 4 deve ser baixado pela etapa 5. **No fim do ciclo, o saldo dessa location virtual é zero**.

### 3.3. Faltam estruturalmente no Odoo

1. **Picking type LF outgoing** com `default_location_dest_id = Estoque Virtual / Em Trânsito (Industrialização)` (não existe hoje — os tipos LF/SAI/IND, LF/SAI/RETIND e LF/SAI/RNA todos vão para Parceiros/Clientes).
2. **stock.rule** ligando os pares (53 → 64) e (novo LF outgoing → 52). Hoje há zero regras nesses picking types — a operação é 100% manual.
3. **Mapeamento CFOP → picking_type no CIEL IT**: a DFe de retorno LF (CFOPs 1124, 1902, 1903) precisa cair automaticamente em `picking_type=52`, não em `picking_type=1` (genérico).

### 3.4. Lançamento contábil ideal por etapa

(Sujeito a validação do contador — esta é a proposta operacional)

**Etapa 1 — Remessa FB → LF (CFOP 5901)**:
```
D 1150200001 MATERIAL EM TERCEIROS                   +X (valor médio dos componentes remetidos)
C 1150100002 MATERIAL DE EMBALAGEM (ou similar)      −X (sai do estoque normal)
```

**Etapa 2 — Recebimento em LF (CFOP 1901)**: apenas controle físico (entra em "LF / Materiais de Terceiros"), sem lançamento patrimonial na LF (mercadoria não é dela). Se a empresa quiser controle contábil em LF: D Compensação Materiais 3os / C Compensação Contrapartida.

**Etapa 3 — MO em LF**: consume componentes (controle interno LF), produz PA. Contabilmente em LF: reconhece **Receita de Serviço de Industrialização** (CFOP 5124) e custo da MO (mão de obra + energia + insumos próprios da LF).

**Etapa 4 — Retorno LF → FB**:
- **Componentes consumidos (CFOP 5902)**: simbólico — não toca estoque físico LF (já consumiu na MO). Em FB:
  ```
  D Custo de Produção / Industrialização (CMV ou conta de incorporação no PA)
  C 1150200001 MATERIAL EM TERCEIROS                  −X (zera a conta de remessa)
  ```
- **Componentes não utilizados / sobra (CFOP 5903)**: volta para estoque normal:
  ```
  D 1150100002 MATERIAL DE EMBALAGEM                  +X (sobra retorna ao estoque)
  C 1150200001 MATERIAL EM TERCEIROS                  −X (zera parcial)
  ```
- **Produto Acabado (CFOP 1124, recebimento da industrialização)**:
  ```
  D 1150100001 PRODUTO ACABADO (ou conta do PA)       +Y
  C Fornecedor LF (a pagar pela industrialização)     −Y (valor agregado pela LF, conforme NF de serviço)
  ```

**No final do ciclo**:
- 1150200001 MATERIAL EM TERCEIROS deve zerar (entra na remessa, sai no retorno simbólico + sobra).
- 1150100002 MATERIAL DE EMBALAGEM **não infla** porque o componente já saiu na remessa e só a sobra (CFOP 5903) reentra.
- O custo do componente é **incorporado ao PA** (Etapa 4 — débito do CMV/Custo de Produção contra MATERIAL EM TERCEIROS).
- Em Trânsito Industrialização (location virtual) **zera** entre cada par remessa↔retorno.

### 3.5. Alternativa: módulo `mrp_subcontracting` nativo do Odoo

O Odoo 16+ tem subcontratação nativa que automatiza tudo isso. Demanda:
- Produto acabado flagado como `is_subcontracted=True`.
- BoM tipo `subcontract` com subcontractor = LA FAMIGLIA – LF.
- Rota subcontracting aplicada.
- Resupply automático dos componentes ao subcontratado.

Pro: zera o problema na raiz, sem operação manual.
Contra: muda o desenho de PO/recebimento; exige BoM completa cadastrada; mistura controle inter-company; exige homologação fiscal CIEL IT do fluxo.

---

## 4. Impacto contábil do passivo acumulado

### 4.1. Tamanho (medido até aqui)

| Escopo | Valor |
|---|---:|
| Apenas MOLHO SHOYU PET 12x1,01L (1 PA, 16 componentes/MPs, 66 retornos) | R$ 785.569,62 |
| Estimativa total (todos os produtos industrializados na LF) | A levantar (estimativa: alguns milhões) |

### 4.2. Modos possíveis de regularização

| Modo | Lançamento | Impacto em DRE | Quando aplicar |
|---|---|---|---|
| **A. Reclassificação** | D MATERIAL EM TERCEIROS / C MATERIAL DE EMBALAGEM | Nenhum (entre Ativos) | Se ficar provado que o estoque "inflado" corresponde a material fisicamente em poder da LF (remessas não baixadas) |
| **B. Ajuste de inventário a menor (despesa)** | D Perdas/Quebras de Inventário / C MATERIAL DE EMBALAGEM | Reduz resultado do exercício corrente | Para componentes que LF já consumiu na MO mas estão duplicados no ativo da FB |
| **C. Ajuste de exercícios anteriores** | D Ajustes de Exercícios Anteriores (PL) / C MATERIAL DE EMBALAGEM | Não afeta DRE corrente; afeta PL | Para erros de exercícios já encerrados, com aprovação fiscal/auditoria |

A escolha entre A, B e C **deve ser feita pelo Contador/Auditor** após análise da materialidade e do exercício de origem.

---

## 5. Perguntas para o Fiscal/Contábil validar

1. **Confirma** que o desenho proposto (item 3) é o tratamento fiscal correto para industrialização por encomenda dentro do grupo (FB encomenda da LF)?
2. **Confirma** que a conta 1150200001 MATERIAL EM TERCEIROS é a conta correta para registrar a remessa FB → LF (CFOP 5901)? Há outra conta padrão da empresa que deveria ser usada?
3. **Confirma** os CFOPs aplicáveis (5901/1901 na remessa; 5124/1124 + 5902/1902 + 5903/1903 no retorno)?
4. **Qual** o tratamento contábil correto para regularizar o passivo já postado (modo A, B ou C do item 4.2)? Há materialidade suficiente para reclassificar para exercícios anteriores?
5. **Há restrição fiscal** para usar o módulo `mrp_subcontracting` do Odoo (item 3.5) considerando que FB e LF têm CNPJs distintos (operação intermunicipal/interestadual)?
6. **Qual** o tratamento para o saldo de R$ −1,49 bi na conta 1150100011 RECEBIMENTO FÍSICO FISCAL — deve ser conciliado e zerado, ou é esperado por outra razão?
7. **Pode** o time de operações desligar imediatamente a entrada de componentes via `picking_type=1` para retornos LF, mesmo antes da regularização do passivo, ou há requisito fiscal que obriga o procedimento atual?

---

## 6. Anexos (disponíveis sob solicitação)

- A1. Lista completa dos 200 pickings FB done com partner LF (CSV: data, número, CFOP, valor, picking_type).
- A2. Detalhamento dos 66 pickings de retorno com PA+componente (1.123 linhas de stock.move).
- A3. Saldo histórico mensal das contas 1150100002, 1150100011, 1150200001, 1150200002, 1150200003 (FB+SC+CD+LF).
- A4. Lista de produtos industrializados pela LF (catálogo de PAs com `linha_producao=LF`).
- A5. Configuração atual dos picking types industrialização (export do Odoo).
