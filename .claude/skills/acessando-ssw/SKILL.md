---
name: acessando-ssw
description: >-
  Base de conhecimento do sistema SSW. Use esta skill sempre que alguem
  perguntar qualquer coisa sobre o SSW — como fazer algo no SSW, o que uma
  opcao numerada faz (opcao 004, opcao 436, etc.), guias passo-a-passo (POPs),
  fluxos de documentos fiscais de transporte (CT-e, MDF-e, CTRC), romaneio,
  faturamento, contas a pagar, transferencias entre filiais, ou se a CarVia
  usa determinado recurso do SSW. Se a pergunta menciona SSW ou envolve
  entender/navegar processos do SSW, use esta skill.

  Nao usar para: cotacao de frete interna Nacom → cotando-frete; rastreamento
  de entregas pos-NF → monitorando-entregas; operacoes Odoo → especialista-odoo;
  consultas SQL → consultando-sql; cadastros/escrita no SSW → operando-ssw.
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

## Regras Anti-Alucinacao

7. **NUNCA invente numeros de opcao**: So cite opcoes que apareceram no output dos scripts ou nos docs lidos. Se o script retornou `"sucesso": true` com opcao 436, use 436 — NAO invente 438 ou 440.
8. **NUNCA invente codigos de POP**: So cite POPs presentes em `pop_relacionado` do script ou encontrados via busca. O mapping opcao→POP e feito pelo script, nao por inferencia.
9. **Fidelidade ao output dos scripts**: Dados do JSON de saida (nomes, numeros, caminhos) devem ser usados EXATAMENTE como retornados. Nao parafrasear nomes de opcao ou caminhos de arquivo.
10. **Busca sem resultados — retry com termos mais simples**: Se `consultar_documentacao_ssw.py` retornar `total_encontrados: 0`, tentar termos mais curtos/simples antes de concluir que nao existe documentacao. Exemplo: "GPS rastreamento frota" → 0 resultados → tentar "GPS" ou "rastreamento" separadamente.
11. **NAO confundir documentos fiscais**: CT-e, MDF-e, NF-e, DACTE e DAMDFE sao documentos diferentes. Nunca use um no lugar do outro.

---

## Estrategia para Queries Compostas

Para perguntas que combinam multiplos temas (ex: "passo a passo CT-e + CarVia ja usa?"):

1. **Executar scripts PRIMEIRO** — scripts dao pontos de entrada estruturados (doc .md + POP + URL)
2. **Ler os docs identificados** — o script indica QUAL doc ler, ler ele para obter conteudo
3. **Consultar CARVIA_STATUS.md** — para a parte "CarVia usa?" (sempre, mesmo se nao perguntou)
4. **Montar resposta unificada** — combinar informacoes de todas as fontes

NAO pule o passo 1 (scripts) e va direto para Grep manual. Os scripts reduzem de ~15 operacoes para ~3.

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
