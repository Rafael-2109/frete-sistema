from app import db
from datetime import datetime

class TabelaFrete(db.Model):
    __tablename__ = 'tabelas_frete'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    uf_origem = db.Column(db.String(2), nullable=False)
    uf_destino = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)

    tipo_carga = db.Column(db.String(20), nullable=False)
    modalidade = db.Column(db.String(50), nullable=False)

    valor_kg = db.Column(db.Float)
    frete_minimo_peso = db.Column(db.Float)
    percentual_valor = db.Column(db.Float)
    frete_minimo_valor = db.Column(db.Float)

    percentual_gris = db.Column(db.Float)
    percentual_adv = db.Column(db.Float)
    percentual_rca = db.Column(db.Float)
    pedagio_por_100kg = db.Column(db.Float)

    valor_despacho = db.Column(db.Float)
    valor_cte = db.Column(db.Float)
    valor_tas = db.Column(db.Float)

    icms_incluso = db.Column(db.Boolean, default=False)
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS (usa o maior entre calculado e mínimo)
    adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV (usa o maior entre calculado e mínimo)
    icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela (substitui ICMS da cidade se informado)

    criado_por = db.Column(db.String(120), nullable=False)  # usuário que criou a tabela
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)  # horário do cadastro automático

    transportadora = db.relationship('Transportadora', backref='tabelas_frete')

    @property
    def status_tabela(self):
        """
        Verifica o status da tabela:
        - 'ok': Tem vínculos apontando para ela
        - 'orfa': Não tem vínculos em lugar nenhum
        - 'grupo_empresarial': Tem vínculos em transportadora do mesmo grupo
        """
        from app.vinculos.models import CidadeAtendida
        
        # 1. Verifica se existe vínculo na mesma transportadora
        vinculo_mesmo_transp = CidadeAtendida.query.filter_by(
            transportadora_id=self.transportadora_id,
            nome_tabela=self.nome_tabela
        ).first()
        
        if vinculo_mesmo_transp:
            return 'ok'
        
        # 2. Verifica se existe vínculo em transportadora do mesmo grupo (nome similar)
        transportadora_atual = self.transportadora.razao_social.upper()
        # Remove palavras comuns para encontrar o nome base
        nome_base = transportadora_atual.replace('LTDA', '').replace('EIRELI', '').replace('S.A.', '').replace('S/A', '').strip()
        
        from app.transportadoras.models import Transportadora
        from sqlalchemy import func
        
        transportadoras_grupo = Transportadora.query.filter(
            func.upper(Transportadora.razao_social).like(f'%{nome_base[:20]}%'),
            Transportadora.id != self.transportadora_id
        ).all()
        
        for transp in transportadoras_grupo:
            vinculo_grupo = CidadeAtendida.query.filter_by(
                transportadora_id=transp.id,
                nome_tabela=self.nome_tabela
            ).first()
            if vinculo_grupo:
                return 'grupo_empresarial'
        
        # 3. Não existe vínculo em lugar nenhum
        return 'orfa'

    @property
    def status_cor(self):
        """Retorna a cor para exibição do status"""
        status = self.status_tabela
        cores = {
            'ok': 'success',
            'orfa': 'danger',
            'grupo_empresarial': 'info'
        }
        return cores.get(status, 'secondary')

    @property
    def status_texto(self):
        """Retorna o texto para exibição do status"""
        status = self.status_tabela
        textos = {
            'ok': '✅ OK',
            'orfa': '❌ Órfã',
            'grupo_empresarial': 'ℹ️ Mesmo Grupo'
        }
        return textos.get(status, '❓ Desconhecido')

    def __repr__(self):
        return f'<TabelaFrete {self.tipo_carga} - {self.modalidade}>'

class HistoricoTabelaFrete(db.Model):
    __tablename__ = 'historico_tabelas_frete'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    uf_origem = db.Column(db.String(2), nullable=False)
    uf_destino = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)

    tipo_carga = db.Column(db.String(20), nullable=False)
    modalidade = db.Column(db.String(50), nullable=False)

    valor_kg = db.Column(db.Float) #frete peso
    frete_minimo_peso = db.Column(db.Float) #peso minimo
    percentual_valor = db.Column(db.Float) #frete valor
    frete_minimo_valor = db.Column(db.Float) #valor minimo

    percentual_gris = db.Column(db.Float) #frete valor
    percentual_adv = db.Column(db.Float) #frete valor
    percentual_rca = db.Column(db.Float) #frete valor
    pedagio_por_100kg = db.Column(db.Float) #pedagio

    valor_despacho = db.Column(db.Float) #Fixo
    valor_cte = db.Column(db.Float) #Fixo
    valor_tas = db.Column(db.Float) #Fixo

    icms_incluso = db.Column(db.Boolean, default=False)
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela

    criado_por = db.Column(db.String(120), nullable=False)  # usuário que criou a tabela
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)  # horário do cadastro automático

    transportadora = db.relationship('Transportadora', backref='historico_tabelas_frete')