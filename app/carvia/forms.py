"""
Formularios WTForms do Modulo CarVia
"""

import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import (
    StringField, DecimalField, IntegerField, SelectField, SubmitField,
    TextAreaField, DateField, HiddenField, RadioField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError


# GAP-26: Validador de digitos verificadores de CNPJ
# Usa funcao centralizada de app.utils.cnpj_utils
def validar_cnpj(_form, field):
    """Valida digitos verificadores de CNPJ (14 digitos)"""
    if not field.data:
        return
    # Extrair apenas digitos
    digitos = re.sub(r'\D', '', field.data)
    if len(digitos) != 14:
        raise ValidationError('CNPJ deve conter exatamente 14 digitos.')
    from app.utils.cnpj_utils import validar_cnpj as _validar_cnpj_central
    if not _validar_cnpj_central(digitos):
        raise ValidationError('CNPJ invalido (digito verificador).')


class OperacaoManualForm(FlaskForm):
    """Formulario para criacao manual de operacao (sem CTe).

    A4.2 (2026-04-18): adiciona 8 campos de endereco textual e 2 campos
    de metadados para registro de correcao (motivo + numero CC-e).
    """
    cnpj_cliente = StringField(
        'CNPJ Cliente',
        validators=[DataRequired(), Length(min=14, max=20), validar_cnpj]
    )
    nome_cliente = StringField(
        'Nome Cliente',
        validators=[DataRequired(), Length(max=255)]
    )
    uf_origem = StringField('UF Origem', validators=[Optional(), Length(max=2)])
    cidade_origem = StringField('Cidade Origem', validators=[Optional(), Length(max=100)])
    uf_destino = StringField('UF Destino', validators=[DataRequired(), Length(max=2)])
    cidade_destino = StringField('Cidade Destino', validators=[DataRequired(), Length(max=100)])
    # A4.1/A4.2: Enderecos textuais (todos opcionais — preenchidos via XML
    # na importacao, editaveis manualmente pos-CC-e)
    remetente_logradouro = StringField(
        'Remetente — Logradouro', validators=[Optional(), Length(max=150)]
    )
    remetente_numero = StringField(
        'Remetente — Numero', validators=[Optional(), Length(max=20)]
    )
    remetente_bairro = StringField(
        'Remetente — Bairro', validators=[Optional(), Length(max=150)]
    )
    remetente_cep = StringField(
        'Remetente — CEP', validators=[Optional(), Length(max=10)]
    )
    destinatario_logradouro = StringField(
        'Destinatario — Logradouro', validators=[Optional(), Length(max=150)]
    )
    destinatario_numero = StringField(
        'Destinatario — Numero', validators=[Optional(), Length(max=20)]
    )
    destinatario_bairro = StringField(
        'Destinatario — Bairro', validators=[Optional(), Length(max=150)]
    )
    destinatario_cep = StringField(
        'Destinatario — CEP', validators=[Optional(), Length(max=10)]
    )
    # Metadados de correcao (validados no service quando campos de endereco mudam)
    motivo_correcao = SelectField(
        'Motivo da Correcao',
        choices=[
            ('CORRECAO_MANUAL', 'Correcao manual'),
            ('CC-E', 'Carta de Correcao (SEFAZ opcao 736)'),
            ('OUTROS', 'Outros'),
        ],
        default='CORRECAO_MANUAL',
        validators=[Optional()],
    )
    numero_cce = StringField(
        'Numero da CC-e no SSW', validators=[Optional(), Length(max=30)]
    )
    peso_bruto = DecimalField('Peso Bruto (kg)', validators=[Optional()], places=3)
    valor_mercadoria = DecimalField('Valor Mercadoria (R$)', validators=[Optional()], places=2)
    # Tomador do frete (obrigatorio 2026-04-20). Persiste em CarviaOperacao.cte_tomador.
    # Para CTe manual sem XML, e a unica fonte do tomador (SOT).
    cte_tomador = SelectField(
        'Tomador do Frete',
        choices=[
            ('', '— selecione —'),
            ('REMETENTE', 'Remetente'),
            ('EXPEDIDOR', 'Expedidor'),
            ('RECEBEDOR', 'Recebedor'),
            ('DESTINATARIO', 'Destinatario'),
            ('TERCEIRO', 'Terceiro'),
        ],
        default='',
        validators=[DataRequired(message='Tomador do frete e obrigatorio.')],
    )
    observacoes = TextAreaField('Observacoes', validators=[Optional()])


class NfManualForm(FlaskForm):
    """Formulario para adicionar NF manualmente"""
    numero_nf = StringField('Numero NF', validators=[DataRequired(), Length(max=20)])
    serie_nf = StringField('Serie', validators=[Optional(), Length(max=5)])
    # GAP-27: Chave de acesso deve ter exatamente 44 digitos (quando preenchida)
    chave_acesso_nf = StringField('Chave de Acesso (44 digitos)', validators=[Optional(), Length(min=44, max=44)])
    data_emissao = DateField('Data Emissao', validators=[Optional()])
    cnpj_emitente = StringField('CNPJ Emitente', validators=[DataRequired(), Length(min=14, max=20), validar_cnpj])
    nome_emitente = StringField('Nome Emitente', validators=[Optional(), Length(max=255)])
    uf_emitente = StringField('UF Emitente', validators=[Optional(), Length(max=2)])
    cidade_emitente = StringField('Cidade Emitente', validators=[Optional(), Length(max=100)])
    cnpj_destinatario = StringField('CNPJ Destinatario', validators=[Optional(), Length(max=20), validar_cnpj])
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


class FiltroFaturasTransportadoraForm(FlaskForm):
    """Filtros para listagem de faturas subcontrato (espelha FiltroFaturasForm do Nacom)"""
    class Meta:
        csrf = False  # GET form, sem CSRF

    numero_fatura = StringField('Número da Fatura')
    transportadora_id = SelectField(
        'Transportadora',
        choices=[],
        validate_choice=False,
    )
    numero_subcontrato = StringField(
        'Número do Subcontrato',
        description='Busca faturas que contêm subcontratos com este número',
    )
    status_conferencia = SelectField(
        'Status Conferência',
        choices=[
            ('', 'Todos'),
            ('PENDENTE', 'Pendente'),
            ('EM_CONFERENCIA', 'Em Conferência'),
            ('CONFERIDO', 'Conferido'),
            ('DIVERGENTE', 'Divergente'),
        ],
    )
    status_pagamento = SelectField(
        'Status Pagamento',
        choices=[
            ('', 'Todos'),
            ('PENDENTE', 'Pendente'),
            ('PAGO', 'Pago'),
        ],
    )
    data_emissao_de = DateField('Data Emissão - De', validators=[Optional()])
    data_emissao_ate = DateField('Data Emissão - Até', validators=[Optional()])
    data_vencimento_de = DateField('Vencimento - De', validators=[Optional()])
    data_vencimento_ate = DateField('Vencimento - Até', validators=[Optional()])


class CarviaEditarCteForm(FlaskForm):
    """Formulario para preenchimento de CTe na fatura subcontratado.

    Espelho do FreteForm (app/fretes/forms.py) adaptado para CarVia.
    numero_cte → CarviaSubcontrato.cte_numero
    valores → CarviaFrete.valor_cte / valor_considerado / valor_pago
    """
    numero_cte = StringField(
        'Numero CTe',
        validators=[DataRequired(), Length(max=20)],
    )
    valor_cte = StringField(
        'Valor CTe',
        validators=[DataRequired()],
        description='Use virgula como separador decimal (ex: 1.234,56)',
    )
    valor_considerado = StringField(
        'Valor Considerado',
        validators=[DataRequired()],
        description='Use virgula como separador decimal (ex: 1.234,56)',
    )
    valor_pago = StringField(
        'Valor Pago',
        validators=[Optional()],
        description='Use virgula como separador decimal (ex: 1.234,56)',
    )
    observacoes = TextAreaField('Observacoes')

    def validate_valor_cte(self, field):
        if field.data:
            from app.utils.valores_brasileiros import validar_valor_brasileiro
            is_valid, error_msg = validar_valor_brasileiro(field.data)
            if not is_valid:
                raise ValidationError(error_msg)

    def validate_valor_considerado(self, field):
        if field.data:
            from app.utils.valores_brasileiros import validar_valor_brasileiro
            is_valid, error_msg = validar_valor_brasileiro(field.data)
            if not is_valid:
                raise ValidationError(error_msg)

    def validate_valor_pago(self, field):
        if field.data:
            from app.utils.valores_brasileiros import validar_valor_brasileiro
            is_valid, error_msg = validar_valor_brasileiro(field.data)
            if not is_valid:
                raise ValidationError(error_msg)


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


# =============================================================================
# DESPESAS EXTRAS (xerox DespesaExtra / DespesaExtraCompletoForm Nacom)
# =============================================================================
# Paridade com app/fretes/forms.py:89-187. Sem setor_responsavel e
# motivo_despesa (decisao: problema do cliente). Sem emails_anexados separado
# — CarVia usa CarviaCustoEntregaAnexo que ja aceita .msg/.eml com metadata.

class CarviaDespesaExtraForm(FlaskForm):
    """Formulario SIMPLIFICADO para despesas extras CarVia (xerox DespesaExtraForm).

    Usado em: /carvia/despesas-extras/criar/<frete_id> e
    /carvia/fretes/<frete_id>/despesas-extras/nova. Sem documento/vencimento
    (preenchidos ao vincular fatura).
    """
    tipo_despesa = SelectField(
        'Tipo de Despesa',
        choices=[],  # Populado na view com CarviaCustoEntrega.TIPOS_CUSTO
        validators=[DataRequired()],
    )

    valor_despesa = StringField(
        'Valor da Despesa',
        validators=[DataRequired()],
        description='Use virgula como separador decimal (ex: 1.234,56)',
    )

    def validate_valor_despesa(self, field):
        if field.data:
            from app.utils.valores_brasileiros import validar_valor_brasileiro
            is_valid, error_msg = validar_valor_brasileiro(field.data)
            if not is_valid:
                raise ValidationError(error_msg)

    # Beneficiario — substitui "Transportadora do Pagamento".
    # 3 modos: TRANSPORTADORA (select), DESTINATARIO (read-only do frete), OUTROS (nome livre).
    tipo_beneficiario = RadioField(
        'Beneficiario',
        choices=[
            ('TRANSPORTADORA', 'Transportadora Subcontratada'),
            ('DESTINATARIO', 'Destinatario'),
            ('OUTROS', 'Outros'),
        ],
        default='TRANSPORTADORA',
        validators=[DataRequired()],
    )

    transportadora_id = SelectField(
        'Transportadora Subcontratada',
        choices=[],
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
    )

    beneficiario_nome = StringField(
        'Nome do Beneficiario',
        validators=[Optional(), Length(max=255)],
    )

    data_custo = DateField(
        'Data do Custo',
        validators=[DataRequired()],
        description='A data de vencimento sera igual a data do custo.',
    )

    anexos = MultipleFileField(
        'Anexar Comprovantes/Emails',
        validators=[
            FileAllowed(
                ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx', 'msg', 'eml'],
                'Formatos aceitos: PDF, imagem, DOC, XLS, MSG, EML'
            )
        ],
    )

    observacoes = TextAreaField('Observacoes')

    def validate_beneficiario_nome(self, field):
        """Exige nome apenas quando tipo_beneficiario=OUTROS."""
        if self.tipo_beneficiario.data == 'OUTROS' and not (field.data or '').strip():
            raise ValidationError('Informe o nome do beneficiario.')


class CarviaDespesaExtraCompletoForm(FlaskForm):
    """Formulario COMPLETO para despesas extras CarVia (xerox DespesaExtraCompletoForm).

    Usado em: /carvia/despesas-extras/<id>/vincular-fatura e
    /carvia/despesas-extras/<id>/editar-documento. Inclui tipo_documento,
    numero_documento e data_vencimento.
    """
    tipo_despesa = SelectField(
        'Tipo de Despesa',
        choices=[],
        validators=[DataRequired()],
    )

    tipo_documento = SelectField(
        'Tipo do Documento',
        choices=[
            ('CTE', 'CTe'),
            ('NFS', 'Nota Fiscal de Servico'),
            ('RECIBO', 'Recibo'),
            ('BOLETO', 'Boleto'),
            ('OUTROS', 'Outros'),
        ],
        validators=[DataRequired()],
    )

    numero_documento = StringField(
        'Numero do Documento',
        validators=[DataRequired(), Length(max=50)],
    )

    valor_despesa = StringField(
        'Valor da Despesa',
        validators=[DataRequired()],
        description='Use virgula como separador decimal (ex: 1.234,56)',
    )

    def validate_valor_despesa(self, field):
        if field.data:
            from app.utils.valores_brasileiros import validar_valor_brasileiro
            is_valid, error_msg = validar_valor_brasileiro(field.data)
            if not is_valid:
                raise ValidationError(error_msg)

    vencimento_despesa = DateField(
        'Vencimento da Despesa',
        validators=[Optional()],
    )

    transportadora_id = SelectField(
        'Transportadora do Pagamento',
        choices=[],
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
    )

    observacoes = TextAreaField('Observacoes')

    submit = SubmitField('Adicionar Despesa')
