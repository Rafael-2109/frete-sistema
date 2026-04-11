# CarVia — Importacao, Parsers e Linking

**Referenciado por**: `app/carvia/CLAUDE.md`

Pipeline de importacao de documentos: upload → classificacao → parsing → matching → linking retroativo.

---

## Fluxo de Classificacao

```
Upload (NF-e XML, CTe XML, DACTE PDF, DANFE PDF, Fatura PDF)
    │
    ├── NF-e XML / PDF DANFE → CarviaNf + CarviaNfItem
    │   └── XML: is_nfe() verifica mod==55 (rejeita CTe disfarçado)
    │
    ├── CTe XML / PDF DACTE → Classificar por CNPJ emitente (R6)
    │   ├── CNPJ == CARVIA_CNPJ → CarviaOperacao (CTe CarVia)
    │   │   └── Vincular NFs via junction (matching por chave de acesso)
    │   └── CNPJ != CARVIA_CNPJ → CarviaSubcontrato (CTe Subcontrato)
    │       └── Vincular a CarviaOperacao via NFs compartilhadas
    │           Se nao encontrar operacao → erro/warning
    │
    ├── [PRE-CHECK] Verificar transportadoras para subcontratos + faturas
    │   └── CNPJs nao cadastrados → transportadoras_nao_encontradas (alerta + modal)
    │
    └── Fatura PDF → parse_multi() (1 fatura por pagina)
        │   Parser: regex → Haiku → Sonnet (3 camadas escalonadas)
        │   Extrai: pagador (cliente), beneficiario (CarVia), tipo frete, itens CTe
        │
        ├── Dedup: verifica banco por (numero_fatura, cnpj_cliente/data_emissao)
        │   Se ja existe → log "Fatura ja existe (ignorando)" + return None
        │
        ├── CNPJ beneficiario == transportadora cadastrada → CarviaFaturaTransportadora
        │   └── Warning se CNPJ beneficiario nao cadastrado e != CARVIA_CNPJ
        └── Outro CNPJ → CarviaFaturaCliente + CarviaFaturaClienteItem (itens)
            cnpj_cliente = cnpj_PAGADOR (NAO cnpj_emissor/beneficiario)
```

**Env var necessaria**: `CARVIA_CNPJ` (apenas digitos, ex: `12345678000199`).
Se nao configurada, todos CTes sao classificados como CarVia (compatibilidade) e um aviso e emitido.

**Pre-check de transportadoras** (no review, ANTES de confirmar):
- `processar_arquivos()` verifica se CNPJs de emitentes de CTes subcontrato e beneficiarios de faturas
  estao cadastrados como transportadoras no banco
- Resultado inclui `transportadoras_nao_encontradas` — lista de CNPJs pendentes com nome/uf/cidade
- Template `importar_resultado.html` mostra alerta com botoes de cadastro rapido (modal AJAX)
- Endpoint `POST /carvia/api/cadastrar-transportadora` (CNPJ, razao_social, cidade, UF, freteiro)
  - Dedup: se CNPJ ja existe, retorna transportadora existente sem erro
  - Formata CNPJ automaticamente (XX.XXX.XXX/XXXX-XX)
- Ao cadastrar, badges na tabela de CTes mudam de vermelho para verde via JS

**Classificacao PDF** (ordem de verificacao):
1. **DACTE**: texto "DACTE"/"Conhecimento de Transporte" ou chave com modelo=57 → `PDF_DACTE`
2. **DANFE**: chave 44 digitos com modelo != 57 → `PDF_DANFE`
3. **Fatura**: fallback → `PDF_FATURA`

**CNPJ matriz vs filial**: Faturas podem usar CNPJ matriz (ex: 0001-49) enquanto DACTEs
usam filial (ex: 0002-20). A classificacao de transportadora busca por CNPJ exato cadastrado.

### Fatura PDF — Multi-Pagina (formato SSW)

PDFs SSW (`ssw.inf.br`) contem N faturas por arquivo (1 por pagina).
`parse_multi()` retorna `List[Dict]` (1 dict por pagina). `parse()` retorna apenas 1o resultado (backwards compat).

**Pagador vs Beneficiario**:
- `cnpj_emissor` / `nome_emissor` = beneficiario (CarVia, quem emite a fatura)
- `cnpj_pagador` / `nome_pagador` = cliente (quem paga) — usado como `cnpj_cliente`
- Bug anterior: `cnpj_emissor` era gravado como `cnpj_cliente` (CNPJ da CarVia em TODAS as faturas)

**Campos SSW extras** (14 novos em CarviaFaturaCliente):
- `tipo_frete` (CIF/FOB), `quantidade_documentos`, `valor_mercadoria`, `valor_icms`, `aliquota_icms`, `valor_pedagio`
- `vencimento_original` (antes de reprogramacao), `cancelada` (flag FATURA CANCELADA → status=CANCELADA)
- `pagador_endereco`, `pagador_cep`, `pagador_cidade`, `pagador_uf`, `pagador_ie`, `pagador_telefone`

---

## Parsers — Ordem de Confiabilidade

| Parser | Confiabilidade | Notas |
|--------|---------------|-------|
| `nfe_xml_parser.py` | Alta | Namespace-agnostic. Fonte de verdade para NF-e. Extrai itens de produto. `is_nfe()` verifica mod==55 |
| `cte_xml_parser_carvia.py` | Alta | Herda CTeXMLParser. `get_nfs_referenciadas()` para matching. `get_emitente()` para classificacao |
| `dacte_pdf_parser.py` | Media-Alta | Multi-formato (SSW, Bsoft, ESL, Lonngren, Montenegro). Deteccao automatica via `_detectar_formato()`. Separa chaves modelo=57 (CTe) de modelo=55 (NF-e). Saida identica a `cte_xml_parser_carvia` + campos extras (formato, tipo_servico, cte_carvia_ref, componentes_frete, volumes) |
| `danfe_pdf_parser.py` | Media | Regex-based com pdfplumber+pypdf fallback. Campo `confianca` (0.0-1.0) |
| `fatura_pdf_parser.py` | Variavel | 3 camadas: Regex (alta) -> Haiku (media) -> Sonnet (baixa). Campo `confianca` + `metodo_extracao` |

### DACTE Multi-Formato — Deteccao e Suporte

| Formato | Emitente(s) | Deteccao (footer) | Campos Extras |
|---------|-------------|-------------------|---------------|
| **SSW** | Tocantins, Velocargas, Dago | `SSW.INF.BR` | Referencia completa |
| **Bsoft** | Transmenezes | `Bsoft Internetworks` | Peso via "PESO X/KG" |
| **ESL** | Transperola | `ESL Informatica` | Origem/Destino via "INICIO/TERMINO DA PRESTACAO", UF-Cidade invertido, PESO TAXADO/CUBADO |
| **Lonngren** | CD Uni Brasil | `Lonngren Sistemas` | Frete via "VALOR TOTAL DO SERVICO" |
| **Montenegro** | Montenegro | `Impresso por :` | Chave robusta (sem strip global), fallback "A RECEBER" |

**Chave de acesso (3 niveis)**: 1) 44 digitos consecutivos → 2) Blocos formatados com separadores (limpa por match, NAO global) → 3) Busca localizada na secao "Chave de acesso"

**Confianca ponderada**: chave=2x, frete=2x, rota=1.5x cada, numero/emitente/peso=1x cada (total 10 pontos)

---

## Matching — Algoritmo de 3 Niveis

1. **CHAVE** — Match exato por `chave_acesso_nf` 44 digitos (alta confianca)
2. **CNPJ_NUMERO** — Fallback por `(cnpj_emitente, numero_nf)` (media confianca)
3. **NAO_ENCONTRADA** — NF referenciada no CTe nao importada

---

## Linking — Vinculacao Cross-Documento

`LinkingService` (`app/carvia/services/linking_service.py`) resolve FKs entre documentos:

| Metodo | Funcao |
|--------|--------|
| `resolver_operacao_por_cte(cte_numero)` | Busca CarviaOperacao por CTe, normaliza zeros a esquerda |
| `resolver_nf_por_numero(nf_numero, cnpj)` | Busca CarviaNf por numero + CNPJ (emitente OU destinatario) |
| `vincular_nf_a_operacoes_orfas(nf)` | Re-linking CTe→NF: busca operacoes com nfs_referenciadas_json que referenciam a NF e cria junctions |
| `vincular_operacao_a_itens_fatura_orfaos(operacao)` | Re-linking CTe→Fat: atualiza operacao_id em itens de fatura orfaos + cria junctions |
| `vincular_nf_a_itens_fatura_orfaos(nf)` | Re-linking NF→Fat: atualiza nf_id em itens de fatura orfaos (incl. stubs FATURA_REFERENCIA) + cria junctions |
| `vincular_operacoes_da_fatura(fatura_id)` | **Backward binding**: seta `fatura_cliente_id` e `status=FATURADO` nas operacoes via itens ja resolvidos |
| `vincular_itens_fatura_cliente(fatura_id, auto_criar_nf)` | Resolve `operacao_id` e `nf_id` em itens existentes (3 niveis de fallback) |
| `_criar_nf_referencia(nf_numero, cnpj, ...)` | Cria CarviaNf stub (FATURA_REFERENCIA) — idempotente |
| `_resolver_nf_via_junction(nf_numero, operacao_id)` | Busca NF via junction carvia_operacao_nfs |
| `_criar_junction_se_necessario(operacao_id, nf_id)` | Cria junction se nao existe — idempotente |
| `criar_itens_fatura_transportadora(fatura_id)` | Gera itens a partir de subcontratos vinculados (usado na importacao) |
| `criar_itens_fatura_transportadora_incremental(fatura_id, sub_ids)` | Gera itens apenas para subcontratos especificos (usado ao anexar) |
| `criar_itens_fatura_cliente_from_operacoes(fatura_id)` | Gera itens a partir de operacoes (faturas manuais) |
| `expandir_itens_com_nfs_do_cte(fatura_id)` | Cria itens suplementares para NFs do CTe ausentes (PDF SSW mostra 1 NF/linha, CTe pode ter N NFs). Valores financeiros NULL para evitar dupla contagem |
| `backfill_todas_faturas()` | One-time para dados existentes |

**Matching de CTe**: `ltrim(cte_numero, '0')` normaliza "00000001" == "1".
**Matching de NF**: numero + CNPJ contraparte (emitente OU destinatario), ambos normalizados.
**Fallback 3 niveis**: 1) Match direto → 2) Via junction → 3) Criar NF referencia (se `auto_criar_nf=True`).

**Chamado automaticamente por**:
- `ImportacaoService.salvar_importacao()` — durante import de fatura PDF
- `ImportacaoService.salvar_importacao()` — apos criar NF: `vincular_nf_a_operacoes_orfas` + `vincular_nf_a_itens_fatura_orfaos`
- `ImportacaoService.salvar_importacao()` — apos criar/reusar CTe: `vincular_operacao_a_itens_fatura_orfaos`
- `fatura_routes.nova_fatura_cliente()` — ao criar fatura manualmente
- `fatura_routes.anexar_subcontratos_fatura_transportadora()` — ao anexar subcontratos via AJAX

**Ordem de importacao**: Independente. Re-linking retroativo garante que TODAS as 6 permutacoes (NF, CTe, Fatura) criam vinculos corretos.
