---
name: acessando-ssw
description: |
  Consulta documentacao SSW, resolve opcoes por numero/nome, guia processos CarVia e auxilia navegacao no sistema.

  USAR QUANDO:
  - Perguntas sobre SSW: "como fazer X no SSW?", "o que e opcao NNN?", "passo a passo para..."
  - Processos CarVia: "a CarVia ja faz manifesto?", "quem faz faturamento?"
  - Opcoes SSW: "para que serve opcao 436?", "qual opcao usar para contas a pagar?"
  - Fluxos end-to-end: "fluxo completo de faturamento", "como funciona transferencia?"
  - Navegacao SSW: "acesse o SSW e preencha...", "navegue ate opcao 004"
  - Regras legais: "sequencia obrigatoria carga direta", "preciso de MDF-e?"

  NAO USAR QUANDO:
  - Cotacao de frete interna (Sistema Fretes) → usar **cotando-frete**
  - Estoque/separacao/embarque → usar **gerindo-expedicao**
  - Status de entrega pos-NF → usar **monitorando-entregas**
  - Operacoes Odoo → usar **rastreando-odoo** ou **especialista-odoo**
  - Consultas analiticas SQL → usar **consultando-sql**
allowed-tools: Read, Bash, Glob, Grep
---

# Acessando SSW

Skill para consultar a documentacao SSW (228 docs, 45 POPs, 20 fluxos) e guiar usuarios nos processos do sistema.

---

## Quando NAO Usar Esta Skill

| Situacao | Skill Correta | Por que? |
|----------|---------------|----------|
| Cotacao de frete (precos, tabelas) | **cotando-frete** | SSW = sistema externo. Cotacao interna usa dados locais |
| Estoque, separacao, embarque | **gerindo-expedicao** | Operacao pre-faturamento e no sistema local, nao no SSW |
| Status de entrega pos-NF | **monitorando-entregas** | Entregas sao rastreadas no sistema local |
| Operacoes Odoo (NF, PO, pagamento) | **rastreando-odoo** | Odoo e sistema separado do SSW |
| Consultas SQL analiticas | **consultando-sql** | Dados analiticos estao no banco local |

### Nacom vs CarVia — Regra de Desambiguacao

> **Nacom Goya** = Industria. CONTRATA frete. Skills: cotando-frete, gerindo-expedicao, monitorando-entregas.
> **CarVia Logistica** = Transportadora. VENDE frete. Skill: acessando-ssw (este arquivo).

Se o usuario diz "cotacao de frete" sem mencionar "SSW" ou "CarVia" → **Nacom** (cotando-frete).
Se diz "cotar no SSW" ou "opcao 002" → **CarVia** (acessando-ssw).
Se ambiguo → perguntar: "Voce quer no SSW (CarVia) ou no sistema interno (Nacom)?"

---

## DECISION TREE — Qual Documento Consultar?

### Mapeamento Rapido

| Se a pergunta menciona... | Consulte | Caminho |
|---------------------------|----------|---------|
| "como fazer X no SSW" / passo a passo | POP correspondente | ROUTING_SSW.md → secao "Mapa Intencao→POP" |
| "o que e opcao NNN" | Doc de opcao | ROUTING_SSW.md → secao "Mapa Intencao→Opcao" |
| "fluxo completo de X" | Fluxo end-to-end | FLUXOS_PROCESSO.md secao FNN |
| "CarVia faz X?" | Status de adocao | CARVIA_STATUS.md |
| "visao geral do modulo X" | Visao geral | visao-geral/NN-modulo.md |
| "regras legais / sequencia" | POP G01/G02 | pops/POP-G01-sequencia-legal-obrigatoria.md |
| "equipe CarVia / quem faz" | Operacao | CARVIA_OPERACAO.md secao 2 |

### Fluxo de Resolucao Completo

```
1. IDENTIFICAR INTENCAO
   |
   ├── Se menciona NUMERO de opcao → resolver_opcao_ssw.py --numero NNN
   ├── Se menciona PROCESSO/ACAO → ROUTING_SSW.md → mapa intencao→POP
   ├── Se menciona FLUXO → FLUXOS_PROCESSO.md
   └── Se busca generica → consultar_documentacao_ssw.py --busca "termo"
   |
2. LOCALIZAR DOCUMENTO
   |
   ├── POP encontrado → Ler e apresentar passo-a-passo
   ├── Doc opcao encontrado → Ler e resumir funcionalidade
   ├── Fluxo encontrado → Ler secao e mostrar diagrama
   └── Nenhum encontrado → Informar ao usuario e sugerir alternativa
   |
3. CONTEXTUALIZAR CARVIA
   |
   ├── Consultar CARVIA_STATUS.md → status de adocao
   └── Informar: "CarVia [ja faz / nao faz / nao conhece] este processo"
   |
4. ACAO (se aplicavel)
   |
   ├── Guiar passo-a-passo (texto)
   └── Navegar via browser tool (se usuario pedir preenchimento)
```

---

## Scripts Disponiveis

### 1. `consultar_documentacao_ssw.py`

Busca na documentacao SSW com 3 modos: regex, semantica (embeddings Voyage AI) e hibrida.

```bash
python scripts/consultar_documentacao_ssw.py --busca "MDF-e"
python scripts/consultar_documentacao_ssw.py --busca "como transferir entre filiais" --modo semantica
python scripts/consultar_documentacao_ssw.py --busca "faturamento manual" --modo hibrida --limite 5
python scripts/consultar_documentacao_ssw.py --busca "conta corrente fornecedor" --diretorio pops --modo regex
```

**Parametros:**
- `--busca` (obrigatorio): Texto a buscar
- `--modo` (opcional, default `hibrida`): Modo de busca — `regex` (textual case-insensitive), `semantica` (embeddings pgvector), `hibrida` (ambos, semantica primeiro)
- `--limite` (opcional, default 10): Maximo de resultados
- `--diretorio` (opcional): Filtrar por subdiretorio (pops, visao-geral, operacional, etc.)

**Retorno:** Lista de arquivos com trechos relevantes, similaridade (modo semantica/hibrida) e fonte de cada resultado.

**Nota:** Modo `semantica` e `hibrida` requerem embeddings indexados (rodar `ssw_indexer.py` primeiro) e `VOYAGE_API_KEY` configurada.

### 2. `resolver_opcao_ssw.py`

Resolve numero ou nome de opcao SSW para arquivo .md e URL de ajuda.

```bash
python scripts/resolver_opcao_ssw.py --numero 436
python scripts/resolver_opcao_ssw.py --nome "faturamento"
python scripts/resolver_opcao_ssw.py --numero 062
```

**Parametros:**
- `--numero` (opcional): Numero da opcao SSW (ex: 004, 436, 475)
- `--nome` (opcional): Nome/descricao da opcao (busca parcial)

**Retorno:** Arquivo .md correspondente + URL de ajuda + POP relacionado (se existir).

---

## Regras Criticas

1. **SEMPRE cite a fonte**: Ao responder sobre SSW, inclua referencia ao arquivo .md consultado
2. **NUNCA invente campos ou telas**: Se nao encontrar documentacao, informe claramente
3. **CONTEXTUALIZE para CarVia**: Sempre informe se a CarVia ja usa o processo (CARVIA_STATUS.md)
4. **Use url-map.json para URLs**: Nunca construa URLs de ajuda SSW manualmente
5. **POPs > docs de opcao**: Se existe POP para o processo, prefira ele (mais detalhado e CarVia-aware)
6. **Opcoes com [CONFIRMAR]**: Se doc existe mas tem marcadores [CONFIRMAR], informar ao usuario que campos sao inferidos e sugerir verificacao via Playwright

---

## Referencias

| Documento | Caminho | Quando usar |
|-----------|---------|-------------|
| Routing SSW | `.claude/references/ssw/ROUTING_SSW.md` | Decision tree, mapas intencao→doc |
| Status CarVia | `.claude/references/ssw/CARVIA_STATUS.md` | Status de adocao por POP |
| Indice SSW | `.claude/references/ssw/INDEX.md` | Ponto de entrada geral |
| Operacao CarVia | `.claude/references/ssw/CARVIA_OPERACAO.md` | Perfil empresa, equipe, gaps |
| Catalogo POPs | `.claude/references/ssw/CATALOGO_POPS.md` | Definicao dos 45 POPs |
| Fluxos Processo | `.claude/references/ssw/FLUXOS_PROCESSO.md` | 20 fluxos end-to-end |
| URL Map | `.claude/references/ssw/url-map.json` | Opcao→URL de ajuda (programatico) |
