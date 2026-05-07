from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError
from app import db
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
        from app.utils.cnpj_utils import validar_cnpj, validar_cpf

        # Limpa o documento (remove caracteres especiais)
        digitos = ''.join(filter(str.isdigit, field.data or ''))

        # Validar digitos verificadores conforme tipo (CPF=11, CNPJ=14)
        if digitos:
            if len(digitos) == 14:
                if not validar_cnpj(digitos):
                    raise ValidationError('CNPJ invalido (digito verificador).')
            elif len(digitos) == 11:
                if not validar_cpf(digitos):
                    raise ValidationError('CPF invalido (digito verificador).')
            else:
                raise ValidationError('Documento invalido: informe CPF (11 digitos) ou CNPJ (14 digitos).')

        # Busca transportadora com este documento (compara pelos digitos limpos
        # para tolerar diferencas de formatacao no que ja esta gravado)
        query = Transportadora.query.filter(
            db.func.regexp_replace(Transportadora.cnpj, r'\D', '', 'g') == digitos
        )

        # Se é edição, exclui o próprio registro da verificação
        if self.id.data:
            query = query.filter(Transportadora.id != int(self.id.data))

        transportadora_existente = query.first()

        if transportadora_existente:
            raise ValidationError(f'CPF/CNPJ ja cadastrado para a transportadora: {transportadora_existente.razao_social}')

class ImportarTransportadorasForm(FlaskForm):
    arquivo = FileField('Arquivo Excel', validators=[
        FileRequired(message='Por favor, selecione um arquivo'),
        FileAllowed(['xlsx', 'xls'], 'Apenas arquivos Excel (.xlsx ou .xls)')
    ])
    submit = SubmitField('Importar')
