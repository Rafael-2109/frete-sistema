# Módulo Pessoal — Evolução em 4 Fases

**Data:** 2026-04-20
**Autor:** Rafael + Claude (brainstorming)
**Spec anterior relacionada:** `2026-04-05-pessoal-controle-financeiro-design.md`

---

## Contexto

O módulo `app/pessoal/` é um controle de finanças pessoais restrito aos
usuários 1, 55, 62. Hoje cobre: importação CSV Bradesco (CC + cartão),
categorização com aprendizado (regras PADRAO/RELATIVO + fuzzy 90 + F1 CPF/CNPJ
+ F4 range de valor), dashboard com tendência e comparativo anual, orçamento
mensal, e a tela de Análise recém-criada (busca fuzzy em categorias,
seleção cumulativa, grupos salvos).

Auditoria identificou 4 lacunas prioritárias a fechar em sequência. Este
spec descreve o design de cada uma e a ordem de entrega.

## Objetivos

1. **Buscar transações** com critérios combinados (texto, valor, conta,
   data, categoria, membro) de forma shareable via URL.
2. **Alertar** quando orçamento por categoria está próximo do limite ou já
   foi excedido — reaproveitando `pessoal_orcamentos`.
3. **Permitir hierarquia** de categorias (pai/filho), migrando
   automaticamente o agrupamento atual baseado em `PessoalCategoria.grupo`.
4. **Detectar e rastrear gastos recorrentes** automaticamente, com alertas
   de ausência e variação de valor.

## Não-objetivos (explícitos)

- Detecção de gastos **anômalos** por categoria (alto risco de falso positivo
  — adiado para fase futura).
- Integração Open Banking (Pluggy/Belvo) — fase futura.
- Split de transação (1 transação → N categorias) — fase futura.
- Reconciliação fatura cartão ↔ débito em CC — fase futura.
- Metas de poupança com tracking — fase futura.
- Notificações push/email dos alertas — apenas UI in-app.

---

## Ordem de entrega

Decidida em brainstorming: **F1 → F2 → F3 → F4**. Cada fase é commit
independente, não quebra as anteriores se for pausada, e entrega valor
visível ao usuário.

| Fase | Feature | Justificativa da ordem |
|---|---|---|
| F1 | Busca global e filtros | Baixo esforço, melhora UX imediata |
| F2 | Alertas de orçamento | Reaproveita `pessoal_orcamentos` existente |
| F3 | Hierarquia de categorias | Pré-requisito do F4 (evita retrabalho em agregações) |
| F4 | Gastos recorrentes | Mais complexo; aproveita hierarquia já migrada |

---

## Fase 1 — Busca global e filtros avançados

### Backend

Estende a rota `/pessoal/transacoes` (já existente) aceitando query params
combinados:

| Param | Tipo | Descrição |
|---|---|---|
| `q` | string | ILIKE em `historico + descricao + observacao` |
| `valor_min` | number | Filtro inferior de valor |
| `valor_max` | number | Filtro superior de valor |
| `conta_id` | int | Conta específica |
| `data_ini` | YYYY-MM-DD | Inicio do período |
| `data_fim` | YYYY-MM-DD | Fim do período |
| `tipo` | string | `debito` ou `credito` |
| `categoria_id` | int | Filtra pela categoria E descendentes (depende F3) |
| `membro_id` | int | Membro |
| `status` | string | `PENDENTE` \| `CATEGORIZADO` \| `REVISADO` |
| `tem_categoria` | string | `sim` \| `nao` \| omitido |
| `page`, `per_page` | int | Paginação |

### Índice pg_trgm

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_historico_trgm
  ON pessoal_transacoes USING gin (historico_completo gin_trgm_ops);
```

Permite ILIKE `%...%` rápido mesmo em >10k transações. Inclui
`historico_completo` que já é a concatenação normalizada.

### Frontend

- Barra de busca principal (campo `q`) sempre visível no topo de
  `/pessoal/transacoes`.
- Toggle "Filtros avançados" que expande formulário com os demais
  critérios.
- Botão "Limpar filtros" reseta todos.
- Botão "Salvar busca" grava em `localStorage` (lista de presets no próprio
  usuário, sem persistir no banco).
- URL reflete os filtros (querystring), permitindo bookmark e share.

### Mudanças de modelo

Nenhuma.

---

## Fase 2 — Alertas de orçamento

### Estratégia

Cálculo on-demand (sem cron, sem worker). Função nova retorna a lista de
alertas ativos para um mês de referência.

### Service

```python
def calcular_alertas_orcamento(ano, mes, threshold_pct=80):
    """Retorna alertas ativos para o mês.

    Returns:
        [
          {
            'categoria_id': int,
            'categoria_nome': str,
            'limite': float,
            'consumido': float,
            'pct': float,  # 0-200+
            'nivel': 'warning' | 'excedido' | 'ritmo_alto',
            'dia_atual': int,
            'dias_no_mes': int,
          }, ...
        ]
    """
```

### Níveis

| Nível | Condição |
|---|---|
| `warning` | `consumido/limite >= 0.80` e `< 1.00` |
| `excedido` | `consumido/limite >= 1.00` |
| `ritmo_alto` | `consumido/limite >= (dia_atual/dias_no_mes) * 1.2` e `< 1.00` |

**Interação com F3:** se a categoria com orçamento tem descendentes, o
consumo soma todas as transações das descendentes via `WITH RECURSIVE`
(query helper introduzido em F3). Antes de F3, soma apenas a categoria em si.

### Frontend

- Card "Alertas ativos" no topo de `/pessoal/dashboard`, só aparece se
  `len(alertas) > 0`.
- Badge com contagem ao lado do item "Dashboard" no menu Pessoal quando há
  alertas.
- Cada alerta mostra: ícone da categoria, nome, barra de progresso
  colorida (amarelo warning, vermelho excedido, laranja ritmo_alto), valor
  consumido / limite.

### Mudanças de modelo

Nenhuma. Reaproveita `pessoal_orcamentos`.

---

## Fase 3 — Hierarquia de categorias

### Modelo

Adicionar coluna self-referential em `PessoalCategoria`:

```python
class PessoalCategoria(db.Model):
    # ... campos existentes ...
    categoria_pai_id = db.Column(
        db.Integer,
        db.ForeignKey('pessoal_categorias.id', ondelete='SET NULL'),
        nullable=True, index=True,
    )
    filhos = db.relationship(
        'PessoalCategoria',
        backref=db.backref('pai', remote_side='PessoalCategoria.id'),
    )
```

### Compatibilidade backward

Campo `grupo` **mantido** como denormalização sincronizada automaticamente:

```python
@event.listens_for(PessoalCategoria, 'before_insert')
@event.listens_for(PessoalCategoria, 'before_update')
def _sync_grupo(mapper, connection, target):
    if target.categoria_pai_id:
        pai = connection.execute(
            select(PessoalCategoria.nome)
              .where(PessoalCategoria.id == target.categoria_pai_id)
        ).scalar()
        target.grupo = pai or target.grupo
```

Código existente que lê `categoria.grupo` continua funcionando sem alteração.

### Migration — Opção A (auto)

Ver SQL na seção "Design consolidado" do brainstorming. Em resumo:

1. `ALTER TABLE` adiciona `categoria_pai_id` + índice.
2. `INSERT` cria uma categoria-pai por valor distinto de `grupo` (nome =
   grupo, sem pai).
3. `UPDATE` liga cada categoria existente ao pai recém-criado.
4. Verificação before/after via Python.

**Idempotência obrigatória** (regra do projeto):
- `ADD COLUMN IF NOT EXISTS`
- `INSERT` com `WHERE NOT EXISTS` para evitar duplicação
- `UPDATE` só quando `categoria_pai_id IS NULL`

### Query helper

```python
def categorias_descendentes_ids(categoria_id: int) -> list[int]:
    """Retorna [id, ...descendentes] via CTE recursiva."""
    sql = text("""
        WITH RECURSIVE descendentes AS (
          SELECT id FROM pessoal_categorias WHERE id = :root
          UNION ALL
          SELECT c.id FROM pessoal_categorias c
            JOIN descendentes d ON c.categoria_pai_id = d.id
        )
        SELECT id FROM descendentes
    """)
    return [r[0] for r in db.session.execute(sql, {'root': categoria_id})]
```

Todas as agregações que hoje filtram `categoria_id = X` passam a filtrar
`categoria_id IN (categorias_descendentes_ids(X))`.

**Impacto:**
- `dashboard_service.py`: `gastos_por_categoria`, `evolucao_por_categoria`.
- `analise_service.py`: `serie_mensal_categorias`, `extrato_por_categorias`.
- Alertas de orçamento (F2).

### Regras de integridade

1. **Sem ciclos:** validar no `salvar_categoria` que novo pai não é
   descendente do nó sendo editado.
2. **Profundidade máxima:** 4 níveis (raiz → sub → sub → sub). Valida na
   edição.
3. **Remoção de categoria com filhos:** rejeita (força desvinculação
   manual antes) — evita perda acidental.
4. **Regras PADRAO apontando para pai com filhos:** warning na
   `salvar_regra` — sugere criar regra numa folha.

### Tela de configuração

- Categorias renderizadas em **árvore** (tree view com expand/collapse).
- Dentro de cada nó: botão "Nova sub-categoria" abre modal pré-preenchido
  com `categoria_pai_id = nó`.
- Ação "Mover" permite reparentear (select do novo pai).
- Validação client-side e server-side.

---

## Fase 4 — Gastos recorrentes

### Modelo

```python
class PessoalGastoRecorrente(db.Model):
    __tablename__ = 'pessoal_gastos_recorrentes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)

    # Chave hierárquica de identificação (ver seção "Chave hierárquica")
    chave_tipo = db.Column(db.String(20), nullable=False)  # regra|cnpj|hash
    chave_valor = db.Column(db.String(200), nullable=False)

    categoria_id = db.Column(db.Integer,
        db.ForeignKey('pessoal_categorias.id', ondelete='SET NULL'))

    # Estatísticas
    valor_tipico = db.Column(db.Numeric(15, 2))  # mediana
    valor_min_observado = db.Column(db.Numeric(15, 2))
    valor_max_observado = db.Column(db.Numeric(15, 2))
    frequencia = db.Column(db.String(20))  # mensal|anual|quinzenal|outro
    dia_tipico = db.Column(db.Integer)  # 1-31, None se não-mensal
    ocorrencias_6m = db.Column(db.Integer, default=0)

    # Datas
    primeira_ocorrencia = db.Column(db.Date)
    ultima_ocorrencia = db.Column(db.Date)
    proxima_prevista = db.Column(db.Date)

    # Status
    status = db.Column(db.String(20), default='sugerido')
    # sugerido | ativo | pausado | cancelado
    confirmado_usuario = db.Column(db.Boolean, default=False)

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('chave_tipo', 'chave_valor',
                            name='uq_pgr_chave'),
        db.Index('idx_pgr_status', 'status'),
    )
```

### Chave hierárquica de identificação

**Contexto real (confirmado em 2026-04-20):** a grande maioria das regras
existentes NÃO tem `cpf_cnpj_padrao` nem `valor_min`/`valor_max` — apenas
uma pequena fração das transações do extrato traz CNPJ extraído. Portanto
**regra é a chave primária**, e a granularização fica sob responsabilidade
do usuário (o próprio trabalho de manter regras específicas para coisas
que ele quer ver como recorrentes).

Em ordem de preferência (primeira que aplica, ganha):

1. **`chave_tipo='regra'`** quando transação tem `regra_id`. Chave =
   `str(regra_id)`. Sem filtro de especificidade da regra — confia no
   usuário. Regras muito genéricas são descartadas pelo **filtro
   estatístico** (abaixo), não por análise sintática da regra.
2. **`chave_tipo='cnpj'`** quando transação NÃO tem regra mas
   `cpf_cnpj_parte` está preenchido. Chave = CNPJ. Fallback útil para
   transações ainda não cobertas por regras.
3. **`chave_tipo='hash'`** fallback final: `sha1(historico_normalizado +
   faixa_valor)`, onde `faixa_valor` = round(valor/10)*10.

### Filtro estatístico de qualidade (qualifica como recorrente)

Um grupo (mesma chave) só vira candidato a recorrente quando:

- **≥3 ocorrências** nos últimos `meses` meses
- **≥3 meses distintos** com pelo menos uma ocorrência
- **Desvio relativo de valor ≤15%** da mediana:
  `max(|valor - mediana|) / mediana <= 0.15`

Este último critério descarta automaticamente regras genéricas demais
(ex: regra "MERCADO" cobrindo R$50 de pão, R$200 de feira, R$800 de
compra mensal — desvio altíssimo → não vira recorrente). Regras
granularizadas pelo usuário (ex: "NETFLIX", "ALUGUEL", "SPOTIFY") têm
valor estável e passam no filtro naturalmente.

Quando uma regra cobre gastos heterogêneos e o usuário quer ver partes
dela como recorrente, o caminho é o trabalho natural de **quebrar a
regra em regras mais específicas** (já suportado pelo sistema após o
fix de 2026-04-20 que permite múltiplas regras com mesmo padrão mas
escopos distintos).

### Detecção

Rodada sob demanda (não cron), via endpoint `POST /pessoal/recorrentes/detectar`:

```python
def detectar_recorrentes(meses=6):
    """
    1. Pega transações debito dos últimos `meses` meses (excluir_relatorio=False).
    2. Agrupa por chave hierárquica.
    3. Para cada grupo com >=3 ocorrências em >=3 meses distintos E
       desvio de valor <=15% da mediana:
       - Infere frequência pela distância média entre datas consecutivas:
         * 25-35 dias => mensal
         * 10-20 dias => quinzenal
         * 330-400 dias => anual
         * outro => 'outro'
       - Calcula mediana, min, max do valor.
       - `dia_tipico` = moda dos dias do mês (só para frequência mensal).
       - `proxima_prevista` = ultima_ocorrencia + delta_mediano.
       - Upsert em PessoalGastoRecorrente via chave (cria como 'sugerido'
         se novo).
    4. Retorna resumo: novos, atualizados, removidos por inatividade (não
       viu em >90 dias).
    """
```

### Alertas sobre recorrentes

Função `alertas_recorrentes()` retorna:

- **"faltando este mês"**: `proxima_prevista < hoje` AND nenhuma transação
  casou a chave neste mês.
- **"variação de valor"**: última transação casada teve
  `|valor - valor_tipico| / valor_tipico > 0.15`.
- **"frequência quebrada"**: última ocorrência > 2x o delta esperado.

### Tela `/pessoal/recorrentes`

- Tabela: nome, categoria, valor típico ± faixa, frequência, último, próximo
  previsto, status, ocorrências_6m, ações.
- Filtros: status, frequência, categoria.
- Ações por linha: confirmar (sugerido → ativo), pausar, cancelar, editar
  nome/categoria.
- Botão "Detectar agora" roda `detectar_recorrentes(6)` e mostra resumo.

### Widget no dashboard

Card "Recorrentes" mostra:
- Total mensal projetado (soma de `valor_tipico` de status='ativo' com
  frequência='mensal').
- Contagem de alertas ativos (faltando, variação, frequência quebrada).
- Link para `/pessoal/recorrentes`.

---

## Mudanças consolidadas de banco

| Fase | Tabela | Mudança |
|---|---|---|
| F1 | `pessoal_transacoes` | Índice GIN pg_trgm sobre `historico_completo` |
| F2 | — | — |
| F3 | `pessoal_categorias` | Nova coluna `categoria_pai_id` + índice |
| F4 | `pessoal_gastos_recorrentes` | Tabela nova |

Todas as migrations seguem regra do projeto: SQL idempotente +
`create_app()` Python com verificação before/after.

---

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Migration F3 falha ao detectar ciclo no grupo atual | Query de verificação roda antes do UPDATE; aborta com mensagem clara |
| Regras apontando para categoria-pai após migração | Permitido tecnicamente; warning no `salvar_regra` ensina usuário a mover para folha |
| Detecção F4 gera falsos positivos | Status inicial = `sugerido`; usuário confirma manualmente; filtro estatístico (desvio ≤15%) corta regras heterogêneas |
| Regra muito genérica aparece como recorrente | Filtro estatístico descarta (desvio de valor alto); se ainda passar, usuário granulariza a regra em regras mais específicas |
| Recorrente cujo identificador muda (fornecedor muda razão social ou regra é editada) | Detecção cria novo recorrente com chave nova; antigo fica inativo após 90 dias; tela permite merge manual |
| Índice pg_trgm grande | Só criado uma vez; extensão já comum em PostgreSQL moderno (Render suporta) |

## Abertos para próximo passo (writing-plans)

- Ordem detalhada de commits dentro de cada fase.
- Testes automatizados (unit + integration) para cada fase — o módulo
  atualmente não tem testes, manter consistência.
- Endpoint ou botão para rodar detecção recorrente (manual vs trigger ao
  importar CSV).
- Profundidade máxima real da hierarquia (proposto 4 níveis).
