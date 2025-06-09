from app import db


class CidadeAtendida(db.Model):
    __tablename__ = 'cidades_atendidas'

    id = db.Column(db.Integer, primary_key=True)
    uf = db.Column(db.String(2), nullable=False)
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidades.id'), nullable=False)
    codigo_ibge = db.Column(db.String(10), nullable=False)  # 🔄 novo campo
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)
    lead_time = db.Column(db.Integer)

    cidade = db.relationship('Cidade', backref='cidades_atendidas')
    transportadora = db.relationship('Transportadora', backref='cidades_atendidas')

    @property
    def status_vinculo(self):
        """
        Verifica o status do vínculo:
        - 'ok': Tabela existe na mesma transportadora
        - 'orfao': Tabela não existe em lugar nenhum
        - 'transportadora_errada': Tabela existe em outra transportadora
        """
        from app.tabelas.models import TabelaFrete
        
        # 1. Verifica se existe tabela na mesma transportadora
        tabela_mesma_transp = TabelaFrete.query.filter_by(
            transportadora_id=self.transportadora_id,
            nome_tabela=self.nome_tabela
        ).first()
        
        if tabela_mesma_transp:
            return 'ok'
        
        # 2. Verifica se existe tabela em transportadora do mesmo grupo (nome similar)
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
            tabela_grupo = TabelaFrete.query.filter_by(
                transportadora_id=transp.id,
                nome_tabela=self.nome_tabela
            ).first()
            if tabela_grupo:
                return 'grupo_empresarial'
        
        # 3. Verifica se existe em qualquer outra transportadora
        tabela_outra = TabelaFrete.query.filter(
            TabelaFrete.nome_tabela == self.nome_tabela,
            TabelaFrete.transportadora_id != self.transportadora_id
        ).first()
        
        if tabela_outra:
            return 'transportadora_errada'
        
        # 4. Não existe em lugar nenhum
        return 'orfao'

    @property
    def status_cor(self):
        """Retorna a cor para exibição do status"""
        status = self.status_vinculo
        cores = {
            'ok': 'success',
            'orfao': 'danger', 
            'transportadora_errada': 'warning',
            'grupo_empresarial': 'info'
        }
        return cores.get(status, 'secondary')

    @property
    def status_texto(self):
        """Retorna o texto para exibição do status"""
        status = self.status_vinculo
        textos = {
            'ok': '✅ OK',
            'orfao': '❌ Órfão',
            'transportadora_errada': '⚠️ Transp. Errada',
            'grupo_empresarial': 'ℹ️ Mesmo Grupo'
        }
        return textos.get(status, '❓ Desconhecido')

    def __repr__(self):
        return f"<CidadeAtendida {self.cidade.nome} ({self.nome_tabela}) por {self.transportadora.razao_social}>"
