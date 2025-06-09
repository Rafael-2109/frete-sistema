from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, FloatField, DateField, SelectField, TextAreaField, BooleanField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length, ValidationError
from app.fretes.models import DespesaExtra

class FreteForm(FlaskForm):
    """Formulário para registro de frete"""
    # Dados do CTe
    numero_cte = StringField('Número CTe', validators=[DataRequired(), Length(max=50)])
    vencimento = DateField('Vencimento', validators=[DataRequired()],
                          description='Vencimento da fatura (preenchido automaticamente)')
    
    # Valores do frete (como StringField para aceitar vírgula)
    valor_cte = StringField('Valor CTe', validators=[DataRequired()],
                           description='Use vírgula como separador decimal (ex: 1.234,56)')
    valor_considerado = StringField('Valor Considerado', validators=[DataRequired()],
                                   description='Use vírgula como separador decimal (ex: 1.234,56)')
    valor_pago = StringField('Valor Pago', validators=[Optional()],
                            description='Use vírgula como separador decimal (ex: 1.234,56)')
    
    # Controles
    considerar_diferenca = BooleanField('Considerar Diferença', 
                                        description='Marque para lançar diferenças até R$ 5,00 na conta corrente')
    observacoes_aprovacao = TextAreaField('Observações')
    
    submit = SubmitField('Salvar Frete')
    
    def validate_valor_cte(self, field):
        """Valida e converte valor com vírgula para float"""
        if field.data:
            try:
                # Remove pontos (milhares) e substitui vírgula por ponto (decimal)
                valor_limpo = field.data.replace('.', '').replace(',', '.')
                valor_float = float(valor_limpo)
                if valor_float < 0:
                    raise ValueError("Valor deve ser positivo")
            except ValueError:
                raise ValidationError('Valor inválido. Use formato: 1.234,56')
    
    def validate_valor_considerado(self, field):
        """Valida e converte valor com vírgula para float"""
        if field.data:
            try:
                valor_limpo = field.data.replace('.', '').replace(',', '.')
                valor_float = float(valor_limpo)
                if valor_float < 0:
                    raise ValueError("Valor deve ser positivo")
            except ValueError:
                raise ValidationError('Valor inválido. Use formato: 1.234,56')
    
    def validate_valor_pago(self, field):
        """Valida e converte valor com vírgula para float"""
        if field.data:
            try:
                valor_limpo = field.data.replace('.', '').replace(',', '.')
                valor_float = float(valor_limpo)
                if valor_float < 0:
                    raise ValueError("Valor deve ser positivo")
            except ValueError:
                raise ValidationError('Valor inválido. Use formato: 1.234,56')

class FaturaFreteForm(FlaskForm):
    """Formulário para cadastro de fatura de frete"""
    numero_fatura = StringField('Número da Fatura', validators=[DataRequired(), Length(max=50)])
    data_emissao = DateField('Data de Emissão', validators=[DataRequired()])
    valor_total_fatura = FloatField('Valor Total da Fatura', validators=[DataRequired(), NumberRange(min=0)])
    vencimento = DateField('Vencimento', validators=[Optional()])
    
    # Upload do PDF
    arquivo_pdf = FileField('Arquivo PDF da Fatura', validators=[
        Optional(),
        FileAllowed(['pdf'], 'Apenas arquivos PDF são permitidos!')
    ])
    
    observacoes_conferencia = TextAreaField('Observações da Conferência')
    
    submit = SubmitField('Salvar Fatura')

class ConferenciaFaturaForm(FlaskForm):
    """Formulário para conferência de fatura"""
    status_conferencia = SelectField('Status da Conferência', 
                                   choices=[
                                       ('PENDENTE', 'Pendente'),
                                       ('EM_CONFERENCIA', 'Em Conferência'),
                                       ('CONFERIDO', 'Conferido')
                                   ])
    observacoes_conferencia = TextAreaField('Observações da Conferência')
    
    submit = SubmitField('Salvar Conferência')

class DespesaExtraForm(FlaskForm):
    """Formulário SIMPLIFICADO para despesas extras - SEM documento e vencimento (só depois da fatura)"""
    tipo_despesa = SelectField('Tipo de Despesa', 
                              choices=[(t, t) for t in DespesaExtra.TIPOS_DESPESA],
                              validators=[DataRequired()])
    
    setor_responsavel = SelectField('Setor Responsável',
                                   choices=[(s, s) for s in DespesaExtra.SETORES_RESPONSAVEIS],
                                   validators=[DataRequired()])
    
    motivo_despesa = SelectField('Motivo da Despesa',
                                choices=[(m, m) for m in DespesaExtra.MOTIVOS_DESPESA],
                                validators=[DataRequired()])
    
    # ✅ REMOVIDO: Documento só será preenchido APÓS vincular fatura
    # ✅ REMOVIDO: Vencimento só será conhecido APÓS vincular fatura
    
    # Valores
    valor_despesa = FloatField('Valor da Despesa', validators=[DataRequired(), NumberRange(min=0)])
    
    observacoes = TextAreaField('Observações')
    
    submit = SubmitField('Continuar')

class DespesaExtraCompletoForm(FlaskForm):
    """Formulário COMPLETO para despesas extras - usado apenas quando já há fatura"""
    tipo_despesa = SelectField('Tipo de Despesa', 
                              choices=[(t, t) for t in DespesaExtra.TIPOS_DESPESA],
                              validators=[DataRequired()])
    
    setor_responsavel = SelectField('Setor Responsável',
                                   choices=[(s, s) for s in DespesaExtra.SETORES_RESPONSAVEIS],
                                   validators=[DataRequired()])
    
    motivo_despesa = SelectField('Motivo da Despesa',
                                choices=[(m, m) for m in DespesaExtra.MOTIVOS_DESPESA],
                                validators=[DataRequired()])
    
    # Documento (só aparece quando há fatura)
    tipo_documento = SelectField('Tipo do Documento',
                               choices=[
                                   ('CTE', 'CTe'),
                                   ('NFS', 'Nota Fiscal de Serviço'),
                                   ('RECIBO', 'Recibo'),
                                   ('OUTROS', 'Outros')
                               ],
                               validators=[DataRequired()])
    
    numero_documento = StringField('Número do Documento', validators=[DataRequired(), Length(max=50)])
    
    # Valores
    valor_despesa = FloatField('Valor da Despesa', validators=[DataRequired(), NumberRange(min=0)])
    vencimento_despesa = DateField('Vencimento da Despesa', validators=[Optional()])
    
    observacoes = TextAreaField('Observações')
    
    submit = SubmitField('Adicionar Despesa')

class AprovacaoFreteForm(FlaskForm):
    """Formulário para aprovação de frete"""
    status = SelectField('Status da Aprovação',
                        choices=[
                            ('PENDENTE', 'Pendente'),
                            ('APROVADO', 'Aprovado'),
                            ('REJEITADO', 'Rejeitado')
                        ],
                        validators=[DataRequired()])
    
    observacoes_aprovacao = TextAreaField('Observações da Aprovação', validators=[DataRequired()])
    
    submit = SubmitField('Salvar Aprovação')

class ContaCorrenteForm(FlaskForm):
    """Formulário para movimentações da conta corrente"""
    tipo_movimentacao = SelectField('Tipo de Movimentação',
                                   choices=[
                                       ('CREDITO', 'Crédito'),
                                       ('DEBITO', 'Débito'),
                                       ('COMPENSACAO', 'Compensação')
                                   ],
                                   validators=[DataRequired()])
    
    valor_diferenca = FloatField('Valor da Diferença', validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=255)])
    observacoes = TextAreaField('Observações')
    
    submit = SubmitField('Registrar Movimentação')

class FiltroFretesForm(FlaskForm):
    """Formulário para filtros na listagem de fretes"""
    embarque_numero = StringField('Número do Embarque')
    cnpj_cliente = StringField('CNPJ do Cliente')
    nome_cliente = StringField('Nome do Cliente')
    numero_cte = StringField('Número CTe')
    numero_fatura = StringField('Número da Fatura')  # NOVO CAMPO
    status = SelectField('Status',
                        choices=[
                            ('', 'Todos'),
                            ('PENDENTE', 'Pendente'),
                            ('EM_TRATATIVA', 'Em Tratativa'),
                            ('APROVADO', 'Aprovado'),
                            ('REJEITADO', 'Rejeitado'),
                            ('PAGO', 'Pago'),
                            ('LANCADO', 'Lançado')
                        ])
    
    data_inicio = DateField('Data Início')
    data_fim = DateField('Data Fim')
    
    submit = SubmitField('Filtrar')

class LancamentoCteForm(FlaskForm):
    """Formulário para lançamento de CTe com base na NF"""
    numero_nf = StringField('Número da NF', validators=[DataRequired(), Length(max=20)])
    
    submit = SubmitField('Buscar Embarque por NF')

class CompensacaoContaCorrenteForm(FlaskForm):
    """Formulário para compensação de valores na conta corrente"""
    movimentacoes_compensar = StringField('IDs das Movimentações (separados por vírgula)', 
                                        validators=[DataRequired()])
    observacoes = TextAreaField('Observações da Compensação')
    
    submit = SubmitField('Efetuar Compensação')

class RelatorioFretesForm(FlaskForm):
    """Formulário para geração de relatórios de fretes"""
    tipo_relatorio = SelectField('Tipo de Relatório',
                                choices=[
                                    ('FRETES_PERIODO', 'Fretes por Período'),
                                    ('CONTA_CORRENTE', 'Conta Corrente por Transportadora'),
                                    ('DESPESAS_EXTRAS', 'Despesas Extras'),
                                    ('APROVACOES_PENDENTES', 'Aprovações Pendentes'),
                                    ('FATURAS_CONFERIR', 'Faturas a Conferir')
                                ],
                                validators=[DataRequired()])
    
    data_inicio = DateField('Data Início', validators=[DataRequired()])
    data_fim = DateField('Data Fim', validators=[DataRequired()])
    transportadora_id = SelectField('Transportadora', coerce=int, choices=[], validators=[Optional()])
    
    submit = SubmitField('Gerar Relatório')

class ConfiguracaoFreteForm(FlaskForm):
    """Formulário para configurações do sistema de fretes"""
    valor_minimo_aprovacao = FloatField('Valor Mínimo para Aprovação', 
                                       validators=[Optional(), NumberRange(min=0)])
    percentual_diferenca_aprovacao = FloatField('% Diferença para Aprovação', 
                                              validators=[Optional(), NumberRange(min=0, max=100)])
    aprovadores_default = TextAreaField('Aprovadores Padrão (um por linha)')
    
    submit = SubmitField('Salvar Configurações')
