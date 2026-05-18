# G008 — excecao_autorizado: NF autorizada mas XML autorizado vazio

**Descoberta**: 2026-05-18 sub-piloto bulk (NF 13150 RETNA/2026/00030)
**Severidade**: HIGH (bloqueia entrada FB automatica)
**Status**: SEM FIX AUTOMATICO — exige acao manual via UI Odoo

---

## Sintoma

NF SEFAZ retornou `situacao_nf = 'excecao_autorizado'` (autorizada com
ressalva). Chave SEFAZ presente, valida — mas:

```
inv 608630 RETNA/2026/00030: state=posted
  l10n_br_chave_nf = '35260518467441000163550010000131501006086306'  ✓ (44 digitos)
  l10n_br_xml_aut_nfe = 0 bytes  ❌ (XML AUTORIZADO VAZIO)
  l10n_br_pdf_aut_nfe = 0 bytes
```

Apos algumas tentativas:
```
File ".../recebimento_lf_odoo_service.py:881"
ValueError: LF invoice 608630: XML autorizado vazio
```

## Causa raiz

SEFAZ retorna `excecao_autorizado` quando o `numero_nf` foi "consumido"
em tentativas anteriores rejeitadas (Falha no Schema XML, etc — ver G007).
A NF e' aceita mas com ressalva fiscal.

CIEL IT detecta `excecao_autorizado` e **NAO baixa o XML completo**
(`nfeProc` = `<NFe>` + `<protNFe>`). Sem o `nfeProc`, nao da para criar
DFe na FB (que e' o que abre a entrada FB).

Tentar fazer upload manual do XML so `<NFe>` (que o usuario tem em
Downloads do CIEL IT como -nfe.xml) falha com:
```
<Fault 2: 'XML Nota Fiscal Eletronica nao esta completa!'>
```

## Solucoes possiveis

### A. Re-consultar SEFAZ via UI Odoo (NAO AUTOMATIZADO)

1. Acessar invoice na UI Odoo
2. Botao "Consultar Documento" ou "Re-consultar SEFAZ" (varia conforme
   versao CIEL IT)
3. CIEL IT vai consultar a SEFAZ novamente e baixar o `nfeProc` completo
4. Re-executar entrada FB no nosso pipeline

### B. Cancelar SEFAZ + recriar NF (LIMPA - recomendado se < 24h)

1. UI Odoo: Cancelar NFe (justificativa min 15 chars, dentro 24h)
2. Reset to draft
3. Criar novo picking + nova NF (proxima execucao do bulk)

### C. Aceitar com ressalva sem entrada FB (NAO recomendado)

NF fiscalmente valida mas estoque LF saiu sem contrapartida na FB.
Inconsistencia fisica. Evitar.

## Como evitar `excecao_autorizado` no futuro

A causa raiz e' que SEFAZ recebeu TENTATIVAS REJEITADAS antes da aceita.
Cada tentativa rejeitada "consome" o numero NF. Para evitar:

1. **Validar custo_medio > 0 ANTES de criar pickings** (G007)
2. **Validar todos os campos obrigatorios** antes de `action_post`:
   - `payment_provider_id` (G004 L5)
   - `fiscal_position_id` (corresponde ao tipo_pedido)
   - `partner_id`, `company_id`
   - `incoterm`, `carrier_id` (G004 L1)
3. **Pre-flight canary** comparando com NF historica de referencia
   (canary F7.6) ANTES de transmitir

## Comportamento esperado em pos-execucao

Se invoice ficou `excecao_autorizado`:
- F5d: ainda marca `F5d_INVOICE_GERADA` (invoice criada)
- F5d.5: payment_provider setado (idempotente)
- F5e: Playwright detecta `chave_nfe` 44 dig + `situacao=excecao_autorizado`
  → marca `F5e_SEFAZ_OK` (tratado como sucesso parcial)
- E (entrada FB): **FALHA** com "XML autorizado vazio"

Para tratar: marcar manualmente o RecLf como `cancelado` e fazer entrada
FB via UI Odoo. Estado DB local fica:
```sql
UPDATE recebimento_lf SET status='cancelado',
  erro_mensagem='excecao_autorizado: XML SEFAZ vazio. Fazer entrada FB manual via UI Odoo.'
WHERE odoo_lf_invoice_id = <inv_id>;
```

## Caso real

NF 13150 (608630, RETNA/2026/00030) — sub-piloto bulk 2026-05-18:
- Tentativas 1-2 rejeitadas (Falha schema XML, custo zero — G007)
- Tentativa 3+ apos corrigir custo_medio → SEFAZ retornou `excecao_autorizado`
- XML autorizado vazio
- RecLf 5 falhou
- Decisao: cancelar invoice local + devolver picking 317294 via 317303
- Pendente: cancelar SEFAZ via UI Odoo (24h)
- Estado: NF "fantasma" autorizada com ressalva, picking devolvido, estoque LF intacto

## Ref

- G004 L4 (wizard confirmacao SEFAZ apos Transmitir)
- G004 L5 (payment_provider_id obrigatorio)
- G007 (custo_medio=0)
- D006 secao L16
