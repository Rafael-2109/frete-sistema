"""
Formularios WTForms do Modulo CarVia
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, DecimalField, IntegerField, SelectField,
    TextAreaField, DateField, HiddenField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class OperacaoManualForm(FlaskForm):
    """Formulario para criacao manual de operacao (sem CTe)"""
    cnpj_cliente = StringField(
        'CNPJ Cliente',
        validators=[DataRequired(), Length(min=14, max=20)]
    )
    nome_cliente = StringField(
        'Nome Cliente',
        validators=[DataRequired(), Length(max=255)]
    )
    uf_origem = StringField('UF Origem', validators=[Optional(), Length(max=2)])
    cidade_origem = StringField('Cidade Origem', validators=[Optional(), Length(max=100)])
    uf_destino = StringField('UF Destino', validators=[DataRequired(), Length(max=2)])
    cidade_destino = StringField('Cidade Destino', validators=[DataRequired(), Length(max=100)])
    peso_bruto = DecimalField('Peso Bruto (kg)', validators=[Optional()], places=3)
    valor_mercadoria = DecimalField('Valor Mercadoria (R$)', validators=[Optional()], places=2)
    observacoes = TextAreaField('Observacoes', validators=[Optional()])


class NfManualForm(FlaskForm):
    """Formulario para adicionar NF manualmente"""
    numero_nf = StringField('Numero NF', validators=[DataRequired(), Length(max=20)])
    serie_nf = StringField('Serie', validators=[Optional(), Length(max=5)])
    chave_acesso_nf = StringField('Chave de Acesso (44 digitos)', validators=[Optional(), Length(max=44)])
    data_emissao = DateField('Data Emissao', validators=[Optional()])
    cnpj_emitente = StringField('CNPJ Emitente', validators=[DataRequired(), Length(max=20)])
    nome_emitente = StringField('Nome Emitente', validators=[Optional(), Length(max=255)])
    uf_emitente = StringField('UF Emitente', validators=[Optional(), Length(max=2)])
    cidade_emitente = StringField('Cidade Emitente', validators=[Optional(), Length(max=100)])
    cnpj_destinatario = StringField('CNPJ Destinatario', validators=[Optional(), Length(max=20)])
    nome_destinatario = StringField('Nome Destinatario', validators=[Optional(), Length(max=255)])
    uf_destinatario = StringField('UF Destino', validators=[Optional(), Length(max=2)])
    cidade_destinatario = StringField('Cidade Destino', validators=[Optional(), Length(max=100)])
    valor_total = DecimalField('Valor Total (R$)', validators=[Optional()], places=2)
    peso_bruto = DecimalField('Peso Bruto (kg)', validators=[Optional()], places=3)
    peso_liquido = DecimalField('Peso Liquido (kg)', validators=[Optional()], places=3)
    quantidade_volumes = IntegerField('Qtd Volumes', validators=[Optional()])


class SubcontratoForm(FlaskForm):
    """Formulario para adicionar subcontrato a uma operacao"""
    operacao_id = HiddenField('Operacao ID', validators=[DataRequired()])
    transportadora_id = SelectField(
        'Transportadora',
        coerce=int,
        validators=[DataRequired()]
    )
    valor_acertado = DecimalField(
        'Valor Acertado (R$)',
        validators=[Optional()],
        places=2,
        description='Se diferente da cotacao automatica'
    )
    observacoes = TextAreaField('Observacoes', validators=[Optional()])


class CubagemForm(FlaskForm):
    """Formulario para informar cubagem da operacao"""
    peso_cubado = DecimalField(
        'Peso Cubado Direto (kg)',
        validators=[Optional()],
        places=3,
        description='Informar diretamente OU calcular por dimensoes'
    )
    cubagem_comprimento = DecimalField('Comprimento (cm)', validators=[Optional()], places=2)
    cubagem_largura = DecimalField('Largura (cm)', validators=[Optional()], places=2)
    cubagem_altura = DecimalField('Altura (cm)', validators=[Optional()], places=2)
    cubagem_fator = DecimalField(
        'Fator Divisor',
        validators=[Optional(), NumberRange(min=1)],
        places=2,
        default=5000
    )
    cubagem_volumes = IntegerField(
        'Volumes',
        validators=[Optional(), NumberRange(min=1)],
        default=1
    )
