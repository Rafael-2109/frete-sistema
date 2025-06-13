from flask_wtf import FlaskForm

from wtforms.validators import DataRequired

from wtforms import StringField
from wtforms import SubmitField
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import FileField
from wtforms import IntegerField
from wtforms.validators import NumberRange



class TabelaFreteForm(FlaskForm):
    transportadora = SelectField('Transportadora', coerce=int, validators=[DataRequired()])
    uf_origem = SelectField('UF Origem', validators=[DataRequired()])
    uf_destino = SelectField('UF Destino', validators=[DataRequired()])
    nome_tabela = StringField('Nome da Tabela', validators=[DataRequired()])    
    
    tipo_carga = SelectField('Tipo de Carga', choices=[('FRACIONADA', 'Fracionada'), ('DIRETA', 'Direta')], validators=[DataRequired()])
    modalidade = SelectField('Modalidade (VALOR, PESO ou Veículo)',
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
        ], validators=[DataRequired()]
        )

    valor_kg = StringField('R$/kg')
    frete_minimo_peso = StringField('Frete Mínimo por Peso')
    percentual_valor = StringField('% sobre Valor')
    frete_minimo_valor = StringField('Frete Mínimo por Valor')

    percentual_gris = StringField('% GRIS')
    percentual_adv = StringField('% ADV')
    percentual_rca = StringField('% RCA / Fluvial')
    pedagio_por_100kg = StringField('Pedágio por 100kg')

    valor_despacho = StringField('Despacho (R$)')
    valor_cte = StringField('CTE (R$)')
    valor_tas = StringField('TAS (R$)')

    icms_incluso = BooleanField('ICMS incluso no valor')

    submit = SubmitField('Salvar')

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
    quantidade_linhas = IntegerField('Quantidade de Linhas', validators=[DataRequired(), NumberRange(min=1, max=1000)], default=50)
    submit = SubmitField("Gerar Template")