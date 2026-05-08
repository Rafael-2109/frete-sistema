from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadPedidoVoeForm(FlaskForm):
    pdf = FileField('PDF do Pedido VOE', validators=[
        FileRequired('Selecione o PDF do pedido.'),
        FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
