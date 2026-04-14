# Formatos Bancarios — CNAB e OFX

Referencia tecnica dos formatos que a skill `lendo-documentos` processa.

---

## CNAB400 (Centro Nacional de Automacao Bancaria)

Padrao brasileiro para troca de arquivos entre empresa e banco. Cada linha tem
**exatamente 400 caracteres** (posicional, sem separadores).

### Estrutura

```
┌─────────────────────────────────────────────┐
│  Tipo 0 — Header (1 linha)                   │ ← abertura do arquivo
├─────────────────────────────────────────────┤
│  Tipo 1 — Detalhe (N linhas)                 │ ← 1 por titulo
│  Tipo 2 — Detalhe opcional (mensagens)       │
│  Tipo 3 — Detalhe opcional (sacador/avalista)│
├─────────────────────────────────────────────┤
│  Tipo 9 — Trailer (1 linha)                  │ ← totais e fechamento
└─────────────────────────────────────────────┘
```

- **Encoding**: `latin-1` (ISO-8859-1) — nao usar UTF-8 para leitura
- **Valores monetarios**: em centavos, **sem separador decimal**
  - Ex: `"0000002472730"` → R$ 24.727,30
- **Datas**: formato `DDMMAA` ou `AAMMDD` (varia por campo/banco)

### .rem vs .ret

| Tipo | Gerador | Consumidor | Funcao |
|------|---------|------------|--------|
| `.rem` (remessa) | Empresa | Banco | Envia instrucoes (cobrar, baixar, cancelar titulo) |
| `.ret` (retorno) | Banco | Empresa | Reporta status (liquidacao, rejeicao, alteracao) |

### Layouts BMP 274 (retorno) — extraido pelo parser

O `Cnab400ParserService` foi desenvolvido para o layout **BMP Money Plus 274**.
Posicoes principais do registro detalhe (tipo 1):

| Campo | Posicao | Descricao |
|-------|---------|-----------|
| Tipo inscricao | 2-3 | 01=CPF, 02=CNPJ |
| CNPJ/CPF pagador | 4-17 | Sacado |
| Identificacao empresa | 38-62 | Texto livre |
| Nosso numero | 71-82 | Identificador do banco |
| Codigo ocorrencia | 109-110 | Ver tabela abaixo |
| Data ocorrencia | 111-116 | DDMMAA (liquidacao) |
| Seu numero | 117-126 | NF/Parcela (`143820/001`) |
| Data vencimento | 147-152 | DDMMAA |
| Valor titulo | 153-165 | Centavos (13 digitos) |
| Despesas cobranca | 176-188 | Centavos |
| Abatimento | 228-240 | Centavos |
| Desconto | 241-253 | Centavos |
| Valor pago | 254-266 | Centavos |
| Juros mora | 267-279 | Centavos |
| Data credito | 296-301 | DDMMAA |

### Codigos de Ocorrencia (tipo 1)

| Codigo | Descricao | Observacao |
|--------|-----------|------------|
| 02 | Entrada Confirmada | Titulo entrou na cobranca |
| 03 | Entrada Rejeitada | Titulo nao aceito |
| 06 | **Liquidacao Normal** | Pagamento na rede |
| 07 | Liquidacao por Conta | Debito em conta |
| 08 | Liquidacao por Saldo | Abatimento saldo |
| 09 | Baixado Automaticamente | Baixa por tempo |
| 10 | Baixado conforme Instrucoes | Empresa solicitou |
| 14 | Alteracao de Vencimento | Data mudou |
| 15 | Liquidacao em Cartorio | Pago apos protesto |
| 23 | Encaminhado a Protesto | Foi para cartorio |
| 26 | Instrucao Rejeitada | Erro na remessa |
| 28 | Debito de Tarifas/Custas | Banco cobrou tarifa |

### Outros bancos

Layouts de outros bancos divergem nas posicoes dos campos. O parser atual nao
e universal — se o `nome_banco` do header nao for "BMP Money Plus", os campos
extraidos podem estar errados (embora a estrutura 0/1/9 se mantenha).

**Bancos conhecidos** (codigo FEBRABAN):

| Codigo | Nome |
|--------|------|
| 001 | Banco do Brasil |
| 033 | Santander |
| 104 | Caixa Economica Federal |
| 237 | Bradesco |
| **274** | **BMP Money Plus** (layout validado) |
| 341 | Itau |
| 422 | Safra |
| 748 | Sicredi |
| 756 | Sicoob |

---

## OFX (Open Financial Exchange)

Padrao internacional (Microsoft/Intuit/CheckFree) usado por extratos bancarios
e softwares financeiros (Quicken, Money, QuickBooks).

### Formato

- **SGML legacy** (brasileiro, comum) — tags sem fechamento: `<TRNAMT>-1597.02`
- **XML moderno** — com tags de fechamento: `<TRNAMT>-1597.02</TRNAMT>`
- **Encoding**: geralmente `latin-1` (bancos brasileiros) ou `utf-8`

### Estrutura (resumida)

```xml
<OFX>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKACCTFROM>
          <ACCTID>450782</ACCTID>
        </BANKACCTFROM>
        <BANKTRANLIST>
          <DTSTART>20260101
          <DTEND>20260131
          <STMTTRN>
            <TRNTYPE>DEBIT
            <DTPOSTED>20260128
            <TRNAMT>-1597.02
            <FITID>202601281597021
            <CHECKNUM>20834751
            <MEMO>DEB.TIT.COMPE EFETIVADO
            <NAME>PAG BOLETO
          </STMTTRN>
          ...
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
```

### Campos principais (dentro de `<STMTTRN>`)

| Tag | Tipo | Descricao |
|-----|------|-----------|
| `TRNTYPE` | string | `DEBIT`, `CREDIT`, `XFER`, `FEE`, etc. |
| `DTPOSTED` | data YYYYMMDD | Data da transacao |
| `TRNAMT` | decimal | Valor (negativo = debito, positivo = credito) |
| `FITID` | string | Identificador unico da transacao |
| `CHECKNUM` | string | Numero do cheque/boleto |
| `REFNUM` | string | Numero de referencia |
| `MEMO` | string | Descricao longa |
| `NAME` | string | Descricao curta |

### Tipos de transacao (TRNTYPE)

| Valor | Descricao |
|-------|-----------|
| `CREDIT` | Credito generico |
| `DEBIT` | Debito generico |
| `INT` | Juros |
| `DIV` | Dividendo |
| `FEE` | Tarifa |
| `SRVCHG` | Taxa de servico |
| `DEP` | Deposito |
| `ATM` | Saque em caixa eletronico |
| `POS` | Compra em maquininha |
| `XFER` | Transferencia |
| `CHECK` | Cheque |
| `PAYMENT` | Pagamento |
| `CASH` | Saque em dinheiro |
| `DIRECTDEP` | Deposito direto (salario) |
| `DIRECTDEBIT` | Debito direto (DDA) |
| `REPEATPMT` | Pagamento recorrente |
| `OTHER` | Outros |

---

## Fluxos tipicos de uso

### Conciliacao CNAB retorno → Odoo

1. Usuario anexa arquivo `.ret` no chat
2. Agente usa `lendo-documentos` com `--tipo cnab`
3. Para cada detalhe com `codigo_ocorrencia in ('06', '07', '08')`:
   - Extrai `seu_numero` (NF/Parcela)
   - Busca titulo no Odoo via `rastreando-odoo`
   - Cria payment via `executando-odoo-financeiro` com `valor_pago` e
     `data_credito` como `data_pagamento`
4. Relatorio ao usuario: X titulos liquidados, Y rejeitados

### Reconciliacao OFX (extrato) → Odoo

1. Usuario anexa `.ofx` do banco
2. Agente usa `lendo-documentos` com `--tipo ofx`
3. Para cada transacao:
   - Debito: buscar titulo a pagar no Odoo correspondente
   - Credito: buscar titulo a receber OU registrar como entrada direta
4. Criar `account.bank.statement.line` via `conciliando-transferencias-internas`
   (se for transferencia interna NACOM) ou via
   `executando-odoo-financeiro` (pagamentos externos)

---

## Limitacoes Conhecidas

1. **CNAB layout hardcoded**: parser atual so cobre BMP 274. Outros bancos
   precisarao de layout-specific parser.
2. **`.rem` sem extracao**: remessa nao tem campos parseados (layout muda
   muito). Agente recebe conteudo posicional cru e deve parsear heuristicamente
   se necessario.
3. **Layouts CNAB240**: o parser atual so cobre CNAB400 (linha de 400 bytes).
   CNAB240 (240 bytes, padrao SPB) nao e suportado.
4. **OFX com multi-account**: parser processa apenas a primeira conta
   (`<BANKACCTFROM>`) — OFX com mais de uma conta pode perder dados.
5. **Encoding nao-padrao**: se arquivo nao for latin-1, pode haver caracteres
   mal decodificados. Reportar ao usuario "caracteres estranhos detectados".

---

## Referencias externas

- FEBRABAN — padrao CNAB: https://portal.febraban.org.br
- OFX homepage: https://www.ofx.net
- BMP Money Plus — documentacao 274: (interno, nao publico)

---

## Arquivos do projeto relacionados

- `app/financeiro/services/cnab400_parser_service.py` — parser retorno (fonte)
- `app/financeiro/services/ofx_parser_service.py` — parser OFX (fonte)
- `app/financeiro/services/cnab400_processor_service.py` — pipeline de
  conciliacao completo (usa o parser + matching com titulos locais)
- `app/financeiro/services/ofx_vinculacao_service.py` — pipeline OFX
- `app/financeiro/routes/cnab400.py` — rotas do pipeline CNAB
- `app/financeiro/CLAUDE.md` — guia de desenvolvimento financeiro
