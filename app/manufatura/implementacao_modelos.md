# IMPLEMENTAÇÃO - MODELOS E BANCO DE DADOS

## 1. CRIAÇÃO DE TABELAS NO BANCO

### 1.1 Tabela: grupo_empresarial
```sql
CREATE TABLE grupo_empresarial (
    id SERIAL PRIMARY KEY,
    nome_grupo VARCHAR(100) NOT NULL UNIQUE,
    tipo_grupo VARCHAR(20) NOT NULL CHECK (tipo_grupo IN ('prefixo_cnpj', 'raz_social')),
    info_grupo TEXT[] NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_grupo_nome ON grupo_empresarial(nome_grupo);
CREATE INDEX idx_grupo_tipo ON grupo_empresarial(tipo_grupo);
```

### 1.2 Tabela: historico_pedidos
```sql
CREATE TABLE historico_pedidos (
    id SERIAL PRIMARY KEY,
    num_pedido VARCHAR(50) NOT NULL,
    data_pedido DATE NOT NULL,
    cnpj_cliente VARCHAR(20) NOT NULL,
    raz_social_red VARCHAR(255),
    nome_grupo VARCHAR(100),
    vendedor VARCHAR(100),
    equipe_vendas VARCHAR(100),
    incoterm VARCHAR(20),
    nome_cidade VARCHAR(100),
    cod_uf VARCHAR(2),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_pedido NUMERIC(15,3) NOT NULL,
    preco_produto_pedido NUMERIC(15,4),
    valor_produto_pedido NUMERIC(15,2),
    icms_produto_pedido NUMERIC(15,2),
    pis_produto_pedido NUMERIC(15,2),
    cofins_produto_pedido NUMERIC(15,2),
    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(num_pedido, cod_produto)
);
CREATE INDEX idx_hist_pedido ON historico_pedidos(num_pedido);
CREATE INDEX idx_hist_produto ON historico_pedidos(cod_produto);
CREATE INDEX idx_hist_grupo ON historico_pedidos(nome_grupo);
CREATE INDEX idx_hist_data ON historico_pedidos(data_pedido);
```

### 1.3 Tabela: previsao_demanda
```sql
CREATE TABLE previsao_demanda (
    id SERIAL PRIMARY KEY,
    data_mes INTEGER NOT NULL CHECK (data_mes BETWEEN 1 AND 12),
    data_ano INTEGER NOT NULL CHECK (data_ano >= 2024),
    nome_grupo VARCHAR(100),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_demanda_prevista NUMERIC(15,3) NOT NULL,
    qtd_demanda_realizada NUMERIC(15,3) DEFAULT 0,
    disparo_producao VARCHAR(3) CHECK (disparo_producao IN ('MTO', 'MTS')),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    UNIQUE(data_mes, data_ano, cod_produto, nome_grupo)
);
CREATE INDEX idx_prev_periodo ON previsao_demanda(data_ano, data_mes);
CREATE INDEX idx_prev_produto ON previsao_demanda(cod_produto);
```

### 1.4 Tabela: plano_mestre_producao
```sql
CREATE TABLE plano_mestre_producao (
    id SERIAL PRIMARY KEY,
    data_mes INTEGER NOT NULL CHECK (data_mes BETWEEN 1 AND 12),
    data_ano INTEGER NOT NULL CHECK (data_ano >= 2024),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_demanda_prevista NUMERIC(15,3),
    disparo_producao VARCHAR(3) CHECK (disparo_producao IN ('MTO', 'MTS')),
    qtd_producao_programada NUMERIC(15,3) DEFAULT 0,
    qtd_producao_realizada NUMERIC(15,3) DEFAULT 0,
    qtd_estoque NUMERIC(15,3) DEFAULT 0,
    qtd_estoque_seguranca NUMERIC(15,3) DEFAULT 0,
    qtd_reposicao_sugerida NUMERIC(15,3) GENERATED ALWAYS AS 
        (qtd_demanda_prevista + qtd_estoque_seguranca - qtd_producao_programada - qtd_producao_realizada) STORED,
    qtd_lote_ideal NUMERIC(15,3),
    qtd_lote_minimo NUMERIC(15,3),
    status_geracao VARCHAR(20) DEFAULT 'rascunho' CHECK (status_geracao IN ('rascunho', 'aprovado', 'executando', 'concluido')),
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(data_mes, data_ano, cod_produto)
);
CREATE INDEX idx_pmp_periodo ON plano_mestre_producao(data_ano, data_mes);
CREATE INDEX idx_pmp_status ON plano_mestre_producao(status_geracao);
```

### 1.5 Tabela: recursos_producao
```sql
CREATE TABLE recursos_producao (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    linha_producao VARCHAR(50) NOT NULL,
    qtd_unidade_por_caixa NUMERIC(10,2),
    capacidade_unidade_minuto NUMERIC(10,3) NOT NULL,
    qtd_lote_ideal NUMERIC(15,3),
    qtd_lote_minimo NUMERIC(15,3),
    eficiencia_media NUMERIC(5,2) DEFAULT 85.00,
    tempo_setup INTEGER DEFAULT 30,
    disponivel BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_produto, linha_producao)
);
CREATE INDEX idx_rec_produto ON recursos_producao(cod_produto);
CREATE INDEX idx_rec_linha ON recursos_producao(linha_producao);
```

### 1.6 Tabela: ordem_producao
```sql
CREATE TABLE ordem_producao (
    id SERIAL PRIMARY KEY,
    numero_ordem VARCHAR(20) UNIQUE NOT NULL,
    origem_ordem VARCHAR(10) CHECK (origem_ordem IN ('PMP', 'MTO', 'Manual')),
    status VARCHAR(20) DEFAULT 'Planejada' CHECK (status IN ('Planejada', 'Liberada', 'Em Produção', 'Concluída', 'Cancelada')),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    materiais_necessarios JSONB,
    qtd_planejada NUMERIC(15,3) NOT NULL,
    qtd_produzida NUMERIC(15,3) DEFAULT 0,
    data_inicio_prevista DATE NOT NULL,
    data_fim_prevista DATE NOT NULL,
    data_inicio_real DATE,
    data_fim_real DATE,
    linha_producao VARCHAR(50),
    turno VARCHAR(20),
    lote_producao VARCHAR(50),
    custo_previsto NUMERIC(15,2),
    custo_real NUMERIC(15,2),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    CHECK (data_fim_prevista >= data_inicio_prevista)
);
CREATE INDEX idx_op_numero ON ordem_producao(numero_ordem);
CREATE INDEX idx_op_status ON ordem_producao(status);
CREATE INDEX idx_op_produto ON ordem_producao(cod_produto);
CREATE INDEX idx_op_data_inicio ON ordem_producao(data_inicio_prevista);
CREATE INDEX idx_op_linha ON ordem_producao(linha_producao);
```

### 1.7 Tabela: requisicao_compras
```sql
CREATE TABLE requisicao_compras (
    id SERIAL PRIMARY KEY,
    num_requisicao VARCHAR(30) UNIQUE NOT NULL,
    data_requisicao_criacao DATE NOT NULL,
    usuario_requisicao_criacao VARCHAR(100),
    lead_time_requisicao INTEGER,
    lead_time_previsto INTEGER,
    data_requisicao_solicitada DATE,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_requisicao NUMERIC(15,3) NOT NULL,
    qtd_produto_sem_requisicao NUMERIC(15,3) DEFAULT 0,
    necessidade BOOLEAN DEFAULT FALSE,
    data_necessidade DATE,
    status VARCHAR(20) DEFAULT 'Pendente' CHECK (status IN ('Pendente', 'Requisitada', 'Em Cotação', 'Pedido Colocado', 'Cancelada')),
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_req_numero ON requisicao_compras(num_requisicao);
CREATE INDEX idx_req_produto ON requisicao_compras(cod_produto);
CREATE INDEX idx_req_status ON requisicao_compras(status);
```

### 1.8 Tabela: pedido_compras
```sql
CREATE TABLE pedido_compras (
    id SERIAL PRIMARY KEY,
    num_pedido VARCHAR(30) UNIQUE NOT NULL,
    num_requisicao VARCHAR(30),
    cnpj_fornecedor VARCHAR(20),
    raz_social VARCHAR(255),
    numero_nf VARCHAR(20),
    data_pedido_criacao DATE,
    usuario_pedido_criacao VARCHAR(100),
    lead_time_pedido INTEGER,
    lead_time_previsto INTEGER,
    data_pedido_previsao DATE,
    data_pedido_entrega DATE,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_pedido NUMERIC(15,3) NOT NULL,
    preco_produto_pedido NUMERIC(15,4),
    icms_produto_pedido NUMERIC(15,2),
    pis_produto_pedido NUMERIC(15,2),
    cofins_produto_pedido NUMERIC(15,2),
    confirmacao_pedido BOOLEAN DEFAULT FALSE,
    confirmado_por VARCHAR(100),
    confirmado_em TIMESTAMP,
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (num_requisicao) REFERENCES requisicao_compras(num_requisicao)
);
CREATE INDEX idx_ped_numero ON pedido_compras(num_pedido);
CREATE INDEX idx_ped_requisicao ON pedido_compras(num_requisicao);
CREATE INDEX idx_ped_fornecedor ON pedido_compras(cnpj_fornecedor);
CREATE INDEX idx_ped_produto ON pedido_compras(cod_produto);
```

### 1.9 Tabela: lead_time_fornecedor
```sql
CREATE TABLE lead_time_fornecedor (
    id SERIAL PRIMARY KEY,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    nome_fornecedor VARCHAR(255),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    lead_time_previsto INTEGER NOT NULL,
    lead_time_historico NUMERIC(5,1),
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cnpj_fornecedor, cod_produto)
);
CREATE INDEX idx_ltf_fornecedor ON lead_time_fornecedor(cnpj_fornecedor);
CREATE INDEX idx_ltf_produto ON lead_time_fornecedor(cod_produto);
```

### 1.10 Tabela: lista_materiais
```sql
CREATE TABLE lista_materiais (
    id SERIAL PRIMARY KEY,
    cod_produto_produzido VARCHAR(50) NOT NULL,
    nome_produto_produzido VARCHAR(255),
    cod_produto_componente VARCHAR(50) NOT NULL,
    nome_produto_componente VARCHAR(255),
    qtd_utilizada NUMERIC(15,6) NOT NULL,
    status VARCHAR(10) DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo')),
    versao VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    UNIQUE(cod_produto_produzido, cod_produto_componente, versao)
);
CREATE INDEX idx_lm_produzido ON lista_materiais(cod_produto_produzido);
CREATE INDEX idx_lm_componente ON lista_materiais(cod_produto_componente);
CREATE INDEX idx_lm_status ON lista_materiais(status);
```

---

## 2. ALTERAÇÕES EM TABELAS EXISTENTES

### 2.1 MovimentacaoEstoque - Adicionar campos
```sql
ALTER TABLE movimentacao_estoque 
ADD COLUMN num_pedido VARCHAR(30),
ADD COLUMN numero_nf VARCHAR(20),
ADD COLUMN ordem_producao_id INTEGER,
ADD FOREIGN KEY (ordem_producao_id) REFERENCES ordem_producao(id);

CREATE INDEX idx_mov_pedido ON movimentacao_estoque(num_pedido);
CREATE INDEX idx_mov_nf ON movimentacao_estoque(numero_nf);
CREATE INDEX idx_mov_ordem ON movimentacao_estoque(ordem_producao_id);
```

### 2.2 CadastroPalletizacao - Adicionar campos
```sql
ALTER TABLE cadastro_palletizacao
ADD COLUMN produto_comprado BOOLEAN DEFAULT FALSE,
ADD COLUMN produto_produzido BOOLEAN DEFAULT FALSE,
ADD COLUMN produto_vendido BOOLEAN DEFAULT TRUE,
ADD COLUMN lead_time_mto INTEGER,
ADD COLUMN disparo_producao VARCHAR(3) CHECK (disparo_producao IN ('MTO', 'MTS')),
ADD COLUMN custo_produto NUMERIC(15,4);

CREATE INDEX idx_cp_comprado ON cadastro_palletizacao(produto_comprado);
CREATE INDEX idx_cp_produzido ON cadastro_palletizacao(produto_produzido);
CREATE INDEX idx_cp_vendido ON cadastro_palletizacao(produto_vendido);
CREATE INDEX idx_cp_disparo ON cadastro_palletizacao(disparo_producao);
```

### 2.3 CarteiraPrincipal - Adicionar campos
```sql
ALTER TABLE carteira_principal
ADD COLUMN ordem_producao_id INTEGER,
ADD COLUMN disparo_producao VARCHAR(3),
ADD FOREIGN KEY (ordem_producao_id) REFERENCES ordem_producao(id);

CREATE INDEX idx_cart_ordem ON carteira_principal(ordem_producao_id);
```

---

## 3. MODELOS SQLALCHEMY

### 3.1 Arquivo: app/manufatura/models.py
```python
from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

class GrupoEmpresarial(db.Model):
    __tablename__ = 'grupo_empresarial'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_grupo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tipo_grupo = db.Column(db.String(20), nullable=False)
    info_grupo = db.Column(ARRAY(db.Text), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)

class HistoricoPedidos(db.Model):
    __tablename__ = 'historico_pedidos'
    
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    data_pedido = db.Column(db.Date, nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False)
    raz_social_red = db.Column(db.String(255))
    nome_grupo = db.Column(db.String(100), index=True)
    vendedor = db.Column(db.String(100))
    equipe_vendas = db.Column(db.String(100))
    incoterm = db.Column(db.String(20))
    nome_cidade = db.Column(db.String(100))
    cod_uf = db.Column(db.String(2))
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    valor_produto_pedido = db.Column(db.Numeric(15, 2))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))
    importado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('num_pedido', 'cod_produto'),
    )

class PrevisaoDemanda(db.Model):
    __tablename__ = 'previsao_demanda'
    
    id = db.Column(db.Integer, primary_key=True)
    data_mes = db.Column(db.Integer, nullable=False)
    data_ano = db.Column(db.Integer, nullable=False, index=True)
    nome_grupo = db.Column(db.String(100))
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_demanda_prevista = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_demanda_realizada = db.Column(db.Numeric(15, 3), default=0)
    disparo_producao = db.Column(db.String(3))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('data_mes', 'data_ano', 'cod_produto', 'nome_grupo'),
    )

class PlanoMestreProducao(db.Model):
    __tablename__ = 'plano_mestre_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    data_mes = db.Column(db.Integer, nullable=False)
    data_ano = db.Column(db.Integer, nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(255))
    qtd_demanda_prevista = db.Column(db.Numeric(15, 3))
    disparo_producao = db.Column(db.String(3))
    qtd_producao_programada = db.Column(db.Numeric(15, 3), default=0)
    qtd_producao_realizada = db.Column(db.Numeric(15, 3), default=0)
    qtd_estoque = db.Column(db.Numeric(15, 3), default=0)
    qtd_estoque_seguranca = db.Column(db.Numeric(15, 3), default=0)
    qtd_reposicao_sugerida = db.Column(db.Numeric(15, 3))
    qtd_lote_ideal = db.Column(db.Numeric(15, 3))
    qtd_lote_minimo = db.Column(db.Numeric(15, 3))
    status_geracao = db.Column(db.String(20), default='rascunho', index=True)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('data_mes', 'data_ano', 'cod_produto'),
    )

class RecursosProducao(db.Model):
    __tablename__ = 'recursos_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    linha_producao = db.Column(db.String(50), nullable=False, index=True)
    qtd_unidade_por_caixa = db.Column(db.Numeric(10, 2))
    capacidade_unidade_minuto = db.Column(db.Numeric(10, 3), nullable=False)
    qtd_lote_ideal = db.Column(db.Numeric(15, 3))
    qtd_lote_minimo = db.Column(db.Numeric(15, 3))
    eficiencia_media = db.Column(db.Numeric(5, 2), default=85.00)
    tempo_setup = db.Column(db.Integer, default=30)
    disponivel = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('cod_produto', 'linha_producao'),
    )

class OrdemProducao(db.Model):
    __tablename__ = 'ordem_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_ordem = db.Column(db.String(20), unique=True, nullable=False, index=True)
    origem_ordem = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Planejada', index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    materiais_necessarios = db.Column(JSONB)
    qtd_planejada = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_produzida = db.Column(db.Numeric(15, 3), default=0)
    data_inicio_prevista = db.Column(db.Date, nullable=False, index=True)
    data_fim_prevista = db.Column(db.Date, nullable=False)
    data_inicio_real = db.Column(db.Date)
    data_fim_real = db.Column(db.Date)
    linha_producao = db.Column(db.String(50), index=True)
    turno = db.Column(db.String(20))
    lote_producao = db.Column(db.String(50))
    custo_previsto = db.Column(db.Numeric(15, 2))
    custo_real = db.Column(db.Numeric(15, 2))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

class RequisicaoCompras(db.Model):
    __tablename__ = 'requisicao_compras'
    
    id = db.Column(db.Integer, primary_key=True)
    num_requisicao = db.Column(db.String(30), unique=True, nullable=False, index=True)
    data_requisicao_criacao = db.Column(db.Date, nullable=False)
    usuario_requisicao_criacao = db.Column(db.String(100))
    lead_time_requisicao = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_requisicao_solicitada = db.Column(db.Date)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_requisicao = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_produto_sem_requisicao = db.Column(db.Numeric(15, 3), default=0)
    necessidade = db.Column(db.Boolean, default=False)
    data_necessidade = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pendente', index=True)
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class PedidoCompras(db.Model):
    __tablename__ = 'pedido_compras'
    
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(30), unique=True, nullable=False, index=True)
    num_requisicao = db.Column(db.String(30), db.ForeignKey('requisicao_compras.num_requisicao'), index=True)
    cnpj_fornecedor = db.Column(db.String(20), index=True)
    raz_social = db.Column(db.String(255))
    numero_nf = db.Column(db.String(20))
    data_pedido_criacao = db.Column(db.Date)
    usuario_pedido_criacao = db.Column(db.String(100))
    lead_time_pedido = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_pedido_previsao = db.Column(db.Date)
    data_pedido_entrega = db.Column(db.Date)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))
    confirmacao_pedido = db.Column(db.Boolean, default=False)
    confirmado_por = db.Column(db.String(100))
    confirmado_em = db.Column(db.DateTime)
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    requisicao = db.relationship('RequisicaoCompras', backref='pedidos')

class LeadTimeFornecedor(db.Model):
    __tablename__ = 'lead_time_fornecedor'
    
    id = db.Column(db.Integer, primary_key=True)
    cnpj_fornecedor = db.Column(db.String(20), nullable=False, index=True)
    nome_fornecedor = db.Column(db.String(255))
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    lead_time_previsto = db.Column(db.Integer, nullable=False)
    lead_time_historico = db.Column(db.Numeric(5, 1))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('cnpj_fornecedor', 'cod_produto'),
    )

class ListaMateriais(db.Model):
    __tablename__ = 'lista_materiais'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_produzido = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_produzido = db.Column(db.String(255))
    cod_produto_componente = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_componente = db.Column(db.String(255))
    qtd_utilizada = db.Column(db.Numeric(15, 6), nullable=False)
    status = db.Column(db.String(10), default='ativo', index=True)
    versao = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    __table_args__ = (
        db.UniqueConstraint('cod_produto_produzido', 'cod_produto_componente', 'versao'),
    )
```

---

## 4. SEQUÊNCIA DE CRIAÇÃO

### 4.1 Ordem de execução dos SQLs:
1. grupo_empresarial
2. historico_pedidos
3. previsao_demanda
4. plano_mestre_producao
5. recursos_producao
6. ordem_producao
7. requisicao_compras
8. pedido_compras
9. lead_time_fornecedor
10. lista_materiais
11. ALTER TABLE movimentacao_estoque
12. ALTER TABLE cadastro_palletizacao
13. ALTER TABLE carteira_principal

### 4.2 Migration Alembic:
```python
# migrations/versions/XXX_add_manufatura_module.py
def upgrade():
    # Executar SQLs na ordem acima
    pass

def downgrade():
    # DROP TABLES na ordem inversa
    pass
```