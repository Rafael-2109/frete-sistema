# Templates de Spec

## Template: Feature Nova

```markdown
# [Nome da Feature]

## Objetivo

[1-2 paragrafos explicando o problema e a solucao]

## Usuarios

- [Tipo de usuario 1]
- [Tipo de usuario 2]

## Requisitos

1. [Requisito funcional 1]
2. [Requisito funcional 2]
3. [Requisito funcional 3]

## Criterios de Aceite

- [ ] [Criterio verificavel 1]
- [ ] [Criterio verificavel 2]
- [ ] [Criterio verificavel 3]
- [ ] [Criterio verificavel 4]

## Notas Tecnicas

### Arquivos Relacionados
- `app/modulo/models.py` - Modelo X
- `app/modulo/routes.py` - Rotas existentes
- `app/templates/modulo/` - Templates

### Padroes a Seguir
- Consultar CLAUDE.md para nomes de campos
- Usar filtro `numero_br` para formatacao numerica
- Adicionar link no menu (base.html)
- Seguir estrutura de rotas existente
```

---

## Template: Bug Fix

```markdown
# Fix: [Descricao curta do bug]

## Problema

[Descricao do comportamento incorreto]

## Comportamento Esperado

[Como deveria funcionar]

## Como Reproduzir

1. [Passo 1]
2. [Passo 2]
3. [Passo 3]

## Criterios de Aceite

- [ ] Bug nao ocorre mais
- [ ] Funcionalidade original preservada
- [ ] Sem regressoes em [area relacionada]

## Notas Tecnicas

### Arquivos Afetados
- `app/modulo/arquivo.py:123` - Linha do problema
```

---

## Template: Integracao

```markdown
# Integracao: [Sistema Externo]

## Objetivo

Integrar com [sistema] para [proposito].

## Dados a Sincronizar

| Campo Local | Campo Externo | Direcao |
|-------------|---------------|---------|
| [campo1] | [campo_ext1] | enviar |
| [campo2] | [campo_ext2] | receber |

## Fluxo

1. [Trigger - quando sincroniza]
2. [Transformacao - como mapeia]
3. [Destino - onde salva]

## Tratamento de Erros

- [Erro 1]: [Acao]
- [Erro 2]: [Acao]

## Criterios de Aceite

- [ ] Dados sincronizam corretamente
- [ ] Erros logados adequadamente
- [ ] Retry automatico em falhas
- [ ] Circuit breaker implementado
```

---

## Template: Refatoracao

```markdown
# Refatoracao: [Area/Modulo]

## Problema Atual

[O que esta ruim e por que]

## Solucao Proposta

[Como vai ficar apos refatoracao]

## Arquivos a Modificar

| Arquivo | Mudanca |
|---------|---------|
| [arquivo1] | [descricao] |
| [arquivo2] | [descricao] |

## Riscos

- [Risco 1]: [Mitigacao]
- [Risco 2]: [Mitigacao]

## Criterios de Aceite

- [ ] Funcionalidade existente preservada
- [ ] Testes passando
- [ ] Codigo mais legivel/manutenivel
- [ ] Sem regressoes
```

---

## Template: Minimo (Para tarefas simples)

```markdown
# [Nome]

## Objetivo
[Uma linha]

## Requisitos
1. [Req 1]
2. [Req 2]

## Criterios de Aceite
- [ ] [Criterio 1]
- [ ] [Criterio 2]
```

---

## Regras de Nomenclatura

| Tipo | Padrao de Nome | Exemplo |
|------|----------------|---------|
| Feature | `nome-feature.md` | `dashboard-vendas.md` |
| Bug | `fix-descricao.md` | `fix-calculo-frete.md` |
| Integracao | `integracao-sistema.md` | `integracao-odoo-estoque.md` |
| Refatoracao | `refactor-area.md` | `refactor-carteira-queries.md` |
