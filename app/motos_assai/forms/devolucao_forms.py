"""Forms da devolucao por NF de venda Q.P.A.

Migration 29 + service devolucao_service. Anexos sao multiplos (PDF, XML,
PNG, JPG) — segue padrao UploadNfQpaForm (faturamento_forms.py).
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import (
    DateField, StringField, TextAreaField, MultipleFileField,
)
from wtforms.validators import DataRequired, Length


class DevolucaoNfForm(FlaskForm):
    """Form da NF de devolucao (NFd).

    Os chassis selecionados sao enviados via campo nao-WTForms
    `chassis_selecionados` (lista) — capturado no route via
    `request.form.getlist('chassis_selecionados')`.
    """

    data_devolucao = DateField(
        'Data da devolucao',
        validators=[DataRequired(message='Data da devolucao obrigatoria.')],
    )
    numero_nfd = StringField(
        'Numero da NFd',
        validators=[
            DataRequired(message='Numero da NFd obrigatorio.'),
            Length(min=1, max=40, message='Maximo 40 caracteres.'),
        ],
    )
    motivo = TextAreaField(
        'Motivo da devolucao',
        validators=[
            DataRequired(message='Motivo obrigatorio.'),
            Length(min=3, max=2000, message='Motivo precisa de pelo menos 3 caracteres.'),
        ],
    )
    anexos = MultipleFileField(
        'Anexos (PDF, XML, PNG, JPG)',
        validators=[
            FileAllowed(
                ['pdf', 'xml', 'png', 'jpg', 'jpeg'],
                'Apenas PDF, XML, PNG ou JPG.',
            ),
        ],
    )
