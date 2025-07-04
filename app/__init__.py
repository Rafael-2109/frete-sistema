from dotenv import load_dotenv
from flask_session import Session
import os
from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from config import Config, TestConfig
import time
from sqlalchemy import text

# 🔄 Carrega as variáveis de ambiente do .env
load_dotenv()

# 🔧 Inicializações globais
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def formatar_data_segura(data, formato='%d/%m/%Y'):
    """
    Filtro Jinja2 para formatar datas de forma segura no timezone brasileiro
    """
    from app.utils.timezone import formatar_data_brasil
    return formatar_data_brasil(data, formato)


def formatar_data_hora_brasil(data, formato='%d/%m/%Y %H:%M'):
    """
    Filtro Jinja2 para formatar data e hora no timezone brasileiro
    """
    from app.utils.timezone import formatar_data_hora_brasil
    return formatar_data_hora_brasil(data, formato)


def formatar_hora_brasil(data, formato='%H:%M'):
    """
    Filtro Jinja2 para formatar apenas hora no timezone brasileiro
    """
    if data is None:
        return ''
    
    try:
        # Se é um objeto time (hora apenas), formata diretamente
        if hasattr(data, 'hour') and not hasattr(data, 'year'):
            return data.strftime(formato)
        
        # Se é um objeto datetime, usa a função de timezone
        elif hasattr(data, 'year'):
            from app.utils.timezone import formatar_data_hora_brasil
            return formatar_data_hora_brasil(data, formato)
        
        # Se é string, retorna como está
        elif isinstance(data, str):
            return data
        
        else:
            return str(data) if data else ''
            
    except Exception as e:
        print(f"Erro ao formatar hora: {e}, data: {data}, tipo: {type(data)}")
        return str(data) if data else ''


def diferenca_timezone():
    """
    Filtro para mostrar diferença de timezone Brasil vs UTC
    """
    from app.utils.timezone import diferenca_horario_brasil
    diff = diferenca_horario_brasil()
    horas = int(diff.total_seconds() / 3600)
    return f"UTC{horas:+d}"

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
    
    # 🔧 Configurar session - CORRIGIDO para evitar logout automático
    from datetime import timedelta
    
    # Configurações de sessão para produção estável
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True  # ✅ CORRIGIDO: Habilita sessões permanentes
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_FILE_DIR'] = './flask_session'
    app.config['SESSION_KEY_PREFIX'] = 'frete_sistema:'
    
    # ✅ NOVO: Define tempo de vida da sessão (4 horas)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)
    
    # ✅ CONFIGURAÇÕES DE SESSÃO APRIMORADAS
    # Remove configurações duplicadas - agora vem do config.py
    
    # 🚀 Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    Session(app)
    
    # ✅ NOVO: Handler específico para erros CSRF
    from flask_wtf.csrf import CSRFError
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Handler específico para erros de CSRF"""
        from flask import render_template, request, flash, redirect, url_for
        
        # Log do erro CSRF para análise
        try:
            from app.utils.logging_config import logger
            logger.warning(f"🔒 ERRO CSRF: {error.description} | Rota: {request.path} | "
                          f"Método: {request.method} | User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}...")
        except:
            pass
        
        # Para requisições AJAX, retorna JSON
        if request.is_json or 'XMLHttpRequest' in request.headers.get('X-Requested-With', ''):
            return {
                'success': False, 
                'message': 'Sua sessão expirou. Por favor, recarregue a página e tente novamente.',
                'csrf_error': True
            }, 400
        
        # Para requisições normais, redireciona com mensagem
        flash('Sua sessão expirou. Por favor, tente novamente.', 'warning')
        
        # Tenta redirecionar para a mesma página ou para o dashboard
        if request.referrer and request.referrer != request.url:
            return redirect(request.referrer)
        else:
            return redirect(url_for('main.dashboard'))

    # 🔧 Configurar login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "info"
    
    # ✅ NOVO: Configurar duração da sessão de login
    login_manager.refresh_view = "auth.login"
    login_manager.needs_refresh_message = "Sua sessão expirou. Faça login novamente."
    login_manager.needs_refresh_message_category = "info"

    # 📊 Sistema de monitoramento e logging
    try:
        from app.utils.logging_config import log_request_info, log_system_status, log_error, logger
        
        @app.before_request
        def before_request():
            """Monitora o início das requisições"""
            g.start_time = time.time()
            
            # Log básico da requisição (só para rotas importantes)
            if not request.path.startswith('/static') and not request.path.endswith('.ico'):
                log_request_info(request)
        
        @app.after_request
        def after_request(response):
            """Monitora o fim das requisições"""
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                
                # Log apenas para rotas que não são estáticas
                if not request.path.startswith('/static') and not request.path.endswith('.ico'):
                    logger.info(f"⏱️ {request.method} {request.path} | "
                               f"Status: {response.status_code} | "
                               f"Tempo: {duration:.3f}s")
                    
                    # Alerta para requisições lentas
                    if duration > 3:
                        logger.warning(f"🐌 REQUISIÇÃO LENTA: {request.path} em {duration:.3f}s")
                        
            return response
        
        @app.errorhandler(404)
        def handle_404(error):
            """Captura erros 404 - não loga favicon e outros recursos estáticos"""
            if request.path.endswith('.ico') or request.path.startswith('/static'):
                # Não loga erros para favicon e arquivos estáticos
                return "Not Found", 404
            else:
                logger.warning(f"🔍 404 - Página não encontrada: {request.path}")
                return "Página não encontrada", 404
            
        @app.errorhandler(500)
        def handle_500(error):
            """Captura erros 500 e faz log detalhado"""
            log_error(error, f"Erro 500 em {request.path}")
            return "Erro interno do servidor", 500
            
        @app.errorhandler(Exception)
        def handle_exception(error):
            """Captura qualquer exceção não tratada"""
            # Evita logar erros 404 como exceções críticas
            if hasattr(error, 'code') and error.code == 404:
                return handle_404(error)
            
            if isinstance(error, Exception) and not isinstance(error, (KeyboardInterrupt, SystemExit)):
                log_error(error, f"Exceção não tratada em {request.path}")
            raise error
        
        # Log do status inicial do sistema
        logger.info("🚀 Sistema de Fretes iniciado com monitoramento ativo")
        log_system_status()
        
    except ImportError as e:
        print(f"Aviso: Sistema de logging não disponível: {e}")
    except Exception as e:
        print(f"Erro ao configurar logging: {e}")

    # Registra os filtros personalizados para formatação de datas e timezone brasileiro
    app.jinja_env.filters['formatar_data'] = formatar_data_segura
    app.jinja_env.filters['formatar_data_segura'] = formatar_data_segura  # ✅ CORRIGIDO: Filtro que faltava
    app.jinja_env.filters['date_format'] = date_format_safe
    app.jinja_env.filters['fmt_date'] = date_format_safe
    app.jinja_env.filters['formatar_data_hora_brasil'] = formatar_data_hora_brasil
    
    # Filtro customizado para formatar protocolos (remove .0)
    def formatar_protocolo(valor):
        """Remove .0 do final do protocolo se existir"""
        if valor is None:
            return ''
        valor_str = str(valor)
        if valor_str.endswith('.0'):
            return valor_str[:-2]
        return valor_str
    
    app.jinja_env.filters['formatar_protocolo'] = formatar_protocolo
    
    # Filtro para formatar datas (flexível para Date, DateTime ou string)
    def formatar_data_brasil(data):
        """Formata campo de data para exibição brasileira (suporta Date, DateTime ou string)"""
        if data is None:
            return ''
        
        try:
            # Se é um objeto Date/DateTime
            if hasattr(data, 'strftime'):
                return data.strftime('%d/%m/%Y')
            
            # Se é string, retorna como está (pode conter texto adicional)
            elif isinstance(data, str):
                data_str = data.strip()
                if data_str:
                    return data_str
                else:
                    return ''
            
            # Se é outro tipo, converte para string
            else:
                return str(data) if data else ''
                
        except Exception as e:
            # Em caso de erro, retorna o valor original como string
            try:
                return str(data) if data else ''
            except:
                return ''
    
    app.jinja_env.filters['formatar_data_brasil'] = formatar_data_brasil
    app.jinja_env.filters['formatar_hora_brasil'] = formatar_hora_brasil
    app.jinja_env.filters['diferenca_timezone'] = diferenca_timezone
    
    # ✅ NOVOS FILTROS: Formatação brasileira de números
    def formatar_valor_brasileiro(valor, decimais=2):
        """Formata valores monetários em padrão brasileiro (R$ 1.234,56)"""
        if valor is None or valor == '':
            return 'R$ 0,00'
        
        try:
            valor_float = float(valor)
            if decimais == 0:
                return f"R$ {valor_float:,.0f}".replace(',', '.')
            else:
                valor_formatado = f"{valor_float:,.{decimais}f}"
                # Converte para padrão brasileiro
                partes = valor_formatado.split('.')
                if len(partes) == 2:
                    inteira = partes[0].replace(',', '.')
                    decimal = partes[1]
                    return f"R$ {inteira},{decimal}"
                else:
                    return f"R$ {valor_formatado.replace(',', '.')}"
        except (ValueError, TypeError):
            return 'R$ 0,00'
    
    def formatar_numero_brasileiro(valor, decimais=0):
        """Formata números em padrão brasileiro (1.234,56 ou 1.234)"""
        if valor is None or valor == '':
            return '0'
        
        try:
            valor_float = float(valor)
            if decimais == 0:
                return f"{valor_float:,.0f}".replace(',', '.')
            else:
                valor_formatado = f"{valor_float:,.{decimais}f}"
                # Converte para padrão brasileiro
                partes = valor_formatado.split('.')
                if len(partes) == 2:
                    inteira = partes[0].replace(',', '.')
                    decimal = partes[1]
                    return f"{inteira},{decimal}"
                else:
                    return valor_formatado.replace(',', '.')
        except (ValueError, TypeError):
            return '0'
    
    def formatar_peso_brasileiro(valor):
        """Formata peso em padrão brasileiro (1.234 kg)"""
        if valor is None or valor == '':
            return '0 kg'
        
        try:
            valor_float = float(valor)
            return f"{valor_float:,.0f} kg".replace(',', '.')
        except (ValueError, TypeError):
            return '0 kg'
    
    app.jinja_env.filters['valor_br'] = formatar_valor_brasileiro
    app.jinja_env.filters['numero_br'] = formatar_numero_brasileiro
    app.jinja_env.filters['peso_br'] = formatar_peso_brasileiro
    
    # ✅ NOVO: Registrar filtros de arquivo
    try:
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
    except ImportError:
        pass

    # Registra funções globais para templates
    @app.template_global()
    def safe_strftime(obj, formato='%d/%m/%Y'):
        """Função global segura para formatação de datas em templates"""
        return formatar_data_segura(obj, formato)
    
    @app.template_global()
    def agora_brasil():
        """Função global para obter datetime atual no timezone brasileiro"""
        from app.utils.timezone import agora_brasil
        return agora_brasil()
    
    @app.template_global()
    def timezone_info():
        """Função global para exibir informações de timezone"""
        from app.utils.timezone import diferenca_horario_brasil, eh_horario_verao_brasil
        diff = diferenca_horario_brasil()
        horas = int(diff.total_seconds() / 3600)
        verao = eh_horario_verao_brasil()
        return {
            'nome': 'America/Sao_Paulo',
            'diferenca_utc': f"UTC{horas:+d}",
            'horario_verao': verao,
            'sigla': 'BRST' if verao else 'BRT'
        }

    @login_manager.user_loader
    def load_user(user_id):
        from app.auth.models import Usuario
        return Usuario.query.get(int(user_id))

    # Registra comandos CLI apenas se existirem
    try:
        from app.cli import normalizar_dados, atualizar_ibge, limpar_cache_localizacao, validar_localizacao, diagnosticar_vinculos, corrigir_vinculos_grupo, importar_cidades_cli
        app.cli.add_command(normalizar_dados)
        app.cli.add_command(atualizar_ibge)
        app.cli.add_command(limpar_cache_localizacao)
        app.cli.add_command(validar_localizacao)
        app.cli.add_command(diagnosticar_vinculos)
        app.cli.add_command(corrigir_vinculos_grupo)
        app.cli.add_command(importar_cidades_cli)
        
        # REMOVIDO: criar_vinculos_faltantes (função perigosa que criava vínculos automaticamente)
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
    from app.api.routes import api_bp
    from app.claude_ai import claude_ai_bp
    
    # 📦 Importando blueprints dos módulos de carteira (seguindo padrão existente)
    from app.carteira.routes import carteira_bp
    from app.estoque.routes import estoque_bp
    from app.producao.routes import producao_bp


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
    
    # 🆕 API REST para funcionalidades MCP
    app.register_blueprint(api_bp)
    
    # 🤖 Claude AI Integration
    app.register_blueprint(claude_ai_bp)
    
    # 📦 Módulos de Carteira de Pedidos
    app.register_blueprint(carteira_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(producao_bp)
    
    # ✅ INICIALIZAR CLAUDE AI DE FORMA EXPLÍCITA
    try:
        # Tentar obter Redis cache se disponível
        redis_cache_instance = None
        try:
            from app.utils.redis_cache import redis_cache
            redis_cache_instance = redis_cache
        except ImportError:
            pass
            
        # Configurar Claude AI
        from app.claude_ai import setup_claude_ai
        if setup_claude_ai(app, redis_cache_instance):
            app.logger.info("✅ Claude AI configurado com sucesso")
        else:
            app.logger.warning("⚠️ Claude AI configurado com funcionalidades limitadas")
    except Exception as e:
        app.logger.error(f"❌ Erro ao configurar Claude AI: {e}")

    # 🧱 Cria tabelas se ainda não existirem (em ambiente local)
    with app.app_context():
        db.create_all()

    # Importa os modelos para que o Flask-Migrate os detecte
    from app.auth.models import Usuario
    from app.pedidos.models import Pedido
    from app.transportadoras.models import Transportadora
    from app.veiculos.models import Veiculo
    from app.cotacao.models import Cotacao
    # Novos modelos dos módulos de carteira
    from app.faturamento.models import FaturamentoProduto
    from app.estoque.models import MovimentacaoEstoque
    from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
    from app.localidades.models import CadastroRota, CadastroSubRota
    
    # 🆕 MODELOS DO SISTEMA CARTEIRA DE PEDIDOS (17 MODELOS)
    from app.carteira.models import (
        CarteiraPrincipal, CarteiraCopia, ControleCruzadoSeparacao,
        InconsistenciaFaturamento, HistoricoFaturamento, LogAtualizacaoCarteira,
        VinculacaoCarteiraSeparacao, EventoCarteira, AprovacaoMudancaCarteira,
        TipoCarga, FaturamentoParcialJustificativa, ControleAlteracaoCarga,
        SaldoStandby, ControleDescasamentoNF, SnapshotCarteira, ValidacaoNFSimples,
        TipoEnvio
    )

    # ✅ MIDDLEWARE PARA RECONEXÃO AUTOMÁTICA DO BANCO
    @app.before_request
    def ensure_db_connection():
        """Garante que a conexão com o banco está ativa"""
        try:
            # Testa a conexão com uma query simples
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            # Se falhar, reconecta
            logger.warning(f"🔄 Reconectando ao banco: {str(e)}")
            db.session.rollback()
            db.session.remove()
            # Força nova conexão
            db.engine.dispose()
            # Tenta novamente
            try:
                db.session.execute(text('SELECT 1'))
            except:
                pass
    
    # ✅ MIDDLEWARE PARA LIMPAR CONEXÕES APÓS CADA REQUEST
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Remove a sessão do banco ao final de cada requisição"""
        try:
            if exception is not None:
                # Se houve erro, fazer rollback
                db.session.rollback()
            else:
                # Se não houve erro, tentar commit de mudanças pendentes
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        finally:
            # Sempre remover a sessão
            db.session.remove()
    
    # ✅ MIDDLEWARE DE LOGGING E PERFORMANCE
    
    # Inicializar sistemas de autonomia do Claude AI
    try:
        from app.claude_ai.security_guard import init_security_guard
        from app.claude_ai.auto_command_processor import init_auto_processor
        from app.claude_ai.claude_code_generator import init_code_generator
        
        with app.app_context():
            # Inicializar sistema de segurança
            security_guard = init_security_guard()
            app.logger.info("🔒 Sistema de segurança Claude AI inicializado")
            
            # Inicializar processador automático de comandos
            auto_processor = init_auto_processor()
            app.logger.info("🤖 Processador automático de comandos inicializado")
            
            # Inicializar gerador de código
            code_generator = init_code_generator()
            app.logger.info("🚀 Gerador de código Claude AI inicializado")
            
    except Exception as e:
        app.logger.warning(f"⚠️ Erro ao inicializar sistemas de autonomia: {e}")
        # Sistema continua funcionando sem autonomia

    return app