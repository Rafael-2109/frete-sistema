from dotenv import load_dotenv
from flask_session import Session
import os
from flask import Flask, request, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, validate_csrf, CSRFError
from flask_migrate import Migrate
from config import Config, TestConfig
from datetime import datetime

# 🔄 Carrega as variáveis de ambiente do .env
load_dotenv()

# 🔧 Inicializações globais
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def formatar_data_segura(data, formato='%d/%m/%Y'):
    """
    Filtro Jinja2 para formatar datas de forma segura, evitando o erro 'None has no attribute strftime'
    """
    if data is None or data == '' or str(data).lower() in ['none', 'null']:
        return ''
    
    try:
        # Se já for datetime.date ou datetime.datetime e não for None
        if hasattr(data, 'strftime'):
            return data.strftime(formato)
        
        # Se for string, tenta converter
        if isinstance(data, str):
            data = data.strip()
            if not data or data.lower() in ['none', 'null', '']:
                return ''
                
            # Tenta vários formatos comuns
            formatos = [
                '%Y-%m-%d',      # 2025-05-29
                '%d/%m/%Y',      # 29/05/2025
                '%Y-%m-%d %H:%M:%S',  # 2025-05-29 10:30:00
                '%d/%m/%Y %H:%M:%S',  # 29/05/2025 10:30:00
                '%d-%m-%Y',      # 29-05-2025
                '%m/%d/%Y',      # 05/29/2025 (formato americano)
            ]
            for formato_origem in formatos:
                try:
                    data_obj = datetime.strptime(data, formato_origem)
                    return data_obj.strftime(formato)
                except ValueError:
                    continue
        
        # Se for número (timestamp)
        if isinstance(data, (int, float)):
            try:
                data_obj = datetime.fromtimestamp(data)
                return data_obj.strftime(formato)
            except:
                pass
        
        # Retorna string vazia para valores inválidos
        return ''
        
    except Exception:
        return ''  # Sempre retorna string vazia em caso de erro

def date_format_safe(data, formato='%d/%m/%Y'):
    """
    Alias para formatar_data_segura com nome mais intuitivo
    """
    return formatar_data_segura(data, formato)

def create_app(config_name=None):
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    if config_name == 'testing':
        app.config.from_object(TestConfig)
    else:
        app.config.from_object(Config)

    # 🔧 Configurações personalizadas baseadas no ambiente
    if app.config.get('ENVIRONMENT') == 'production':
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
    else:
        app.config['SQLALCHEMY_ECHO'] = False  # Para não poluir os logs
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')

    # 🔧 Configurar upload
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # 🔧 Configurar tamanho máximo do arquivo (16MB)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # 🔧 Configurar session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_FILE_DIR'] = './flask_session'
    app.config['SESSION_KEY_PREFIX'] = 'frete_sistema:'

    # 🚀 Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    Session(app)

    # 🔧 Configurar login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "info"

    # Registra os filtros personalizados para formatação de datas
    app.jinja_env.filters['formatar_data'] = formatar_data_segura
    app.jinja_env.filters['date_format'] = date_format_safe
    app.jinja_env.filters['fmt_date'] = date_format_safe

    # Registra uma função global para templates que detecta uso inseguro de strftime
    @app.template_global()
    def safe_strftime(obj, formato='%d/%m/%Y'):
        """Função global segura para formatação de datas em templates"""
        return formatar_data_segura(obj, formato)

    @login_manager.user_loader
    def load_user(user_id):
        from app.auth.models import User
        return User.query.get(int(user_id))

    # Registra comandos CLI apenas se existirem
    try:
        from app.cli import normalizar_dados, atualizar_ibge, limpar_cache_localizacao, validar_localizacao, diagnosticar_vinculos, corrigir_vinculos_grupo
        app.cli.add_command(normalizar_dados)
        app.cli.add_command(atualizar_ibge)
        app.cli.add_command(limpar_cache_localizacao)
        app.cli.add_command(validar_localizacao)
        app.cli.add_command(diagnosticar_vinculos)
        app.cli.add_command(corrigir_vinculos_grupo)
        
        # Tenta importar criar_vinculos_faltantes se existir
        try:
            from app.cli import criar_vinculos_faltantes
            app.cli.add_command(criar_vinculos_faltantes)
        except ImportError:
            pass  # Se não existir, apenas ignora
    except ImportError as e:
        print(f"Aviso: Não foi possível importar alguns comandos CLI: {e}")

    # 🔗 Importa e registra Blueprints
    from app.auth.routes import auth_bp
    from app.embarques.routes import embarques_bp
    from app.faturamento.routes import faturamento_bp
    from app.localidades.routes import localidades_bp
    from app.main.routes import main_bp
    from app.monitoramento.routes import monitoramento_bp
    from app.tabelas.routes import tabelas_bp
    from app.transportadoras import transportadoras_bp
    from app.veiculos.routes import veiculos_bp
    from app.vinculos.routes import vinculos_bp
    from app.fretes.routes import fretes_bp
    from app.financeiro.routes import financeiro_bp
    from app.cadastros_agendamento.routes import cadastros_agendamento_bp
    from app.separacao.routes import separacao_bp
    from app.pedidos.routes import pedidos_bp
    from app.cotacao.routes import cotacao_bp
    from app.portaria.routes import portaria_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(embarques_bp)
    app.register_blueprint(faturamento_bp)
    app.register_blueprint(localidades_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(monitoramento_bp)
    app.register_blueprint(tabelas_bp)
    app.register_blueprint(transportadoras_bp)
    app.register_blueprint(veiculos_bp)
    app.register_blueprint(vinculos_bp)
    app.register_blueprint(fretes_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(cadastros_agendamento_bp)
    app.register_blueprint(separacao_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(cotacao_bp)
    app.register_blueprint(portaria_bp)

    # 🧱 Cria tabelas se ainda não existirem (em ambiente local)
    with app.app_context():
        db.create_all()

    # Importa os modelos para que o Flask-Migrate os detecte
    from app.auth.models import Usuario
    from app.pedidos.models import Pedido
    from app.transportadoras.models import Transportadora
    from app.veiculos.models import Veiculo
    from app.cotacao.models import Cotacao

    return app