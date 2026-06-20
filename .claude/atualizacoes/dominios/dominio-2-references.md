Voce e o agente de revisao de References do projeto Sistema de Fretes.
Execute a revisao completa dos arquivos em `.claude/references/`.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Ler o manual ANTES de executar: `.claude/atualizacoes/references/README.md`
- Gerar relatorio em `.claude/atualizacoes/references/atualizacao-{DATA}-1.md`
- Atualizar `.claude/atualizacoes/references/historico.md` com ponteiro para o relatorio

---

## GRUPOS DE PRIORIDADE

| Grupo | Escopo | Profundidade |
|-------|--------|-------------|
| P0 | Root (12 files em `.claude/references/`) | Revisao COMPLETA |
| P1 | `modelos/` + `negocio/` (10 files) | Revisao COMPLETA |
| P2 | `odoo/` (8 files) | Revisao COMPLETA |
| P3-P4 | `design/`, `linx/`, `ssw/` | Scan rapido — apenas problemas criticos |

---

## PASSO 0 — VERIFICACAO DE ALCANCABILIDADE C8 (deterministica, rodar PRIMEIRO)

> **Por que aqui:** o pre-commit roda `doc_audit.py` em escopo PARCIAL (`--enforce-added`), que
> AUTO-SKIPA a verificacao de alcancabilidade C8 (orfaos / bidirecionalidade / hub quebrado) —
> `doc_audit.py:67-68` so roda C8 quando `partial=False`. Logo a UNICA cadencia automatizada de
> C8 e' esta, no semanal. Sem ela, des-wirings de hub acumulam silenciosamente entre rodadas manuais.

Rodar a varredura GLOBAL (cobre `docs/`, `.claude/references/`, `app/**/CLAUDE.md`, `CLAUDE.md`):

```bash
source .venv/bin/activate 2>/dev/null
python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>&1 | grep -E "^C8" | tee /tmp/manutencao-$DATA/c8-orfaos.txt
```

Para cada finding C8, **triar vivo/morto ANTES de wirar** (`git log -1 --format=%ci -- <doc>`; varios docs
de modulo sao historico de 2025 e merecem `_deprecated/`, nao ponteiro):
- `orfao: nao alcancavel de CLAUDE.md via hubs` → o doc NAO tem caminho de descoberta. Se VIVO:
  adicionar 1 linha-ponteiro no hub correto (o `INDEX.md`/`README.md` do dir, ou a tabela do `CLAUDE.md`
  raiz) **E** corrigir o campo `hub:` do `doc:meta` para o indice que de fato o lista. Se MORTO: `_deprecated/`.
- `hub X nao lista este doc de volta (item-9)` → bidirecionalidade quebrada: adicionar o doc ao hub X,
  ou apontar o `hub:` do `doc:meta` para o indice que REALMENTE o lista.
- `hub declarado inexistente/nao-gerenciado` → corrigir o path do `hub:`.

Registrar a contagem em `c8_orfaos` / `c8_corrigidos` do status.json. C8 e' severidade `block` no lint —
um orfao nao tratado aqui so' sera pego na proxima rodada manual.

---

## PROCEDIMENTO PARA P0-P2

Para cada arquivo:

1. **Verificar versoes de dependencias** contra `requirements.txt`
2. **Verificar caminhos e arquivos** mencionados existem no filesystem
3. **Verificar regras de negocio** contra implementacao real no codigo
4. **Identificar informacoes factualmente incorretas** ou desatualizadas
5. **Corrigir divergencias** encontradas

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-2-status.json` com:

```json
{
  "dominio": 2,
  "nome": "References Audit",
  "status": "OK | PARCIAL | FAILED",
  "arquivos_revisados": 0,
  "arquivos_corrigidos": 0,
  "caminhos_quebrados": 0,
  "c8_orfaos": 0,
  "c8_corrigidos": 0,
  "relatorio": ".claude/atualizacoes/references/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: P0-P2 revisados completamente, P3-P4 escaneados
- **PARCIAL**: alguns grupos revisados, outros falharam
- **FAILED**: falha critica que impediu a execucao
