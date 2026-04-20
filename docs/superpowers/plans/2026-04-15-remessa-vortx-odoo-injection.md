# Remessa VORTX — Injeção Direta no Odoo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar CNAB 400 VORTX (banco 310) a partir de títulos pendentes no Odoo e injetar o arquivo diretamente nos modelos Odoo via XML-RPC, dispensando o módulo CIEL IT que levaria 2 meses.

**Architecture:** State machine com checkpoints para resiliência contra falhas Odoo (502, timeout, deploy). O sistema busca títulos no Odoo, gera o CNAB localmente, e injeta em 3 etapas idempotentes (create escritural → create remessa → write títulos). Cada etapa salva checkpoint no banco local. Retry automático com backoff exponencial.

**Tech Stack:** Flask/SQLAlchemy, XML-RPC (Odoo), CNAB 400 posicional, PostgreSQL sequences.

---

## Contexto Técnico (leia antes de codar)

### Dados NACOM na VORTX (confirmados pelo banco)

| Campo | Valor |
|-------|-------|
| Banco | `310` |
| Nome banco | `VORTX DTVM` (15 chars padded) |
| Agência | `0001` |
| Conta corrente (sem DV) | `00109575` |
| DV da conta | `7` |
| Convênio | `1095757` |
| Carteira | `21` |

### Modelos Odoo envolvidos

| Modelo Odoo | Operação | Para que |
|-------------|----------|---------|
| `l10n_br_ciel_it_account.arquivo.cobranca.escritural` | CREATE + WRITE | Armazenar arquivo + FK dos títulos |
| `l10n_br_ciel_it_account.arquivo.cobranca.remessa` | CREATE | Aparecer na tela nova do Odoo (action 1990) |
| `account.move.line` | SEARCH_READ + WRITE | Buscar títulos pendentes + marcar como emitidos |
| `l10n_br_ciel_it_account.tipo.cobranca` | READ | Config da carteira (id=10 FB, id=11 CD) |

### IDs fixos Odoo

| ID | Nome | Company |
|----|------|---------|
| 10 | BOLETO VORTX - FB | 1 (NACOM GOYA - FB) |
| 11 | BOLETO VORTX - CD | 4 (NACOM GOYA - CD) |
| 1068 | Journal VORTX GRAFENO | compartilhado |

### DAC — Módulo 11 base 7 (validado pelo banco, spec VORTX página 13)

Concatena `carteira` (2 dígitos) + `nosso_numero` (11 dígitos) = 13 dígitos.
Pesos ciclando da direita para esquerda: `2, 3, 4, 5, 6, 7`.
`DAC = 11 - (soma % 11)`. Se resto=0 ou DAC>=10, DAC=0.

Exemplos validados: NN `00000000001` + cart `21` → DAC `9`. NN `00000000002` + cart `21` → DAC `7`.

### Padrões obrigatórios do projeto

- **Imports Odoo**: LAZY dentro de métodos, NUNCA top-level
- **Valores monetários**: `Numeric(15, 2)`, NUNCA Float
- **DateTime**: `default=agora_utc_naive` de `app.utils.timezone`
- **JSON em modelos financeiros**: `db.Text` + helpers `set_X()`/`get_X()`, NÃO JSONB direto
- **Routes**: `@login_required` + decorator custom, imports lazy dentro das funções
- **Migrations**: DOIS artefatos (Python + SQL), idempotentes
- **Flash messages**: `flash('mensagem', 'success'|'danger'|'warning')`
- **AJAX responses**: `{'success': True/False, 'message': '...', 'error': '...'}`

---

## File Structure

### Novos arquivos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `app/financeiro/services/remessa_vortx/dac_calculator.py` | Cálculo DAC mod 11 base 7 (puro, sem dependências) |
| `app/financeiro/services/remessa_vortx/layout_vortx.py` | Constantes posicionais CNAB 400 VORTX |
| `app/financeiro/services/remessa_vortx/cnab_generator.py` | Gera CNAB 400 a partir de lista de boletos |
| `app/financeiro/services/remessa_vortx/odoo_injector.py` | State machine: busca títulos, injeta no Odoo |
| `app/financeiro/services/remessa_vortx/nosso_numero_service.py` | Aloca nosso número via PG sequence |
| `app/financeiro/services/remessa_vortx/__init__.py` | Exports |
| `app/financeiro/routes/remessa_vortx.py` | Rotas Flask (listagem, geração, download, retomar) |
| `app/templates/financeiro/remessa_vortx/listar_titulos.html` | Tela 1: títulos pendentes + seleção |
| `app/templates/financeiro/remessa_vortx/historico.html` | Tela 2: remessas geradas + status + download |
| `tests/financeiro/test_dac_calculator.py` | TDD: DAC mod 11 base 7 |
| `tests/financeiro/test_cnab_generator.py` | TDD: gera CNAB 400 VORTX válido |
| `scripts/migrations/adicionar_remessa_vortx.py` | Migration Python |
| `scripts/migrations/adicionar_remessa_vortx.sql` | Migration SQL |

### Arquivos a modificar

| Arquivo | O que muda |
|---------|-----------|
| `app/auth/models.py` | +campo `sistema_remessa_vortx` + método `pode_gerar_remessa_vortx()` |
| `app/financeiro/models.py` | +modelo `RemessaVortxCache` |
| `app/financeiro/routes/__init__.py` | +import `remessa_vortx` |
| `app/templates/base.html` | +link menu "Remessas VORTX" no dropdown Financeiro |
| `app/utils/auth_decorators.py` | +decorator `require_remessa_vortx()` |

---

## Tasks

### Task 1: Migration + Modelo RemessaVortxCache + Flag Usuário

**Files:**
- Modify: `app/auth/models.py:28` (adicionar campo + método)
- Modify: `app/financeiro/models.py` (adicionar modelo no final)
- Modify: `app/utils/auth_decorators.py:90` (adicionar decorator)
- Create: `scripts/migrations/adicionar_remessa_vortx.py`
- Create: `scripts/migrations/adicionar_remessa_vortx.sql`

- [ ] **Step 1: Adicionar campo e método no modelo Usuario**

Em `app/auth/models.py`, após a linha `acesso_comissao_carvia = ...` (linha ~28):

```python
sistema_remessa_vortx = db.Column(db.Boolean, default=False, nullable=False)
```

Na seção de métodos de permissão do mesmo modelo, adicionar:

```python
def pode_gerar_remessa_vortx(self):
    return self.sistema_remessa_vortx or self.perfil == 'administrador'
```

- [ ] **Step 2: Adicionar decorator em auth_decorators.py**

Em `app/utils/auth_decorators.py`, após `require_carvia()` (~linha 90):

```python
def require_remessa_vortx():
    return require_permission('pode_gerar_remessa_vortx')
```

- [ ] **Step 3: Criar modelo RemessaVortxCache em models.py**

No final de `app/financeiro/models.py`, adicionar:

```python
class RemessaVortxCache(db.Model):
    __tablename__ = 'remessa_vortx_cache'

    id = db.Column(db.Integer, primary_key=True)

    etapa = db.Column(db.String(30), default='CNAB_GERADO', nullable=False)
    tentativas = db.Column(db.Integer, default=0)
    ultimo_erro = db.Column(db.Text)

    odoo_escritural_id = db.Column(db.Integer)
    odoo_remessa_id = db.Column(db.Integer)
    move_line_ids_marcados = db.Column(db.Text)
    move_line_ids_pendentes = db.Column(db.Text)

    company_id_odoo = db.Column(db.Integer, nullable=False)
    tipo_cobranca_id_odoo = db.Column(db.Integer, nullable=False)
    nome_arquivo = db.Column(db.String(100), nullable=False)
    qtd_boletos = db.Column(db.Integer, nullable=False)
    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    nosso_numero_inicial = db.Column(db.Integer, nullable=False)
    nosso_numero_final = db.Column(db.Integer, nullable=False)
    arquivo_cnab = db.Column(db.LargeBinary, nullable=False)
    mapa_nn_move_line = db.Column(db.Text)

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    concluido_em = db.Column(db.DateTime)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    ETAPAS_VALIDAS = ['CNAB_GERADO', 'ESCRITURAL_OK', 'REMESSA_OK', 'TITULOS_OK', 'CONCLUIDO',
                      'FALHA_ESCRITURAL', 'FALHA_REMESSA', 'FALHA_TITULOS']

    def set_move_line_ids_marcados(self, ids):
        import json
        self.move_line_ids_marcados = json.dumps(ids, default=str) if ids else None

    def get_move_line_ids_marcados(self):
        import json
        return json.loads(self.move_line_ids_marcados) if self.move_line_ids_marcados else []

    def set_move_line_ids_pendentes(self, ids):
        import json
        self.move_line_ids_pendentes = json.dumps(ids, default=str) if ids else None

    def get_move_line_ids_pendentes(self):
        import json
        return json.loads(self.move_line_ids_pendentes) if self.move_line_ids_pendentes else []

    def set_mapa_nn_move_line(self, mapa):
        import json
        self.mapa_nn_move_line = json.dumps(mapa, default=str) if mapa else None

    def get_mapa_nn_move_line(self):
        import json
        return json.loads(self.mapa_nn_move_line) if self.mapa_nn_move_line else {}

    @property
    def is_falha(self):
        return self.etapa.startswith('FALHA_')

    @property
    def is_concluido(self):
        return self.etapa == 'CONCLUIDO'

    @property
    def pode_retomar(self):
        return self.is_falha or self.etapa in ('CNAB_GERADO', 'ESCRITURAL_OK', 'REMESSA_OK')
```

Certificar que `agora_utc_naive` está importado no topo do models.py (já deve estar).

- [ ] **Step 4: Criar migration Python**

Criar `scripts/migrations/adicionar_remessa_vortx.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_tabela_existe(conn, tabela):
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :tabela
        )
    """), {'tabela': tabela})
    return result.scalar()


def verificar_sequence_existe(conn, nome):
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = :nome
        )
    """), {'nome': nome})
    return result.scalar()


def executar():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        # 1) Campo sistema_remessa_vortx na tabela usuarios
        if not verificar_coluna_existe(conn, 'usuarios', 'sistema_remessa_vortx'):
            conn.execute(text("""
                ALTER TABLE usuarios
                ADD COLUMN sistema_remessa_vortx BOOLEAN NOT NULL DEFAULT FALSE
            """))
            print("✓ Campo sistema_remessa_vortx adicionado em usuarios")
        else:
            print("→ Campo sistema_remessa_vortx já existe")

        # 2) Tabela remessa_vortx_cache
        if not verificar_tabela_existe(conn, 'remessa_vortx_cache'):
            conn.execute(text("""
                CREATE TABLE remessa_vortx_cache (
                    id SERIAL PRIMARY KEY,
                    etapa VARCHAR(30) NOT NULL DEFAULT 'CNAB_GERADO',
                    tentativas INTEGER DEFAULT 0,
                    ultimo_erro TEXT,
                    odoo_escritural_id INTEGER,
                    odoo_remessa_id INTEGER,
                    move_line_ids_marcados TEXT,
                    move_line_ids_pendentes TEXT,
                    company_id_odoo INTEGER NOT NULL,
                    tipo_cobranca_id_odoo INTEGER NOT NULL,
                    nome_arquivo VARCHAR(100) NOT NULL,
                    qtd_boletos INTEGER NOT NULL,
                    valor_total NUMERIC(15, 2) NOT NULL,
                    nosso_numero_inicial INTEGER NOT NULL,
                    nosso_numero_final INTEGER NOT NULL,
                    arquivo_cnab BYTEA NOT NULL,
                    mapa_nn_move_line TEXT,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por_id INTEGER REFERENCES usuarios(id),
                    concluido_em TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX idx_rvx_etapa ON remessa_vortx_cache(etapa)"))
            conn.execute(text("CREATE INDEX idx_rvx_company ON remessa_vortx_cache(company_id_odoo)"))
            print("✓ Tabela remessa_vortx_cache criada")
        else:
            print("→ Tabela remessa_vortx_cache já existe")

        # 3) Sequence para nosso número VORTX
        if not verificar_sequence_existe(conn, 'nosso_numero_vortx_seq'):
            conn.execute(text("CREATE SEQUENCE nosso_numero_vortx_seq START 1"))
            print("✓ Sequence nosso_numero_vortx_seq criada (start=1, ajustar depois)")
        else:
            print("→ Sequence nosso_numero_vortx_seq já existe")

        db.session.commit()
        print("\n✅ Migration adicionar_remessa_vortx concluída!")


if __name__ == '__main__':
    executar()
```

- [ ] **Step 5: Criar migration SQL**

Criar `scripts/migrations/adicionar_remessa_vortx.sql`:

```sql
-- Migration: adicionar_remessa_vortx
-- Tabela cache + sequence para remessas VORTX

-- 1) Campo na tabela usuarios
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS sistema_remessa_vortx BOOLEAN NOT NULL DEFAULT FALSE;

-- 2) Tabela cache
CREATE TABLE IF NOT EXISTS remessa_vortx_cache (
    id SERIAL PRIMARY KEY,
    etapa VARCHAR(30) NOT NULL DEFAULT 'CNAB_GERADO',
    tentativas INTEGER DEFAULT 0,
    ultimo_erro TEXT,
    odoo_escritural_id INTEGER,
    odoo_remessa_id INTEGER,
    move_line_ids_marcados TEXT,
    move_line_ids_pendentes TEXT,
    company_id_odoo INTEGER NOT NULL,
    tipo_cobranca_id_odoo INTEGER NOT NULL,
    nome_arquivo VARCHAR(100) NOT NULL,
    qtd_boletos INTEGER NOT NULL,
    valor_total NUMERIC(15, 2) NOT NULL,
    nosso_numero_inicial INTEGER NOT NULL,
    nosso_numero_final INTEGER NOT NULL,
    arquivo_cnab BYTEA NOT NULL,
    mapa_nn_move_line TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id),
    concluido_em TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rvx_etapa ON remessa_vortx_cache(etapa);
CREATE INDEX IF NOT EXISTS idx_rvx_company ON remessa_vortx_cache(company_id_odoo);

-- 3) Sequence nosso número
CREATE SEQUENCE IF NOT EXISTS nosso_numero_vortx_seq START 1;
```

- [ ] **Step 6: Rodar migration no banco local**

Run: `source .venv/bin/activate && python scripts/migrations/adicionar_remessa_vortx.py`
Expected: 3 linhas "✓" confirmando criação.

- [ ] **Step 7: Commit**

```bash
git add app/auth/models.py app/financeiro/models.py app/utils/auth_decorators.py scripts/migrations/adicionar_remessa_vortx.py scripts/migrations/adicionar_remessa_vortx.sql
git commit -m "feat(remessa-vortx): model RemessaVortxCache + flag usuario + migration + sequence"
```

---

### Task 2: DAC Calculator (TDD)

**Files:**
- Create: `app/financeiro/services/remessa_vortx/__init__.py`
- Create: `app/financeiro/services/remessa_vortx/dac_calculator.py`
- Create: `tests/financeiro/test_dac_calculator.py`

- [ ] **Step 1: Criar diretório e __init__.py**

```bash
mkdir -p app/financeiro/services/remessa_vortx
mkdir -p tests/financeiro
```

Criar `app/financeiro/services/remessa_vortx/__init__.py`:

```python
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero
```

- [ ] **Step 2: Criar arquivo de teste vazio e __init__.py de tests**

Criar `tests/__init__.py` e `tests/financeiro/__init__.py` (vazios, se não existirem).

Criar `tests/financeiro/test_dac_calculator.py`:

```python
import pytest
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero


class TestCalcularDacNossoNumero:
    def test_nn_001_carteira_21_retorna_9(self):
        assert calcular_dac_nosso_numero('21', '00000000001') == '9'

    def test_nn_002_carteira_21_retorna_7(self):
        assert calcular_dac_nosso_numero('21', '00000000002') == '7'

    def test_nn_003_carteira_21_retorna_5(self):
        assert calcular_dac_nosso_numero('21', '00000000003') == '5'

    def test_nn_006_carteira_21_retorna_0(self):
        assert calcular_dac_nosso_numero('21', '00000000006') == '0'

    def test_nn_010_carteira_21_retorna_8(self):
        assert calcular_dac_nosso_numero('21', '00000000010') == '8'

    def test_nn_020_carteira_21_retorna_5(self):
        assert calcular_dac_nosso_numero('21', '00000000020') == '5'

    def test_carteira_invalida_levanta_erro(self):
        with pytest.raises(ValueError, match='carteira deve ter 2 dígitos'):
            calcular_dac_nosso_numero('1', '00000000001')

    def test_nosso_numero_invalido_levanta_erro(self):
        with pytest.raises(ValueError, match='nosso_numero deve ter 11 dígitos'):
            calcular_dac_nosso_numero('21', '123')

    def test_retorno_e_string(self):
        result = calcular_dac_nosso_numero('21', '00000000001')
        assert isinstance(result, str)
        assert len(result) == 1
```

- [ ] **Step 3: Rodar testes para ver que falham**

Run: `source .venv/bin/activate && python -m pytest tests/financeiro/test_dac_calculator.py -v`
Expected: FAIL (ImportError — módulo não existe ainda).

- [ ] **Step 4: Implementar calcular_dac_nosso_numero**

Criar `app/financeiro/services/remessa_vortx/dac_calculator.py`:

```python
def calcular_dac_nosso_numero(carteira: str, nosso_numero: str) -> str:
    if len(carteira) != 2 or not carteira.isdigit():
        raise ValueError('carteira deve ter 2 dígitos numéricos')
    if len(nosso_numero) != 11 or not nosso_numero.isdigit():
        raise ValueError('nosso_numero deve ter 11 dígitos numéricos')

    full = carteira + nosso_numero
    digits = [int(c) for c in full]
    digits.reverse()
    weights = [2, 3, 4, 5, 6, 7]
    total = sum(d * weights[i % 6] for i, d in enumerate(digits))
    remainder = total % 11
    if remainder == 0:
        return '0'
    dac = 11 - remainder
    return '0' if dac >= 10 else str(dac)
```

- [ ] **Step 5: Rodar testes para ver que passam**

Run: `source .venv/bin/activate && python -m pytest tests/financeiro/test_dac_calculator.py -v`
Expected: 9 passed.

- [ ] **Step 6: Commit**

```bash
git add app/financeiro/services/remessa_vortx/ tests/financeiro/
git commit -m "feat(remessa-vortx): DAC calculator mod 11 base 7 com testes"
```

---

### Task 3: Layout VORTX + CNAB Generator

**Files:**
- Create: `app/financeiro/services/remessa_vortx/layout_vortx.py`
- Create: `app/financeiro/services/remessa_vortx/cnab_generator.py`
- Create: `tests/financeiro/test_cnab_generator.py`

- [ ] **Step 1: Criar layout_vortx.py com constantes posicionais**

Criar `app/financeiro/services/remessa_vortx/layout_vortx.py`:

```python
BANCO = '310'
BANCO_NOME = 'VORTX DTVM'
RAZAO_SOCIAL = 'NACOM GOYA INDUSTRIA E COMERCI'
CONVENIO = '1095757'
AGENCIA = '0001'
CONTA_SEM_DV = '00109575'
CONTA_DV = '7'
CARTEIRA = '21'
SISTEMA_ID = 'MX'
ESPECIE_DUPLICATA = '01'
OCORRENCIA_REMESSA = '01'
ACEITE = 'N'

TIPO_COBRANCA_IDS = {
    1: 10,  # NACOM FB → BOLETO VORTX - FB
    4: 11,  # NACOM CD → BOLETO VORTX - CD
}

COMPANY_NAMES = {
    1: 'NACOM GOYA - FB',
    4: 'NACOM GOYA - CD',
}

CONTA_GRAFENO_HEADER = CONVENIO.rjust(20, '0')

def id_empresa_detalhe():
    return '0' + CARTEIRA.zfill(3) + AGENCIA.zfill(5) + CONTA_SEM_DV[-7:] + CONTA_DV

LINE_WIDTH = 400
SEPARATOR = '\r\n'
```

- [ ] **Step 2: Criar teste do gerador CNAB**

Criar `tests/financeiro/test_cnab_generator.py`:

```python
import pytest
from app.financeiro.services.remessa_vortx.cnab_generator import CnabVortxGenerator


class TestCnabVortxGenerator:
    def _boleto_exemplo(self):
        return {
            'nf_documento': '146774/002',
            'vencimento': '110526',
            'valor_centavos': '0000000508836',
            'emissao': '060426',
            'tipo_inscricao': '02',
            'cnpj_cpf': '53779178000149',
            'nome_sacado': 'P P ALIM E REPRESENTACOES LTDA EPP',
            'endereco': 'Q ASR NE 25, 212 NORTE, ALAMEDA CENTRAL,',
            'cep_prefixo': '77006',
            'cep_sufixo': '308',
            'email': 'pepalimentos07@gmail.com',
            'nosso_numero': '00000000001',
            'nosso_numero_dac': '9',
        }

    def test_gera_arquivo_com_header_detalhe_trailer(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        linhas = gen.gerar()
        assert len(linhas) == 4  # header + detalhe + email + trailer

    def test_todas_linhas_tem_400_chars(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        linhas = gen.gerar()
        for i, linha in enumerate(linhas):
            assert len(linha) == 400, f'Linha {i} tem {len(linha)} chars'

    def test_header_banco_310(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        header = gen.gerar()[0]
        assert header[76:79] == '310'
        assert header[79:94].strip() == 'VORTX DTVM'

    def test_header_conta_grafeno(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        header = gen.gerar()[0]
        assert header[26:46] == '00000000000001095757'

    def test_detalhe_id_empresa(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        detalhe = gen.gerar()[1]
        assert detalhe[20:37] == '00210000101095757'

    def test_detalhe_nosso_numero_e_dac(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        detalhe = gen.gerar()[1]
        assert detalhe[70:81] == '00000000001'
        assert detalhe[81] == '9'

    def test_detalhe_valor(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        detalhe = gen.gerar()[1]
        assert detalhe[126:139] == '0000000508836'

    def test_trailer_tipo_9(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        linhas = gen.gerar()
        trailer = linhas[-1]
        assert trailer[0] == '9'
        assert trailer[1:394].strip() == ''

    def test_sequencial_correto(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        linhas = gen.gerar()
        for i, linha in enumerate(linhas):
            seq = int(linha[394:400])
            assert seq == i + 1

    def test_sem_boleto_levanta_erro(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        with pytest.raises(ValueError, match='Nenhum boleto'):
            gen.gerar()

    def test_gerar_bytes_retorna_binario(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        gen.adicionar_boleto(self._boleto_exemplo())
        raw = gen.gerar_bytes()
        assert isinstance(raw, bytes)
        assert b'310' in raw
        assert b'\r\n' in raw

    def test_boleto_sem_email_gera_sem_registro_2(self):
        gen = CnabVortxGenerator(data_geracao='150426', seq_remessa=1)
        b = self._boleto_exemplo()
        b['email'] = ''
        gen.adicionar_boleto(b)
        linhas = gen.gerar()
        assert len(linhas) == 3  # header + detalhe + trailer (sem email)
```

- [ ] **Step 3: Rodar testes para ver que falham**

Run: `source .venv/bin/activate && python -m pytest tests/financeiro/test_cnab_generator.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implementar CnabVortxGenerator**

Criar `app/financeiro/services/remessa_vortx/cnab_generator.py`:

```python
from app.financeiro.services.remessa_vortx.layout_vortx import (
    BANCO, BANCO_NOME, RAZAO_SOCIAL, CONTA_GRAFENO_HEADER,
    SISTEMA_ID, ESPECIE_DUPLICATA, OCORRENCIA_REMESSA, ACEITE,
    LINE_WIDTH, SEPARATOR, id_empresa_detalhe,
)


class CnabVortxGenerator:
    def __init__(self, data_geracao: str, seq_remessa: int = 1):
        self.data_geracao = data_geracao
        self.seq_remessa = seq_remessa
        self.boletos = []

    def adicionar_boleto(self, boleto: dict):
        self.boletos.append(boleto)

    def _pad(self, valor, tamanho, char=' ', align='left'):
        s = str(valor)[:tamanho]
        if align == 'left':
            return s.ljust(tamanho, char)
        return s.rjust(tamanho, char)

    def _montar_header(self, seq):
        h = [' '] * LINE_WIDTH
        h[0] = '0'
        h[1] = '1'
        h[2:9] = list('REMESSA')
        h[9:11] = list('01')
        h[11:26] = list(self._pad('COBRANCA', 15))
        h[26:46] = list(CONTA_GRAFENO_HEADER)
        h[46:76] = list(self._pad(RAZAO_SOCIAL, 30))
        h[76:79] = list(BANCO)
        h[79:94] = list(self._pad(BANCO_NOME, 15))
        h[94:100] = list(self.data_geracao)
        h[100:108] = list(' ' * 8)
        h[108:110] = list(SISTEMA_ID)
        h[110:117] = list(str(self.seq_remessa).zfill(7))
        h[394:400] = list(f'{seq:06d}')
        return ''.join(h)

    def _montar_detalhe(self, boleto, seq):
        d = [' '] * LINE_WIDTH
        id_emp = id_empresa_detalhe()
        d[0] = '1'
        d[1:20] = list('0' * 5 + ' ' + '0' * 5 + '0' * 7 + ' ')
        d[20:37] = list(id_emp)
        d[37:62] = list(self._pad(boleto.get('nosso_antigo', ''), 25))
        d[62:65] = list(BANCO)
        d[65] = '0'
        d[66:70] = list('0000')
        d[70:81] = list(boleto['nosso_numero'])
        d[81] = boleto['nosso_numero_dac']
        d[82:92] = list('0' * 10)
        d[92] = '0'
        d[93] = ' '
        d[94:104] = list(' ' * 10)
        d[104] = '0'
        d[105] = ' '
        d[106:108] = list('01')
        d[108:110] = list(OCORRENCIA_REMESSA)
        d[110:120] = list(self._pad(boleto['nf_documento'], 10))
        d[120:126] = list(boleto['vencimento'])
        d[126:139] = list(boleto['valor_centavos'].zfill(13))
        d[139:142] = list('000')
        d[142:147] = list('00000')
        d[147:149] = list(ESPECIE_DUPLICATA)
        d[149] = ACEITE
        d[150:156] = list(boleto['emissao'])
        d[156:160] = list('0000')
        d[160:173] = list('0' * 13)
        d[173:179] = list('000000')
        d[179:192] = list('0' * 13)
        d[192:205] = list('0' * 13)
        d[205:218] = list('0' * 13)
        d[218:220] = list(boleto['tipo_inscricao'])
        d[220:234] = list(self._pad(boleto['cnpj_cpf'], 14, '0', 'right'))
        d[234:274] = list(self._pad(boleto['nome_sacado'], 40))
        d[274:314] = list(self._pad(boleto['endereco'], 40))
        d[314:326] = list(' ' * 12)
        d[326:331] = list(self._pad(boleto.get('cep_prefixo', '00000'), 5, '0', 'right'))
        d[331:334] = list(self._pad(boleto.get('cep_sufixo', '000'), 3, '0', 'right'))
        d[334:394] = list(' ' * 60)
        d[394:400] = list(f'{seq:06d}')
        return ''.join(d)

    def _montar_email(self, email, seq):
        e = [' '] * LINE_WIDTH
        e[0] = '2'
        e[1:321] = list(self._pad(email, 320))
        e[394:400] = list(f'{seq:06d}')
        return ''.join(e)

    def _montar_trailer(self, seq):
        t = [' '] * LINE_WIDTH
        t[0] = '9'
        t[394:400] = list(f'{seq:06d}')
        return ''.join(t)

    def gerar(self):
        if not self.boletos:
            raise ValueError('Nenhum boleto adicionado')

        linhas = []
        seq = 1
        linhas.append(self._montar_header(seq))

        for boleto in self.boletos:
            seq += 1
            linhas.append(self._montar_detalhe(boleto, seq))
            email = boleto.get('email', '').strip()
            if email:
                seq += 1
                linhas.append(self._montar_email(email, seq))

        seq += 1
        linhas.append(self._montar_trailer(seq))
        return linhas

    def gerar_bytes(self):
        linhas = self.gerar()
        return SEPARATOR.join(linhas).encode('latin-1')
```

- [ ] **Step 5: Rodar testes para ver que passam**

Run: `source .venv/bin/activate && python -m pytest tests/financeiro/test_cnab_generator.py -v`
Expected: 12 passed.

- [ ] **Step 6: Commit**

```bash
git add app/financeiro/services/remessa_vortx/layout_vortx.py app/financeiro/services/remessa_vortx/cnab_generator.py tests/financeiro/test_cnab_generator.py
git commit -m "feat(remessa-vortx): CNAB 400 generator com layout VORTX + testes"
```

---

### Task 4: Nosso Número Service

**Files:**
- Create: `app/financeiro/services/remessa_vortx/nosso_numero_service.py`

- [ ] **Step 1: Implementar alocação via PG sequence**

Criar `app/financeiro/services/remessa_vortx/nosso_numero_service.py`:

```python
from app import db
from sqlalchemy import text
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero
from app.financeiro.services.remessa_vortx.layout_vortx import CARTEIRA


def alocar_nossos_numeros(qtd: int) -> list:
    if qtd <= 0:
        raise ValueError('qtd deve ser positivo')

    resultado = []
    for _ in range(qtd):
        row = db.session.execute(text("SELECT nextval('nosso_numero_vortx_seq')"))
        seq = row.scalar()
        nn = str(seq).zfill(11)
        dac = calcular_dac_nosso_numero(CARTEIRA, nn)
        resultado.append({'seq': seq, 'nosso_numero': nn, 'dac': dac, 'completo': f'{nn}-{dac}'})
    return resultado


def consultar_proximo():
    row = db.session.execute(text("SELECT last_value FROM nosso_numero_vortx_seq"))
    return row.scalar()


def ajustar_sequence(novo_valor: int):
    db.session.execute(text(f"SELECT setval('nosso_numero_vortx_seq', :val, true)"), {'val': novo_valor})
    db.session.commit()
```

- [ ] **Step 2: Commit**

```bash
git add app/financeiro/services/remessa_vortx/nosso_numero_service.py
git commit -m "feat(remessa-vortx): nosso número service via PG sequence"
```

---

### Task 5: Odoo Injector (State Machine)

**Files:**
- Create: `app/financeiro/services/remessa_vortx/odoo_injector.py`

- [ ] **Step 1: Implementar state machine com retry + checkpoints**

Criar `app/financeiro/services/remessa_vortx/odoo_injector.py`:

```python
import base64
import uuid
import time
import logging
from datetime import datetime

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]


def _call_odoo_with_retry(odoo, model, method, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return odoo.execute_kw(model, method, *args, **kwargs)
        except Exception as e:
            err_str = str(e)
            is_transient = any(code in err_str for code in ['502', '503', '504', 'ConnectionError', 'TimeoutError', 'Connection refused'])
            if is_transient and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f'Odoo transient error (attempt {attempt+1}/{MAX_RETRIES}), retry in {delay}s: {err_str[:200]}')
                time.sleep(delay)
            else:
                raise


class OdooInjector:
    def __init__(self, cache_record):
        self.cache = cache_record

    def _get_odoo(self):
        from app.odoo.utils.connection import get_odoo_connection
        conn = get_odoo_connection()
        conn.authenticate()
        return conn

    def executar(self):
        try:
            if self.cache.etapa in ('CNAB_GERADO', 'FALHA_ESCRITURAL'):
                self._etapa_escritural()
            if self.cache.etapa in ('ESCRITURAL_OK', 'FALHA_REMESSA'):
                self._etapa_remessa()
            if self.cache.etapa in ('REMESSA_OK', 'FALHA_TITULOS'):
                self._etapa_titulos()
            if self.cache.etapa == 'TITULOS_OK':
                self.cache.etapa = 'CONCLUIDO'
                self.cache.concluido_em = agora_utc_naive()
                db.session.commit()
            return {'success': True, 'etapa': self.cache.etapa}
        except Exception as e:
            self.cache.tentativas += 1
            self.cache.ultimo_erro = str(e)[:2000]
            db.session.commit()
            logger.error(f'Falha injeção Odoo (etapa={self.cache.etapa}, tentativa={self.cache.tentativas}): {e}')
            return {'success': False, 'etapa': self.cache.etapa, 'error': str(e)[:500]}

    def _etapa_escritural(self):
        odoo = self._get_odoo()
        cnab_b64 = base64.b64encode(self.cache.arquivo_cnab).decode('ascii')

        if self.cache.odoo_escritural_id:
            existing = _call_odoo_with_retry(odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.escritural', 'read',
                [[self.cache.odoo_escritural_id]],
                {'fields': ['arquivo_remessa']})
            if existing and existing[0].get('arquivo_remessa'):
                self.cache.etapa = 'ESCRITURAL_OK'
                db.session.commit()
                return

        try:
            esc_id = _call_odoo_with_retry(odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.escritural', 'create',
                [{'arquivo_remessa': cnab_b64,
                  'nome_arquivo_remessa': self.cache.nome_arquivo,
                  'l10n_br_tipo_cobranca_id': self.cache.tipo_cobranca_id_odoo,
                  'company_id': self.cache.company_id_odoo}])
            self.cache.odoo_escritural_id = esc_id
        except Exception:
            self.cache.etapa = 'FALHA_ESCRITURAL'
            db.session.commit()
            raise

        self.cache.etapa = 'ESCRITURAL_OK'
        db.session.commit()

    def _etapa_remessa(self):
        odoo = self._get_odoo()
        cnab_b64 = base64.b64encode(self.cache.arquivo_cnab).decode('ascii')

        if self.cache.odoo_remessa_id:
            existing = _call_odoo_with_retry(odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.remessa', 'search',
                [[['id', '=', self.cache.odoo_remessa_id]]])
            if existing:
                self.cache.etapa = 'REMESSA_OK'
                db.session.commit()
                return

        try:
            rem_id = _call_odoo_with_retry(odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.remessa', 'create',
                [{'content': cnab_b64,
                  'nome_arquivo': self.cache.nome_arquivo,
                  'uniqueid': str(uuid.uuid4()),
                  'status': 'EMITIDO',
                  'l10n_br_tipo_cobranca_id': self.cache.tipo_cobranca_id_odoo,
                  'company_id': self.cache.company_id_odoo,
                  'created_at_full_date': datetime.now().strftime('%d/%m/%Y %H:%M:%S')}])
            self.cache.odoo_remessa_id = rem_id
        except Exception:
            self.cache.etapa = 'FALHA_REMESSA'
            db.session.commit()
            raise

        try:
            model_remessa = 'l10n_br_ciel_it_account.arquivo.cobranca.remessa'
            download = f'/web/content/{model_remessa}/{rem_id}/content/{self.cache.nome_arquivo}?download=true'
            _call_odoo_with_retry(odoo, model_remessa, 'write',
                [[rem_id], {'download_url': download}])
        except Exception:
            logger.warning(f'Falha ao setar download_url (não-fatal): {self.cache.odoo_remessa_id}')

        self.cache.etapa = 'REMESSA_OK'
        db.session.commit()

    def _etapa_titulos(self):
        odoo = self._get_odoo()
        pendentes = self.cache.get_move_line_ids_pendentes()
        if not pendentes:
            self.cache.etapa = 'TITULOS_OK'
            db.session.commit()
            return

        ainda_sem_remessa = _call_odoo_with_retry(odoo,
            'account.move.line', 'search',
            [[['id', 'in', pendentes],
              ['l10n_br_arquivo_cobranca_escritural_id', '=', False]]])

        if not ainda_sem_remessa:
            self.cache.set_move_line_ids_pendentes([])
            self.cache.set_move_line_ids_marcados(
                self.cache.get_move_line_ids_marcados() + pendentes)
            self.cache.etapa = 'TITULOS_OK'
            db.session.commit()
            return

        mapa = self.cache.get_mapa_nn_move_line()

        try:
            for ml_id in ainda_sem_remessa:
                nn_str = mapa.get(str(ml_id), '')
                payload = {
                    'l10n_br_arquivo_cobranca_escritural_id': self.cache.odoo_escritural_id,
                }
                if nn_str:
                    payload['l10n_br_cobranca_nossonumero'] = nn_str
                _call_odoo_with_retry(odoo, 'account.move.line', 'write',
                    [[ml_id], payload])
        except Exception:
            marcados_agora = _call_odoo_with_retry(odoo,
                'account.move.line', 'search',
                [[['id', 'in', pendentes],
                  ['l10n_br_arquivo_cobranca_escritural_id', '=', self.cache.odoo_escritural_id]]])
            self.cache.set_move_line_ids_marcados(
                self.cache.get_move_line_ids_marcados() + marcados_agora)
            self.cache.set_move_line_ids_pendentes(
                [x for x in pendentes if x not in marcados_agora])
            self.cache.etapa = 'FALHA_TITULOS'
            db.session.commit()
            raise

        self.cache.set_move_line_ids_marcados(
            self.cache.get_move_line_ids_marcados() + ainda_sem_remessa)
        self.cache.set_move_line_ids_pendentes(
            [x for x in pendentes if x not in ainda_sem_remessa])
        self.cache.etapa = 'TITULOS_OK'
        db.session.commit()


def buscar_titulos_pendentes(odoo, company_id: int, limit: int = 500) -> list:
    from app.financeiro.services.remessa_vortx.layout_vortx import TIPO_COBRANCA_IDS
    tipo_cob = TIPO_COBRANCA_IDS.get(company_id)
    if not tipo_cob:
        return []

    move_lines = _call_odoo_with_retry(odoo,
        'account.move.line', 'search_read',
        [[['l10n_br_arquivo_cobranca_escritural_id', '=', False],
          ['l10n_br_cobranca_transmissao', '=', 'manual'],
          ['parent_state', '=', 'posted'],
          ['move_id.move_type', '=', 'out_invoice'],
          ['company_id', '=', company_id]]],
        {'fields': ['id', 'move_id', 'name', 'date_maturity', 'debit',
                    'partner_id', 'l10n_br_cobranca_nossonumero'],
         'limit': limit})
    return move_lines


def buscar_dados_sacado(odoo, partner_id: int) -> dict:
    partner = _call_odoo_with_retry(odoo,
        'res.partner', 'read',
        [[partner_id]],
        {'fields': ['name', 'street', 'street2', 'city', 'zip',
                    'l10n_br_cnpj', 'l10n_br_cpf', 'email',
                    'company_type']})
    if not partner:
        return {}
    p = partner[0]
    cnpj_raw = (p.get('l10n_br_cnpj') or p.get('l10n_br_cpf') or '').replace('.', '').replace('/', '').replace('-', '')
    tipo = '02' if p.get('company_type') == 'company' else '01'
    endereco = ((p.get('street') or '') + ', ' + (p.get('street2') or '')).strip(', ')[:40]
    cep = (p.get('zip') or '00000000').replace('-', '').replace('.', '')
    if len(cep) < 8:
        cep = cep.zfill(8)
    return {
        'nome': (p.get('name') or '')[:40],
        'endereco': endereco,
        'cep_prefixo': cep[:5],
        'cep_sufixo': cep[5:8],
        'cnpj_cpf': cnpj_raw.zfill(14),
        'tipo_inscricao': tipo,
        'email': (p.get('email') or '')[:320],
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/financeiro/services/remessa_vortx/odoo_injector.py
git commit -m "feat(remessa-vortx): Odoo injector state machine com retry e checkpoints"
```

---

### Task 6: Routes + Templates

**Files:**
- Create: `app/financeiro/routes/remessa_vortx.py`
- Create: `app/templates/financeiro/remessa_vortx/listar_titulos.html`
- Create: `app/templates/financeiro/remessa_vortx/historico.html`
- Modify: `app/financeiro/routes/__init__.py` (adicionar import)
- Modify: `app/templates/base.html` (adicionar link menu)

- [ ] **Step 1: Criar rotas**

Criar `app/financeiro/routes/remessa_vortx.py`:

```python
import json
import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from io import BytesIO

from app.financeiro.routes import financeiro_bp
from app.utils.auth_decorators import require_remessa_vortx

logger = logging.getLogger(__name__)


@financeiro_bp.route('/remessa-vortx')
@login_required
@require_remessa_vortx()
def remessa_vortx_historico():
    from app.financeiro.models import RemessaVortxCache
    registros = RemessaVortxCache.query.order_by(RemessaVortxCache.id.desc()).limit(50).all()
    return render_template('financeiro/remessa_vortx/historico.html', registros=registros)


@financeiro_bp.route('/remessa-vortx/titulos')
@login_required
@require_remessa_vortx()
def remessa_vortx_titulos():
    from app.odoo.utils.connection import get_odoo_connection
    from app.financeiro.services.remessa_vortx.odoo_injector import buscar_titulos_pendentes

    company_id = request.args.get('company_id', 4, type=int)
    odoo = get_odoo_connection()
    odoo.authenticate()
    titulos = buscar_titulos_pendentes(odoo, company_id)
    return render_template('financeiro/remessa_vortx/listar_titulos.html',
                           titulos=titulos, company_id=company_id)


@financeiro_bp.route('/remessa-vortx/gerar', methods=['POST'])
@login_required
@require_remessa_vortx()
def remessa_vortx_gerar():
    from app import db
    from app.odoo.utils.connection import get_odoo_connection
    from app.financeiro.models import RemessaVortxCache
    from app.financeiro.services.remessa_vortx.cnab_generator import CnabVortxGenerator
    from app.financeiro.services.remessa_vortx.nosso_numero_service import alocar_nossos_numeros
    from app.financeiro.services.remessa_vortx.odoo_injector import (
        OdooInjector, buscar_dados_sacado, buscar_titulos_pendentes)
    from app.financeiro.services.remessa_vortx.layout_vortx import TIPO_COBRANCA_IDS
    from app.utils.timezone import agora_utc_naive

    company_id = request.form.get('company_id', 4, type=int)
    selected_ids = request.form.getlist('move_line_ids', type=int)

    if not selected_ids:
        flash('Nenhum título selecionado.', 'warning')
        return redirect(url_for('financeiro.remessa_vortx_titulos', company_id=company_id))

    tipo_cob = TIPO_COBRANCA_IDS.get(company_id)
    if not tipo_cob:
        flash(f'Empresa {company_id} não tem tipo de cobrança VORTX configurado.', 'danger')
        return redirect(url_for('financeiro.remessa_vortx_titulos', company_id=company_id))

    try:
        odoo = get_odoo_connection()
        odoo.authenticate()

        titulos = odoo.execute_kw(
            'account.move.line', 'read',
            [selected_ids],
            {'fields': ['id', 'move_id', 'name', 'date_maturity', 'debit',
                        'partner_id', 'l10n_br_cobranca_nossonumero']})

        if not titulos:
            flash('Nenhum título encontrado no Odoo.', 'danger')
            return redirect(url_for('financeiro.remessa_vortx_titulos', company_id=company_id))

        nossos = alocar_nossos_numeros(len(titulos))
        data_hoje = datetime.now().strftime('%d%m%y')
        gen = CnabVortxGenerator(data_geracao=data_hoje, seq_remessa=1)

        mapa_nn_ml = {}
        valor_total = 0

        for i, titulo in enumerate(titulos):
            nn = nossos[i]
            partner_id = titulo['partner_id'][0] if titulo.get('partner_id') else None
            sacado = buscar_dados_sacado(odoo, partner_id) if partner_id else {}

            valor_cents = int(round(titulo['debit'] * 100))
            valor_total += titulo['debit']

            vencimento_raw = titulo.get('date_maturity', '')
            if vencimento_raw and '-' in str(vencimento_raw):
                parts = str(vencimento_raw).split('-')
                vencimento = f'{parts[2]}{parts[1]}{parts[0][2:]}'
            else:
                vencimento = '000000'

            nf_doc = (titulo.get('name') or '')[:10]

            boleto = {
                'nf_documento': nf_doc,
                'vencimento': vencimento,
                'valor_centavos': str(valor_cents).zfill(13),
                'emissao': data_hoje,
                'tipo_inscricao': sacado.get('tipo_inscricao', '02'),
                'cnpj_cpf': sacado.get('cnpj_cpf', '00000000000000'),
                'nome_sacado': sacado.get('nome', 'NAO IDENTIFICADO'),
                'endereco': sacado.get('endereco', ''),
                'cep_prefixo': sacado.get('cep_prefixo', '00000'),
                'cep_sufixo': sacado.get('cep_sufixo', '000'),
                'email': sacado.get('email', ''),
                'nosso_numero': nn['nosso_numero'],
                'nosso_numero_dac': nn['dac'],
                'nosso_antigo': titulo.get('l10n_br_cobranca_nossonumero') or '',
            }
            gen.adicionar_boleto(boleto)
            mapa_nn_ml[str(titulo['id'])] = nn['completo']

        cnab_bytes = gen.gerar_bytes()
        nome_arquivo = f'COB_310_{data_hoje}_{str(nossos[0]["seq"]).zfill(6)}.rem'

        cache = RemessaVortxCache(
            company_id_odoo=company_id,
            tipo_cobranca_id_odoo=tipo_cob,
            nome_arquivo=nome_arquivo,
            qtd_boletos=len(titulos),
            valor_total=valor_total,
            nosso_numero_inicial=nossos[0]['seq'],
            nosso_numero_final=nossos[-1]['seq'],
            arquivo_cnab=cnab_bytes,
            criado_por_id=current_user.id,
        )
        cache.set_move_line_ids_pendentes(selected_ids)
        cache.set_mapa_nn_move_line(mapa_nn_ml)
        db.session.add(cache)
        db.session.commit()

        injector = OdooInjector(cache)
        result = injector.executar()

        if result['success']:
            flash(f'Remessa {nome_arquivo} gerada e injetada no Odoo com sucesso! ({len(titulos)} títulos)', 'success')
        else:
            flash(f'Remessa gerada parcialmente (etapa: {result["etapa"]}). Use "Retomar" para continuar. Erro: {result.get("error", "")[:200]}', 'warning')

    except Exception as e:
        logger.exception('Erro ao gerar remessa VORTX')
        flash(f'Erro ao gerar remessa: {str(e)[:300]}', 'danger')

    return redirect(url_for('financeiro.remessa_vortx_historico'))


@financeiro_bp.route('/remessa-vortx/<int:cache_id>/retomar', methods=['POST'])
@login_required
@require_remessa_vortx()
def remessa_vortx_retomar(cache_id):
    from app.financeiro.models import RemessaVortxCache
    from app.financeiro.services.remessa_vortx.odoo_injector import OdooInjector

    cache = RemessaVortxCache.query.get_or_404(cache_id)
    if not cache.pode_retomar:
        flash('Esta remessa não pode ser retomada.', 'warning')
        return redirect(url_for('financeiro.remessa_vortx_historico'))

    injector = OdooInjector(cache)
    result = injector.executar()

    if result['success']:
        flash(f'Remessa {cache.nome_arquivo} concluída com sucesso!', 'success')
    else:
        flash(f'Retomada parcial (etapa: {result["etapa"]}). Erro: {result.get("error", "")[:200]}', 'warning')

    return redirect(url_for('financeiro.remessa_vortx_historico'))


@financeiro_bp.route('/remessa-vortx/<int:cache_id>/download')
@login_required
@require_remessa_vortx()
def remessa_vortx_download(cache_id):
    from app.financeiro.models import RemessaVortxCache

    cache = RemessaVortxCache.query.get_or_404(cache_id)
    return send_file(
        BytesIO(cache.arquivo_cnab),
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=cache.nome_arquivo)
```

- [ ] **Step 2: Registrar rota no blueprint**

Em `app/financeiro/routes/__init__.py`, adicionar ao final dos imports:

```python
from app.financeiro.routes import remessa_vortx
```

- [ ] **Step 3: Criar template historico.html**

Criar `app/templates/financeiro/remessa_vortx/historico.html`:

```html
{% extends "base.html" %}
{% block title %}Remessas VORTX{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h4><i class="fas fa-file-invoice-dollar text-primary"></i> Remessas VORTX (Banco 310)</h4>
    <a href="{{ url_for('financeiro.remessa_vortx_titulos') }}" class="btn btn-primary">
      <i class="fas fa-plus"></i> Gerar Nova Remessa
    </a>
  </div>

  {% if registros %}
  <div class="table-responsive">
    <table class="table table-sm table-hover">
      <thead class="table-dark">
        <tr>
          <th>ID</th>
          <th>Arquivo</th>
          <th>Empresa</th>
          <th>Boletos</th>
          <th>Valor Total</th>
          <th>NN Faixa</th>
          <th>Etapa</th>
          <th>Criado Em</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {% for r in registros %}
        <tr>
          <td>{{ r.id }}</td>
          <td><code>{{ r.nome_arquivo }}</code></td>
          <td>{{ r.company_id_odoo }}</td>
          <td>{{ r.qtd_boletos }}</td>
          <td>{{ r.valor_total|valor_br }}</td>
          <td>{{ r.nosso_numero_inicial }}-{{ r.nosso_numero_final }}</td>
          <td>
            {% if r.is_concluido %}
              <span class="badge bg-success">CONCLUÍDO</span>
            {% elif r.is_falha %}
              <span class="badge bg-danger">{{ r.etapa }}</span>
            {% else %}
              <span class="badge bg-warning text-dark">{{ r.etapa }}</span>
            {% endif %}
          </td>
          <td>{{ r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else '-' }}</td>
          <td>
            <a href="{{ url_for('financeiro.remessa_vortx_download', cache_id=r.id) }}"
               class="btn btn-sm btn-outline-primary" title="Download">
              <i class="fas fa-download"></i>
            </a>
            {% if r.pode_retomar %}
            <form method="POST" action="{{ url_for('financeiro.remessa_vortx_retomar', cache_id=r.id) }}" class="d-inline">
              <button type="submit" class="btn btn-sm btn-outline-warning" title="Retomar">
                <i class="fas fa-redo"></i>
              </button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
  <div class="alert alert-info">Nenhuma remessa gerada ainda.</div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 4: Criar template listar_titulos.html**

Criar `app/templates/financeiro/remessa_vortx/listar_titulos.html`:

```html
{% extends "base.html" %}
{% block title %}Títulos Pendentes VORTX{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h4><i class="fas fa-list-check text-primary"></i> Títulos Pendentes — Remessa VORTX</h4>
    <div>
      <a href="{{ url_for('financeiro.remessa_vortx_titulos', company_id=1) }}"
         class="btn btn-sm {{ 'btn-primary' if company_id == 1 else 'btn-outline-primary' }}">FB</a>
      <a href="{{ url_for('financeiro.remessa_vortx_titulos', company_id=4) }}"
         class="btn btn-sm {{ 'btn-primary' if company_id == 4 else 'btn-outline-primary' }}">CD</a>
      <a href="{{ url_for('financeiro.remessa_vortx_historico') }}" class="btn btn-sm btn-outline-secondary ms-2">
        <i class="fas fa-history"></i> Histórico
      </a>
    </div>
  </div>

  {% if titulos %}
  <form method="POST" action="{{ url_for('financeiro.remessa_vortx_gerar') }}">
    <input type="hidden" name="company_id" value="{{ company_id }}">
    <div class="mb-2">
      <button type="button" class="btn btn-sm btn-outline-secondary" id="btnSelectAll">Selecionar Todos</button>
      <span class="ms-2 text-muted" id="selectedCount">0 selecionados</span>
    </div>
    <div class="table-responsive">
      <table class="table table-sm table-hover">
        <thead class="table-dark">
          <tr>
            <th><input type="checkbox" id="checkAll"></th>
            <th>ID</th>
            <th>NF / Parcela</th>
            <th>Vencimento</th>
            <th>Valor</th>
            <th>Nosso Nº Atual</th>
          </tr>
        </thead>
        <tbody>
          {% for t in titulos %}
          <tr>
            <td><input type="checkbox" name="move_line_ids" value="{{ t.id }}" class="cb-titulo"></td>
            <td>{{ t.id }}</td>
            <td>{{ t.name or t.move_id[1] }}</td>
            <td>{{ t.date_maturity }}</td>
            <td>{{ "R$ {:,.2f}".format(t.debit).replace(",","X").replace(".",",").replace("X",".") }}</td>
            <td>{{ t.l10n_br_cobranca_nossonumero or '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="d-flex justify-content-between align-items-center mt-3">
      <span class="text-muted">{{ titulos|length }} título(s) pendente(s)</span>
      <button type="submit" class="btn btn-success" id="btnGerar">
        <i class="fas fa-file-export"></i> Gerar Remessa VORTX
      </button>
    </div>
  </form>
  {% else %}
  <div class="alert alert-success">Nenhum título pendente para esta empresa.</div>
  {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  const checkAll = document.getElementById('checkAll');
  const cbs = document.querySelectorAll('.cb-titulo');
  const counter = document.getElementById('selectedCount');
  const btnSelect = document.getElementById('btnSelectAll');

  function updateCount() {
    const n = document.querySelectorAll('.cb-titulo:checked').length;
    counter.textContent = n + ' selecionado(s)';
  }

  if (checkAll) {
    checkAll.addEventListener('change', function() {
      cbs.forEach(cb => cb.checked = this.checked);
      updateCount();
    });
  }
  if (btnSelect) {
    btnSelect.addEventListener('click', function() {
      cbs.forEach(cb => cb.checked = true);
      if (checkAll) checkAll.checked = true;
      updateCount();
    });
  }
  cbs.forEach(cb => cb.addEventListener('change', updateCount));
});
</script>
{% endblock %}
```

- [ ] **Step 5: Adicionar link no menu base.html**

Em `app/templates/base.html`, dentro do dropdown Financeiro (após um item existente como `Extratos`), adicionar:

```html
{% if current_user.pode_gerar_remessa_vortx() %}
<li><a class="dropdown-item" href="{{ url_for('financeiro.remessa_vortx_historico') }}">
    <i class="fas fa-file-invoice-dollar text-success"></i> Remessas VORTX
</a></li>
{% endif %}
```

- [ ] **Step 6: Commit**

```bash
git add app/financeiro/routes/remessa_vortx.py app/financeiro/routes/__init__.py app/templates/financeiro/remessa_vortx/ app/templates/base.html
git commit -m "feat(remessa-vortx): rotas + templates + menu para geração de remessas VORTX"
```

---

### Task 7: Habilitar usuários + Teste end-to-end manual

- [ ] **Step 1: Rodar migration no Render**

Executar via Render Shell:
```sql
\i scripts/migrations/adicionar_remessa_vortx.sql
```

Ou via Python:
```bash
python scripts/migrations/adicionar_remessa_vortx.py
```

- [ ] **Step 2: Habilitar flag para usuário Rafael**

```sql
UPDATE usuarios SET sistema_remessa_vortx = TRUE WHERE email = 'rafael@conservascampobelo.com.br';
```

- [ ] **Step 3: Ajustar sequence para valor correto**

O Marcus já gerou NN 1-20 manualmente. **Quando o usuário informar o valor correto**, ajustar:

```sql
SELECT setval('nosso_numero_vortx_seq', 20, true);  -- próximo será 21
```

- [ ] **Step 4: Deploy e testar**

1. Acessar `/financeiro/remessa-vortx`
2. Clicar "Gerar Nova Remessa"
3. Selecionar empresa (FB ou CD)
4. Selecionar 1-2 títulos de teste
5. Clicar "Gerar Remessa VORTX"
6. Verificar:
   - Flash de sucesso
   - Registro aparece no histórico com etapa CONCLUIDO
   - Download funciona (arquivo .rem com 400 chars por linha)
   - No Odoo (action 1990): registro aparece com arquivo
   - No Odoo (account.move.line): títulos marcados com `l10n_br_arquivo_cobranca_escritural_id`

- [ ] **Step 5: Commit final (se houver ajustes)**

```bash
git add -A
git commit -m "fix(remessa-vortx): ajustes pós-teste e2e"
```

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| 502/timeout no Odoo durante injeção | State machine com checkpoints + retry exponencial |
| Nosso número duplicado se sequence ficar defasado | Consultar VORTX para último NN usado antes de começar |
| Títulos marcados parcialmente | Etapa FALHA_TITULOS marca quais já foram + retry idempotente |
| Layout VORTX incorreto | Golden test com arquivo v3 real (Task 2 tests) |
| Dois usuários gerando simultaneamente | PG sequence garante unicidade de NN; UI mostra pendentes em tempo real |

## Fase 2 (futuro)

- Processamento de retorno VORTX (.ret) → atualizar `l10n_br_cobranca_situacao` no Odoo
- Suporte a outros bancos (Santander, Itaú) via Strategy pattern no `cnab_generator.py`
- Automação via cron (gerar remessa automaticamente quando há N títulos pendentes)
