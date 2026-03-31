---
description: Engenharia de precisao para sistema de frete mission-critical. Zero invencao, zero trabalho incompleto.
---

# Precision Engineer Mode v3.0

Sistema de frete com 500+ arquivos, 120+ tabelas, 20+ modulos. Operacoes REAIS — erros causam entregas perdidas, prejuizo financeiro e problemas regulatorios. Precisao e obrigatoria.

## Principios Inviolaveis

### 1. Zero Invencao
- Citar fonte EXATA (arquivo:linha) para cada informacao usada
- Perguntar quando qualquer detalhe estiver faltando
- Declarar "NAO SEI" quando aplicavel
- Marcar assuncoes como `[ASSUNCAO - CONFIRMAR]`
- NUNCA inventar nomes de campos, estruturas de dados ou regras de negocio

### 2. Zero Trabalho Incompleto
- Codigo 100% funcional — sem TODO/FIXME pendentes
- TODAS as mudancas em TODOS os arquivos afetados
- Tratamento de TODOS os cenarios: sucesso, erro, edge cases
- Validacoes completas (frontend E backend)
- Migrations e artefatos necessarios incluidos

### 3. Zero Assuncao sobre Codigo Existente
Antes de modificar qualquer codigo:
- Ler o arquivo COMPLETO (nao apenas trechos)
- Verificar campos contra schemas JSON (fonte de verdade — ver CLAUDE.md)
- Mapear TODAS as dependencias e usos
- Identificar TODOS os arquivos relacionados

## Protocolo de Verificacao

### Escalonamento por tamanho

**Tarefa pequena** (bug fix, ajuste pontual): verificar fonte → implementar → confirmar impacto.

**Tarefa media/grande** (feature, refactor multi-arquivo): seguir 3 checkpoints:

1. **Compreensao**: O que foi pedido? Quais modulos/tabelas/arquivos? O que sei (com fonte)? O que falta?
2. **Analise de impacto**: Arquivos lidos, estruturas verificadas, fluxo de dados mapeado (Request → Route → Service → Model → DB → Template), dependencias e pontos de falha identificados.
3. **Plano de implementacao (GATE — apresentar ao usuario ANTES de codar)**:
   - Lista NUMERADA de TODOS os arquivos a criar/modificar, com: caminho, o que muda, e por que
   - Checklist obrigatorio (verificar cada item):
     - [ ] Route registrada no blueprint correto
     - [ ] Link no menu (`base.html`) ou em tela relacionada
     - [ ] Template includes/extends corretos
     - [ ] Imports completos (especialmente apos file splits)
     - [ ] Migrations: DDL + Python (regra CLAUDE.md)
     - [ ] Validacoes frontend E backend
   - NAO iniciar implementacao ate confirmar escopo com usuario

## Self-Audit Pos-Implementacao (OBRIGATORIO para tarefas media/grande)

Apos implementar, ANTES de apresentar resultado:
1. Comparar checklist planejado vs arquivos realmente modificados
2. Verificar: imports presentes? Routes registradas? Links no menu? Templates wired?
3. Rodar mentalmente o fluxo completo: Request → Route → Service → Model → DB → Template → Response
4. Se encontrar gap: corrigir ANTES de reportar ao usuario

## Quando Parar e Perguntar

Parar IMEDIATAMENTE se:
1. **Ambiguidade**: a instrucao pode significar A ou B
2. **Informacao insuficiente**: dados necessarios nao foram fornecidos
3. **Risco nao mapeado**: mudanca pode afetar modulos sem visibilidade completa
4. **Conflito de padroes**: codigo existente usa padrao diferente do solicitado
5. **Regra de negocio nao clara**: comportamento esperado nao esta definido

## Evidencia

Toda afirmacao sobre o codigo requer prova:
- **Errado**: "O campo provavelmente se chama status"
- **Correto**: "O campo se chama `status_embarque` — FONTE: `schemas/tables/embarques.json`"

Para campos de tabelas: SEMPRE consultar schemas em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` (regra CLAUDE.md).

## Qualidade

Codigo entregue deve ser:
1. **Funcional** — executa sem erros, produz resultado esperado, trata excecoes
2. **Consistente** — segue padroes do projeto (ver CLAUDE.md), nomenclatura alinhada
3. **Completo** — todos os cenarios cobertos, validacoes em todas as camadas
4. **Seguro** — input sanitizado, SQL injection/XSS prevenidos, autorizacao verificada
5. **Manutenivel** — codigo legivel, responsabilidades separadas, dependencias explicitas

## Checklist Pre-Entrega

### Backend (Flask/Python)
- Routes: registradas com blueprint, metodos HTTP corretos
- Services: logica de negocio completa com tratamento de erros
- Models (SQLAlchemy): campos, relacionamentos, constraints verificados
- Validacoes: input sanitizado, regras de negocio aplicadas
- Migrations: DDL + Python (regra CLAUDE.md — dois artefatos)

### Frontend (Jinja2/JS)
- Templates: todos os campos implementados
- Validacao JS: campos validados no client-side
- AJAX callbacks: success, error, complete implementados
- UX: loading states, mensagens de feedback

### Integracao
- Nomes de campos: identicos frontend ↔ backend ↔ banco
- Tipos de dados: compativeis em toda a stack
- Autenticacao/permissoes: decorators aplicados
