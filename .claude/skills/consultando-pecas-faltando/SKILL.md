---
name: consultando-pecas-faltando
description: >-
  Esta skill deve ser usada pelo Agente Lojas HORA quando o usuario pergunta
  sobre pecas faltando registradas na conferencia: "quais pecas faltando?",
  "o chassi X ta com peca faltando?", "pecas abertas da minha loja", "tem
  chassi doador?", "pecas pendentes de resolucao". Lista registros com fotos
  (S3 keys), status de resolucao e chassi doador se houver. Respeita escopo.

  USAR QUANDO:
  - "quais pecas faltando?"
  - "pecas pendentes"
  - "o chassi X ta com peca faltando?"
  - "tem peca aberta na minha loja?"
  - "chassi doador"

  NAO USAR PARA:
  - Conferencia completa (usar conferindo-recebimento)
  - Status de pedido (usar acompanhando-pedido)
  - Divergencias de chassi errado/moto faltando (essas sao tipo_divergencia no
    conferindo-recebimento; peca faltando e categoria separada)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Pecas Faltando HORA

Lista registros de pecas faltando em motos recebidas: descricao da peca,
fotos tiradas pelo operador, status e chassi doador (se houver).

---

## Quando Usar

USE para:
- "quais pecas faltando?"
- "pecas pendentes de resolucao"
- "chassi X tem pecas em aberto?"
- "quantas pecas abertas na minha loja?"

NAO USE para:
- Conferencia completa (inclui chassis OK) -> `conferindo-recebimento`
- Divergencia de chassi/moto -> `conferindo-recebimento` (tipo_divergencia)

---

## REGRAS CRITICAS

### 1. RESPEITAR ESCOPO
Peca faltando vincula a recebimento_conferencia -> recebimento -> loja_id.
Filtra por `loja_ids_permitidas` via join.

### 2. STATUS
Valores esperados de `hora_peca_faltando.status`:
- `ABERTO` / `PENDENTE` -> ainda nao resolvida
- `RESOLVIDO` / `FINALIZADO` -> peca recebida/substituida
(Valores exatos dependem do dominio — o script retorna `status_normalizado`
como `aberto|resolvido|outro` para padronizar.)

### 3. FOTOS
`hora_peca_faltando_foto.foto_s3_key` e chave S3. Nao tente abrir — apenas
expor URL para o operador consultar no sistema.

---

## Invocacao

```bash
python .claude/skills/consultando-pecas-faltando/scripts/consultando_pecas_faltando.py \
    --loja-ids 2
    # opcional: --chassi LA2025SA110003988
    # opcional: --somente-abertos
```

---

## Output JSON (exemplo)

```json
{
  "escopo_aplicado": {"loja_ids": [2], "pode_ver_todas": false},
  "totais": {"abertas": 3, "resolvidas": 5, "outras": 0},
  "pecas": [
    {
      "id": 12, "numero_chassi": "LA2025SA110003988",
      "descricao": "retrovisor direito", "chassi_doador": null,
      "status": "ABERTO", "status_normalizado": "aberto",
      "loja_id": 2, "loja_apelido": "MOTOCHEFE BRAGANCA",
      "recebimento_id": 1, "nf_numero": "36612",
      "criado_em": "2026-04-22T22:00", "criado_por": "tester",
      "resolvido_em": null, "resolvido_por": null,
      "fotos": [
        {"foto_s3_key": "hora-pecas/2026-04/12-001.jpg", "legenda": "falta retrovisor"}
      ]
    }
  ]
}
```
