from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from app.utils.ufs import UF_LIST

class TransportadoraForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    razao_social = StringField('Razão Social', validators=[DataRequired(), Length(max=120)])
    cidade = StringField('Cidade', validators=[DataRequired(), Length(max=100)])
    uf = SelectField('UF', choices=UF_LIST)
    optante = SelectField('Optante Simples', choices=[('False', 'Não'), ('True', 'Sim')], default='False')
    condicao_pgto = StringField('Condição de Pagamento', validators=[Length(max=50)])
    freteiro = SelectField('É Freteiro?', choices=[('False', 'Não'), ('True', 'Sim')], default='False')

class ImportarTransportadorasForm(FlaskForm):
    arquivo = FileField('Arquivo Excel', validators=[
        FileRequired(message='Por favor, selecione um arquivo'),
        FileAllowed(['xlsx', 'xls'], 'Apenas arquivos Excel (.xlsx ou .xls)')
    ])
    submit = SubmitField('Importar')
