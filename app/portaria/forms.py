from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, Optional
from wtforms.widgets import TextArea
from app.veiculos.models import Veiculo
from app.embarques.models import Embarque
from app.utils.local_cd import LOCAL_CD_DEFAULT, LOCAL_CD_CHOICES, normalizar_local_cd

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

    # 🏭 CD/portaria ativo (Victorio Marchezine / Tenente Marques). Hidden field cujo valor
    # vem do seletor de contexto da tela. populate_obj(registro) grava registro.local_cd.
    # O filtro normaliza qualquer entrada para um valor canonico (VM/TM); entrada
    # invalida/vazia cai no default VM (Nacom). Constantes em app/utils/local_cd.py.
    local_cd = HiddenField(
        validators=[Optional()],
        filters=[lambda v: normalizar_local_cd(v) or LOCAL_CD_DEFAULT],
        default=LOCAL_CD_DEFAULT,
    )

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
    
    def __init__(self, *args, local_cd_ativo=None, **kwargs):
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

        # 🏭 Carrega embarques pendentes de SAIDA do CD ativo (2CD-aware).
        # NAO filtrar por `data_embarque IS NULL`: num embarque MISTO, a 1a saida de
        # qualquer CD ja preenche o cabecalho e esconderia o embarque do 2o CD. O
        # criterio correto (item ativo do CD + sem saida do CD) vem do helper unico.
        local = normalizar_local_cd(local_cd_ativo) or LOCAL_CD_DEFAULT
        self.embarque_id.choices = [('', 'Selecione um embarque')]
        try:
            from app.portaria.models import ControlePortaria
            embarques = ControlePortaria.embarques_pendentes_do_cd_query(local).order_by(
                Embarque.numero.desc()
            ).all()
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

    motorista_nome = StringField(
        'Motorista',
        validators=[Optional()],
        render_kw={'placeholder': 'Nome do motorista', 'class': 'form-control'}
    )

    placa = StringField(
        'Placa',
        validators=[Optional()],
        render_kw={'placeholder': 'Ex: ABC-1234', 'class': 'form-control', 'style': 'text-transform: uppercase;'}
    )

    empresa = StringField(
        'Empresa',
        validators=[Optional()],
        render_kw={'placeholder': 'Nome da empresa', 'class': 'form-control'}
    )

    embarque_numero = StringField(
        'Embarque',
        validators=[Optional()],
        render_kw={'placeholder': 'N. do embarque', 'class': 'form-control'}
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

    # 🏭 Filtro por CD/portaria (Victorio Marchezine / Tenente Marques / todos)
    local_cd = SelectField(
        'CD / Portaria',
        choices=[('', 'Todos os CDs')] + LOCAL_CD_CHOICES,
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


class RegistroPortariaEmbarqueAdminForm(FlaskForm):
    """Form ADMIN: cria um ControlePortaria direto do embarque ja com chegada,
    entrada e saida (datas/horas informadas manualmente — registro retroativo).

    Usado pela rota `portaria.criar_registro_embarque` (admin-only). A saida dispara
    a cadeia de efeitos normal da portaria (ver app/portaria/CLAUDE.md R2/R5).
    `cd_choices` (kwarg) restringe o local_cd aos CDs com itens ativos do embarque.
    """
    # Motorista (preenchido via busca por CPF — reusa /portaria/buscar_motorista).
    # cpf so' alimenta a busca AJAX no front; o vinculo real e' motorista_id (FK NOT NULL).
    cpf = StringField('CPF do Motorista', validators=[Optional()],
                      render_kw={'placeholder': '000.000.000-00'})
    motorista_id = HiddenField(
        validators=[DataRequired(message='Busque e selecione um motorista (CPF) antes de salvar')]
    )
    nome_completo = StringField('Nome Completo', render_kw={'readonly': True})
    rg = StringField('RG', render_kw={'readonly': True})
    telefone = StringField('Telefone', render_kw={'readonly': True})

    # Veiculo
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
        'Tipo de Veículo', coerce=coerce_int_or_none, validators=[Optional()], choices=[]
    )

    # Carga
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
        ],
        default='Entrega',
    )
    empresa = StringField(
        'Empresa',
        validators=[
            DataRequired(message='Empresa é obrigatória'),
            Length(min=2, max=255, message='Nome da empresa deve ter entre 2 e 255 caracteres')
        ],
        render_kw={'placeholder': 'Nome da empresa'}
    )

    # 🏭 CD/portaria deste registro (R3: 1 registro por CD). Choices = CDs com item
    # ativo do embarque (preenchidos no __init__); fallback = todos os CDs.
    local_cd = SelectField(
        'CD / Portaria',
        validators=[DataRequired(message='Selecione o CD da saída')],
        choices=[],
    )

    # Horarios (registro retroativo — StringField + type=date/time, parse na rota).
    data_chegada = StringField('Data Chegada', validators=[DataRequired(message='Data de chegada é obrigatória')],
                               render_kw={'type': 'date'})
    hora_chegada = StringField('Hora Chegada', validators=[DataRequired(message='Hora de chegada é obrigatória')],
                               render_kw={'type': 'time'})
    data_entrada = StringField('Data Entrada', validators=[DataRequired(message='Data de entrada é obrigatória')],
                               render_kw={'type': 'date'})
    hora_entrada = StringField('Hora Entrada', validators=[DataRequired(message='Hora de entrada é obrigatória')],
                               render_kw={'type': 'time'})
    data_saida = StringField('Data Saída', validators=[DataRequired(message='Data de saída é obrigatória')],
                             render_kw={'type': 'date'})
    hora_saida = StringField('Hora Saída', validators=[DataRequired(message='Hora de saída é obrigatória')],
                             render_kw={'type': 'time'})

    submit = SubmitField('Criar registro e dar saída')

    def __init__(self, *args, cd_choices=None, **kwargs):
        super(RegistroPortariaEmbarqueAdminForm, self).__init__(*args, **kwargs)

        # CD: restringe aos CDs do embarque (passado pela rota); fallback = todos.
        self.local_cd.choices = list(cd_choices) if cd_choices else list(LOCAL_CD_CHOICES)

        # Tipos de veiculo (igual ControlePortariaForm)
        self.tipo_veiculo_id.choices = [('', 'Selecione o tipo de veículo')]
        try:
            veiculos = Veiculo.query.order_by(Veiculo.nome).all()
            self.tipo_veiculo_id.choices.extend([(v.id, v.nome) for v in veiculos])
        except Exception:
            pass


