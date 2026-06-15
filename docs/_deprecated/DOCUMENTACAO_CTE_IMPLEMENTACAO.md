# 📋 IMPLEMENTAÇÃO: Tabela de Conhecimento de Transporte (CTe)

**Data de Criação**: 13/11/2025
**Objetivo**: Criar estrutura para registrar CTes do Odoo e sincronizar com Fretes do sistema
**Status**: 🟡 Aguardando Implementação

---

## 🎯 CONTEXTO E OBJETIVO

### Situação Atual
O sistema já possui:
- ✅ **Módulo de Fretes** funcionando (`app/fretes/`)
- ✅ **Integração com Odoo** via `app/odoo/`
- ✅ **Modelo DFe** no Odoo: `l10n_br_ciel_it_account.dfe`
- ✅ **Sistema de sincronização** de NFs de entrada (pedidos de compras)

### O Que Precisa Ser Feito
Criar sistema para:
1. **Buscar CTes** do Odoo usando filtro específico
2. **Armazenar CTes** em tabela local
3. **Sincronizar com Fretes** do sistema
4. **Baixar PDFs/XMLs** dos CTes (similar ao que foi feito com NFs)

---

## 📊 ESTRUTURA DO MODELO: ConhecimentoTransporte

### Localização
**Arquivo**: `app/fretes/models.py` (adicionar ao módulo de fretes)

### Campos do Modelo

```python
class ConhecimentoTransporte(db.Model):
    """
    Modelo para registrar Conhecimentos de Transporte (CTe) do Odoo
    e vincular com fretes do sistema
    """
    __tablename__ = 'conhecimento_transporte'

    id = db.Column(db.Integer, primary_key=True)

    # ================================================
    # VÍNCULO COM ODOO
    # ================================================
    dfe_id = db.Column(db.String(50), nullable=False, unique=True, index=True)  # ID do DFe no Odoo
    odoo_ativo = db.Column(db.Boolean, default=True)  # Campo active do Odoo

    # ================================================
    # DADOS DO CTe (campos do DFe do Odoo)
    # ================================================
    # Chave e Numeração
    chave_acesso = db.Column(db.String(44), nullable=True, index=True)  # protnfe_infnfe_chnfe
    numero_cte = db.Column(db.String(20), nullable=True, index=True)    # nfe_infnfe_ide_nnf
    serie_cte = db.Column(db.String(10), nullable=True)                 # nfe_infnfe_ide_serie

    # Datas
    data_emissao = db.Column(db.Date, nullable=True, index=True)        # nfe_infnfe_ide_dhemi

    # Valores
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)           # nfe_infnfe_total_icmstot_vnf
    valor_frete = db.Column(db.Numeric(15, 2), nullable=True)           # nfe_infnfe_total_icms_vfrete

    # Emissor (Transportadora)
    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True) # nfe_infnfe_emit_cnpj
    nome_emitente = db.Column(db.String(255), nullable=True)            # nfe_infnfe_emit_xnome

    # Destinatário (Cliente que recebe a mercadoria)
    cnpj_destinatario = db.Column(db.String(20), nullable=True)         # nfe_infnfe_dest_cnpj

    # Remetente (Quem envia a mercadoria)
    cnpj_remetente = db.Column(db.String(20), nullable=True, index=True) # nfe_infnfe_rem_cnpj

    # Expedidor (Se houver)
    cnpj_expedidor = db.Column(db.String(20), nullable=True)            # nfe_infnfe_exped_cnpj

    # Dados Adicionais
    informacoes_complementares = db.Column(db.Text, nullable=True)      # nfe_infnfe_infadic_infcpl

    # ================================================
    # ARQUIVOS (PDF/XML)
    # ================================================
    cte_pdf_path = db.Column(db.String(500), nullable=True)  # Caminho S3/local do PDF
    cte_xml_path = db.Column(db.String(500), nullable=True)  # Caminho S3/local do XML

    # ================================================
    # VÍNCULO COM FRETE DO SISTEMA
    # ================================================
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=True, index=True)
    vinculado_manualmente = db.Column(db.Boolean, default=False)  # Se foi vinculado manualmente

    # Relacionamento
    frete = db.relationship('Frete', backref='conhecimentos_transporte', lazy=True)

    # ================================================
    # AUDITORIA
    # ================================================
    importado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    importado_por = db.Column(db.String(100), default='Sistema Odoo')
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # ================================================
    # ÍNDICES
    # ================================================
    __table_args__ = (
        db.Index('idx_cte_chave_acesso', 'chave_acesso'),
        db.Index('idx_cte_numero', 'numero_cte', 'serie_cte'),
        db.Index('idx_cte_cnpj_emitente', 'cnpj_emitente'),
        db.Index('idx_cte_cnpj_remetente', 'cnpj_remetente'),
        db.Index('idx_cte_data_emissao', 'data_emissao'),
        db.Index('idx_cte_frete', 'frete_id'),
    )

    def __repr__(self):
        return f'<CTe {self.numero_cte} - {self.nome_emitente}>'

    def to_dict(self):
        return {
            'id': self.id,
            'dfe_id': self.dfe_id,
            'chave_acesso': self.chave_acesso,
            'numero_cte': self.numero_cte,
            'serie_cte': self.serie_cte,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'valor_total': float(self.valor_total) if self.valor_total else 0,
            'valor_frete': float(self.valor_frete) if self.valor_frete else 0,
            'cnpj_emitente': self.cnpj_emitente,
            'nome_emitente': self.nome_emitente,
            'cnpj_destinatario': self.cnpj_destinatario,
            'cnpj_remetente': self.cnpj_remetente,
            'frete_id': self.frete_id,
            'cte_pdf_path': self.cte_pdf_path,
            'cte_xml_path': self.cte_xml_path,
            'importado_em': self.importado_em.isoformat() if self.importado_em else None
        }
```

---

## 🔧 MIGRATION: Criar Tabela

### Script Python (Local)
**Arquivo**: `scripts/migrations/criar_tabela_conhecimento_transporte.py`

```python
"""
Migration: Criar tabela conhecimento_transporte
================================================

OBJETIVO: Criar tabela para armazenar CTes do Odoo e vincular com fretes

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

def criar_tabela_cte():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Criar tabela conhecimento_transporte")
            print("=" * 80)

            # Verificar se tabela já existe
            print("\n1️⃣ Verificando se tabela já existe...")

            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'conhecimento_transporte'
                )
            """))

            existe = resultado.scalar()

            if existe:
                print("⚠️  Tabela já existe! Nada a fazer.")
                return

            print("✅ Tabela não existe. Criando...")

            # Criar tabela
            print("\n2️⃣ Criando tabela conhecimento_transporte...")

            db.session.execute(text("""
                CREATE TABLE conhecimento_transporte (
                    id SERIAL PRIMARY KEY,

                    -- Vínculo Odoo
                    dfe_id VARCHAR(50) NOT NULL UNIQUE,
                    odoo_ativo BOOLEAN DEFAULT TRUE,

                    -- Dados CTe
                    chave_acesso VARCHAR(44),
                    numero_cte VARCHAR(20),
                    serie_cte VARCHAR(10),
                    data_emissao DATE,
                    valor_total NUMERIC(15, 2),
                    valor_frete NUMERIC(15, 2),

                    -- Partes
                    cnpj_emitente VARCHAR(20),
                    nome_emitente VARCHAR(255),
                    cnpj_destinatario VARCHAR(20),
                    cnpj_remetente VARCHAR(20),
                    cnpj_expedidor VARCHAR(20),

                    -- Dados adicionais
                    informacoes_complementares TEXT,

                    -- Arquivos
                    cte_pdf_path VARCHAR(500),
                    cte_xml_path VARCHAR(500),

                    -- Vínculo com frete
                    frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
                    vinculado_manualmente BOOLEAN DEFAULT FALSE,

                    -- Auditoria
                    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    importado_por VARCHAR(100) DEFAULT 'Sistema Odoo',
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),
                    ativo BOOLEAN DEFAULT TRUE
                )
            """))

            db.session.commit()
            print("✅ Tabela criada com sucesso!")

            # Criar índices
            print("\n3️⃣ Criando índices...")

            indices = [
                ("idx_cte_dfe_id", "dfe_id"),
                ("idx_cte_chave_acesso", "chave_acesso"),
                ("idx_cte_numero_serie", "numero_cte, serie_cte"),
                ("idx_cte_cnpj_emitente", "cnpj_emitente"),
                ("idx_cte_cnpj_remetente", "cnpj_remetente"),
                ("idx_cte_data_emissao", "data_emissao"),
                ("idx_cte_frete", "frete_id"),
                ("idx_cte_ativo", "ativo"),
            ]

            for nome_indice, campos in indices:
                print(f"   📊 Criando índice {nome_indice}...")
                db.session.execute(text(f"""
                    CREATE INDEX {nome_indice} ON conhecimento_transporte ({campos})
                """))

            db.session.commit()
            print("✅ Índices criados com sucesso!")

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            raise

if __name__ == '__main__':
    criar_tabela_cte()
```

### Script SQL (Render)
**Arquivo**: `scripts/migrations/criar_tabela_conhecimento_transporte.sql`

```sql
-- ============================================================================
-- Migration: Criar tabela conhecimento_transporte
-- ============================================================================
-- OBJETIVO: Criar tabela para armazenar CTes do Odoo
-- DATA: 13/11/2025
-- EXECUTAR NO: Shell do Render (psql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conhecimento_transporte (
    id SERIAL PRIMARY KEY,

    -- Vínculo Odoo
    dfe_id VARCHAR(50) NOT NULL UNIQUE,
    odoo_ativo BOOLEAN DEFAULT TRUE,

    -- Dados CTe
    chave_acesso VARCHAR(44),
    numero_cte VARCHAR(20),
    serie_cte VARCHAR(10),
    data_emissao DATE,
    valor_total NUMERIC(15, 2),
    valor_frete NUMERIC(15, 2),

    -- Partes
    cnpj_emitente VARCHAR(20),
    nome_emitente VARCHAR(255),
    cnpj_destinatario VARCHAR(20),
    cnpj_remetente VARCHAR(20),
    cnpj_expedidor VARCHAR(20),

    -- Dados adicionais
    informacoes_complementares TEXT,

    -- Arquivos
    cte_pdf_path VARCHAR(500),
    cte_xml_path VARCHAR(500),

    -- Vínculo com frete
    frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
    vinculado_manualmente BOOLEAN DEFAULT FALSE,

    -- Auditoria
    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    importado_por VARCHAR(100) DEFAULT 'Sistema Odoo',
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_cte_dfe_id ON conhecimento_transporte (dfe_id);
CREATE INDEX IF NOT EXISTS idx_cte_chave_acesso ON conhecimento_transporte (chave_acesso);
CREATE INDEX IF NOT EXISTS idx_cte_numero_serie ON conhecimento_transporte (numero_cte, serie_cte);
CREATE INDEX IF NOT EXISTS idx_cte_cnpj_emitente ON conhecimento_transporte (cnpj_emitente);
CREATE INDEX IF NOT EXISTS idx_cte_cnpj_remetente ON conhecimento_transporte (cnpj_remetente);
CREATE INDEX IF NOT EXISTS idx_cte_data_emissao ON conhecimento_transporte (data_emissao);
CREATE INDEX IF NOT EXISTS idx_cte_frete ON conhecimento_transporte (frete_id);
CREATE INDEX IF NOT EXISTS idx_cte_ativo ON conhecimento_transporte (ativo);

-- Verificar criação
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
ORDER BY ordinal_position;
```

---

## 🔄 SERVIÇO DE SINCRONIZAÇÃO: CteService

### Localização
**Arquivo**: `app/odoo/services/cte_service.py`

### Estrutura do Serviço

```python
"""
Service para Importação de CTes (Conhecimento de Transporte) do Odoo
====================================================================

OBJETIVO:
    Buscar CTes do Odoo (modelo l10n_br_ciel_it_account.dfe)
    e registrar em ConhecimentoTransporte

FILTRO ODOO:
    ["&", "|", ("active", "=", True), ("active", "=", False), ("is_cte", "=", True)]

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import base64
from io import BytesIO

from app import db
from app.fretes.models import ConhecimentoTransporte, Frete
from app.odoo.utils.connection import get_odoo_connection
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)


class CteService:
    """
    Service para importação de CTes do Odoo
    """

    def __init__(self):
        """Inicializa conexão com Odoo"""
        self.odoo = get_odoo_connection()
        self.file_storage = get_file_storage()

    def importar_ctes(
        self,
        dias_retroativos: int = 30,
        limite: Optional[int] = None
    ) -> Dict:
        """
        Importa CTes do Odoo

        Args:
            dias_retroativos: Quantos dias para trás buscar (padrão: 30)
            limite: Limite de registros (None = todos)

        Returns:
            Dict com estatísticas da importação
        """
        logger.info("=" * 80)
        logger.info("📄 INICIANDO IMPORTAÇÃO DE CTes")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'ctes_processados': 0,
            'ctes_novos': 0,
            'ctes_atualizados': 0,
            'ctes_ignorados': 0,
            'erros': []
        }

        try:
            # 1. Buscar CTes do Odoo
            data_inicio = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')
            logger.info(f"📅 Buscando CTes desde {data_inicio}")

            ctes = self._buscar_ctes_odoo(data_inicio, limite)

            if not ctes:
                logger.warning("⚠️  Nenhum CTe encontrado no Odoo")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"📦 Total de CTes encontrados: {len(ctes)}")

            # 2. Processar cada CTe
            for cte_data in ctes:
                try:
                    dfe_id = str(cte_data.get('id'))
                    logger.info(f"\n📋 Processando CTe: DFe ID {dfe_id}")

                    estatisticas = self._processar_cte(cte_data)

                    resultado['ctes_processados'] += 1
                    if estatisticas.get('novo'):
                        resultado['ctes_novos'] += 1
                    else:
                        resultado['ctes_atualizados'] += 1

                except Exception as e:
                    erro_msg = f"Erro ao processar CTe {cte_data.get('id')}: {str(e)}"
                    logger.error(f"❌ {erro_msg}")
                    resultado['erros'].append(erro_msg)

            # 3. Commit final
            db.session.commit()

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("✅ IMPORTAÇÃO DE CTes CONCLUÍDA")
            logger.info(f"   📊 Processados: {resultado['ctes_processados']}")
            logger.info(f"   ✨ Novos: {resultado['ctes_novos']}")
            logger.info(f"   🔄 Atualizados: {resultado['ctes_atualizados']}")
            logger.info(f"   ❌ Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importação de CTes: {str(e)}"
            logger.error(f"❌ {erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_ctes_odoo(
        self,
        data_inicio: str,
        limite: Optional[int]
    ) -> List[Dict]:
        """
        Busca CTes no Odoo

        Filtro: ["&", "|", ("active", "=", True), ("active", "=", False), ("is_cte", "=", True)]

        Args:
            data_inicio: Data mínima (YYYY-MM-DD)
            limite: Limite de registros

        Returns:
            Lista de CTes
        """
        try:
            # Filtro conforme especificado
            filtros = [
                "&",
                "|",
                ("active", "=", True),
                ("active", "=", False),
                ("is_cte", "=", True),
                # Adicionar filtro de data se campo existir
                # ("nfe_infnfe_ide_dhemi", ">=", data_inicio)
            ]

            campos = [
                'id',
                'active',
                # Chave e numeração
                'protnfe_infnfe_chnfe',  # Chave de acesso
                'nfe_infnfe_ide_nnf',     # Número do CTe
                'nfe_infnfe_ide_serie',   # Série

                # Data
                'nfe_infnfe_ide_dhemi',   # Data de emissão

                # Valores
                'nfe_infnfe_total_icmstot_vnf',  # Valor total
                'nfe_infnfe_total_icms_vfrete',  # Valor do frete

                # Emissor (Transportadora)
                'nfe_infnfe_emit_cnpj',
                'nfe_infnfe_emit_xnome',

                # Destinatário
                'nfe_infnfe_dest_cnpj',

                # Remetente
                'nfe_infnfe_rem_cnpj',

                # Expedidor
                'nfe_infnfe_exped_cnpj',

                # Informações complementares
                'nfe_infnfe_infadic_infcpl',

                # Arquivos
                'l10n_br_pdf_dfe',
                'l10n_br_pdf_dfe_fname',
                'l10n_br_xml_dfe',
                'l10n_br_xml_dfe_fname',
            ]

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            ctes = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'search_read',
                [filtros],
                params
            )

            return ctes or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar CTes do Odoo: {e}")
            return []

    def _processar_cte(self, cte_data: Dict) -> Dict:
        """
        Processa um CTe e cria/atualiza ConhecimentoTransporte

        Args:
            cte_data: Dados do CTe do Odoo

        Returns:
            Dict com estatísticas
        """
        dfe_id = str(cte_data.get('id'))

        # Verificar se já existe
        cte_existente = ConhecimentoTransporte.query.filter_by(dfe_id=dfe_id).first()

        # Extrair dados
        chave_acesso = cte_data.get('protnfe_infnfe_chnfe')
        numero_cte = cte_data.get('nfe_infnfe_ide_nnf')
        serie_cte = cte_data.get('nfe_infnfe_ide_serie')

        # Data
        data_emissao_str = cte_data.get('nfe_infnfe_ide_dhemi')
        data_emissao = None
        if data_emissao_str:
            try:
                if isinstance(data_emissao_str, str):
                    data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()
                else:
                    data_emissao = data_emissao_str
            except Exception:
                pass

        # Valores
        valor_total = cte_data.get('nfe_infnfe_total_icmstot_vnf')
        valor_frete = cte_data.get('nfe_infnfe_total_icms_vfrete')

        # Limpar CNPJs
        cnpj_emitente = cte_data.get('nfe_infnfe_emit_cnpj')
        nome_emitente = cte_data.get('nfe_infnfe_emit_xnome')
        cnpj_destinatario = cte_data.get('nfe_infnfe_dest_cnpj')
        cnpj_remetente = cte_data.get('nfe_infnfe_rem_cnpj')
        cnpj_expedidor = cte_data.get('nfe_infnfe_exped_cnpj')

        # Informações complementares
        info_complementares = cte_data.get('nfe_infnfe_infadic_infcpl')

        # Baixar e salvar PDF/XML
        pdf_path, xml_path = self._salvar_arquivos_cte(cte_data, cnpj_emitente)

        if cte_existente:
            # Atualizar
            logger.info(f"   🔄 Atualizando CTe existente: {numero_cte}")

            cte_existente.odoo_ativo = cte_data.get('active', True)
            cte_existente.chave_acesso = chave_acesso
            cte_existente.numero_cte = numero_cte
            cte_existente.serie_cte = serie_cte
            cte_existente.data_emissao = data_emissao
            cte_existente.valor_total = Decimal(str(valor_total)) if valor_total else None
            cte_existente.valor_frete = Decimal(str(valor_frete)) if valor_frete else None
            cte_existente.cnpj_emitente = cnpj_emitente
            cte_existente.nome_emitente = nome_emitente
            cte_existente.cnpj_destinatario = cnpj_destinatario
            cte_existente.cnpj_remetente = cnpj_remetente
            cte_existente.cnpj_expedidor = cnpj_expedidor
            cte_existente.informacoes_complementares = info_complementares
            cte_existente.cte_pdf_path = pdf_path
            cte_existente.cte_xml_path = xml_path
            cte_existente.atualizado_em = datetime.now()
            cte_existente.atualizado_por = 'Sistema Odoo'

            return {'novo': False}

        else:
            # Criar novo
            logger.info(f"   ✨ Criando novo CTe: {numero_cte}")

            cte = ConhecimentoTransporte(
                dfe_id=dfe_id,
                odoo_ativo=cte_data.get('active', True),
                chave_acesso=chave_acesso,
                numero_cte=numero_cte,
                serie_cte=serie_cte,
                data_emissao=data_emissao,
                valor_total=Decimal(str(valor_total)) if valor_total else None,
                valor_frete=Decimal(str(valor_frete)) if valor_frete else None,
                cnpj_emitente=cnpj_emitente,
                nome_emitente=nome_emitente,
                cnpj_destinatario=cnpj_destinatario,
                cnpj_remetente=cnpj_remetente,
                cnpj_expedidor=cnpj_expedidor,
                informacoes_complementares=info_complementares,
                cte_pdf_path=pdf_path,
                cte_xml_path=xml_path,
                importado_por='Sistema Odoo'
            )

            db.session.add(cte)

            return {'novo': True}

    def _salvar_arquivos_cte(
        self,
        cte_data: Dict,
        cnpj_emitente: str
    ) -> tuple:
        """
        Salva PDF e XML do CTe em S3/local

        Args:
            cte_data: Dados do CTe
            cnpj_emitente: CNPJ da transportadora

        Returns:
            tuple: (pdf_path, xml_path)
        """
        pdf_path = None
        xml_path = None

        # Limpar CNPJ para pasta
        cnpj_limpo = cnpj_emitente.replace('.', '').replace('/', '').replace('-', '') if cnpj_emitente else 'sem_cnpj'

        # Organizar em pastas por data
        data_hoje = datetime.now()
        pasta_base = f"ctes/{data_hoje.year}/{data_hoje.month:02d}/{cnpj_limpo}"

        # Chave de acesso para nome do arquivo
        chave_acesso = cte_data.get('protnfe_infnfe_chnfe', str(cte_data['id']))

        # Salvar PDF
        pdf_base64 = cte_data.get('l10n_br_pdf_dfe')
        if pdf_base64:
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                pdf_file = BytesIO(pdf_bytes)
                pdf_file.name = f"{chave_acesso}.pdf"

                pdf_path = self.file_storage.save_file(
                    file=pdf_file,
                    folder=pasta_base,
                    filename=f"{chave_acesso}.pdf",
                    allowed_extensions=['pdf']
                )

                if pdf_path:
                    logger.info(f"   ✅ PDF salvo: {pdf_path}")
            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar PDF: {e}")

        # Salvar XML
        xml_base64 = cte_data.get('l10n_br_xml_dfe')
        if xml_base64:
            try:
                xml_bytes = base64.b64decode(xml_base64)
                xml_file = BytesIO(xml_bytes)
                xml_file.name = f"{chave_acesso}.xml"

                xml_path = self.file_storage.save_file(
                    file=xml_file,
                    folder=pasta_base,
                    filename=f"{chave_acesso}.xml",
                    allowed_extensions=['xml']
                )

                if xml_path:
                    logger.info(f"   ✅ XML salvo: {xml_path}")
            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar XML: {e}")

        return pdf_path, xml_path

    def vincular_cte_com_frete(
        self,
        cte_id: int,
        frete_id: int,
        manual: bool = True
    ) -> bool:
        """
        Vincula um CTe com um Frete do sistema

        Args:
            cte_id: ID do ConhecimentoTransporte
            frete_id: ID do Frete
            manual: Se o vínculo foi manual ou automático

        Returns:
            bool: True se vinculado com sucesso
        """
        try:
            cte = ConhecimentoTransporte.query.get(cte_id)
            frete = Frete.query.get(frete_id)

            if not cte or not frete:
                return False

            cte.frete_id = frete_id
            cte.vinculado_manualmente = manual
            cte.atualizado_em = datetime.now()

            db.session.commit()

            logger.info(f"✅ CTe {cte.numero_cte} vinculado ao Frete {frete.id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao vincular CTe com Frete: {e}")
            return False
```

---

## 🎯 PRÓXIMOS PASSOS (Ordem de Implementação)

### 1️⃣ **Criar Modelo** ✅
- [ ] Adicionar modelo `ConhecimentoTransporte` em `app/fretes/models.py`
- [ ] Executar migration local
- [ ] Executar migration no Render

### 2️⃣ **Criar Serviço de Sincronização** ✅
- [ ] Criar `app/odoo/services/cte_service.py`
- [ ] Testar busca de CTes do Odoo
- [ ] Testar download de PDF/XML
- [ ] Testar inserção no banco

### 3️⃣ **Criar Rotas e Interface** 📋
- [ ] Criar blueprint `app/fretes/cte_routes.py`
- [ ] Rota: `/fretes/ctes` - Listar CTes
- [ ] Rota: `/fretes/ctes/sincronizar` - Sincronizar com Odoo
- [ ] Rota: `/fretes/ctes/<id>/pdf` - Visualizar PDF
- [ ] Rota: `/fretes/ctes/<id>/vincular-frete` - Vincular com frete
- [ ] Template: `templates/fretes/ctes/index.html`

### 4️⃣ **Vincular com Fretes** 🔗
- [ ] Lógica automática de vinculação (por CNPJ, data, valor)
- [ ] Interface manual de vinculação
- [ ] Mostrar CTe na tela de detalhes do frete

### 5️⃣ **Dashboard e Relatórios** 📊
- [ ] Card: "CTes não vinculados"
- [ ] Card: "CTes importados este mês"
- [ ] Filtros: Por transportadora, por período, por status

---

## 📝 NOTAS IMPORTANTES

### Filtro do Odoo
```python
# SEMPRE usar este filtro para buscar CTes:
filtros = [
    "&",
    "|",
    ("active", "=", True),
    ("active", "=", False),
    ("is_cte", "=", True)
]
```

### Campos do DFe para CTe
Os campos são os MESMOS do modelo DFe usado para NFe, porém o conteúdo é específico de CTe:
- `protnfe_infnfe_chnfe` → Chave de acesso do CTe
- `nfe_infnfe_ide_nnf` → Número do CTe
- `nfe_infnfe_emit_cnpj` → CNPJ da transportadora
- `nfe_infnfe_rem_cnpj` → CNPJ do remetente (quem envia a carga)

### Estrutura de Pastas S3/Local
```
ctes/
  └─ YYYY/
      └─ MM/
          └─ {cnpj_transportadora}/
              ├─ {chave_acesso}.pdf
              └─ {chave_acesso}.xml
```

### Relação com Fretes
Um **CTe** pode estar vinculado a **UM Frete** do sistema.
Um **Frete** pode ter **VÁRIOS CTes** (ex: frete com múltiplas entregas).

---

## 🔗 REFERÊNCIAS

### Arquivos Relacionados
- `app/fretes/models.py` - Modelo Frete existente
- `app/odoo/services/entrada_material_service.py` - Exemplo de sincronização similar
- `app/manufatura/routes/pedidos_compras_routes.py` - Exemplo de rota para visualizar PDF
- `app/utils/file_storage.py` - Sistema de armazenamento S3/local

### Documentação Existente
- `CLAUDE.md` - Referência de modelos e campos
- `IMPLEMENTACAO_ENTRADAS_MATERIAIS_RESUMO.md` - Resumo de implementação similar

---

## ✅ CHECKLIST FINAL

Antes de começar, certifique-se de:
- [ ] Ler este documento completamente
- [ ] Entender o fluxo de importação de NFs (similar ao CTe)
- [ ] Verificar modelo `Frete` existente
- [ ] Testar filtro do Odoo para garantir que retorna CTes
- [ ] Executar migrations localmente antes do Render

---

**Documento criado em**: 13/11/2025
**Última atualização**: 13/11/2025
**Status**: 🟢 Pronto para implementação
