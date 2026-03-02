# Guia de Componentes UI — Mapeamento Semantico

**Ultima Atualizacao**: 02/03/2026

> Consulte ANTES de escrever botoes, badges ou elementos com cor.
> Para tokens e arquitetura CSS: ver `MAPEAMENTO_CORES.md` (mesmo diretorio).

---

## 1. Botoes: Mapeamento Semantico

### Tabela de Decisao Rapida

| Intencao | Classe | Cor Visual | Texto | Exemplo |
|----------|--------|------------|-------|---------|
| Acao principal da tela | `btn-primary` | Ambar | Escuro | "Salvar", "Criar", "Novo" |
| Acao secundaria/neutra | `btn-secondary` | Cinza | Tema | "Cancelar", "Voltar", "Fechar" |
| Confirmado/Sucesso/Aprovado | `btn-success` | Verde | Branco | "Confirmado", "Aprovado", "Concluido" |
| Perigo/Excluir/Rejeitar | `btn-danger` | Vermelho | Branco | "Excluir", "Rejeitar", "Cancelar pedido" |
| Atencao/Aguardando/Pendente | `btn-warning` | Amarelo | Escuro | "Pendente", "Aguardando", "Revisar" |
| Informativo/Neutro sem acao | `btn-info` | Cinza medio | Branco | Raramente usado |
| Variante leve (outline) | `btn-outline-*` | Borda colorida | Colorido | Acoes secundarias em headers |

### Regras de Texto (text-white / text-dark)

| Classe | `--_btn-color` definido | `text-white` necessario? |
|--------|------------------------|--------------------------|
| `btn-primary` | `hsl(0 0% 10%)` (escuro) | NAO — texto ja e escuro |
| `btn-secondary` | `var(--text)` (tema) | NAO |
| `btn-success` | `hsl(0 0% 100%)` (branco) | NAO — ja e branco |
| `btn-danger` | `hsl(0 0% 100%)` (branco) | NAO — ja e branco |
| `btn-warning` | `hsl(0 0% 10%)` (escuro) | NAO — texto ja e escuro |
| `btn-info` | `hsl(0 0% 100%)` (branco) | NAO — ja e branco |
| `btn-dark` | `hsl(0 0% 95%)` (claro) | NAO — ja e claro |

**Resumo**: `text-white` e SEMPRE redundante nos botoes filled deste sistema. A cor do texto ja e definida pela variavel `--_btn-color` em `_buttons.css`.

### Erros Comuns

| Erro | Por que esta errado | Correcao |
|------|-------------------|----------|
| `btn-primary` para "Confirmado" | Primary = acao principal, NAO status | `btn-success` |
| `btn-primary` para "Pendente" | Primary = acao principal, NAO alerta | `btn-warning` |
| `btn-warning` para "Cancelar" | Warning = atencao/pendente, NAO perigo | `btn-secondary` ou `btn-danger` |
| `btn-success text-white` | `text-white` redundante | `btn-success` (remover `text-white`) |
| `btn-danger text-white` | `text-white` redundante | `btn-danger` (remover `text-white`) |
| `btn-info text-white` | `text-white` redundante | `btn-info` (remover `text-white`) |

---

## 2. Badges de Status

### Tabela de Decisao

| Status | Classe | Cor |
|--------|--------|-----|
| Pendente / Aguardando | `badge bg-warning text-dark` | Amarelo |
| Confirmado / Aprovado / Concluido | `badge bg-success` | Verde |
| Cancelado / Rejeitado / Erro | `badge bg-danger` | Vermelho |
| Em andamento / Processando | `badge bg-info` | Cinza medio |
| Rascunho / Sem estado / Neutro | `badge bg-secondary` | Cinza neutro |

### Regras

- `text-dark` e necessario APENAS com `bg-warning` (fundo amarelo claro, texto precisa ser escuro)
- `text-white` NAO e necessario com `bg-success`, `bg-danger`, `bg-info` (ja contrastam)
- Para badges customizados do sistema de design: usar classes de `_badges.css` (`badge-status-pendente`, `badge-status-concluido`, etc.)

---

## 3. Layout: Gotchas e Solucoes

### Botoes com Conteudo Complexo

| Problema | Causa | Solucao |
|----------|-------|---------|
| Filhos de `.btn` nao empilham vertical | `.btn` usa `display: inline-flex` + `flex-direction: row` (padrao) | Adicionar classe `flex-column` ao `.btn` |
| Texto longo nao quebra no botao | `.btn` tem `white-space: nowrap` (linha 41 de `_buttons.css`) | Adicionar `style="white-space: normal"` |
| `d-block` nao funciona dentro de `.btn` | `inline-flex` governa layout dos filhos, `d-block` e ignorado | Usar `flex-column` no pai |

### Botoes em Headers Ambar (`bg-primary`)

Quando o header usa `bg-primary` (fundo ambar), usar `btn-outline-light` para contraste:

```html
<!-- Correto: outline-light em header ambar -->
<div class="card-header bg-primary">
    <button class="btn btn-outline-light btn-sm">Filtros</button>
</div>
```

O CSS em `_buttons.css:316-326` ja cuida do contraste branco.

---

## 4. Cores no Design System (Resumo Rapido)

| Bootstrap class | Cor REAL neste sistema | Hex aproximado | Fonte |
|-----------------|----------------------|----------------|-------|
| `*-primary` | Ambar (NAO azul!) | `hsl(45, 95%, 55%)` / `var(--amber-55)` | `_buttons.css:75` |
| `*-secondary` | Cinza neutro | `var(--bg-button)` | `_buttons.css:88` |
| `*-success` | Verde | `hsl(145, 65%, 40%)` / `var(--semantic-success)` | `_buttons.css:101` |
| `*-danger` | Vermelho | `hsl(0, 70%, 50%)` / `var(--semantic-danger)` | `_buttons.css:108` |
| `*-warning` | Amarelo (ambar 50) | `hsl(45, 100%, 50%)` / `var(--amber-50)` | `_buttons.css:115` |
| `*-info` | Cinza medio (NAO azul!) | `hsl(0, 0%, 45%)` | `_buttons.css:122` |
| `*-light` | Fundo adaptivo | `var(--bg-light)` | `_buttons.css:129` |
| `*-dark` | Escuro fixo | `hsl(0, 0%, 20%)` | `_buttons.css:136` |

**ATENCAO**: `primary` e `info` NAO sao azuis neste sistema. `primary` = ambar, `info` = cinza.

---

## 5. Checklist Pre-Implementacao

Antes de escrever qualquer botao, badge ou elemento colorido:

1. Identificar a INTENCAO semantica (acao principal? status? perigo?)
2. Consultar tabela da Secao 1 (botoes) ou Secao 2 (badges)
3. Verificar se `text-white` e necessario (geralmente NAO — ver tabela Secao 1)
4. Se botao com conteudo multi-linha: usar `flex-column` + `white-space: normal`
5. Se botao em header ambar: usar `btn-outline-light`
6. Testar em dark mode E light mode
