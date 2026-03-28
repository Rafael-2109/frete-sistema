Voce e o agente de manutencao semanal do projeto Sistema de Fretes.
Execute os 3 dominios abaixo em sequencia, gerando relatorios rastreaveis para cada um.

INSTRUCOES OBRIGATORIAS:
- Ler o manual (README.md) de cada dominio ANTES de executar
- Gerar 1 relatorio por dominio no formato atualizacao-{DATA}-N.md
- Atualizar o historico.md de cada dominio com ponteiro para o relatorio
- Commits atomicos por dominio com mensagem descritiva
- DATA: usar output de `date +%Y-%m-%d`

---

## DOMINIO 1: CLAUDE.md (9 arquivos)

Manual: .claude/atualizacoes/claude_md/README.md

Arquivos a auditar:
- CLAUDE.md (raiz)
- app/agente/CLAUDE.md
- app/agente/services/CLAUDE.md
- app/carteira/CLAUDE.md
- app/carvia/CLAUDE.md
- app/financeiro/CLAUDE.md
- app/odoo/CLAUDE.md
- app/seguranca/CLAUDE.md
- app/teams/CLAUDE.md

Para cada arquivo:
1. Contar LOC e arquivos do modulo (find + wc -l)
2. Verificar que TODOS os caminhos mencionados existem
3. Comparar contagens documentadas vs reais
4. Identificar arquivos novos no modulo nao documentados
5. Corrigir divergencias encontradas
6. Atualizar data "Ultima Atualizacao" nos modificados

Relatorio: .claude/atualizacoes/claude_md/atualizacao-{DATA}-1.md
Historico: .claude/atualizacoes/claude_md/historico.md

---

## DOMINIO 2: References (.claude/references/)

Manual: .claude/atualizacoes/references/README.md

Grupos de prioridade:
- P0 (root, 12 files): revisao COMPLETA
- P1 (modelos/ + negocio/, 10 files): revisao COMPLETA
- P2 (odoo/, 8 files): revisao COMPLETA
- P3-P4 (design/, linx/, ssw/): scan rapido — reportar apenas problemas criticos

Para P0-P2:
1. Verificar versoes de dependencias contra requirements.txt
2. Verificar que caminhos e arquivos mencionados existem
3. Verificar regras de negocio contra implementacao real no codigo
4. Identificar informacoes factualmente incorretas ou desatualizadas
5. Corrigir divergencias

Relatorio: .claude/atualizacoes/references/atualizacao-{DATA}-1.md
Historico: .claude/atualizacoes/references/historico.md

---

## DOMINIO 3: Memorias

Manual: .claude/atualizacoes/memorias/README.md

Diretorio: /home/rafaelnascimento/.claude/projects/-home-rafaelnascimento-projetos-frete-sistema/memory/

Para cada arquivo de memoria:
1. Verificar frontmatter (name, description, type) presente e correto
2. Avaliar relevancia atual:
   - Projeto concluido/resolvido → considerar remocao
   - Duplica conteudo de CLAUDE.md → remover (redundante)
   - Informacao factualmente errada → corrigir ou remover
   - Fragmentado (2+ memorias sobre mesmo tema) → consolidar em 1
3. Verificar que MEMORY.md tem menos de 150 linhas
4. Verificar que TODAS as entradas em MEMORY.md apontam para arquivos existentes
5. Reorganizar semanticamente se necessario

Relatorio: .claude/atualizacoes/memorias/atualizacao-{DATA}-1.md
Historico: .claude/atualizacoes/memorias/historico.md

---

APOS TODOS OS 3 DOMINIOS:
1. git checkout -b manutencao/semanal-{DATA}
2. git add dos arquivos modificados (CLAUDE.md, references, memorias, relatorios)
3. Criar commits atomicos por dominio
4. NAO fazer git push
