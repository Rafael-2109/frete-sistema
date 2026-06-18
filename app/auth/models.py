from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import flag_modified
from app.utils.timezone import agora_utc_naive

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    
    # Níveis de usuário conforme especificação
    perfil = db.Column(db.String(30), default='vendedor')  # portaria, vendedor, gerente_comercial, financeiro, logistica, administrador
    status = db.Column(db.String(20), default='pendente')  # pendente, ativo, rejeitado, bloqueado

    empresa = db.Column(db.String(100), nullable=True)  # Empresa do usuário
    cargo = db.Column(db.String(100), nullable=True)  # Cargo do usuário
    telefone = db.Column(db.String(20), nullable=True)  # Telefone para contato
    # Opt-in explicito para receber/enviar mensagens via WhatsApp Bot (canal OpenClaw).
    # Migration: 2026_05_09_whatsapp_module. Default FALSE — telefone cadastrado para
    # contato generico nao habilita bot automaticamente. Ver Usuario.find_by_whatsapp_jid.
    whatsapp_autorizado = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    # Vinculo Microsoft Teams (AAD object ID). Preenchido por codigo de pareamento
    # (fast-path "vincular ABC123"), auto-match por email corporativo ou admin.
    # Migration: 2026_06_10_teams_identidade. Ver Usuario.find_by_teams_aad_id.
    teams_user_id = db.Column(db.String(64), nullable=True)
    teams_vinculo_origem = db.Column(db.String(20), nullable=True)  # 'codigo'|'email'|'admin'
    vendedor_vinculado = db.Column(db.String(100), nullable=True)  # Nome do vendedor no faturamento (para perfil vendedor)

    # Sistemas permitidos (novo - para separar logística de motochefe)
    sistema_logistica = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao sistema de logística
    sistema_motochefe = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao sistema motochefe
    sistema_carvia = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao sistema CarVia (frete subcontratado)
    sistema_seguranca = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao modulo de seguranca
    acesso_comissao_carvia = db.Column(db.Boolean, default=False, nullable=False)  # Acesso a comissoes CarVia
    acesso_recebimento_carvia = db.Column(db.Boolean, default=False, nullable=False, server_default='false')  # Acesso SO ao recebimento por chassi das Coletas CarVia (operador, sem valores)
    sistema_remessa_vortx = db.Column(db.Boolean, default=False, nullable=False)  # Acesso a geracao de remessa VORTX
    sistema_lojas = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao modulo Lojas HORA
    sistema_motos_assai = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao módulo Motos Assaí
    agente_fable5 = db.Column(db.Boolean, nullable=False, default=False, server_default='false')  # Opt-in modelo Fable 5 (caro)
    # Segregacao por loja HORA: NULL = acesso a todas; <id> = restrito a 1 loja.
    # Nao usa FK explicita (manter app/auth independente de app/hora).
    loja_hora_id = db.Column(db.Integer, nullable=True)

    # Criterio de filtragem dos Pedidos de Venda HORA na listagem /hora/vendas:
    #   'loja'     -> escopo por loja_hora_id (comportamento padrao).
    #   'vendedor' -> apenas pedidos cujo vendedor (ou vendedor_vinculado) ou
    #                 criado_por_id e este usuario (ignora escopo de loja).
    # Definido na tela /hora/permissoes. Sem efeito fora da listagem de pedidos.
    criterio_pedidos_hora = db.Column(
        db.String(10), nullable=False, default='loja', server_default='loja',
    )

    # Dados de controle
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(120), nullable=True)  # Email do admin que aprovou
    ultimo_login = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)  # Observações do admin

    # Preferencias per-user (JSONB). Migration: 2026_04_23_add_usuarios_preferences.
    # Chaves conhecidas:
    #   - agent_thinking_display: 'summarized' | 'omitted' (default 'omitted')
    #     Controla ThinkingConfig.display do Agent SDK (SDK 0.1.65+).
    #     'summarized' gera resumo do raciocinio (tokens extras + latencia).
    #     'omitted' pula a etapa de resumo (mesmo resultado, mais rapido, menos tokens).
    preferences = db.Column(JSONB, nullable=False, default=dict, server_default='{}')

    def set_senha(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def verificar_senha(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)
    
    @property
    def is_approved(self):
        """Usuário só está aprovado se status == 'ativo'"""
        return self.status == 'ativo'
    
    # Flask-Login requer que is_active sempre retorne True
    # Usamos is_approved para verificar se o usuário foi aprovado
    
    def aprovar(self, admin_email, vendedor_vinculado=None):
        """Aprova o usuário"""
        self.status = 'ativo'
        self.aprovado_em = agora_utc_naive()
        self.aprovado_por = admin_email
        if vendedor_vinculado:
            self.vendedor_vinculado = vendedor_vinculado
    
    def rejeitar(self, motivo=None):
        """Rejeita o usuário"""
        self.status = 'rejeitado'
        if motivo:
            self.observacoes = motivo

    # ─── WhatsApp Bot integration ────────────────────────────────────────

    @staticmethod
    def normalize_whatsapp_identifier(jid_or_phone):
        """Normaliza JID Baileys ou telefone livre para variantes pesquisaveis.

        OpenClaw entrega `event.senderId` em formatos diferentes conforme contexto:
        - DM: E.164 sem '+' (ex: '5511991642998')
        - Grupo: JID Baileys completo (ex: '5511991642998@s.whatsapp.net')

        E o campo `usuarios.telefone` no banco pode estar em formato legado BR
        sem prefixo 55 (ex: '11991642998'). Esta funcao gera todas as variantes
        equivalentes para match em `IN (...)`.

        Args:
            jid_or_phone: string em qualquer formato (com '+', '@s.whatsapp.net',
                espacos, parenteses etc).

        Returns:
            set[str]: variantes em digitos puros. Vazio se input invalido.

        Exemplos:
            >>> Usuario.normalize_whatsapp_identifier('+5511991642998')
            {'5511991642998', '11991642998'}
            >>> Usuario.normalize_whatsapp_identifier('5511991642998@s.whatsapp.net')
            {'5511991642998', '11991642998'}
            >>> Usuario.normalize_whatsapp_identifier('11991642998')
            {'11991642998', '5511991642998'}
        """
        if not jid_or_phone:
            return set()

        raw = str(jid_or_phone)
        # Strip JID suffix Baileys
        if '@' in raw:
            raw = raw.split('@', 1)[0]
        # Manter apenas digitos
        digits = ''.join(c for c in raw if c.isdigit())
        if not digits:
            return set()

        variants = {digits}
        # Variante com 55 (E.164 BR): se nao comeca com 55 e tem 10-11 digitos (DDD+numero)
        if not digits.startswith('55') and 10 <= len(digits) <= 11:
            variants.add('55' + digits)
        # Variante sem 55: se comeca com 55 e tem >= 12 digitos
        if digits.startswith('55') and len(digits) >= 12:
            variants.add(digits[2:])
        return variants

    @classmethod
    def find_by_whatsapp_jid(cls, jid_or_phone):
        """Resolve JID/telefone WhatsApp para Usuario autorizado e ativo.

        Match em qualquer das variantes geradas por `normalize_whatsapp_identifier`,
        filtrando obrigatoriamente por `whatsapp_autorizado=True` e `status='ativo'`.

        Args:
            jid_or_phone: identificador vindo do plugin OpenClaw (header
                X-OpenClaw-Sender) ou string livre.

        Returns:
            Usuario | None
        """
        variants = cls.normalize_whatsapp_identifier(jid_or_phone)
        if not variants:
            return None
        return (
            cls.query
            .filter(cls.telefone.in_(variants))
            .filter(cls.whatsapp_autorizado.is_(True))
            .filter(cls.status == 'ativo')
            .first()
        )

    @classmethod
    def find_by_teams_aad_id(cls, aad_id):
        """Resolve AAD object ID do Teams para Usuario ativo (espelha find_by_whatsapp_jid).

        Args:
            aad_id: Azure AD object ID vindo do bot (activity.from_property.aad_object_id)

        Returns:
            Usuario | None
        """
        if not aad_id:
            return None
        return cls.query.filter_by(teams_user_id=str(aad_id), status='ativo').first()


    def bloquear(self, motivo=None):
        """Bloqueia o usuário"""
        self.status = 'bloqueado'
        if motivo:
            self.observacoes = motivo
    
    @property
    def status_badge_class(self):
        """Retorna a classe CSS para o badge de status"""
        classes = {
            'pendente': 'badge bg-warning',
            'ativo': 'badge bg-success', 
            'rejeitado': 'badge bg-danger',
            'bloqueado': 'badge bg-dark'
        }
        return classes.get(self.status, 'badge bg-secondary')
    
    @property
    def perfil_badge_class(self):
        """Retorna a classe CSS para o badge de perfil"""
        classes = {
            'administrador': 'badge bg-danger',
            'gerente_comercial': 'badge bg-primary',
            'financeiro': 'badge bg-success',
            'logistica': 'badge bg-info',
            'portaria': 'badge bg-warning text-dark',
            'vendedor': 'badge bg-secondary'
        }
        return classes.get(self.perfil, 'badge bg-light text-dark')
    
    @property
    def perfil_nome(self):
        """Retorna o nome amigável do perfil"""
        nomes = {
            'administrador': 'Administrador',
            'gerente_comercial': 'Gerente Comercial',
            'financeiro': 'Financeiro',
            'logistica': 'Logística',
            'portaria': 'Portaria',
            'vendedor': 'Vendedor'
        }
        return nomes.get(self.perfil, self.perfil.title())
    
    # Métodos de verificação de permissões
    def _tem_acesso_nacom(self):
        """Helper interno: usuario tem acesso aos modulos Nacom Goya (logistica)?

        Sistema e 100% Nacom exceto 5 dominios isolados (Lojas HORA, Motochefe,
        CarVia, Comercial, Pessoal). Acesso aos modulos Nacom exige:
        - status='ativo' (bloqueado/rejeitado/pendente nao acessa nada);
        - sistema_logistica=True OU perfil='administrador' (admin sempre passa).

        Usuario HORA-only (sistema_lojas=True, sistema_logistica=False) com
        perfil 'financeiro'/'logistica'/'vendedor' NAO acessa Nacom.
        """
        if self.status != 'ativo':
            return False
        return self.sistema_logistica or self.perfil == 'administrador'

    def pode_aprovar_usuarios(self):
        """Verifica se pode aprovar usuários (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'gerente_comercial']

    def pode_acessar_financeiro(self):
        """Verifica se pode acessar módulos financeiros (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']

    def pode_acessar_embarques(self):
        """Verifica se pode acessar embarques (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial', 'portaria']

    def pode_acessar_portaria(self):
        """Verifica se pode acessar módulos de portaria (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial', 'portaria']

    def pode_acessar_monitoramento_geral(self):
        """Verifica se pode acessar todo monitoramento (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']

    def pode_acessar_monitoramento_vendedor(self):
        """Verifica se pode acessar monitoramento como vendedor (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil == 'vendedor' and self.vendedor_vinculado

    def pode_editar_cadastros(self):
        """Verifica se pode editar cadastros (Nacom)"""
        if not self._tem_acesso_nacom():
            return False
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']

    # Métodos de verificação de acesso aos sistemas
    def pode_acessar_logistica(self):
        """Verifica se pode acessar o sistema de logística"""
        return self.sistema_logistica

    def pode_acessar_motochefe(self):
        """Verifica se pode acessar o sistema motochefe"""
        return self.sistema_motochefe

    def pode_acessar_carvia(self):
        """Verifica se pode acessar o sistema CarVia (frete subcontratado)"""
        return self.sistema_carvia

    def pode_acessar_seguranca(self):
        """Verifica se pode acessar o modulo de seguranca (apenas admins)"""
        return self.perfil == 'administrador'

    def pode_acessar_comissao_carvia(self):
        """Verifica se pode acessar comissoes CarVia (admin ou flag dedicada)"""
        return self.sistema_carvia and (
            self.acesso_comissao_carvia or self.perfil == 'administrador'
        )

    def pode_acessar_recebimento_carvia(self):
        """Acesso ao recebimento por chassi das Coletas CarVia (operador). Quem tem o sistema
        CarVia completo ja entra; a flag dedicada libera SO o recebimento (sem valores/CRUD)."""
        return self.sistema_carvia or self.acesso_recebimento_carvia or self.perfil == 'administrador'

    def pode_gerar_remessa_vortx(self):
        """Verifica se pode gerar remessa VORTX (flag dedicada ou admin)"""
        return self.sistema_remessa_vortx or self.perfil == 'administrador'

    def pode_acessar_lojas(self):
        """Verifica se pode acessar o modulo Lojas HORA (varejo B2C).

        Usuario com status != 'ativo' (bloqueado, rejeitado, pendente) NAO acessa,
        mesmo com sistema_lojas=True. Admin segue o mesmo gate.
        """
        if self.status != 'ativo':
            return False
        return self.sistema_lojas or self.perfil == 'administrador'

    def pode_acessar_motos_assai(self):
        """Acesso ao módulo Motos Assaí.

        Gate de status (idêntico ao Hora): admin sempre passa; usuário
        com status != 'ativo' é bloqueado mesmo que tenha o flag True.
        """
        if self.status != 'ativo':
            return False
        return self.sistema_motos_assai or self.perfil == 'administrador'

    def lojas_hora_ids_permitidas(self):
        """Retorna restricao de loja para este usuario no modulo HORA.

        - None: acesso a TODAS as lojas (admin ou usuario sem loja_hora_id setada).
        - [<id>]: restrito a 1 loja HORA (segregacao por loja).
        """
        # Admin ve tudo, independente de loja_hora_id.
        if self.perfil == 'administrador':
            return None
        if self.loja_hora_id is None:
            return None
        return [self.loja_hora_id]

    def tem_perm_hora(self, modulo: str, acao: str = 'ver') -> bool:
        """Atalho para checar permissao granular HORA em templates Jinja.

        Admin com status='ativo' sempre True; usuario com status != 'ativo' False;
        usuario sem sistema_lojas e nao-admin False.
        Demais casos consultam tabela hora_user_permissao via service.

        Usa cache por instancia (`_hora_perm_cache`) para evitar N+1 quando o
        template chama este metodo varias vezes (uma por link no menu).
        Como `current_user` e resolvido 1x por request pelo flask-login, o cache
        fica per-request naturalmente.
        """
        # Validacao de inputs primeiro — typo no template falha rapido para todos
        # (incluindo admin), evitando que strings invalidas vazem silenciosas.
        try:
            from app.hora.services.permissao_service import (
                get_matriz, _validar_modulo, _validar_acao,
            )
        except ImportError:
            return False
        try:
            _validar_modulo(modulo)
            _validar_acao(acao)
        except ValueError:
            return False

        # Gates rapidos (sem query) — inativo/admin/sem sistema_lojas.
        if self.status != 'ativo':
            return False
        if self.perfil == 'administrador':
            return True
        if not self.sistema_lojas:
            return False

        # Cache por instancia (per-request via current_user).
        cache = getattr(self, '_hora_perm_cache', None)
        if cache is None:
            cache = get_matriz(self.id)
            self._hora_perm_cache = cache
        return cache.get(modulo, {}).get(acao, False)

    # ====== PREFERENCIAS (JSONB) ======

    def get_preference(self, key: str, default=None):
        """Le preferencia do JSONB `preferences`. Retorna `default` se ausente/corrompido."""
        try:
            prefs = self.preferences or {}
            return prefs.get(key, default)
        except Exception:
            return default

    def set_preference(self, key: str, value) -> None:
        """Grava preferencia no JSONB. **Nao commita** — caller deve db.session.commit().

        Usa flag_modified pois SQLAlchemy nao detecta mutacao in-place em JSONB.
        """
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
        flag_modified(self, 'preferences')

    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    # ====== METODOS DE PERMISSAO (VENDEDORES/EQUIPES) ======

    def get_vendedores_autorizados(self):
        """Retorna lista de vendedores autorizados para o usuário"""
        from app.permissions.models import UserVendedor
        return UserVendedor.get_vendedores_usuario(self.id)
    
    def get_equipes_autorizadas(self):
        """Retorna lista de equipes autorizadas para o usuário"""
        from app.permissions.models import UserEquipe
        return UserEquipe.get_equipes_usuario(self.id)
    
    # ====== MÉTODOS DE COMPATIBILIDADE (mantém funcionamento antigo) ======

    def tem_permissao(self, modulo, funcao=None, submodulo=None):
        """Verifica permissão usando sistema de perfis"""
        return self._tem_permissao_legacy(modulo)

    def pode_editar(self, modulo, funcao=None, submodulo=None):
        """Verifica se pode editar usando sistema de perfis"""
        return self._tem_permissao_legacy(modulo)

    def _tem_permissao_legacy(self, modulo):
        """Método de compatibilidade que usa o sistema antigo de perfis"""
        # Este método mantém a lógica antiga para garantir que nada quebre
        # enquanto migra-se gradualmente para o novo sistema
        if modulo == 'usuarios':
            return self.pode_aprovar_usuarios()
        elif modulo == 'financeiro':
            return self.pode_acessar_financeiro()
        elif modulo == 'embarques':
            return self.pode_acessar_embarques()
        elif modulo == 'portaria':
            return self.pode_acessar_portaria()
        elif modulo == 'monitoramento':
            return self.pode_acessar_monitoramento_geral() or self.pode_acessar_monitoramento_vendedor()
        return self.perfil == 'administrador'


class TeamsVinculoCodigo(db.Model):
    """Codigo de pareamento Teams <-> Web (uso unico, TTL 10 min).

    Fluxo: usuario logado no web gera codigo (tela /auth/vincular-teams) ->
    envia "vincular ABC123" ao bot no Teams -> fast-path valida o hash e grava
    Usuario.teams_user_id (AAD object ID). Prova posse das DUAS contas —
    independe de e-mail correto no cadastro.

    Migration: 2026_06_10_teams_identidade.
    """
    __tablename__ = 'teams_vinculo_codigos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    codigo_hash = db.Column(db.String(64), nullable=False, index=True)  # sha256 hex
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    def __repr__(self):
        return f"<TeamsVinculoCodigo user_id={self.user_id} used={self.used_at is not None}>"
