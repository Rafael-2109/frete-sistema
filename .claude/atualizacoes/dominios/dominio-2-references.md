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
  "relatorio": ".claude/atualizacoes/references/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: P0-P2 revisados completamente, P3-P4 escaneados
- **PARCIAL**: alguns grupos revisados, outros falharam
- **FAILED**: falha critica que impediu a execucao
