"""
TrainerService - Orquestracao do fluxo de ensino.

Coordena todo o processo:
1. Iniciar sessao de ensino
2. Receber decomposicao
3. Gerar codigo
4. Debate e refinamento
5. Teste e validacao
6. Ativacao

Limite: 300 linhas
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app import db

logger = logging.getLogger(__name__)


class TrainerService:
    """
    Orquestra o fluxo completo de ensino do Claude.

    Uso:
        service = TrainerService()

        # Inicia sessao
        sessao = service.iniciar_sessao(pergunta_id=123, usuario="admin")

        # Usuario decompoe
        service.salvar_decomposicao(sessao.id, decomposicao)

        # Gera codigo
        codigo = service.gerar_codigo(sessao.id)

        # Debate
        resposta = service.debater(sessao.id, "E se o cliente nao existir?")

        # Testa
        resultado = service.testar_codigo(sessao.id)

        # Ativa
        service.ativar_codigo(sessao.id)
    """

    def iniciar_sessao(
        self,
        pergunta_id: int,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Inicia uma nova sessao de ensino.

        Args:
            pergunta_id: ID da pergunta nao respondida
            usuario: Nome do usuario

        Returns:
            Dict com dados da sessao criada
        """
        from ..models import SessaoEnsinoIA
        from ...models import ClaudePerguntaNaoRespondida

        # Busca a pergunta
        pergunta = ClaudePerguntaNaoRespondida.query.get(pergunta_id)
        if not pergunta:
            return {
                'sucesso': False,
                'erro': 'Pergunta nao encontrada'
            }

        # Verifica se ja tem sessao ativa para essa pergunta
        sessao_existente = SessaoEnsinoIA.query.filter_by(
            pergunta_origem_id=pergunta_id
        ).filter(
            SessaoEnsinoIA.status.notin_(['cancelada', 'ativada'])
        ).first()

        if sessao_existente:
            return {
                'sucesso': True,
                'sessao': sessao_existente.to_dict(),
                'mensagem': 'Sessao existente retomada'
            }

        # Cria nova sessao
        sessao = SessaoEnsinoIA(
            pergunta_origem_id=pergunta_id,
            pergunta_original=pergunta.consulta,
            status='iniciada',
            criado_por=usuario
        )
        db.session.add(sessao)
        db.session.commit()

        logger.info(f"[TRAINER] Sessao {sessao.id} iniciada para pergunta {pergunta_id}")

        return {
            'sucesso': True,
            'sessao': sessao.to_dict(),
            'pergunta': pergunta.to_dict()
        }

    def obter_sessao(self, sessao_id: int) -> Optional[Dict]:
        """Obtem dados de uma sessao."""
        from ..models import SessaoEnsinoIA

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return None

        resultado = sessao.to_dict()

        # Adiciona codigo gerado se houver
        if sessao.codigo_gerado:
            resultado['codigo_gerado'] = sessao.codigo_gerado.to_dict()

        return resultado

    def sugerir_decomposicao(self, sessao_id: int) -> Dict[str, Any]:
        """
        Sugere decomposicao inicial para a pergunta.
        """
        from ..models import SessaoEnsinoIA
        from .code_generator import CodeGenerator

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        generator = CodeGenerator()
        return generator.sugerir_decomposicao(sessao.pergunta_original)

    def salvar_decomposicao(
        self,
        sessao_id: int,
        decomposicao: List[Dict]
    ) -> Dict[str, Any]:
        """
        Salva a decomposicao feita pelo usuario.

        Args:
            sessao_id: ID da sessao
            decomposicao: Lista de partes explicadas
        """
        from ..models import SessaoEnsinoIA

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        sessao.decomposicao = decomposicao
        sessao.atualizar_status('decomposta')
        db.session.commit()

        return {
            'sucesso': True,
            'sessao': sessao.to_dict()
        }

    def gerar_codigo(self, sessao_id: int) -> Dict[str, Any]:
        """
        Gera codigo baseado na decomposicao.
        """
        from ..models import SessaoEnsinoIA
        from .code_generator import CodeGenerator
        from .codebase_reader import CodebaseReader

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        if not sessao.decomposicao:
            return {'sucesso': False, 'erro': 'Decomposicao nao encontrada. Salve a decomposicao primeiro.'}

        # Salva dados necessarios antes da operacao longa (evita problemas de sessao)
        pergunta_original = sessao.pergunta_original
        decomposicao = sessao.decomposicao

        # Gera contexto do codigo
        reader = CodebaseReader()
        contexto = reader.gerar_contexto_para_claude()

        # Gera codigo (operacao LONGA - pode levar 30-60 segundos)
        generator = CodeGenerator()
        resultado = generator.gerar_codigo(
            pergunta=pergunta_original,
            decomposicao=decomposicao,
            contexto_codigo=contexto
        )

        # IMPORTANTE: Reconecta ao banco apos operacao longa
        # A conexao SSL pode ter sido fechada durante a chamada a API
        self._reconectar_se_necessario()

        # Rebusca a sessao com conexao fresca
        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada apos reconexao'}

        if not resultado.get('sucesso'):
            sessao.adicionar_mensagem_debate('sistema', f"Erro na geracao: {resultado.get('erro')}")
            db.session.commit()
            return resultado

        # Adiciona ao debate
        sessao.adicionar_mensagem_debate('assistente', f"Codigo gerado:\n```json\n{resultado}\n```")
        sessao.atualizar_status('codigo_gerado')
        db.session.commit()

        return resultado

    def _reconectar_se_necessario(self):
        """
        Verifica e reconecta ao banco se a conexao foi perdida.

        Isso eh necessario apos operacoes longas (como chamadas a API Claude)
        onde a conexao SSL pode ter sido fechada por timeout.
        """
        from sqlalchemy import text

        try:
            # Tenta um comando simples para verificar conexao
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            logger.warning(f"[TRAINER] Conexao perdida, reconectando: {e}")
            # Remove conexoes invalidas do pool
            db.session.rollback()
            db.session.remove()
            # Nova sessao sera criada automaticamente na proxima query

    def debater(
        self,
        sessao_id: int,
        mensagem_usuario: str
    ) -> Dict[str, Any]:
        """
        Processa mensagem de debate do usuario.

        Permite questionar, refinar ou ajustar o codigo.
        """
        from ..models import SessaoEnsinoIA
        from .code_generator import CodeGenerator

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        # Registra mensagem do usuario
        sessao.adicionar_mensagem_debate('usuario', mensagem_usuario)
        sessao.atualizar_status('em_debate')

        # Busca codigo atual
        codigo_atual = None
        if sessao.historico_debate:
            # Procura ultimo codigo no debate
            for msg in reversed(sessao.historico_debate):
                if msg['role'] == 'assistente' and 'codigo gerado' in msg['content'].lower():
                    # Extrai JSON do codigo
                    import json
                    import re
                    match = re.search(r'```json\s*(\{.*?\})\s*```', msg['content'], re.DOTALL)
                    if match:
                        try:
                            codigo_atual = json.loads(match.group(1))
                        except:
                            pass
                    break

        if not codigo_atual:
            # Primeira geracao
            resultado = self.gerar_codigo(sessao_id)
        else:
            # Refinamento
            generator = CodeGenerator()
            resultado = generator.refinar_codigo(codigo_atual, mensagem_usuario)

        if resultado.get('sucesso'):
            import json
            sessao.adicionar_mensagem_debate(
                'assistente',
                f"Codigo refinado:\n```json\n{json.dumps(resultado, indent=2, ensure_ascii=False)}\n```"
            )

        db.session.commit()
        return resultado

    def testar_codigo(self, sessao_id: int) -> Dict[str, Any]:
        """
        Testa o codigo gerado.
        """
        from ..models import SessaoEnsinoIA, CodigoSistemaGerado
        from .code_validator import CodeValidator
        from .code_executor import CodeExecutor

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        # Busca ultimo codigo do debate
        codigo_gerado = self._extrair_ultimo_codigo(sessao)
        if not codigo_gerado:
            return {'sucesso': False, 'erro': 'Nenhum codigo encontrado para testar'}

        sessao.atualizar_status('testando')

        # 1. Valida o codigo
        validator = CodeValidator()
        validacao = validator.validar_definicao_tecnica(
            codigo_gerado.get('tipo_codigo', 'filtro'),
            codigo_gerado.get('definicao_tecnica', '')
        )

        if not validacao['valido']:
            sessao.adicionar_mensagem_debate(
                'sistema',
                f"Validacao falhou: {validacao['erros']}"
            )
            db.session.commit()
            return {
                'sucesso': False,
                'erro': 'Validacao falhou',
                'detalhes': validacao
            }

        # 2. Executa teste
        executor = CodeExecutor()

        if codigo_gerado.get('tipo_codigo') == 'filtro':
            models = codigo_gerado.get('models_referenciados', [])
            model = models[0] if models else 'CarteiraPrincipal'

            resultado_teste = executor.executar_filtro(
                model=model,
                filtro=codigo_gerado.get('definicao_tecnica', ''),
                limite=5
            )
        else:
            resultado_teste = {
                'sucesso': True,
                'mensagem': f"Tipo '{codigo_gerado.get('tipo_codigo')}' validado (sem execucao)"
            }

        # Registra resultado
        sessao.adicionar_mensagem_debate(
            'sistema',
            f"Teste: {'SUCESSO' if resultado_teste['sucesso'] else 'FALHA'}\n"
            f"Detalhes: {resultado_teste}"
        )

        if resultado_teste['sucesso']:
            sessao.atualizar_status('validada')

        db.session.commit()

        return {
            'sucesso': resultado_teste['sucesso'],
            'validacao': validacao,
            'execucao': resultado_teste
        }

    def ativar_codigo(
        self,
        sessao_id: int,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Ativa o codigo gerado, tornando-o disponivel para uso.
        """
        from ..models import SessaoEnsinoIA, CodigoSistemaGerado
        from ...models import ClaudePerguntaNaoRespondida

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        if sessao.status not in ['validada', 'codigo_gerado', 'em_debate']:
            return {'sucesso': False, 'erro': f'Status invalido para ativacao: {sessao.status}'}

        # Extrai codigo
        codigo_dados = self._extrair_ultimo_codigo(sessao)
        if not codigo_dados:
            return {'sucesso': False, 'erro': 'Nenhum codigo encontrado'}

        # Cria registro do codigo
        codigo = CodigoSistemaGerado(
            nome=codigo_dados.get('nome'),
            tipo_codigo=codigo_dados.get('tipo_codigo'),
            dominio=codigo_dados.get('dominio'),
            gatilhos=codigo_dados.get('gatilhos', []),
            composicao=codigo_dados.get('composicao'),
            definicao_tecnica=codigo_dados.get('definicao_tecnica'),
            models_referenciados=codigo_dados.get('models_referenciados'),
            campos_referenciados=codigo_dados.get('campos_referenciados'),
            descricao_claude=codigo_dados.get('descricao_claude'),
            exemplos_uso=codigo_dados.get('exemplos_uso'),
            variacoes=codigo_dados.get('variacoes'),
            ativo=True,
            validado=True,
            data_validacao=datetime.now(),
            validado_por=usuario,
            pergunta_origem_id=sessao.pergunta_origem_id,
            sessao_ensino_id=sessao.id,
            criado_por=usuario
        )

        db.session.add(codigo)

        # Atualiza sessao
        sessao.codigo_gerado_id = codigo.id
        sessao.atualizar_status('ativada')

        # Marca pergunta como solucionada
        pergunta = ClaudePerguntaNaoRespondida.query.get(sessao.pergunta_origem_id)
        if pergunta:
            pergunta.status = 'implementado'

        db.session.commit()

        # Invalida cache de codigos para que o novo codigo seja carregado
        from .codigo_loader import invalidar_cache
        invalidar_cache()

        logger.info(f"[TRAINER] Codigo {codigo.id} ativado para sessao {sessao_id}")

        return {
            'sucesso': True,
            'codigo': codigo.to_dict(),
            'mensagem': 'Codigo ativado com sucesso!'
        }

    def _extrair_ultimo_codigo(self, sessao) -> Optional[Dict]:
        """Extrai ultimo codigo do historico de debate."""
        import json
        import re

        if not sessao.historico_debate:
            return None

        for msg in reversed(sessao.historico_debate):
            if msg['role'] == 'assistente':
                match = re.search(r'```json\s*(\{.*?\})\s*```', msg['content'], re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except:
                        pass

        return None

    def cancelar_sessao(self, sessao_id: int) -> Dict[str, Any]:
        """Cancela uma sessao de ensino."""
        from ..models import SessaoEnsinoIA

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return {'sucesso': False, 'erro': 'Sessao nao encontrada'}

        sessao.atualizar_status('cancelada')
        db.session.commit()

        return {'sucesso': True, 'mensagem': 'Sessao cancelada'}

    def listar_sessoes(
        self,
        status: str = None,
        limite: int = 20
    ) -> List[Dict]:
        """Lista sessoes de ensino."""
        from ..models import SessaoEnsinoIA

        query = SessaoEnsinoIA.query

        if status:
            query = query.filter_by(status=status)

        sessoes = query.order_by(SessaoEnsinoIA.criado_em.desc()).limit(limite).all()

        return [s.to_dict() for s in sessoes]
