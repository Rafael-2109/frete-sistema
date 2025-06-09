from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegistroForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    empresa = StringField('Empresa', validators=[DataRequired(), Length(min=2, max=100)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(min=2, max=100)])
    telefone = StringField('Telefone', validators=[DataRequired(), Length(min=10, max=20)])
    perfil = SelectField('Tipo de Acesso Solicitado', choices=[
        ('vendedor', 'Vendedor'),
        ('portaria', 'Portaria'),
        ('financeiro', 'Financeiro'),
        ('logistica', 'Logística')
    ], validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', 
                                  validators=[DataRequired(), EqualTo('senha', message='Senhas devem ser iguais')])
    submit = SubmitField('Solicitar Acesso')

class AprovarUsuarioForm(FlaskForm):
    perfil = SelectField('Perfil', choices=[
        ('vendedor', 'Vendedor'),
        ('portaria', 'Portaria'), 
        ('financeiro', 'Financeiro'),
        ('logistica', 'Logística'),
        ('gerente_comercial', 'Gerente Comercial'),
        ('administrador', 'Administrador')
    ], validators=[DataRequired()])
    vendedor_vinculado = SelectField('Vendedor Vinculado', choices=[], validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    submit = SubmitField('Aprovar Usuário')

class RejeitarUsuarioForm(FlaskForm):
    motivo = TextAreaField('Motivo da Rejeição', validators=[DataRequired()])
    submit = SubmitField('Rejeitar Usuário')

class EditarUsuarioForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    empresa = StringField('Empresa', validators=[Optional(), Length(max=100)])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    perfil = SelectField('Perfil', choices=[
        ('vendedor', 'Vendedor'),
        ('portaria', 'Portaria'),
        ('financeiro', 'Financeiro'),
        ('logistica', 'Logística'),
        ('gerente_comercial', 'Gerente Comercial'),
        ('administrador', 'Administrador')
    ], validators=[DataRequired()])
    vendedor_vinculado = SelectField('Vendedor Vinculado', choices=[], validators=[Optional()])
    status = SelectField('Status', choices=[
        ('ativo', 'Ativo'),
        ('bloqueado', 'Bloqueado'),
        ('rejeitado', 'Rejeitado')
    ], validators=[DataRequired()])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    submit = SubmitField('Salvar Alterações')







