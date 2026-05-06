# Visual Regression — Snapshots

> Protege contra regressao visual durante o cleanup de templates (Fase E do
> design system) e qualquer mudanca futura em CSS/Bootstrap. Audit numerico
> nao detecta mudanca de pixel; este sistema sim.

## Como Funciona

1. **Baseline** — captura "estado bom conhecido" em `snapshots/baseline/<page>_<theme>.png` (commitado)
2. **Current** — captura local atual em `snapshots/current/` (gitignored)
3. **Compare** — diff pixel-a-pixel; falha se exceder threshold (default 1%)

## Pre-Requisitos

```bash
# Browser para Playwright (uma vez por maquina)
python -m playwright install chromium

# Credenciais de teste (qualquer usuario com acesso aos modulos das pages.yml)
export UI_VISUAL_EMAIL="seu_email@dominio.com"
export UI_VISUAL_PASSWORD="senha"

# App rodando (terminal separado)
python run.py
```

## Workflow Tipico

### Primeira vez (estabelecer baseline)

```bash
# captura baseline (sera commitado)
python tests/visual/capture.py --target baseline

# verifica visualmente que esta correto (opcional)
ls tests/visual/snapshots/baseline/

# commit
git add tests/visual/snapshots/baseline/*.png
git commit -m "chore(visual): baseline pos-Fase-C"
```

### Antes de cada PR de cleanup

```bash
# 1. Captura estado atual
python tests/visual/capture.py --target current

# 2. Compara
python tests/visual/compare.py
# → exit 0: OK, sem regressao visual
# → exit 1: alguma pagina diff > 1%, ver report.html
```

### Apos cleanup intencional (mudou visual de proposito)

```bash
# Promove current para baseline
python tests/visual/compare.py --update-baseline

# Commita o novo baseline
git add tests/visual/snapshots/baseline/
git commit -m "chore(visual): atualiza baseline apos cleanup V6 batch"
```

## Comandos Uteis

```bash
# Captura paginas especificas
python tests/visual/capture.py --pages hora_pedidos_lista,hora_estoque_lista

# Captura so dark
python tests/visual/capture.py --themes dark

# Browser visivel (debug)
python tests/visual/capture.py --headed

# Threshold mais rigoroso (0.5%)
python tests/visual/compare.py --threshold 0.5

# URL diferente (CI/staging)
python tests/visual/capture.py --base-url http://staging.example.com

# Paginas com {id} placeholder (raras hoje)
export SAMPLE_IDS='{"hora_pedido": 123}'
python tests/visual/capture.py
```

## Estrutura

```
tests/visual/
├── README.md          # este arquivo
├── pages.yml          # config: paginas, viewport, themes, threshold
├── capture.py         # Playwright snapshot
├── compare.py         # PIL diff + report HTML
└── snapshots/
    ├── baseline/      # commitado — fonte de verdade
    ├── current/       # gitignored — captura atual
    └── reports/       # gitignored — relatorios HTML de diff
```

## Threshold e Falsos Positivos

Default `1%` cobre:
- Antialiasing de fontes (variacao por OS/browser)
- Animacoes CSS sutis (transitions)
- Diferencas de carga (lazy images, async render)

Se um PR mostra muitas pages "FAIL" com diff < 5%, provavelmente eh:
- Fonte renderizada diferente em containers (verificar se rodando mesmo browser)
- Dado mudou no DB entre baseline e current (refixar baseline com dado estavel)
- Animacao em curso quando screenshot tirou (aumentar `wait_for` em pages.yml)

Se diff > 10% em uma pagina sem alteracao intencional → bug visual real.

## Adicionar Nova Pagina

Edite `pages.yml`:

```yaml
pages:
  - name: meu_modulo_lista
    url: "/meu-modulo/lista"
    description: "Por que esta pagina importa"
```

Depois capture/promova baseline:

```bash
python tests/visual/capture.py --target baseline --pages meu_modulo_lista
git add tests/visual/snapshots/baseline/meu_modulo_lista_*.png
```

## Limitacoes Conhecidas

- **Dados dinamicos**: paginas que mostram `agora()` ou contadores live tem ruido. Filtrar/mockar essas areas no baseline (TODO: opcao mask em pages.yml).
- **Login**: usuario configurado precisa ter permissao em todos os modulos das pages.yml. Sem permissao = redirect = screenshot da pagina errada.
- **Dependencia de DB**: snapshots refletem dados do DB local. Para CI: usar fixture estavel ou DB de teste.
- **Tamanho do baseline**: PNGs podem chegar a 200-500KB cada. 13 paginas × 2 temas = ~5-6 MB no repo. Aceitavel mas considerar git-lfs se crescer.

## Quando Atualizar Este Documento

- Adicionou pagina nova → atualizar Secao "Adicionar Nova Pagina" com exemplo se nao for trivial
- Threshold padrao mudou → atualizar default no `pages.yml` e nesta doc
- Adicionou flag nova no capture/compare → adicionar em "Comandos Uteis"
