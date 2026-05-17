---
name: parseando-sped-ecd
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. NAO invocar do agente
  principal. Parseia arquivo SPED ECD Leiaute 9 (Latin-1, streaming) em
  dict JSON indexado por registro. Output salvo em /tmp/sped-parsed-{token}.json
  para reaproveitamento pelas demais skills de auditoria SPED. Use quando o
  usuario pedir "audita SPED V21", "le o SPED gerado", "parseia o arquivo
  SPED", "estrutura o SPED para auditoria".
allowed-tools: Read, Bash
---

# parseando-sped-ecd — Parser SPED ECD Leiaute 9

## Quando usar

Sempre como **primeira skill** numa sessao de auditoria SPED. As demais skills
de auditoria (`auditando-sped-contabil`, `comparando-sped-ground-truth`,
`auditando-sped-vs-manual`) consomem o JSON gerado por esta skill.

## Como usar

```bash
source .venv/bin/activate
python .claude/skills/parseando-sped-ecd/scripts/parse_sped.py \
    /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V21_3COMPANIES.txt \
    /tmp/sped-parsed-v21.json
```

Output: JSON com `metadata` (total_lines, stats por registro) + `registros`
(dict REG -> lista de registros nomeados por campo).

## Schema de saida

```json
{
  "metadata": {
    "total_lines": 73891,
    "encoding": "latin-1",
    "path": "/home/.../SPED_V21.txt",
    "stats": {"0000": 1, "I050": 1234, "I250": 60123, ...}
  },
  "registros": {
    "0000": [{"NOME": "NACOM GOYA", "CNPJ": "61724241000178", ...}],
    "I050": [{"COD_NAT": "01", "IND_CTA": "A", "COD_CTA": "11101", ...}, ...]
  }
}
```

## Campos mapeados

51 registros do Manual ECD Leiaute 9 (Bloco 0 + I + J + 9 completo).
Schemas em `scripts/parse_sped.py:REGISTRO_CAMPOS`.

Registros nao mapeados: campos preservados como `campo_1`, `campo_2`, etc.

## Gotchas

1. **Encoding Latin-1 puro** — falha em UTF-8. `latin1` ate `0xFF`.
2. **Streaming line-by-line** — SPED de 70MB cabe em memoria intermediaria
   mas NAO carregue arquivo inteiro com `.read()`.
3. **Campos vazios** (`||` consecutivo) preservados como string vazia, NAO
   `None`.
4. **I250 COD_PART** vem na posicao 8 (nao 7) — bug historico V1.6
   (`app/relatorios_fiscais/CLAUDE.md:237`).

## NAO usar quando

- Para gerar SPED (usar `app/relatorios_fiscais/services/sped_ecd_service.py`)
- Para validar SPED estruturalmente (usar `sped_ecd_validator.py` ou skill
  `auditando-sped-vs-manual`)
- Fora do subagente `auditor-sped-ecd` (skill esta reservada via
  SPED_SKILLS_RESERVED em `app/agente/config/settings.py`)
