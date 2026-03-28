Voce e o agente de auditoria de arquivos CLAUDE.md do projeto Sistema de Fretes.
Execute a auditoria completa dos 9 arquivos CLAUDE.md abaixo.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Ler o manual ANTES de executar: `.claude/atualizacoes/claude_md/README.md`
- Gerar relatorio em `.claude/atualizacoes/claude_md/atualizacao-{DATA}-1.md`
- Atualizar `.claude/atualizacoes/claude_md/historico.md` com ponteiro para o relatorio

---

## ARQUIVOS A AUDITAR (9)

1. `CLAUDE.md` (raiz)
2. `app/agente/CLAUDE.md`
3. `app/agente/services/CLAUDE.md`
4. `app/carteira/CLAUDE.md`
5. `app/carvia/CLAUDE.md`
6. `app/financeiro/CLAUDE.md`
7. `app/odoo/CLAUDE.md`
8. `app/seguranca/CLAUDE.md`
9. `app/teams/CLAUDE.md`

---

## PROCEDIMENTO POR ARQUIVO

1. Contar LOC e arquivos do modulo:
   ```bash
   find app/{modulo}/ -name "*.py" | wc -l
   find app/{modulo}/ -name "*.py" -exec wc -l {} + | tail -1
   find app/templates/{modulo}/ -name "*.html" 2>/dev/null | wc -l
   ```
2. Verificar que TODOS os caminhos mencionados existem
3. Comparar contagens documentadas vs reais
4. Identificar arquivos novos no modulo nao documentados
5. Corrigir divergencias encontradas
6. Atualizar data "Ultima Atualizacao" nos modificados

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-1-status.json` com:

```json
{
  "dominio": 1,
  "nome": "CLAUDE.md Audit",
  "status": "OK | PARCIAL | FAILED",
  "arquivos_auditados": 9,
  "arquivos_modificados": 0,
  "relatorio": ".claude/atualizacoes/claude_md/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: todos os 9 auditados, divergencias corrigidas
- **PARCIAL**: alguns auditados, outros falharam (listar em `erros`)
- **FAILED**: falha critica que impediu a execucao
