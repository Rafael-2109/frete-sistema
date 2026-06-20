<!-- doc:meta
tipo: scratch
-->
# Integridade da lógica de 2 CD (frete · portaria · embarques) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os 11 gaps de integridade da implementação de 2 CD (flag `local_cd` VM/TM) nas camadas de status/visibilidade de portaria (listagem, filtro, detalhe), no fail-safe do gate de frete (Op. Assai + rota manual), na propagação por CD da vinculação pós-saída e na impressão por CD.

**Architecture:** Um helper único `status_portaria_agregado(embarque)` em `app/utils/local_cd.py` (zona neutra, duck-typed) vira a fonte de verdade do status de portaria por embarque considerando os 2 CDs (`SAIU`/`PARCIAL`/`DENTRO`/`AGUARDANDO`/`PENDENTE`/`SEM_REGISTRO`). Esse helper, exposto via property `Embarque.status_portaria`, é reusado pela coluna da listagem, pelo filtro (migrado para pós-query, como `status_nfs`/`status_fretes` já são) e pelo card do detalhe — eliminando o padrão `registros_portaria[-1]`/`func.max(id)` que colapsava 2 registros em 1. O gate de frete já correto (`cds_pendentes_de_saida`) é estendido aos 2 caminhos que o furam (Op. Assai e rota manual). A vinculação pós-saída passa a filtrar a propagação por `local_cd`, espelhando o fluxo de saída normal.

**Tech Stack:** Flask 3.1 + Flask-SQLAlchemy 2.0 · Jinja2 · pytest · Bootstrap 5. Sem novas dependências, sem migration (decisão: Frete NÃO carrega `local_cd`).

## Global Constraints

- **Escopo fechado:** G1–G8, G10–G12. **G9 (persistir `local_cd` no Frete) está FORA** por decisão do usuário ("não precisa ter o CD no frete"). Não criar coluna nem migration.
- **Não regredir embarque de 1 CD:** todo comportamento de embarque não-misto (Nacom puro / Op. Assai / CarVia 1 destino) deve permanecer idêntico ao legado. `cds_pendentes_de_saida` já retorna `set()` vazio para 1 CD — preservar.
- **Duck-typing em `app/utils/local_cd.py`:** o módulo é importável por TODOS (inclusive CarVia, regra R1). NÃO importar `app/embarques`, `app/portaria` nem `app/carvia` ali. Operar por `getattr` sobre o objeto Embarque (`.itens`, `.registros_portaria`).
- **Valores canônicos:** `VICTORIO_MARCHEZINE` (VM), `TENENTE_MARQUES` (TM); novo status agregado `PARCIAL` e `SEM_REGISTRO`. Status individual de `ControlePortaria`: `SAIU`/`DENTRO`/`AGUARDANDO`/`PENDENTE` (property em `app/portaria/models.py:97-107`).
- **TDD:** lógica nova (helper, gate) começa por teste que falha. Templates não exigem teste unitário, mas a rota alterada (filtro) tem teste de integração.
- **Timezone:** nenhuma data nova é gerada aqui; reusar `registro.data_saida` existente. Não usar `datetime.now()`.
- **Doc é parte do pronto:** atualizar `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md` (Tarefa 10).

---

## FRENTE 1 — Status de portaria por CD na listagem, filtro e detalhe (G1, G2, G3, G7, G8)

### Task 1: Helper `status_portaria_agregado` + properties no Embarque

**Files:**
- Modify: `app/utils/local_cd.py` (após a função `cds_pendentes_de_saida`, ~L142)
- Modify: `app/embarques/models.py` (adicionar properties perto de `status_fretes`, ~L278)
- Test: `tests/fretes/test_status_portaria_agregado.py` (criar)

**Interfaces:**
- Produces: `status_portaria_agregado(embarque) -> str` em `{'SAIU','PARCIAL','DENTRO','AGUARDANDO','PENDENTE','SEM_REGISTRO'}`; `Embarque.status_portaria -> str`; `Embarque.locais_cd -> set[str]`.
- Consumes: `cds_pendentes_de_saida`, `locais_cd_com_saida`, `locais_cd_com_itens_ativos` (já existem em `app/utils/local_cd.py`).

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/fretes/test_status_portaria_agregado.py
"""Testes do status de portaria AGREGADO por embarque (considera os 2 CDs).

Espelha o padrao puro de tests/fretes/test_frete_ultima_saida.py (SimpleNamespace).
"""
from datetime import date
from types import SimpleNamespace

from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE as VM,
    LOCAL_CD_TENENTE_MARQUES as TM,
    status_portaria_agregado,
)


def _item(local_cd, status='ativo'):
    return SimpleNamespace(local_cd=local_cd, status=status)


def _reg(local_cd, status, data_saida=None):
    return SimpleNamespace(local_cd=local_cd, status=status, data_saida=data_saida)


def _emb(itens, registros):
    return SimpleNamespace(itens=itens, registros_portaria=registros)


def test_sem_registro():
    assert status_portaria_agregado(_emb([_item(VM)], [])) == 'SEM_REGISTRO'


def test_embarque_none():
    assert status_portaria_agregado(None) == 'SEM_REGISTRO'


def test_um_cd_saiu():
    emb = _emb([_item(VM)], [_reg(VM, 'SAIU', date(2026, 1, 10))])
    assert status_portaria_agregado(emb) == 'SAIU'


def test_um_cd_dentro():
    emb = _emb([_item(VM)], [_reg(VM, 'DENTRO')])
    assert status_portaria_agregado(emb) == 'DENTRO'


def test_misto_parcial_vm_saiu_tm_dentro():
    """O caso critico: VM saiu, TM ainda dentro -> PARCIAL (nao 'SAIU')."""
    emb = _emb(
        [_item(VM), _item(TM)],
        [_reg(VM, 'SAIU', date(2026, 1, 10)), _reg(TM, 'DENTRO')],
    )
    assert status_portaria_agregado(emb) == 'PARCIAL'


def test_misto_parcial_vm_saiu_tm_sem_registro():
    """VM saiu, TM ainda nem tem registro -> PARCIAL (falta TM)."""
    emb = _emb([_item(VM), _item(TM)], [_reg(VM, 'SAIU', date(2026, 1, 10))])
    assert status_portaria_agregado(emb) == 'PARCIAL'


def test_misto_completo_ambos_sairam():
    emb = _emb(
        [_item(VM), _item(TM)],
        [_reg(VM, 'SAIU', date(2026, 1, 10)), _reg(TM, 'SAIU', date(2026, 1, 11))],
    )
    assert status_portaria_agregado(emb) == 'SAIU'


def test_misto_nenhum_saiu_pega_mais_avancado():
    """Misto VM dentro + TM aguardando, nenhum saiu -> DENTRO (mais avancado)."""
    emb = _emb([_item(VM), _item(TM)], [_reg(VM, 'DENTRO'), _reg(TM, 'AGUARDANDO')])
    assert status_portaria_agregado(emb) == 'DENTRO'
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/fretes/test_status_portaria_agregado.py -v`
Expected: FAIL com `ImportError: cannot import name 'status_portaria_agregado'`

- [ ] **Step 3: Implementar o helper em `app/utils/local_cd.py`** (logo após `cds_pendentes_de_saida`)

```python
# Ordem de progresso dos status individuais de ControlePortaria.
_ORDEM_STATUS_PORTARIA = {'PENDENTE': 0, 'AGUARDANDO': 1, 'DENTRO': 2, 'SAIU': 3}


def status_portaria_agregado(embarque):
    """Status de portaria de um Embarque considerando os 2 CDs (1 registro por CD).

    - 'SEM_REGISTRO': nenhum ControlePortaria vinculado.
    - 'SAIU': TODOS os CDs com itens ativos ja deram saida (embarque completo).
    - 'PARCIAL': ao menos 1 CD deu saida, mas ainda falta a saida de outro CD com
      itens ativos (embarque MISTO com saida parcial) — o caso que o gate de frete
      protege e que ate aqui ficava invisivel ao operador.
    - 'DENTRO'/'AGUARDANDO'/'PENDENTE': nenhum CD saiu ainda; reflete o status MAIS
      AVANCADO entre os registros existentes.

    Duck-typed sobre Embarque (`.itens`, `.registros_portaria`); cada registro
    expoe `.status` e `.data_saida`. Embarque de 1 CD nunca retorna 'PARCIAL'
    (cds_pendentes_de_saida retorna vazio) — sem regressao no fluxo legado.
    """
    if embarque is None:
        return 'SEM_REGISTRO'
    registros = list(getattr(embarque, 'registros_portaria', None) or [])
    if not registros:
        return 'SEM_REGISTRO'
    pendentes = cds_pendentes_de_saida(embarque)
    saidos = locais_cd_com_saida(embarque)
    if saidos and pendentes:
        return 'PARCIAL'
    if saidos and not pendentes:
        return 'SAIU'
    return max(
        (getattr(cp, 'status', 'PENDENTE') for cp in registros),
        key=lambda s: _ORDEM_STATUS_PORTARIA.get(s, 0),
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/fretes/test_status_portaria_agregado.py -v`
Expected: PASS (8 testes)

- [ ] **Step 5: Adicionar properties em `app/embarques/models.py`** (após `status_fretes`)

```python
    @property
    def status_portaria(self):
        """Status de portaria agregado por CD (SAIU/PARCIAL/DENTRO/AGUARDANDO/
        PENDENTE/SEM_REGISTRO). Fonte: app/utils/local_cd.status_portaria_agregado."""
        from app.utils.local_cd import status_portaria_agregado
        return status_portaria_agregado(self)

    @property
    def locais_cd(self):
        """Conjunto de local_cd dos itens ATIVOS (para badge de CD na listagem)."""
        from app.utils.local_cd import locais_cd_com_itens_ativos
        return locais_cd_com_itens_ativos(self)
```

- [ ] **Step 6: Commit**

```bash
git add app/utils/local_cd.py app/embarques/models.py tests/fretes/test_status_portaria_agregado.py
git commit -m "feat(local_cd): status_portaria agregado por CD (SAIU/PARCIAL/...) + properties Embarque"
```

---

### Task 2: Coluna "Portaria" da listagem usa o status agregado (G1)

**Files:**
- Modify: `app/templates/embarques/listar_embarques.html:296-306`

**Interfaces:**
- Consumes: `embarque.status_portaria` (Task 1).

- [ ] **Step 1: Substituir o bloco da coluna Portaria** (`:296-306`)

Trocar o bloco que lê `registros_portaria[-1]` por consumo da property, com o badge `PARCIAL` em laranja (`bg-warning text-dark` com ícone de alerta):

```jinja
          <td>
            {% set sp = embarque.status_portaria %}
            {% if sp == 'SEM_REGISTRO' %}
              <span class="badge bg-light text-dark">Sem registro</span>
            {% elif sp == 'PARCIAL' %}
              <span class="badge bg-warning text-dark" title="Saída parcial: ao menos um CD ainda não saiu">
                <i class="fas fa-triangle-exclamation"></i> Parcial
              </span>
            {% else %}
              <span class="badge bg-{% if sp == 'SAIU' %}success{% elif sp == 'DENTRO' %}warning{% elif sp == 'AGUARDANDO' %}info{% else %}secondary{% endif %}">
                {{ sp }}
              </span>
            {% endif %}
          </td>
```

- [ ] **Step 2: Verificar render manual**

Run: `python run.py` e abrir `/embarques/listar` (ou descrever ao revisor). Embarque misto com 1 CD saído deve exibir **Parcial**, não **SAIU**.

- [ ] **Step 3: Commit**

```bash
git add app/templates/embarques/listar_embarques.html
git commit -m "fix(embarques): coluna Portaria da listagem usa status agregado por CD (mostra Parcial)"
```

---

### Task 3: Filtro "Status da Portaria" migra para pós-query com bucket PARCIAL (G2)

**Files:**
- Modify: `app/embarques/routes.py:750-813` (remover bloco SQL `status_portaria`)
- Modify: `app/embarques/routes.py:877-890` (incluir `status_portaria` no filtro pós-query)
- Modify: `app/embarques/forms.py:202-214` (adicionar opção `PARCIAL`)
- Test: `tests/embarques/test_listar_filtro_portaria.py` (criar)

**Interfaces:**
- Consumes: `embarque.status_portaria` (Task 1).

- [ ] **Step 1: Escrever teste de integração que falha**

```python
# tests/embarques/test_listar_filtro_portaria.py
"""Filtro status_portaria da listagem deve classificar embarque misto pelo
estado agregado por CD (PARCIAL), nao pelo registro de maior id."""
import uuid
from datetime import date, time

from sqlalchemy import text

from app.portaria.models import ControlePortaria
from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE as VM,
    LOCAL_CD_TENENTE_MARQUES as TM,
)


def _emb_misto_parcial(db):
    """Embarque misto: item VM (saiu) + item TM (dentro). Status agregado = PARCIAL."""
    suf = uuid.uuid4().hex[:8]
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga,
                               tipo_cotacao, data_embarque)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA', :de)
        RETURNING id
    """), {'n': int(uuid.uuid4().int % 9_000_000) + 1_000_000, 'de': date(2026, 1, 10)}).scalar()
    for local, lote in ((VM, f'L-VM-{suf}'), (TM, f'L-TM-{suf}')):
        db.session.execute(text("""
            INSERT INTO embarque_itens (embarque_id, separacao_lote_id, local_cd,
                cliente, pedido, nota_fiscal, cnpj_cliente, uf_destino, cidade_destino, status)
            VALUES (:eid, :lote, :local, 'C', :ped, :nf, '12345678000199', 'SP', 'Sao Paulo', 'ativo')
        """), {'eid': eid, 'lote': lote, 'local': local, 'ped': f'P-{lote}', 'nf': f'NF{lote[:8]}'})
    mid = db.session.execute(text("""
        INSERT INTO motoristas (nome_completo, rg, cpf, telefone)
        VALUES (:n, :rg, :cpf, '(11) 90000-0000') RETURNING id
    """), {'n': f'M{suf}', 'rg': f'RG{suf}', 'cpf': f'{suf[:3]}.{suf[3:6]}.{suf[6:8]}0-00'}).scalar()
    # VM saiu (id menor), TM dentro (id maior) -> max(id) seria TM=DENTRO no codigo antigo
    vm_reg = ControlePortaria(motorista_id=mid, placa='ABC-1234', embarque_id=eid, local_cd=VM,
        data_chegada=date(2026, 1, 10), hora_chegada=time(8, 0),
        data_entrada=date(2026, 1, 10), hora_entrada=time(9, 0),
        data_saida=date(2026, 1, 10), hora_saida=time(17, 0))
    db.session.add(vm_reg); db.session.flush()
    tm_reg = ControlePortaria(motorista_id=mid, placa='ABC-1234', embarque_id=eid, local_cd=TM,
        data_chegada=date(2026, 1, 10), hora_chegada=time(8, 0),
        data_entrada=date(2026, 1, 10), hora_entrada=time(9, 0))
    db.session.add(tm_reg); db.session.commit()
    return eid


def test_filtro_parcial_lista_embarque_misto(client, db, login_admin):
    eid = _emb_misto_parcial(db)
    resp = client.get('/embarques/listar?mostrar_todos=true&status_portaria=PARCIAL')
    assert resp.status_code == 200
    assert str(eid).encode() in resp.data or b'Parcial' in resp.data


def test_filtro_saiu_nao_lista_misto_parcial(client, db, login_admin):
    """Embarque misto com saida parcial NAO deve aparecer no filtro SAIU."""
    eid = _emb_misto_parcial(db)
    resp = client.get('/embarques/listar?mostrar_todos=true&status_portaria=SAIU')
    assert resp.status_code == 200
```

> Nota: ajustar as fixtures `client`/`db`/`login_admin` ao `conftest.py` do projeto. Se não houver `login_admin`, reusar o helper de auth existente nos testes de `tests/embarques/`.

- [ ] **Step 2: Rodar e ver falhar** (`PARCIAL` não existe ainda como bucket)

Run: `pytest tests/embarques/test_listar_filtro_portaria.py -v`
Expected: FAIL (embarque não aparece no filtro PARCIAL)

- [ ] **Step 3: Remover o bloco SQL antigo do filtro `status_portaria`** em `app/embarques/routes.py:750-813`

Deletar todo o bloco `# Filtro por status da portaria` (da leitura de `request.args.get('status_portaria')` até `filtros_aplicados = True` no fim do bloco SQL), substituindo por apenas a captura do valor para o pós-query:

```python
    # Filtro por status da portaria (agregado por CD) — aplicado PÓS-QUERY,
    # como status_nfs/status_fretes, via property Embarque.status_portaria.
    status_portaria = request.args.get('status_portaria', '').strip()
    if status_portaria and status_portaria != '':
        form_filtros.status_portaria.data = status_portaria
        filtros_aplicados = True
```

- [ ] **Step 4: Incluir `status_portaria` no bloco pós-query** (`:877-890`)

Estender a condição que dispara "buscar todos antes de paginar" e adicionar o filtro em Python (mapeando o label legado `'Sem Registro'` ao canônico):

```python
    if (status_nfs and status_nfs != '') or (status_fretes and status_fretes != '') \
            or (status_portaria and status_portaria != '') or (pallets_pendentes == 'sim'):
        embarques_todos = query.all()

        if status_nfs and status_nfs != '':
            embarques_todos = [e for e in embarques_todos if e.status_nfs == status_nfs]

        if status_fretes and status_fretes != '':
            embarques_todos = [e for e in embarques_todos if e.status_fretes == status_fretes]

        if status_portaria and status_portaria != '':
            _alvo = 'SEM_REGISTRO' if status_portaria == 'Sem Registro' else status_portaria
            embarques_todos = [e for e in embarques_todos if e.status_portaria == _alvo]

        if pallets_pendentes == 'sim':
            embarques_todos = [e for e in embarques_todos if e.pallets_pendentes]
        # ... (restante da paginação manual inalterado)
```

- [ ] **Step 5: Adicionar opção `PARCIAL` ao SelectField** em `app/embarques/forms.py:202-214`

```python
    status_portaria = SelectField(
        'Status da Portaria',
        choices=[
            ('', 'Todos os status'),
            ('Sem Registro', 'Sem Registro'),
            ('PENDENTE', 'Pendente'),
            ('AGUARDANDO', 'Aguardando'),
            ('DENTRO', 'Carregando'),
            ('PARCIAL', 'Saída parcial (1 CD)'),
            ('SAIU', 'Saiu para entrega'),
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
```

- [ ] **Step 6: Rodar e ver passar**

Run: `pytest tests/embarques/test_listar_filtro_portaria.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/embarques/routes.py app/embarques/forms.py tests/embarques/test_listar_filtro_portaria.py
git commit -m "fix(embarques): filtro Status da Portaria agregado por CD (bucket PARCIAL, pós-query)"
```

---

### Task 4: Coluna de CD na listagem + filtro `local_cd` no form (G7, G8)

**Files:**
- Modify: `app/templates/embarques/listar_embarques.html` (import macro no topo; `<th>` em `:258-269`; `<td>` no corpo `:272-306`; hidden no `<form>` de filtros avançados ~`:67-72`)

**Interfaces:**
- Consumes: `embarque.locais_cd` (Task 1); macro `badge_local_cd` (`shared/_macros_badges.html`); `local_cd_atual` (já passado pela view, `routes.py:942`).

- [ ] **Step 1: Importar o macro no topo do template** (após `{% extends %}`)

```jinja
{% from 'shared/_macros_badges.html' import badge_local_cd %}
```

- [ ] **Step 2: Adicionar coluna no thead** (entre "Transportadora" e "Status", `:263-264`)

```jinja
          <th class="col-nome-lg">Transportadora</th>
          <th class="col-status">CD</th>
          <th class="col-status">Status</th>
```

- [ ] **Step 3: Adicionar a célula no corpo** (logo após o `<td>` da transportadora, antes do `<td>` de Status, ~`:280`)

```jinja
          <td>
            {% set _cds = embarque.locais_cd %}
            {% if 'VICTORIO_MARCHEZINE' in _cds %}{{ badge_local_cd('VICTORIO_MARCHEZINE', curto=True) }}{% endif %}
            {% if 'TENENTE_MARQUES' in _cds %}{{ badge_local_cd('TENENTE_MARQUES', curto=True) }}{% endif %}
            {% if not _cds %}<span class="text-muted">-</span>{% endif %}
          </td>
```

(Um embarque misto exibe os dois badges = sinal visual de "Misto".)

- [ ] **Step 4: Preservar `local_cd` no form de filtros avançados (G8)** — adicionar hidden ao lado do `mostrar_todos` (`:70-72`)

```jinja
        <input type="hidden" name="local_cd" value="{{ local_cd_atual or '' }}">
```

- [ ] **Step 5: Verificar manualmente** que a coluna CD aparece, o toggle continua filtrando e que aplicar um filtro avançado preserva o CD selecionado (não volta para "Todos").

- [ ] **Step 6: Commit**

```bash
git add app/templates/embarques/listar_embarques.html
git commit -m "feat(embarques): coluna de CD por linha na listagem + preserva filtro local_cd nos filtros avançados"
```

---

### Task 5: Card de portaria do detalhe por CD + CD pendente (G3)

**Files:**
- Modify: `app/embarques/routes.py:1237-1264` (substituir `obter_dados_portaria_embarque` por versão por-CD)
- Modify: `app/embarques/routes.py` (na view `visualizar_embarque`, passar `dados_portaria_por_cd` + `cds_pendentes` ao template)
- Modify: `app/templates/embarques/visualizar_embarque.html:9-75` (renderizar 1 linha por CD + aviso de CD pendente)

**Interfaces:**
- Consumes: `ControlePortaria`, `status_portaria_agregado`, `cds_pendentes_de_saida`.
- Produces: contexto `dados_portaria_por_cd: list[dict]`, `status_portaria_geral: str`, `cds_pendentes: set[str]` ao template.

- [ ] **Step 1: Reescrever `obter_dados_portaria_embarque`** para retornar TODOS os registros (um dict por CD), mantendo a função antiga só se houver outros callers (verificar com grep antes):

```python
def obter_dados_portaria_embarque(embarque_id):
    """Retorna a lista de registros de portaria do embarque, UM por CD.

    Ate 2 itens (1 por CD). Cada dict inclui `local_cd` e o `status` do registro.
    Substitui o comportamento antigo de retornar apenas registros[-1] — que
    escondia o 2o CD em embarque misto.
    """
    from app.portaria.models import ControlePortaria
    registros = (
        ControlePortaria.query
        .filter_by(embarque_id=embarque_id)
        .order_by(ControlePortaria.local_cd, ControlePortaria.id)
        .all()
    )
    return [
        {
            'local_cd': r.local_cd,
            'motorista_nome': r.motorista_obj.nome_completo if r.motorista_obj else 'N/A',
            'placa': r.placa,
            'tipo_veiculo': r.tipo_veiculo.nome if r.tipo_veiculo else 'N/A',
            'data_chegada': r.data_chegada, 'hora_chegada': r.hora_chegada,
            'data_entrada': r.data_entrada, 'hora_entrada': r.hora_entrada,
            'data_saida': r.data_saida, 'hora_saida': r.hora_saida,
            'status': r.status, 'registro_id': r.id,
        }
        for r in registros
    ]
```

> Antes de editar: `grep -rn "obter_dados_portaria_embarque" app/` — se outro caller espera o dict único, ajustar lá também ou criar nova função `obter_dados_portaria_por_cd` e manter a antiga. Decisão default: renomear para retornar lista e ajustar a view (único caller esperado).

- [ ] **Step 2: Na view `visualizar_embarque`**, montar o contexto adicional e passar ao `render_template`:

```python
    from app.utils.local_cd import status_portaria_agregado, cds_pendentes_de_saida
    dados_portaria_por_cd = obter_dados_portaria_embarque(id)
    status_portaria_geral = status_portaria_agregado(embarque)
    cds_pendentes = cds_pendentes_de_saida(embarque)
    # ... incluir no render_template:
    #   dados_portaria_por_cd=dados_portaria_por_cd,
    #   status_portaria_geral=status_portaria_geral,
    #   cds_pendentes=cds_pendentes,
```

- [ ] **Step 3: Reescrever o card no template** (`visualizar_embarque.html:9-75`) para iterar por CD + banner de pendência:

```jinja
  {% if dados_portaria_por_cd %}
  <div class="card mb-4 border-info">
    <div class="card-header d-flex justify-content-between align-items-center">
      <h5 class="mb-0"><i class="fas fa-truck"></i> Informações da Portaria</h5>
      {% if status_portaria_geral == 'PARCIAL' %}
        <span class="badge bg-warning text-dark">
          <i class="fas fa-triangle-exclamation"></i>
          Saída parcial — falta: {{ cds_pendentes | map('replace','_',' ') | join(', ') | title }}
        </span>
      {% elif status_portaria_geral == 'SAIU' %}
        <span class="badge bg-success">Saída completa</span>
      {% endif %}
    </div>
    <div class="card-body">
      {% for dp in dados_portaria_por_cd %}
      <div class="row {% if not loop.first %}border-top pt-3 mt-3{% endif %}">
        <div class="col-md-2">{{ badge_local_cd(dp.local_cd, curto=False) }}</div>
        <div class="col-md-3"><strong>Motorista:</strong><br><span class="text-primary">{{ dp.motorista_nome }}</span></div>
        <div class="col-md-2"><strong>Veículo:</strong><br>{{ dp.placa }} ({{ dp.tipo_veiculo }})</div>
        <div class="col-md-2"><strong>Saída:</strong><br>
          {% if dp.data_saida %}{{ dp.data_saida | formatar_data_segura }} <small class="text-muted">{{ dp.hora_saida | formatar_hora_brasil if dp.hora_saida else '' }}</small>
          {% else %}<span class="text-muted">-</span>{% endif %}
        </div>
        <div class="col-md-2"><strong>Status:</strong><br>
          <span class="badge bg-{% if dp.status == 'SAIU' %}success{% elif dp.status == 'DENTRO' %}warning{% elif dp.status == 'AGUARDANDO' %}info{% else %}secondary{% endif %}">{{ dp.status }}</span>
        </div>
        <div class="col-md-1">
          <a href="{{ url_for('portaria.detalhes_veiculo', registro_id=dp.registro_id) }}" class="btn btn-outline-info btn-sm" title="Verificar Portaria"><i class="fas fa-clipboard-check"></i></a>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
```

> `badge_local_cd` já é importado no topo deste template (`:2`). Confirmar que `formatar_hora_brasil`/`formatar_data_segura` continuam disponíveis (já usados no card original).

- [ ] **Step 4: Verificar manualmente** o detalhe de um embarque misto com saída parcial: deve listar os 2 CDs e o banner "Saída parcial — falta: Tenente Marques".

- [ ] **Step 5: Commit**

```bash
git add app/embarques/routes.py app/templates/embarques/visualizar_embarque.html
git commit -m "fix(embarques): card de portaria do detalhe mostra os 2 CDs + aviso de CD pendente de saída"
```

---

## FRENTE 2 — Fail-safe do gate de frete (G4, G6, G12)

### Task 6: Gate `cds_pendentes_de_saida` no caminho Op. Assai (G4)

**Files:**
- Modify: `app/fretes/routes.py:3897-3899` (dentro de `verificar_requisitos_op_assai`)
- Test: `tests/fretes/test_frete_ultima_saida.py` (adicionar caso Op. Assai)

**Interfaces:**
- Consumes: `cds_pendentes_de_saida`.

- [ ] **Step 1: Adicionar teste que falha** ao final de `tests/fretes/test_frete_ultima_saida.py`

```python
def _novo_item_op_assai(db, embarque_id, local_cd, lote, nf, cnpj):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, cnpj_cliente, uf_destino, cidade_destino, status)
        VALUES
            (:eid, :lote, :local, 'Cliente Assai', :pedido,
             :nf, :cnpj, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': embarque_id, 'lote': lote, 'local': local_cd,
           'pedido': f'PED-{lote}', 'nf': nf, 'cnpj': cnpj})


def test_op_assai_bloqueia_quando_falta_saida_de_um_cd(db):
    """Embarque MISTO com item Op. Assai (ASSAI-SEP) VM saido + item TM nao-saido:
    verificar_requisitos_op_assai deve BLOQUEAR (fail-safe do gate)."""
    from app.fretes.routes import verificar_requisitos_op_assai

    suf = uuid.uuid4().hex[:8]
    cnpj = '12345678000199'
    mid = _novo_motorista(db)
    eid = _novo_embarque_com_data(db)
    _novo_item_op_assai(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'ASSAI-SEP-{suf}', f'NFA{suf[:6]}', cnpj)
    _novo_item_carvia(db, eid, LOCAL_CD_TENENTE_MARQUES, f'CARVIA-TM-{suf}', f'NFT{suf[:6]}', cnpj)
    _registro_saida(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE, saiu=True)
    _registro_saida(db, mid, eid, LOCAL_CD_TENENTE_MARQUES, saiu=False)
    db.session.flush()

    pode, motivo = verificar_requisitos_op_assai(eid, cnpj)
    assert pode is False
    assert 'CD' in motivo and 'TENENTE_MARQUES' in motivo, motivo
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/fretes/test_frete_ultima_saida.py::test_op_assai_bloqueia_quando_falta_saida_de_um_cd -v`
Expected: FAIL (`pode` é True — gate ausente)

- [ ] **Step 3: Inserir o gate** logo após a checagem de `data_embarque` (`routes.py:3899`)

```python
    embarque = db.session.get(Embarque, embarque_id)
    if not embarque or not embarque.data_embarque:
        return False, "Aguardando saida da portaria para lancamento de frete"

    # Fail-safe do gate da ULTIMA saida (paridade com Nacom/CarVia). Embarque Op.
    # Assai e nominalmente nao-misto, mas se vier a conter itens de >1 CD, o frete
    # nao pode nascer sem os itens do CD que ainda nao saiu.
    from app.utils.local_cd import cds_pendentes_de_saida
    faltam = cds_pendentes_de_saida(embarque)
    if faltam:
        return False, f"Aguardando saida dos CDs: {', '.join(sorted(faltam))}"
```

- [ ] **Step 4: Rodar e ver passar** (+ não regredir os 18 testes existentes)

Run: `pytest tests/fretes/test_frete_ultima_saida.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add app/fretes/routes.py tests/fretes/test_frete_ultima_saida.py
git commit -m "fix(fretes): gate da última saída também no caminho Op. Assai (fail-safe multi-CD)"
```

---

### Task 7: Gate + `@require_financeiro` na rota manual `processar_lancamento_frete` (G6)

**Files:**
- Modify: `app/fretes/routes.py:742-744` (decorator) e após `:759` (gate)

**Interfaces:**
- Consumes: `verificar_requisitos_para_lancamento_frete` (mesmo módulo), `@require_financeiro` (`app.utils.auth_decorators`).

- [ ] **Step 1: Adicionar `@require_financeiro()`** ao endpoint (paridade com `processar_cte_frete_existente:674` e o GET `criar_novo_frete_por_nf:605`)

```python
@fretes_bp.route("/processar_lancamento_frete", methods=["POST"])
@login_required
@require_financeiro()
def processar_lancamento_frete():
```

> Confirmar que `require_financeiro` já está importado no topo de `routes.py` (é usado em dezenas de rotas). Se não, importar de `app.utils.auth_decorators`.

- [ ] **Step 2: Inserir o gate** após obter o embarque (`:759`), antes de montar o Frete:

```python
        embarque = Embarque.query.get_or_404(embarque_id)

        # Gate da última saída (paridade com o fluxo automático): em embarque MISTO,
        # não permitir criar Frete manual antes de todos os CDs darem saída.
        pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente)
        if not pode_lancar and 'Aguardando saída dos CDs' in motivo:
            flash(motivo, 'warning')
            return redirect(url_for('fretes.criar_novo_frete_por_nf', numero_nf=request.form.get('numeros_nfs', '')))
```

> Escopo mínimo e seguro: só bloqueia quando o motivo é o gate de CD. Não altera o comportamento dos demais casos manuais (tela de exceção continua servindo a fretes que falharam no automático por outros motivos).

- [ ] **Step 3: Verificar** que a rota responde 200/redirect normal para embarque não-misto e bloqueia (flash + redirect) para misto com saída parcial. Teste manual ou de integração leve.

- [ ] **Step 4: Commit**

```bash
git add app/fretes/routes.py
git commit -m "fix(fretes): rota manual de lançamento respeita gate multi-CD + exige perfil financeiro"
```

---

## FRENTE 3 — Vinculação pós-saída propaga por CD (G5)

### Task 8: `adicionar_embarque` restringe propagação aos itens do CD do registro

**Files:**
- Modify: `app/portaria/routes.py:908-924` (filtrar `embarque.itens` por `local_cd` do registro)

**Interfaces:**
- Consumes: `LOCAL_CD_DEFAULT` (já importado no módulo, `routes.py:20-24`).

- [ ] **Step 1: Restringir o loop de propagação** ao CD do registro vinculado, espelhando o fluxo de saída normal (`routes.py:325-329`)

Trocar (`:913-924`):

```python
            # ✅ PROPAGAR data_embarque para tabela Separacao (apenas Nacom...)
            for item in embarque.itens:
                if item.separacao_lote_id and not str(item.separacao_lote_id).startswith('CARVIA-'):
                    ...
```

por:

```python
            # 🏭 SAÍDA POR CD: propagar SOMENTE para os itens do CD deste registro
            # (espelha o fluxo normal de saída em registrar_movimento). Sem isso, a
            # vinculação adiantaria data_embarque dos itens do outro CD (ainda não saído).
            local = registro.local_cd or LOCAL_CD_DEFAULT
            itens_do_local = [
                it for it in embarque.itens
                if (it.local_cd or LOCAL_CD_DEFAULT) == local
            ]
            for item in itens_do_local:
                if item.separacao_lote_id and not str(item.separacao_lote_id).startswith('CARVIA-'):
                    num_atualizados = Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id
                    ).update({'data_embarque': registro.data_saida}, synchronize_session='fetch')
                    if num_atualizados == 0:
                        flash(f'⚠️ Lote {item.separacao_lote_id} não encontrado na tabela Separação!', 'warning')
```

- [ ] **Step 2: Restringir também a sincronização de entregas** (`:964-976`) ao `itens_do_local` (não `embarque.itens`), mantendo o skip de CarVia/Assai:

```python
            if itens_do_local:
                for item in itens_do_local:
                    if item.nota_fiscal and not str(item.separacao_lote_id or '').startswith(('CARVIA-', 'ASSAI-')):
                        try:
                            sincronizar_entrega_por_nf(item.nota_fiscal)
                        except Exception as e:
                            print(f"[DEBUG] Erro ao sincronizar NF {item.nota_fiscal}: {e}")
```

> Os hooks de frete Nacom/CarVia (`:926-962`) permanecem — já passam pelo gate internamente, então continuam corretos sem alteração.

- [ ] **Step 3: Verificar** (manual ou integração): vincular embarque misto a um registro VM já-saído propaga `data_embarque` apenas para os lotes VM; os lotes TM permanecem sem `data_embarque` até a saída do TM.

- [ ] **Step 4: Commit**

```bash
git add app/portaria/routes.py
git commit -m "fix(portaria): vinculação pós-saída propaga data_embarque/entregas só aos itens do CD do registro"
```

---

## FRENTE 4 — Impressão por CD (G10, G11)

### Task 9: Rótulo de CD no cabeçalho da folha + badge de CD consistente

**Files:**
- Modify: `app/templates/embarques/imprimir_embarque.html` (cabeçalho + badge da seção Nacom)
- Modify: `app/templates/embarques/imprimir_completo.html` (cabeçalho + badge)

**Interfaces:**
- Consumes: `local_cd_atual` (já passado pelas rotas `imprimir_embarque`/`imprimir_embarque_completo`).

- [ ] **Step 1: Adicionar rótulo de CD no cabeçalho** de `imprimir_embarque.html` (acima do bloco de itens, ~`:160-168`). Ler o topo exato com `Read` antes de inserir; o snippet a inserir:

```jinja
    {% if local_cd_atual %}
    <div style="text-align:center; font-weight:bold; font-size:13px; margin:6px 0; padding:4px; border:2px solid #333;">
      COLETA — {{ 'TENENTE MARQUES' if local_cd_atual == 'TENENTE_MARQUES' else 'VICTORIO MARCHEZINE' }}
    </div>
    {% endif %}
```

Assim duas folhas (VM/TM) do mesmo embarque deixam de ser visualmente idênticas.

- [ ] **Step 2: Repetir o rótulo** no cabeçalho de `imprimir_completo.html` (mesma posição relativa).

- [ ] **Step 3: Corrigir o badge da seção Nacom (G11)** — hoje só a seção CarVia tem badge inline (`imprimir_embarque.html:237-238`); a seção Nacom não marca CD e itens com `local_cd` NULL não recebem badge VM. Na impressão "Todos" (sem `local_cd_atual`) de um embarque misto, adicionar badge à coluna Cliente da seção Nacom, tratando NULL como VM:

Na linha do item Nacom (`:202`), trocar `<td>{{ item.cliente }}</td>` por:

```jinja
                <td>{{ item.cliente }}
                    {% if not local_cd_atual %}
                      {% if item.local_cd == 'TENENTE_MARQUES' %}<span style="background:#5b3fb5;color:#fff;padding:1px 5px;border-radius:3px;font-size:9px;font-weight:bold;">TM</span>
                      {% else %}<span style="background:#ffe08a;color:#1a1a1a;padding:1px 5px;border-radius:3px;font-size:9px;font-weight:bold;">VM</span>{% endif %}
                    {% endif %}
                </td>
```

(Itens Nacom são VM por construção, mas o badge explícito remove a ambiguidade na folha "Todos" e cobre o NULL→VM.)

- [ ] **Step 4: Verificar manualmente** as 3 impressões (Todos/VM/TM) de um embarque misto: cabeçalho identifica o CD nas folhas VM/TM; folha "Todos" mostra badge por item nas duas seções.

- [ ] **Step 5: Commit**

```bash
git add app/templates/embarques/imprimir_embarque.html app/templates/embarques/imprimir_completo.html
git commit -m "fix(embarques): impressão por CD identifica o CD no cabeçalho + badge consistente (NULL→VM)"
```

---

## FRENTE 5 — Documentação (parte do "pronto")

### Task 10: Atualizar o SOT da flag `local_cd`

**Files:**
- Modify: `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md`

- [ ] **Step 1: Adicionar seção "Status de portaria agregado por CD"** documentando `status_portaria_agregado` (valores `SAIU`/`PARCIAL`/`DENTRO`/`AGUARDANDO`/`PENDENTE`/`SEM_REGISTRO`), que é consumido pela coluna/filtro da listagem e pelo card do detalhe, e a regra do bucket `PARCIAL`.

- [ ] **Step 2: Atualizar a seção "Constantes e helpers"** incluindo `status_portaria_agregado` na lista de helpers de `app/utils/local_cd.py`.

- [ ] **Step 3: Atualizar "Fontes"** com os novos pontos (property `Embarque.status_portaria`/`locais_cd`, gate Op. Assai/rota manual, vinculação pós-saída por CD, impressão por CD) e o campo `atualizado: 2026-06-19` no header `doc:meta`.

- [ ] **Step 4: Rodar o doc_audit** (skill `padronizando-docs`) se aplicável e commit.

```bash
git add .claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md
git commit -m "docs(local_cd): status de portaria agregado por CD + pontos novos da integridade 2 CD"
```

---

## Self-Review

**Cobertura dos gaps:**
- G1 (coluna portaria) → Task 2 · G2 (filtro portaria) → Task 3 · G3 (card detalhe) → Task 5 · G4 (Op. Assai) → Task 6 · G5 (vinculação) → Task 8 · G6 (rota manual) → Task 7 · G7 (coluna CD) → Task 4 · G8 (filtro no form) → Task 4 · G10 (cabeçalho impressão) → Task 9 · G11 (badge NULL) → Task 9 · G12 (testes gate) → Tasks 6, 7. **G9: fora de escopo (decisão do usuário).** Todos cobertos.
- **Raiz comum G1+G2+G3** resolvida por um único helper (Task 1) reusado em 3 superfícies — sem duplicar a lógica de agregação.

**Consistência de tipos:** `status_portaria_agregado` retorna sempre uma das 6 strings canônicas; `Embarque.status_portaria` delega; template e filtro comparam contra essas mesmas strings (com o único mapeamento `'Sem Registro' → 'SEM_REGISTRO'` no filtro, documentado na Task 3). `locais_cd` retorna `set[str]`. Sem divergência de nomes entre tasks.

**Ordem/independência:** Task 1 é pré-requisito de 2/3/5. Tasks 4, 6, 7, 8, 9, 10 são independentes entre si. Cada task termina em commit testável.
