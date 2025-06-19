from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError
from app.utils.ufs import UF_LIST

class TransportadoraForm(FlaskForm):
    id = HiddenField('ID')  # Para edição
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    razao_social = StringField('Razão Social', validators=[DataRequired(), Length(max=120)])
    cidade = StringField('Cidade', validators=[DataRequired(), Length(max=100)])
    uf = SelectField('UF', choices=UF_LIST)
    optante = SelectField('Optante Simples', choices=[('False', 'Não'), ('True', 'Sim')], default='False')
    condicao_pgto = StringField('Condição de Pagamento', validators=[Length(max=50)])
    freteiro = SelectField('É Freteiro?', choices=[('False', 'Não'), ('True', 'Sim')], default='False')
    
    def validate_cnpj(self, field):
        from app.transportadoras.models import Transportadora
        
        # Limpa o CNPJ (remove caracteres especiais)
        cnpj_limpo = ''.join(filter(str.isdigit, field.data))
        
        # Busca transportadora com este CNPJ
        query = Transportadora.query.filter_by(cnpj=cnpj_limpo)
        
        # Se é edição, exclui o próprio registro da verificação
        if self.id.data:
            query = query.filter(Transportadora.id != int(self.id.data))
        
        transportadora_existente = query.first()
        
        if transportadora_existente:
            raise ValidationError(f'CNPJ já cadastrado para a transportadora: {transportadora_existente.razao_social}')

class ImportarTransportadorasForm(FlaskForm):
    arquivo = FileField('Arquivo Excel', validators=[
        FileRequired(message='Por favor, selecione um arquivo'),
        FileAllowed(['xlsx', 'xls'], 'Apenas arquivos Excel (.xlsx ou .xls)')
    ])
    submit = SubmitField('Importar')
