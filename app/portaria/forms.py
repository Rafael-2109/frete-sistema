from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, Optional
from wtforms.widgets import TextArea
from app.veiculos.models import Veiculo
from app.embarques.models import Embarque

def coerce_int_or_none(value):
    """Converte para int ou retorna None se vazio"""
    if value == '' or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class CadastroMotoristaForm(FlaskForm):
    """
    Formulário para cadastro/edição de motoristas
    """
    nome_completo = StringField(
        'Nome Completo', 
        validators=[
            DataRequired(message='Nome completo é obrigatório'),
            Length(min=3, max=255, message='Nome deve ter entre 3 e 255 caracteres')
        ],
        render_kw={'placeholder': 'Digite o nome completo do motorista'}
    )
    
    rg = StringField(
        'RG',
        validators=[
            DataRequired(message='RG é obrigatório'),
            Length(min=7, max=20, message='RG deve ter entre 7 e 20 caracteres')
        ],
        render_kw={'placeholder': 'Ex: 12.345.678-9'}
    )
    
    cpf = StringField(
        'CPF',
        validators=[
            DataRequired(message='CPF é obrigatório'),
            Regexp(
                r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$',
                message='CPF deve estar no formato 000.000.000-00'
            )
        ],
        render_kw={'placeholder': '000.000.000-00'}
    )
    
    telefone = StringField(
        'Telefone',
        validators=[
            DataRequired(message='Telefone é obrigatório'),
            Regexp(
                r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message='Telefone deve estar no formato (11) 99999-9999'
            )
        ],
        render_kw={'placeholder': '(11) 99999-9999'}
    )
    
    foto_documento = FileField(
        'Foto do Documento',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas arquivos JPG, JPEG e PNG são permitidos')
        ]
    )
    
    submit = SubmitField('Salvar Motorista')

class BuscarMotoristaForm(FlaskForm):
    """
    Formulário para buscar motorista por CPF
    """
    cpf = StringField(
        'CPF',
        validators=[
            DataRequired(message='CPF é obrigatório para busca'),
            Length(min=11, max=14, message='CPF deve ter 11 dígitos')
        ],
        render_kw={'placeholder': '000.000.000-00'}
    )
    
    buscar = SubmitField('Buscar')
    cadastrar = SubmitField('Cadastrar')

class ControlePortariaForm(FlaskForm):
    """
    Formulário para controle de portaria
    """
    # Campos do motorista (preenchidos após busca)
    motorista_id = HiddenField(validators=[Optional()])
    nome_completo = StringField('Nome Completo', render_kw={'readonly': True})
    rg = StringField('RG', render_kw={'readonly': True})
    telefone = StringField('Telefone', render_kw={'readonly': True})
    
    # Dados do veículo
    placa = StringField(
        'Placa',
        validators=[
            DataRequired(message='Placa é obrigatória'),
            Regexp(
                r'^[A-Z]{3}-?\d{4}$|^[A-Z]{3}-?\d{1}[A-Z]{1}\d{2}$',
                message='Placa deve estar no formato ABC-1234 (antiga) ou ABC-1D23 (Mercosul)'
            )
        ],
        render_kw={'placeholder': 'ABC-1234 ou ABC-1D23', 'style': 'text-transform: uppercase;'}
    )
    
    tipo_veiculo_id = SelectField(
        'Tipo de Veículo',
        coerce=coerce_int_or_none,
        validators=[Optional()],
        choices=[]
    )
    
    # Dados da carga
    tipo_carga = SelectField(
        'Tipo de Carga',
        validators=[DataRequired(message='Tipo de carga é obrigatório')],
        choices=[
            ('', 'Selecione o tipo de carga'),
            ('Coleta', 'Coleta'),
            ('Coleta + Devolução', 'Coleta + Devolução'),
            ('Devolução', 'Devolução'),
            ('Entrega', 'Entrega'),
            ('Coleta de Moto', 'Coleta de Moto'),
        ]
    )
    
    empresa = StringField(
        'Empresa',
        validators=[
            DataRequired(message='Empresa é obrigatória'),
            Length(min=2, max=255, message='Nome da empresa deve ter entre 2 e 255 caracteres')
        ],
        render_kw={'placeholder': 'Nome da empresa'}
    )
    
    embarque_id = SelectField(
        'Embarque',
        coerce=coerce_int_or_none,
        validators=[Optional()],
        choices=[]
    )
    
    # Nota: Botões de ação removidos para evitar conflito com métodos do modelo
    # Os botões são renderizados diretamente no template
    
    def __init__(self, *args, **kwargs):
        super(ControlePortariaForm, self).__init__(*args, **kwargs)
        
        # Carrega opções de veículos
        self.tipo_veiculo_id.choices = [('', 'Selecione o tipo de veículo')]
        try:
            veiculos = Veiculo.query.order_by(Veiculo.nome).all()
            self.tipo_veiculo_id.choices.extend([
                (v.id, v.nome) for v in veiculos
            ])
        except:
            pass  # Em caso de erro na consulta
        
        # Carrega apenas embarques pendentes de embarque (sem data_embarque)
        self.embarque_id.choices = [('', 'Selecione um embarque')]
        try:
            embarques = Embarque.query.filter(
                Embarque.status == 'ativo',
                Embarque.data_embarque.is_(None)  # Apenas embarques que ainda não saíram
            ).order_by(Embarque.numero.desc()).all()
            self.embarque_id.choices.extend([
                (e.id, f'Embarque #{e.numero} - {e.transportadora.razao_social if e.transportadora else ""} (PENDENTE)') 
                for e in embarques
            ])
        except:
            pass  # Em caso de erro na consulta

class FiltroHistoricoForm(FlaskForm):
    """
    Formulário para filtrar histórico da portaria
    """
    data_inicio = StringField(
        'Data Início',
        validators=[Optional()],
        render_kw={'type': 'date', 'class': 'form-control'}
    )
    
    data_fim = StringField(
        'Data Fim',
        validators=[Optional()],
        render_kw={'type': 'date', 'class': 'form-control'}
    )
    
    embarque_numero = StringField(
        'Número do Embarque',
        validators=[Optional()],
        render_kw={'placeholder': 'Digite o número do embarque', 'class': 'form-control'}
    )
    
    tem_embarque = SelectField(
        'Vinculado a Embarque',
        choices=[
            ('', 'Todos os registros'),
            ('sim', 'Com embarque vinculado'),
            ('nao', 'Sem embarque vinculado')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    tipo_carga = SelectField(
        'Tipo de Carga',
        choices=[
            ('', 'Todos os tipos'),
            ('Coleta', 'Coleta'),
            ('Coleta + Devolução', 'Coleta + Devolução'),
            ('Devolução', 'Devolução'),
            ('Entrega', 'Entrega'),
            ('Coleta de Moto', 'Coleta de Moto')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    tipo_veiculo_id = SelectField(
        'Tipo de Veículo',
        coerce=coerce_int_or_none,
        validators=[Optional()],
        choices=[],  # Será populado dinamicamente
        render_kw={'class': 'form-control'}
    )
    
    status = SelectField(
        'Status',
        choices=[
            ('', 'Todos os status'),
            ('PENDENTE', 'Pendente'),
            ('AGUARDANDO', 'Aguardando'),
            ('DENTRO', 'Carregando'),
            ('SAIU', 'Saiu para entrega')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    filtrar = SubmitField('Filtrar')
    limpar = SubmitField('Limpar Filtros')
    
    def __init__(self, *args, **kwargs):
        super(FiltroHistoricoForm, self).__init__(*args, **kwargs)
        
        # Carrega opções de tipos de veículos
        self.tipo_veiculo_id.choices = [('', 'Todos os tipos')]
        try:
            from app.veiculos.models import Veiculo
            veiculos = Veiculo.query.order_by(Veiculo.nome).all()
            self.tipo_veiculo_id.choices.extend([
                (v.id, v.nome) for v in veiculos
            ])
        except:
            pass  # Em caso de erro na consulta


