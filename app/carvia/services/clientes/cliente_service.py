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

        Considera apenas enderecos ATIVOS — inativos nao devem sugerir cliente.

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
            CarviaClienteEndereco.ativo == True,
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

        # Verificar duplicata (considera apenas ativos — o index parcial ignora inativos)
        existente = CarviaClienteEndereco.query.filter_by(
            cliente_id=cliente_id,
            cnpj=cnpj_limpo,
            tipo=tipo,
            ativo=True,
        ).first()
        if existente:
            return None, f'Endereco com documento {cnpj_limpo} ({tipo}) ja cadastrado para este cliente.'

        # Montar dados Receita
        receita = dados_receita or {}
        # Se dados_fisico nao fornecido, copiar da Receita (pre-preenchido)
        fisico = dados_fisico if dados_fisico else dict(receita)

        endereco = CarviaClienteEndereco(
            cliente_id=cliente_id,
            cnpj=cnpj_limpo,
            razao_social=razao_social,
            tipo=tipo,
            principal=False,
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
    def atualizar_endereco(
        endereco_id: int, dados: dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Atualiza endereco fisico (editavel). Retorna (sucesso, erro, contexto).

        Aceita tambem:
        - cliente_id: transferir endereco para outro cliente (pre-valida duplicata)
        - cnpj: preencher CNPJ pendente (converte provisorio para definitivo)
        - ativo: soft delete / reativar
        - dados_receita_*: preencher campos da Receita ao definir CNPJ

        Quando a transferencia de cliente causaria violacao do unique
        (cliente_id, cnpj, tipo), retorna (False, msg, {
            'acao_sugerida': 'mesclar',
            'endereco_existente_id': <id>,
            'cliente_destino_id': <id>,
            'cliente_destino_nome': <nome>,
        }). Chamador pode oferecer mesclar ao usuario.
        """
        from app.carvia.models import CarviaCliente, CarviaClienteEndereco

        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco:
            return False, 'Endereco nao encontrado.', None

        # Transferir para outro cliente (pre-validar antes do flush)
        if 'cliente_id' in dados:
            novo_cliente_id = dados['cliente_id']
            if novo_cliente_id is not None:
                novo_cliente_id = int(novo_cliente_id)
                novo_cliente = db.session.get(CarviaCliente, novo_cliente_id)
                if not novo_cliente:
                    return False, 'Cliente destino nao encontrado.', None
                if not novo_cliente.ativo:
                    return False, 'Cliente destino esta inativo.', None

                # Detectar duplicata ANTES do flush (evitar UniqueViolation cru)
                if (endereco.cnpj and endereco.tipo and
                        novo_cliente_id != endereco.cliente_id):
                    duplicata = CarviaClienteEndereco.query.filter(
                        CarviaClienteEndereco.cliente_id == novo_cliente_id,
                        CarviaClienteEndereco.cnpj == endereco.cnpj,
                        CarviaClienteEndereco.tipo == endereco.tipo,
                        CarviaClienteEndereco.ativo == True,
                        CarviaClienteEndereco.id != endereco_id,
                    ).first()
                    if duplicata:
                        return (
                            False,
                            (f'Ja existe endereco ativo com CNPJ {endereco.cnpj} '
                             f'({endereco.tipo}) no cliente "{novo_cliente.nome_comercial}". '
                             f'Deseja mesclar o historico neste existente?'),
                            {
                                'acao_sugerida': 'mesclar',
                                'endereco_existente_id': duplicata.id,
                                'cliente_destino_id': novo_cliente_id,
                                'cliente_destino_nome': novo_cliente.nome_comercial,
                            },
                        )
            endereco.cliente_id = novo_cliente_id

        # Soft-delete / reativar
        if 'ativo' in dados:
            novo_ativo = bool(dados['ativo'])
            # Ao reativar, detectar conflito com unique parcial
            if novo_ativo and not endereco.ativo and endereco.cnpj and endereco.cliente_id:
                conflito = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cliente_id == endereco.cliente_id,
                    CarviaClienteEndereco.cnpj == endereco.cnpj,
                    CarviaClienteEndereco.tipo == endereco.tipo,
                    CarviaClienteEndereco.ativo == True,
                    CarviaClienteEndereco.id != endereco_id,
                ).first()
                if conflito:
                    return (
                        False,
                        (f'Nao e possivel reativar: ja existe outro endereco ativo '
                         f'com mesmo CNPJ e tipo neste cliente (id={conflito.id}).'),
                        {
                            'acao_sugerida': 'mesclar',
                            'endereco_existente_id': conflito.id,
                        },
                    )
            endereco.ativo = novo_ativo

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
        return True, None, None

    @staticmethod
    def buscar_candidatos_migracao(endereco_id: int) -> List:
        """Retorna outros enderecos ativos com mesmo (cnpj, tipo) em OUTROS clientes.

        Usado antes de hard delete para oferecer opcao de migracao do historico.
        """
        from app.carvia.models import CarviaClienteEndereco

        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco or not endereco.cnpj:
            return []

        query = CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.cnpj == endereco.cnpj,
            CarviaClienteEndereco.tipo == endereco.tipo,
            CarviaClienteEndereco.ativo == True,
            CarviaClienteEndereco.id != endereco_id,
        )
        # Se o endereco pertence a cliente, considerar apenas enderecos de OUTROS
        # clientes (nao origens globais). Se e origem global, nao ha candidato (seria
        # a propria — origens globais sao unicas por CNPJ).
        if endereco.cliente_id is not None:
            query = query.filter(CarviaClienteEndereco.cliente_id.isnot(None))
            query = query.filter(CarviaClienteEndereco.cliente_id != endereco.cliente_id)
        else:
            query = query.filter(CarviaClienteEndereco.cliente_id.is_(None))

        return query.all()

    @staticmethod
    def _migrar_referencias(origem_id: int, destino_id: int) -> int:
        """Migra todas FKs de origem_id → destino_id. Retorna total migrado.

        Atualmente so carvia_cotacoes (endereco_origem_id, endereco_destino_id).
        Se novas FKs forem adicionadas, incluir aqui.
        """
        from app.carvia.models import CarviaCotacao

        total = 0
        total += CarviaCotacao.query.filter_by(
            endereco_origem_id=origem_id
        ).update({'endereco_origem_id': destino_id}, synchronize_session=False)
        total += CarviaCotacao.query.filter_by(
            endereco_destino_id=origem_id
        ).update({'endereco_destino_id': destino_id}, synchronize_session=False)
        return total

    @staticmethod
    def mesclar_enderecos(
        origem_id: int, destino_id: int
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Mescla origem → destino: migra cotacoes + soft-delete origem.

        Pre-requisitos: mesmo cnpj E mesmo tipo. IDs distintos. Destino ativo.
        Retorna (sucesso, erro, {total_migrado, origem_id, destino_id}).
        """
        from app.carvia.models import CarviaClienteEndereco

        if origem_id == destino_id:
            return False, 'Origem e destino sao o mesmo endereco.', None

        origem = db.session.get(CarviaClienteEndereco, origem_id)
        destino = db.session.get(CarviaClienteEndereco, destino_id)
        if not origem:
            return False, 'Endereco origem nao encontrado.', None
        if not destino:
            return False, 'Endereco destino nao encontrado.', None
        if not destino.ativo:
            return False, 'Endereco destino esta inativo — reative antes de mesclar.', None
        if origem.cnpj != destino.cnpj:
            return False, 'CNPJ do origem e destino nao coincidem.', None
        if origem.tipo != destino.tipo:
            return False, 'Tipo (ORIGEM/DESTINO) do origem e destino nao coincidem.', None

        total = CarviaClienteService._migrar_referencias(origem_id, destino_id)
        origem.ativo = False  # soft-delete: historico preservado
        db.session.flush()

        return True, None, {
            'total_migrado': total,
            'origem_id': origem_id,
            'destino_id': destino_id,
        }

    @staticmethod
    def migrar_e_remover(
        origem_id: int, destino_id: int
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Migra cotacoes origem → destino e DELETA fisicamente o origem.

        Usado quando usuario quer erradicar o endereco errado. Requer destino
        valido (candidato em OUTRO cliente com mesmo cnpj+tipo).
        Retorna (sucesso, erro, {total_migrado}).
        """
        from app.carvia.models import CarviaClienteEndereco

        if origem_id == destino_id:
            return False, 'Origem e destino sao o mesmo endereco.', None

        origem = db.session.get(CarviaClienteEndereco, origem_id)
        destino = db.session.get(CarviaClienteEndereco, destino_id)
        if not origem:
            return False, 'Endereco origem nao encontrado.', None
        if not destino:
            return False, 'Endereco destino nao encontrado.', None
        if not destino.ativo:
            return False, 'Endereco destino esta inativo.', None
        if origem.cnpj != destino.cnpj or origem.tipo != destino.tipo:
            return False, 'Destino deve ter mesmo CNPJ e tipo do origem.', None

        total = CarviaClienteService._migrar_referencias(origem_id, destino_id)
        db.session.delete(origem)
        db.session.flush()
        return True, None, {'total_migrado': total}

    @staticmethod
    def remover_endereco(
        endereco_id: int, forcar: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Remove endereco (hard delete). Retorna (sucesso, erro, contexto).

        Regras:
          - Se endereco NAO tem cotacoes vinculadas → DELETE direto.
          - Se tem cotacoes, exige migracao para outro endereco valido (via
            migrar_e_remover) — este metodo retorna erro + candidatos.
          - `forcar=True`: apenas para callers internos; deleta mesmo com
            cotacoes (usado por migrar_e_remover).

        Contexto quando bloqueado:
            {
              'candidatos_migracao': [ {id, cliente_id, cliente_nome, fisico_cidade, fisico_uf, razao_social} ],
              'total_cotacoes': <int>,
              'sugestao': 'migrar_e_remover' | 'desativar'
            }
        """
        from app.carvia.models import CarviaClienteEndereco, CarviaCotacao, CarviaCliente

        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco:
            return False, 'Endereco nao encontrado.', None

        # Contar cotacoes vinculadas (todos status — e FK real no banco)
        total_cotacoes = CarviaCotacao.query.filter(
            db.or_(
                CarviaCotacao.endereco_origem_id == endereco_id,
                CarviaCotacao.endereco_destino_id == endereco_id,
            ),
        ).count()

        if total_cotacoes == 0 or forcar:
            db.session.delete(endereco)
            db.session.flush()
            return True, None, {'total_cotacoes': total_cotacoes}

        # Tem cotacoes: buscar candidatos para migracao
        candidatos = CarviaClienteService.buscar_candidatos_migracao(endereco_id)

        candidatos_serial = []
        for c in candidatos:
            cliente_nome = None
            if c.cliente_id:
                cli = db.session.get(CarviaCliente, c.cliente_id)
                cliente_nome = cli.nome_comercial if cli else None
            candidatos_serial.append({
                'id': c.id,
                'cliente_id': c.cliente_id,
                'cliente_nome': cliente_nome,
                'razao_social': c.razao_social,
                'fisico_cidade': c.fisico_cidade,
                'fisico_uf': c.fisico_uf,
            })

        if candidatos_serial:
            return (
                False,
                (f'Endereco vinculado a {total_cotacoes} cotacao(oes). '
                 f'Selecione um destino abaixo para migrar o historico e remover.'),
                {
                    'candidatos_migracao': candidatos_serial,
                    'total_cotacoes': total_cotacoes,
                    'sugestao': 'migrar_e_remover',
                },
            )

        return (
            False,
            (f'Endereco vinculado a {total_cotacoes} cotacao(oes) e nao ha outro '
             f'endereco valido (mesmo CNPJ+tipo) para migrar o historico. '
             f'Use "Desativar" para remove-lo das opcoes sem perder o historico.'),
            {
                'candidatos_migracao': [],
                'total_cotacoes': total_cotacoes,
                'sugestao': 'desativar',
            },
        )

    @staticmethod
    def buscar_enderecos_por_cnpj(cnpj: str, apenas_ativos: bool = True) -> List:
        """Busca todos os enderecos cadastrados para um CNPJ (cross-cliente).

        Inclui origens globais (cliente_id IS NULL) e destinos de clientes.
        Por padrao retorna apenas ativos — callers que precisam de historico
        completo devem passar apenas_ativos=False explicitamente.
        """
        from app.carvia.models import CarviaClienteEndereco

        cnpj_limpo = CarviaClienteService._limpar_cnpj(cnpj)
        query = CarviaClienteEndereco.query.filter_by(cnpj=cnpj_limpo)
        if apenas_ativos:
            query = query.filter(CarviaClienteEndereco.ativo == True)
        return query.all()

    # ==================== ORIGENS GLOBAIS ====================

    @staticmethod
    def listar_origens_globais(apenas_ativos: bool = True) -> List:
        """Retorna todas as origens globais (cliente_id IS NULL, tipo=ORIGEM).

        Por padrao filtra apenas ativas — origens desativadas nao aparecem como opcao.
        """
        from app.carvia.models import CarviaClienteEndereco

        query = CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.tipo == 'ORIGEM',
            CarviaClienteEndereco.cliente_id.is_(None),
        )
        if apenas_ativos:
            query = query.filter(CarviaClienteEndereco.ativo == True)
        return query.order_by(CarviaClienteEndereco.razao_social).all()

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

        # Verificar se ja existe origem global ATIVA com esse CNPJ
        existente = CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.cnpj == cnpj_limpo,
            CarviaClienteEndereco.tipo == 'ORIGEM',
            CarviaClienteEndereco.cliente_id.is_(None),
            CarviaClienteEndereco.ativo == True,
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
