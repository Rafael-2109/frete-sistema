"""
CarviaClienteService — CRUD de clientes + enderecos + integracao CNPJ Receita
"""

import logging
import re
from typing import Optional, Dict, List, Tuple

from app import db

logger = logging.getLogger(__name__)


class CarviaClienteService:
    """Gerencia clientes CarVia e seus enderecos"""

    # ==================== CLIENTES ====================

    @staticmethod
    def listar_clientes(apenas_ativos: bool = False, busca: Optional[str] = None):
        """Lista clientes com filtros opcionais."""
        from app.carvia.models import CarviaCliente

        query = CarviaCliente.query

        if apenas_ativos:
            query = query.filter_by(ativo=True)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                CarviaCliente.nome_comercial.ilike(busca_like)
            )

        return query.order_by(CarviaCliente.nome_comercial.asc()).all()

    @staticmethod
    def buscar_por_id(cliente_id: int):
        """Busca cliente por ID com enderecos carregados."""
        from app.carvia.models import CarviaCliente
        return db.session.get(CarviaCliente, cliente_id)

    @staticmethod
    def criar_cliente(nome_comercial: str, criado_por: str,
                      observacoes: Optional[str] = None):
        """Cria novo cliente. Retorna (cliente, erro)."""
        from app.carvia.models import CarviaCliente
        from app.utils.timezone import agora_utc_naive

        nome = nome_comercial.strip()
        if not nome:
            return None, 'Nome comercial e obrigatorio.'

        # Dedup: verificar se ja existe cliente com mesmo nome (case-insensitive)
        existente = CarviaCliente.query.filter(
            db.func.lower(CarviaCliente.nome_comercial) == nome.lower(),
        ).first()
        if existente:
            return None, f'Ja existe um cliente com o nome "{existente.nome_comercial}" (ID {existente.id}).'

        cliente = CarviaCliente(
            nome_comercial=nome,
            observacoes=observacoes,
            criado_por=criado_por,
            criado_em=agora_utc_naive(),
            atualizado_em=agora_utc_naive(),
        )
        db.session.add(cliente)
        db.session.flush()  # Gera ID
        return cliente, None

    @staticmethod
    def atualizar_cliente(cliente_id: int, dados: dict) -> Tuple[bool, Optional[str]]:
        """Atualiza dados do cliente. Retorna (sucesso, erro)."""
        from app.carvia.models import CarviaCliente

        cliente = db.session.get(CarviaCliente, cliente_id)
        if not cliente:
            return False, 'Cliente nao encontrado.'

        if 'nome_comercial' in dados:
            nome = (dados['nome_comercial'] or '').strip()
            if not nome:
                return False, 'Nome comercial e obrigatorio.'
            # Dedup: verificar se outro cliente ja tem esse nome (case-insensitive)
            existente = CarviaCliente.query.filter(
                db.func.lower(CarviaCliente.nome_comercial) == nome.lower(),
                CarviaCliente.id != cliente_id,
            ).first()
            if existente:
                return False, f'Ja existe um cliente com o nome "{existente.nome_comercial}" (ID {existente.id}).'
            cliente.nome_comercial = nome

        if 'observacoes' in dados:
            cliente.observacoes = dados['observacoes']

        if 'ativo' in dados:
            cliente.ativo = dados['ativo']

        db.session.flush()
        return True, None

    # ==================== RESOLUCAO CNPJ → CLIENTE ====================

    @staticmethod
    def resolver_clientes_por_cnpjs(cnpjs) -> Dict[str, Dict]:
        """Resolve conjunto de CNPJs para CarviaCliente (batch, sem N+1).

        Args:
            cnpjs: iteravel de CNPJs (com ou sem formatacao)

        Returns:
            dict mapeando cnpj_limpo → {id, nome_comercial}
        """
        from app.carvia.models import CarviaCliente, CarviaClienteEndereco

        cnpjs_limpos = {
            CarviaClienteService._limpar_cnpj(c)
            for c in cnpjs if c
        }
        cnpjs_limpos.discard('')

        if not cnpjs_limpos:
            return {}

        rows = db.session.query(
            CarviaClienteEndereco.cnpj,
            CarviaCliente.id,
            CarviaCliente.nome_comercial,
        ).join(
            CarviaCliente,
            CarviaClienteEndereco.cliente_id == CarviaCliente.id,
        ).filter(
            CarviaClienteEndereco.cnpj.in_(cnpjs_limpos),
            CarviaClienteEndereco.cliente_id.isnot(None),
        ).all()

        result: Dict[str, Dict] = {}
        for cnpj, cliente_id, nome_comercial in rows:
            if cnpj and cnpj not in result:
                result[cnpj] = {'id': cliente_id, 'nome_comercial': nome_comercial}
        return result

    # ==================== ENDERECOS ====================

    @staticmethod
    def _limpar_cnpj(cnpj: str) -> str:
        """Remove formatacao do CNPJ."""
        return re.sub(r'\D', '', str(cnpj))

    @staticmethod
    def adicionar_endereco(
        cliente_id: int,
        cnpj: str,
        tipo: str,
        criado_por: str,
        razao_social: Optional[str] = None,
        dados_receita: Optional[Dict] = None,
        dados_fisico: Optional[Dict] = None,
        principal: bool = False,
    ) -> Tuple[Optional[object], Optional[str]]:
        """Adiciona endereco ao cliente. Retorna (endereco, erro).

        Args:
            dados_receita: dict com campos uf, cidade, logradouro, numero, bairro, cep, complemento
            dados_fisico: dict com mesmos campos (editaveis). Se None, copia dados_receita.
        """
        from app.carvia.models import CarviaCliente, CarviaClienteEndereco
        from app.utils.timezone import agora_utc_naive

        cliente = db.session.get(CarviaCliente, cliente_id)
        if not cliente:
            return None, 'Cliente nao encontrado.'

        cnpj_limpo = CarviaClienteService._limpar_cnpj(cnpj)
        if not cnpj_limpo or len(cnpj_limpo) not in (11, 14):
            return None, 'Documento invalido (CNPJ=14 digitos, CPF=11 digitos).'

        tipo = tipo.upper()
        if tipo not in ('ORIGEM', 'DESTINO'):
            return None, 'Tipo deve ser ORIGEM ou DESTINO.'

        # Origens sao SEMPRE globais (cliente_id=NULL) — usar adicionar_origem_global()
        if tipo == 'ORIGEM':
            return None, 'Origens sao globais. Use adicionar_origem_global() em vez de adicionar_endereco().'

        # Verificar duplicata
        existente = CarviaClienteEndereco.query.filter_by(
            cliente_id=cliente_id,
            cnpj=cnpj_limpo,
            tipo=tipo,
        ).first()
        if existente:
            return None, f'Endereco com documento {cnpj_limpo} ({tipo}) ja cadastrado para este cliente.'

        # Montar dados Receita
        receita = dados_receita or {}
        # Se dados_fisico nao fornecido, copiar da Receita (pre-preenchido)
        fisico = dados_fisico if dados_fisico else dict(receita)

        # Se marcando como principal, desmarcar outros do mesmo (cliente_id, tipo)
        if principal:
            CarviaClienteEndereco.query.filter(
                CarviaClienteEndereco.cliente_id == cliente_id,
                CarviaClienteEndereco.tipo == tipo,
                CarviaClienteEndereco.principal.is_(True),
            ).update({'principal': False})

        endereco = CarviaClienteEndereco(
            cliente_id=cliente_id,
            cnpj=cnpj_limpo,
            razao_social=razao_social,
            tipo=tipo,
            principal=principal,
            criado_por=criado_por,
            criado_em=agora_utc_naive(),
            # Receita
            receita_uf=receita.get('uf'),
            receita_cidade=receita.get('cidade'),
            receita_logradouro=receita.get('logradouro'),
            receita_numero=receita.get('numero'),
            receita_bairro=receita.get('bairro'),
            receita_cep=receita.get('cep'),
            receita_complemento=receita.get('complemento'),
            # Fisico
            fisico_uf=fisico.get('uf'),
            fisico_cidade=fisico.get('cidade'),
            fisico_logradouro=fisico.get('logradouro'),
            fisico_numero=fisico.get('numero'),
            fisico_bairro=fisico.get('bairro'),
            fisico_cep=fisico.get('cep'),
            fisico_complemento=fisico.get('complemento'),
        )
        db.session.add(endereco)
        db.session.flush()
        return endereco, None

    @staticmethod
    def atualizar_endereco(endereco_id: int, dados: dict) -> Tuple[bool, Optional[str]]:
        """Atualiza endereco fisico (editavel). Retorna (sucesso, erro).

        Para destinos provisorios, tambem aceita:
        - cnpj: preencher CNPJ pendente (converte provisorio para definitivo)
        - dados_receita_*: preencher campos da Receita ao definir CNPJ
        """
        from app.carvia.models import CarviaClienteEndereco

        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco:
            return False, 'Endereco nao encontrado.'

        # Campos fisicos editaveis
        for campo in ('uf', 'cidade', 'logradouro', 'numero', 'bairro', 'cep', 'complemento'):
            chave = f'fisico_{campo}'
            if chave in dados:
                setattr(endereco, chave, dados[chave])

        if 'tipo' in dados:
            tipo = dados['tipo'].upper()
            if tipo in ('ORIGEM', 'DESTINO'):
                endereco.tipo = tipo
        if 'razao_social' in dados:
            endereco.razao_social = dados['razao_social']
        if 'principal' in dados:
            # Se marcando como principal, desmarcar outros do mesmo (cliente_id, tipo)
            if dados['principal'] and endereco.cliente_id:
                from app.carvia.models import CarviaClienteEndereco as _CCE
                _CCE.query.filter(
                    _CCE.cliente_id == endereco.cliente_id,
                    _CCE.tipo == endereco.tipo,
                    _CCE.principal.is_(True),
                    _CCE.id != endereco_id,
                ).update({'principal': False})
            endereco.principal = dados['principal']

        # Atualizar CNPJ (para completar destino provisorio)
        if 'cnpj' in dados and dados['cnpj']:
            cnpj_limpo = CarviaClienteService._limpar_cnpj(dados['cnpj'])
            if cnpj_limpo and len(cnpj_limpo) in (11, 14):
                endereco.cnpj = cnpj_limpo
                if endereco.provisorio:
                    endereco.provisorio = False

        # Campos Receita (preenchidos ao definir CNPJ via Receita Federal)
        for campo in ('uf', 'cidade', 'logradouro', 'numero', 'bairro', 'cep', 'complemento'):
            chave = f'receita_{campo}'
            if chave in dados:
                setattr(endereco, chave, dados[chave])

        db.session.flush()
        return True, None

    @staticmethod
    def remover_endereco(endereco_id: int) -> Tuple[bool, Optional[str]]:
        """Remove endereco. Retorna (sucesso, erro)."""
        from app.carvia.models import CarviaClienteEndereco, CarviaCotacao

        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco:
            return False, 'Endereco nao encontrado.'

        # Verificar se esta em uso por cotacoes
        em_uso = CarviaCotacao.query.filter(
            db.or_(
                CarviaCotacao.endereco_origem_id == endereco_id,
                CarviaCotacao.endereco_destino_id == endereco_id,
            )
        ).count()
        if em_uso:
            return False, f'Endereco em uso por {em_uso} cotacao(oes). Nao e possivel remover.'

        db.session.delete(endereco)
        db.session.flush()
        return True, None

    @staticmethod
    def buscar_enderecos_por_cnpj(cnpj: str) -> List:
        """Busca todos os enderecos cadastrados para um CNPJ (cross-cliente).

        Inclui origens globais (cliente_id IS NULL) e destinos de clientes.
        """
        from app.carvia.models import CarviaClienteEndereco

        cnpj_limpo = CarviaClienteService._limpar_cnpj(cnpj)
        return CarviaClienteEndereco.query.filter_by(cnpj=cnpj_limpo).all()

    # ==================== ORIGENS GLOBAIS ====================

    @staticmethod
    def listar_origens_globais() -> List:
        """Retorna todas as origens globais (cliente_id IS NULL, tipo=ORIGEM)."""
        from app.carvia.models import CarviaClienteEndereco

        return CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.tipo == 'ORIGEM',
            CarviaClienteEndereco.cliente_id.is_(None),
        ).order_by(CarviaClienteEndereco.razao_social).all()

    @staticmethod
    def adicionar_origem_global(
        cnpj: str,
        criado_por: str,
        razao_social: Optional[str] = None,
        dados_receita: Optional[Dict] = None,
        dados_fisico: Optional[Dict] = None,
    ) -> Tuple[Optional[object], Optional[str]]:
        """Cria origem global (compartilhada entre todos os clientes).

        Retorna (endereco, erro).
        """
        from app.carvia.models import CarviaClienteEndereco
        from app.utils.timezone import agora_utc_naive

        cnpj_limpo = CarviaClienteService._limpar_cnpj(cnpj)
        if not cnpj_limpo or len(cnpj_limpo) not in (11, 14):
            return None, 'Documento invalido (CNPJ=14 digitos, CPF=11 digitos).'

        # Verificar se ja existe origem global com esse CNPJ
        existente = CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.cnpj == cnpj_limpo,
            CarviaClienteEndereco.tipo == 'ORIGEM',
            CarviaClienteEndereco.cliente_id.is_(None),
        ).first()
        if existente:
            return existente, None  # Retorna existente sem erro

        receita = dados_receita or {}
        fisico = dados_fisico if dados_fisico else dict(receita)

        endereco = CarviaClienteEndereco(
            cliente_id=None,  # Origem global
            cnpj=cnpj_limpo,
            razao_social=razao_social,
            tipo='ORIGEM',
            principal=False,
            criado_por=criado_por,
            criado_em=agora_utc_naive(),
            receita_uf=receita.get('uf'),
            receita_cidade=receita.get('cidade'),
            receita_logradouro=receita.get('logradouro'),
            receita_numero=receita.get('numero'),
            receita_bairro=receita.get('bairro'),
            receita_cep=receita.get('cep'),
            receita_complemento=receita.get('complemento'),
            fisico_uf=fisico.get('uf'),
            fisico_cidade=fisico.get('cidade'),
            fisico_logradouro=fisico.get('logradouro'),
            fisico_numero=fisico.get('numero'),
            fisico_bairro=fisico.get('bairro'),
            fisico_cep=fisico.get('cep'),
            fisico_complemento=fisico.get('complemento'),
        )
        db.session.add(endereco)
        db.session.flush()
        return endereco, None

    # ==================== DESTINO PROVISORIO ====================

    @staticmethod
    def adicionar_destino_provisorio(
        cliente_id: int,
        criado_por: str,
        razao_social: Optional[str] = None,
        dados_fisico: Optional[Dict] = None,
    ) -> Tuple[Optional[object], Optional[str]]:
        """Cria destino provisorio sem CNPJ para cotacao de frete.

        CNPJ sera preenchido depois, antes da aprovacao.
        Endereco fisico (UF + cidade) e obrigatorio.
        """
        from app.carvia.models import CarviaCliente, CarviaClienteEndereco
        from app.utils.timezone import agora_utc_naive

        cliente = db.session.get(CarviaCliente, cliente_id)
        if not cliente:
            return None, 'Cliente nao encontrado.'

        fisico = dados_fisico or {}
        if not fisico.get('uf') or not fisico.get('cidade'):
            return None, 'UF e cidade do destino sao obrigatorios mesmo para provisorio.'

        endereco = CarviaClienteEndereco(
            cliente_id=cliente_id,
            cnpj=None,
            razao_social=razao_social,
            tipo='DESTINO',
            principal=False,
            provisorio=True,
            criado_por=criado_por,
            criado_em=agora_utc_naive(),
            fisico_uf=fisico.get('uf'),
            fisico_cidade=fisico.get('cidade'),
            fisico_logradouro=fisico.get('logradouro'),
            fisico_numero=fisico.get('numero'),
            fisico_bairro=fisico.get('bairro'),
            fisico_cep=fisico.get('cep'),
            fisico_complemento=fisico.get('complemento'),
        )
        db.session.add(endereco)
        db.session.flush()
        return endereco, None

    # ==================== INTEGRACAO RECEITA ====================

    @staticmethod
    def buscar_cnpj_receita(cnpj: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Busca dados de CNPJ na API da Receita. Retorna (dados, erro).

        Retorno formatado:
        {
            'cnpj': '12345678000199',
            'razao_social': 'EMPRESA LTDA',
            'nome_fantasia': 'EMPRESA',
            'uf': 'SP',
            'cidade': 'SAO PAULO',
            'logradouro': 'RUA X',
            'numero': '123',
            'bairro': 'CENTRO',
            'cep': '01234567',
            'complemento': 'SALA 1',
            'situacao': 'ATIVA',
        }
        """
        from app.utils.api_receita import APIReceita

        resultado = APIReceita.buscar_cnpj(cnpj)
        if not resultado:
            return None, 'CNPJ nao encontrado ou erro na API da Receita.'

        if resultado.get('status') == 'ERROR':
            return None, resultado.get('message', 'Erro na consulta do CNPJ.')

        dados = {
            'cnpj': APIReceita.limpar_cnpj(cnpj),
            'razao_social': resultado.get('nome', ''),
            'nome_fantasia': resultado.get('fantasia', ''),
            'uf': resultado.get('uf', ''),
            'cidade': resultado.get('municipio', ''),
            'logradouro': resultado.get('logradouro', ''),
            'numero': resultado.get('numero', ''),
            'bairro': resultado.get('bairro', ''),
            'cep': re.sub(r'\D', '', resultado.get('cep', '')),
            'complemento': resultado.get('complemento', ''),
            'situacao': resultado.get('situacao', ''),
        }

        return dados, None
