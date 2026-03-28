Voce e o agente de reorganizacao de memorias do projeto Sistema de Fretes.
Execute a auditoria e cleanup das memorias do Claude Code.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Ler o manual ANTES de executar: `.claude/atualizacoes/memorias/README.md`
- Gerar relatorio em `.claude/atualizacoes/memorias/atualizacao-{DATA}-1.md`
- Atualizar `.claude/atualizacoes/memorias/historico.md` com ponteiro para o relatorio

---

## DIRETORIO DE MEMORIAS

`/home/rafaelnascimento/.claude/projects/-home-rafaelnascimento-projetos-frete-sistema/memory/`

---

## PROCEDIMENTO POR ARQUIVO

1. **Verificar frontmatter** (`name`, `description`, `type`) presente e correto
2. **Avaliar relevancia atual**:
   - Projeto concluido/resolvido → considerar remocao
   - Duplica conteudo de CLAUDE.md → remover (redundante)
   - Informacao factualmente errada → corrigir ou remover
   - Fragmentado (2+ memorias sobre mesmo tema) → consolidar em 1
3. **Verificar MEMORY.md** tem menos de 150 linhas
4. **Verificar que TODAS as entradas** em MEMORY.md apontam para arquivos existentes
5. **Reorganizar semanticamente** se necessario

---

## REGRAS DE MEMORIA (Anthropic Best Practices)

### DEVE estar em memoria
| Tipo | Quando | Exemplo |
|------|--------|---------|
| `user` | Papel, preferencias | "Senior dev, respostas curtas" |
| `feedback` | Correcoes/confirmacoes | "Nao mockar banco em testes" |
| `project` | Trabalho em andamento | "Merge freeze 05/03" |
| `reference` | Ponteiros externos | "Bugs em Linear projeto INGEST" |

### NAO deve estar em memoria
- Code patterns, convencoes, arquitetura (ler codigo)
- Git history (usar git log/blame)
- Conteudo ja em CLAUDE.md
- Detalhes efemeros

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-3-status.json` com:

```json
{
  "dominio": 3,
  "nome": "Memorias Cleanup",
  "status": "OK | PARCIAL | FAILED",
  "memorias_auditadas": 0,
  "memorias_removidas": 0,
  "memorias_consolidadas": 0,
  "memorias_atualizadas": 0,
  "memory_md_linhas": 0,
  "relatorio": ".claude/atualizacoes/memorias/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: todas auditadas, MEMORY.md < 150 linhas, entradas validas
- **PARCIAL**: auditoria incompleta ou MEMORY.md excede limite
- **FAILED**: falha critica
