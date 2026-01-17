from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, FileField, IntegerField, HiddenField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from app import db



class TabelaFreteForm(FlaskForm):
    id = HiddenField('ID')  # Para edição
    transportadora = SelectField('Transportadora', coerce=int, validators=[DataRequired()])
    uf_origem = SelectField('UF Origem', validators=[DataRequired()])
    uf_destino = SelectField('UF Destino', validators=[DataRequired()])
    nome_tabela = StringField('Nome da Tabela', validators=[DataRequired()])    
    
    tipo_carga = SelectField('Tipo de Carga', choices=[('FRACIONADA', 'Fracionada'), ('DIRETA', 'Direta')], validators=[DataRequired()])
    modalidade = SelectField('Modalidade (VALOR, PESO ou Veículo)',
                             choices=[
        ('FRETE PESO','Frete Peso'), # noqa: E122
        ('FRETE VALOR','Frete Valor'), # noqa: E122
        ('FIORINO','Fiorino'), # noqa: E122
        ('VAN/HR','Van/HR'), # noqa: E122
        ('MASTER','Master'), # noqa: E122
        ('IVECO','Iveco'), # noqa: E122
        ('3/4','3/4'), # noqa: E122
        ('TOCO','Toco'), # noqa: E122
        ('TRUCK','Truck'), # noqa: E122
        ('CARRETA','Carreta') # noqa: E122
        ], validators=[DataRequired()] # noqa: E122
        ) # noqa: E123

    valor_kg = StringField('R$/kg')
    frete_minimo_peso = StringField('Frete Mínimo por Peso')
    percentual_valor = StringField('% sobre Valor')
    frete_minimo_valor = StringField('Frete Mínimo por Valor')

    percentual_gris = StringField('% GRIS')
    gris_minimo = StringField('GRIS Mínimo (R$)')
    percentual_adv = StringField('% ADV')
    adv_minimo = StringField('ADV Mínimo (R$)')
    percentual_rca = StringField('% RCA / Fluvial')
    pedagio_por_100kg = StringField('Pedágio por 100kg')

    valor_despacho = StringField('Despacho (R$)')
    valor_cte = StringField('CTE (R$)')
    valor_tas = StringField('TAS (R$)')

    icms_incluso = BooleanField('ICMS incluso no valor')
    icms_proprio = StringField('% ICMS Próprio')

    submit = SubmitField('Salvar')
    
    def validate_nome_tabela(self, field):
        """Valida se já existe tabela com a mesma combinação: transportadora + UF destino + nome + modalidade"""
        from app.tabelas.models import TabelaFrete
        
        # Busca tabela com esta combinação
        query = TabelaFrete.query.filter_by(
            transportadora_id=self.transportadora.data,
            uf_destino=self.uf_destino.data,
            nome_tabela=field.data,
            modalidade=self.modalidade.data
        )
        
        # Se é edição, exclui o próprio registro da verificação
        if self.id.data:
            query = query.filter(TabelaFrete.id != int(self.id.data))
        
        tabela_existente = query.first()
        
        if tabela_existente:
            from app.transportadoras.models import Transportadora
            transportadora = db.session.get(Transportadora,self.transportadora.data) if self.transportadora.data else None
            raise ValidationError(f'Já existe tabela "{field.data}" para {transportadora.razao_social} com destino {self.uf_destino.data} e modalidade {self.modalidade.data}')

class ImportarTabelaFreteForm(FlaskForm):
    arquivo = FileField("Arquivo Excel", validators=[DataRequired()])
    submit = SubmitField("Importar")

class GerarTemplateFreteForm(FlaskForm):
    transportadora = SelectField('Transportadora', coerce=int, validators=[DataRequired()])
    tipo_carga = SelectField('Tipo de Carga', 
                           choices=[('FRACIONADA', 'Fracionada'), ('DIRETA', 'Direta')], 
                           validators=[DataRequired()])
    modalidade = SelectField('Modalidade',
                           choices=[
                               ('FRETE PESO','Frete Peso'),
                               ('FRETE VALOR','Frete Valor'),
                               ('FIORINO','Fiorino'),
                               ('VAN/HR','Van/HR'),
                               ('MASTER','Master'),
                               ('IVECO','Iveco'),
                               ('3/4','3/4'),
                               ('TOCO','Toco'),
                               ('TRUCK','Truck'),
                               ('CARRETA','Carreta')
                           ], validators=[DataRequired()])
    uf_origem = SelectField('UF Origem', validators=[DataRequired()])
    uf_destino = SelectField('UF Destino', validators=[DataRequired()])
    icms_incluso = SelectField('ICMS Incluso', 
                             choices=[('N', 'N - Não Incluso'), ('S', 'S - Incluso')], 
                             validators=[DataRequired()], default='N')
    quantidade_linhas = IntegerField('Quantidade de Linhas', validators=[DataRequired(), NumberRange(min=1, max=1000)], default=50)
    submit = SubmitField("Gerar Template")