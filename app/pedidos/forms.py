from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, BooleanField, HiddenField, SelectField
from wtforms.validators import Optional
from app.utils.ufs import UF_LIST

class FiltroPedidosForm(FlaskForm):
    numero_pedido = StringField("Número Pedido")
    cnpj_cpf = StringField("CNPJ/CPF")
    cliente = StringField("Cliente (Razão Social)")
    uf = SelectField("UF", choices=[('', 'Todas'), ('FOB', 'FOB')] + UF_LIST, validators=[Optional()])
    rota = SelectField("Rota", choices=[('', 'Todas')], validators=[Optional()])
    sub_rota = SelectField("Sub Rota", choices=[('', 'Todas')], validators=[Optional()])
    status = SelectField("Status", choices=[
        ('', 'Todos'), 
        ('ABERTO', 'Aberto'), 
        ('COTADO', 'Cotado'), 
        ('EMBARCADO', 'Embarcado'),
        ('FATURADO', 'Faturado'),
        ('NF no CD', 'NF no CD')
    ], validators=[Optional()])
    pendente_cotacao = BooleanField("Apenas pendentes de cotação")
    expedicao_inicio = DateField("Expedição De", validators=[Optional()])
    expedicao_fim = DateField("Expedição Até", validators=[Optional()])
    somente_sem_nf = BooleanField("Somente sem NF")
    submit = SubmitField("Buscar")

class CotarFreteForm(FlaskForm):
    """
    Formulário minimalista apenas para fornecer o token CSRF
    e permitir que o POST seja validado pelo Flask-WTF.
    """
    # Se quiser adicionar campo oculto, por exemplo:
    dummy = HiddenField()
    pass