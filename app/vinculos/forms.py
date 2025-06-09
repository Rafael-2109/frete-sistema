from flask_wtf import FlaskForm

from wtforms.validators import DataRequired, Optional

from wtforms import StringField
from wtforms import SubmitField
from wtforms import HiddenField
from wtforms import FileField

class EditarVinculoForm(FlaskForm):
    vinculo_id = HiddenField('ID do Vínculo', validators=[DataRequired(message="ID obrigatório para editar o vínculo.")])
    razao_social = StringField('Razão Social', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[Optional()])
    uf = StringField('UF', validators=[Optional()])
    cidade = StringField('Cidade', validators=[Optional()])
    codigo_ibge = StringField('Código IBGE', validators=[Optional()])
    nome_tabela = StringField('Nome da Tabela', validators=[Optional()])
    lead_time = StringField('Lead Time (dias)', validators=[Optional()])  # <-- Atualizado para StringField
    submit = SubmitField('Salvar Alterações')

class ConsultaVinculoForm(FlaskForm):
    razao_social = StringField('Razão Social')
    cnpj = StringField('CNPJ')
    uf = StringField('UF')
    cidade = StringField('Cidade')
    codigo_ibge = StringField('Código IBGE')
    nome_tabela = StringField('Nome Tabela')
    submit = SubmitField('🔍 Buscar')

class UploadVinculoForm(FlaskForm):
    arquivo = FileField('Arquivo Excel (.xlsx)', validators=[DataRequired()])
    submit = SubmitField('Validar Arquivo')


class ConfirmarImportacaoForm(FlaskForm):
    dados_validos = HiddenField('Dados Validados')
    submit = SubmitField('Confirmar Importação')
