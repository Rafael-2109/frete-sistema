# COTACAO — 002

Documentacao detalhada do script de cotacao de frete no SSW.

---

- [Parametros](#parametros)
- [Regra CEP Origem (CRITICA)](#regra-cep-origem-critica)
- [Workflow do Agente](#workflow-do-agente)
- [FIELD_MAP](#field_map-10-campos)
- [Resultado Agrupado](#resultado-agrupado)
- [Formato de Apresentacao](#formato-de-apresentacao)
- [GOTCHAS](#gotchas)

---

## cotar_frete_ssw_002.py

Cota frete no SSW (opcao 002). Preenche formulario e executa `calcula('S')` para simular proposta. Retorna resultado agrupado por categoria com indicadores extras.

```bash
python .claude/skills/operando-ssw/scripts/cotar_frete_ssw_002.py \
  --cnpj-pagador 33119545000251 \
  --cep-destino 26020157 \
  --peso 1894.405 --valor 14649.73 \
  --coletar N --entregar S \
  [--cep-origem 06530581] [--frete CIF] [--contribuinte S] \
  [--cubagem 0] [--defaults-file ssw_defaults.json] \
  [--dry-run] [--discover]
```

### Parametros

| Parametro | Obrigatorio | Default | Descricao |
|-----------|-------------|---------|-----------|
| --cnpj-pagador | **Sim** | — | CNPJ do cliente pagador (14 digitos) |
| --cep-destino | **Sim** | — | CEP de entrega (8 digitos) |
| --peso | **Sim** | — | Peso em kg (ex: 1894.405) |
| --valor | **Sim** | — | Valor mercadoria em R$ (ex: 14649.73) |
| --cep-origem | Condicional | CEP CarVia se coletar=N | CEP de coleta/origem (8 digitos) |
| --frete | Nao | CIF | CIF ou FOB |
| --coletar | Nao | S | S=CarVia coleta no cliente, N=cliente entrega na CarVia |
| --entregar | Nao | S | S=CarVia entrega no destino, N=destinatario retira |
| --contribuinte | Nao | S | S/N destinatario contribuinte ICMS |
| --cubagem | Nao | automatico | Cubagem em m3 (SSW calcula pelo peso se omitido) |
| --dry-run | — | — | Preenche formulario sem simular |
| --discover | — | — | Lista todos os campos do formulario |

### Regra CEP Origem (CRITICA)

```
coletar=S → CEP origem = endereco do CLIENTE (CarVia coleta la)
             Agente DEVE perguntar --cep-origem ao usuario

coletar=N → CEP origem = CEP da CARVIA (cliente entrega na CarVia)
             Script auto-resolve usando endereco_fiscal.cep do ssw_defaults.json
             Agente NAO precisa perguntar --cep-origem
```

**Impacto**: CEP origem determina a ROTA no SSW. CEP errado = tabela de preco errada. Exemplo: CEP cliente em Amparo/SP → rota CARR-GIGR (Generica). CEP CarVia → rota CARP-GIGR (Promocional).

### Workflow do Agente

```
1. PERGUNTAR (obrigatorios): CNPJ pagador, CEP destino, Peso kg, Valor R$
2. PERGUNTAR (decisoes): Coletar? (S/N), Entregar? (S/N)
3. INFORMAR parametros assumidos (defaults):
   "Frete: CIF | Contribuinte: S | Cubagem: auto | CEP origem: [se coletar=N] 06530581"
4. EXECUTAR --dry-run → preview
5. CONFIRMAR com usuario → executar sem --dry-run
6. APRESENTAR resultado agrupado (ver "Formato de Apresentacao")
```

O campo `parametros_assumidos` no retorno JSON lista cada assuncao. Agente DEVE exibir antes e depois da simulacao.

### FIELD_MAP (10 campos)

| Parametro CLI | Campo SSW | Limite | Descricao |
|---------------|-----------|--------|-----------|
| cnpj_pagador | `cgc_pag` | 14 | CNPJ (somente digitos) |
| tipo_frete | `tp_frete` | 1 | 1=CIF, 2=FOB (NAO "C"/"F") |
| cep_origem | `cep_origem` | 8 | CEP origem |
| cep_destino | `cep_destino` | 8 | CEP destino |
| coletar | `coletar` | 1 | S/N |
| entregar | `entregar` | 1 | S/N |
| valor_mercadoria | `vlr_merc` | 15 | R$ formato brasileiro |
| peso | `peso` | 12 | kg formato brasileiro |
| cubagem | `cubagem` | 12 | m3 formato brasileiro |
| contribuinte | `contribuinte` | 1 | S/N (OBRIGATORIO para simulacao) |

### Fluxo SSW

Login → abrir 002 → `ajaxEnvia('NEW', 1)` → interceptar → injetar DOM → re-override createNewDoc → preencher campos via `preencher_campo_js` → `calcula('S')` → aguardar resultado → capturar RESULT_FIELDS

### Resultado Agrupado

6 categorias no retorno `proposta`:

| Categoria | Campos SSW | Representa |
|-----------|-----------|------------|
| **transporte** | `fretepeso`, `despacho` | Frete por peso e taxa CTE |
| **seguros** | `fretevalor`(=Ad Valorem), `gris`, `seguro_fluvial` | Seguro sobre valor NF + gestao de risco |
| **taxas** | `coleta`, `ent_geral`, `pedagio`, `tas`, `tdc`, `entrega`(=TDE), `tar`, `trt`, `adic_local`(=TDA), + 13 outros | Taxas operacionais |
| **impostos** | `impostos` | Imposto repassado |
| **totais** | `vlr_frete`(=total), `ntc`, `tributacao`, `base_tribut` | Totais e referencia NTC |
| **indicadores** | `percfretepeso`, `percfretemerc`, `descatual`, `rcatual`, `rota` | % e rota selecionada |

**Indicadores extras** (calculados pelo script): `ad_valorem_pct`, `gris_pct`, `seguro_total`, `seguro_total_pct`.

**INFO_FIELDS** (7 campos readOnly): `cidadeori`, `cidadedest`, `unid_col`, `unid_ent`, `dias_entrega`, `prev_ent`, `pesocalculo`.

### Formato de Apresentacao

```
COTACAO SSW — [ORIGEM] → [DESTINO]
Rota: [ROTA] | Tabela: [nome se disponivel]

TRANSPORTE
  Frete Peso ............. R$ X.XXX,XX
  Despacho/CTE ........... R$ XX,XX

SEGUROS
  Ad Valorem (X,XX%) ..... R$ XX,XX
  GRIS (X,XX%) ........... R$ XX,XX
  Seguro Total ........... R$ XX,XX

TAXAS
  Coleta ................. R$ XX,XX
  Entrega ................ R$ XX,XX
  Pedagio ................ R$ XX,XX
  [demais taxas > 0]

IMPOSTOS
  Impostos ............... R$ XX,XX

  TOTAL FRETE ............ R$ X.XXX,XX

Prazo: X dias | Previsao: DD/MM/AA
Frete/kg: R$ X,XX | Frete/mercadoria: X,XX%

Parametros assumidos:
  - [lista de parametros_assumidos]
```

### GOTCHAS

1. **`contribuinte` OBRIGATORIO**: Sem ele, `calcula('S')` mostra overlay DOM e retorna zeros. O overlay NAO e browser alert — e `<div>` no DOM.
2. **`tp_frete` numerico**: SSW usa `1`=CIF, `2`=FOB. NAO letras. Script converte automaticamente.
3. **`calcula('S')` NAO e ajaxEnvia**: E funcao JS que valida campos e chama ajaxEnvia internamente.
4. **`ajaxEnvia('NEW', 1)` para nova cotacao**: Tela inicial = listagem. `NEW` abre formulario. NAO `INC`.
5. **Re-override createNewDoc**: Necessario apos cada `injetar_html_no_dom`.
6. **Rota**: CARP = CarVia Polo (coletar=N). CARR = rota generica.
7. **Ad Valorem = Seguro**: `fretevalor` = componente seguro (Ad Valorem sobre NF). Seguro total = `fretevalor` + `gris`.
