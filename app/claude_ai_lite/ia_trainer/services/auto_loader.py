"""
AutoLoader - Geracao autonoma de loaders em tempo real.

Quando o sistema nao encontra capacidade para responder uma pergunta,
este servico tenta:
1. Gerar um loader estruturado via Claude
2. Executar o loader para obter resposta imediata
3. Salvar o loader como PENDENTE_REVISAO para aprovacao humana

REGRAS:
- Loaders auto-gerados NAO sao ativados automaticamente
- Resposta eh marcada como "experimental"
- Admin revisa e ativa/descarta depois
- Sem retentativas em caso de falha

Criado em: 23/11/2025
Limite: 300 linhas
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoLoaderService:
    """
    Servico de auto-geracao de loaders.

    Uso:
        service = AutoLoaderService()
        resultado = service.tentar_responder(
            consulta="Ha pedidos do cliente Assai sem agendamento?",
            intencao={"dominio": "carteira", "entidades": {...}},
            usuario_id=123
        )

        if resultado['sucesso']:
            print(resultado['resposta'])  # Resposta experimental
            print(resultado['loader_id'])  # ID do loader salvo para revisao
    """

    def __init__(self):
        self._code_generator = None
        self._loader_executor = None

    def _get_code_generator(self):
        """Lazy loading do CodeGenerator."""
        if self._code_generator is None:
            from .code_generator import CodeGenerator
            self._code_generator = CodeGenerator()
        return self._code_generator

    def _get_loader_executor(self):
        """Lazy loading do LoaderExecutor."""
        if self._loader_executor is None:
            from .loader_executor import LoaderExecutor
            self._loader_executor = LoaderExecutor()
        return self._loader_executor

    def tentar_responder(
        self,
        consulta: str,
        intencao: Dict[str, Any],
        usuario_id: int = None,
        usuario: str = "sistema",
        conhecimento_negocio: str = None
    ) -> Dict[str, Any]:
        """
        Tenta gerar um loader e responder a pergunta automaticamente.

        Args:
            consulta: Pergunta do usuario
            intencao: Resultado da classificacao (dominio, entidades, etc)
            usuario_id: ID do usuario
            usuario: Nome do usuario
            conhecimento_negocio: NOVO v3.5.2 - Aprendizados de negocio (opcional)

        Returns:
            Dict com:
            - sucesso: bool
            - resposta: str (resposta formatada ou None)
            - experimental: bool (sempre True para auto-gerados)
            - loader_id: int (ID do loader salvo para revisao)
            - erro: str (se falhou)
        """
        resultado = {
            'sucesso': False,
            'resposta': None,
            'experimental': True,
            'loader_id': None,
            'erro': None
        }

        try:
            # 1. Verifica se pergunta eh simples o suficiente para auto-gerar
            if not self._pergunta_elegivel(consulta, intencao):
                resultado['erro'] = 'Pergunta muito complexa para auto-geracao'
                return resultado

            logger.info(f"[AUTO_LOADER] Tentando auto-gerar loader para: {consulta[:50]}...")

            # 1.1 NOVO v3.5.2: Carrega conhecimento se nao fornecido
            if not conhecimento_negocio and usuario_id:
                conhecimento_negocio = self._carregar_conhecimento(usuario_id)

            # 2. Gera decomposicao automatica simplificada
            decomposicao = self._gerar_decomposicao_automatica(consulta, intencao)

            # 3. Gera loader via Claude (com conhecimento de negocio)
            codigo_gerado = self._gerar_loader(consulta, decomposicao, conhecimento_negocio)

            if not codigo_gerado.get('sucesso'):
                resultado['erro'] = f"Falha ao gerar loader: {codigo_gerado.get('erro')}"
                return resultado

            # 4. Valida se eh um loader estruturado valido
            definicao_tecnica = codigo_gerado.get('definicao_tecnica')
            if not self._validar_loader_estruturado(definicao_tecnica):
                resultado['erro'] = 'Loader gerado nao eh estruturado valido'
                return resultado

            # Log do loader gerado para debug
            logger.info(f"[AUTO_LOADER] Loader gerado: {definicao_tecnica}")

            # 5. Executa o loader para obter resposta
            resultado_execucao = self._executar_loader(definicao_tecnica, intencao.get('entidades', {}))

            if not resultado_execucao.get('sucesso'):
                resultado['erro'] = f"Falha ao executar loader: {resultado_execucao.get('erro')}"
                # Mesmo falhando, salva para revisao
                loader_id = self._salvar_loader_pendente(
                    consulta, codigo_gerado, usuario,
                    erro_execucao=resultado_execucao.get('erro')
                )
                resultado['loader_id'] = loader_id
                return resultado

            # 6. Formata resposta
            resposta = self._formatar_resposta(consulta, resultado_execucao)
            resultado['resposta'] = resposta
            resultado['sucesso'] = True

            # 7. Salva loader como pendente de revisao
            loader_id = self._salvar_loader_pendente(
                consulta, codigo_gerado, usuario,
                resultado_execucao=resultado_execucao
            )
            resultado['loader_id'] = loader_id

            logger.info(f"[AUTO_LOADER] Sucesso! Loader #{loader_id} salvo para revisao")

        except Exception as e:
            logger.error(f"[AUTO_LOADER] Erro: {e}")
            resultado['erro'] = str(e)

        return resultado

    def _pergunta_elegivel(self, consulta: str, intencao: Dict) -> bool:
        """
        Verifica se pergunta eh elegivel para auto-geracao.

        Criterios:
        - Dominio conhecido (carteira, estoque, etc)
        - Pelo menos uma entidade identificada
        - Nao eh acao (criar, deletar, etc)
        """
        dominio = intencao.get('dominio', '')
        entidades = intencao.get('entidades', {})
        intencao_tipo = intencao.get('intencao', '')

        # Dominios permitidos
        dominios_permitidos = ['carteira', 'estoque', 'fretes', 'embarques', 'faturamento']
        if dominio not in dominios_permitidos:
            return False

        # Deve ter pelo menos uma entidade
        entidades_preenchidas = [k for k, v in entidades.items() if v]
        if not entidades_preenchidas:
            return False

        # Nao pode ser acao
        if dominio == 'acao' or intencao_tipo in ('criar_separacao', 'confirmar_acao'):
            return False

        return True

    def _gerar_decomposicao_automatica(self, consulta: str, intencao: Dict) -> List[Dict]:
        """
        Gera decomposicao automatica baseada nas entidades detectadas.

        Nao eh tao boa quanto a decomposicao humana, mas funciona para casos simples.
        """
        decomposicao = []
        entidades = intencao.get('entidades', {})

        # Adiciona entidades como partes
        for campo, valor in entidades.items():
            if valor:
                decomposicao.append({
                    'parte': str(valor),
                    'explicacao': f"Valor para o campo {campo}",
                    'tipo': 'entidade',
                    'campo': campo
                })

        # Adiciona contexto da pergunta
        decomposicao.append({
            'parte': consulta,
            'explicacao': 'Pergunta completa do usuario - gerar loader estruturado para responder',
            'tipo': 'loader'
        })

        return decomposicao

    def _carregar_conhecimento(self, usuario_id: int) -> Optional[str]:
        """
        NOVO v3.5.2: Carrega conhecimento de negocio para o usuario.

        Args:
            usuario_id: ID do usuario

        Returns:
            String com aprendizados formatados ou None
        """
        try:
            from ...prompts.intent_prompt import _carregar_aprendizados_usuario
            return _carregar_aprendizados_usuario(usuario_id)
        except Exception as e:
            logger.debug(f"[AUTO_LOADER] Erro ao carregar conhecimento: {e}")
            return None

    def _gerar_loader(self, consulta: str, decomposicao: List[Dict], conhecimento_negocio: str = None) -> Dict[str, Any]:
        """Gera loader via CodeGenerator."""
        generator = self._get_code_generator()

        # Adiciona instrucao para preferir loader estruturado
        decomposicao_enhanced = decomposicao + [{
            'parte': '[INSTRUCAO]',
            'explicacao': 'OBRIGATORIO: Gere um LOADER com definicao_tecnica em formato JSON estruturado. '
                          'NAO gere codigo Python. Use o formato com modelo_base, filtros, campos_retorno.',
            'tipo': 'instrucao'
        }]

        # NOVO v3.5.2: Passa conhecimento de negocio ao CodeGenerator
        return generator.gerar_codigo(
            pergunta=consulta,
            decomposicao=decomposicao_enhanced,
            conhecimento_negocio=conhecimento_negocio
        )

    def _validar_loader_estruturado(self, definicao_tecnica) -> bool:
        """Verifica se a definicao eh um loader estruturado valido."""
        if not definicao_tecnica:
            return False

        # Se for string, tenta parsear
        if isinstance(definicao_tecnica, str):
            try:
                # Remove markdown code blocks se houver
                if '```' in definicao_tecnica:
                    import re
                    match = re.search(r'```(?:json)?\s*(.*?)\s*```', definicao_tecnica, re.DOTALL)
                    if match:
                        definicao_tecnica = match.group(1)
                definicao_tecnica = json.loads(definicao_tecnica)
            except json.JSONDecodeError:
                return False

        # Verifica campos obrigatorios
        if not isinstance(definicao_tecnica, dict):
            return False

        if 'modelo_base' not in definicao_tecnica:
            return False

        return True

    def _executar_loader(self, definicao_tecnica, entidades: Dict) -> Dict[str, Any]:
        """Executa o loader via LoaderExecutor."""
        executor = self._get_loader_executor()

        # Parseia definicao se necessario
        if isinstance(definicao_tecnica, str):
            try:
                if '```' in definicao_tecnica:
                    import re
                    match = re.search(r'```(?:json)?\s*(.*?)\s*```', definicao_tecnica, re.DOTALL)
                    if match:
                        definicao_tecnica = match.group(1)
                definicao_tecnica = json.loads(definicao_tecnica)
            except json.JSONDecodeError as e:
                return {'sucesso': False, 'erro': f'JSON invalido: {e}'}

        # Monta parametros a partir das entidades
        parametros = {}
        for campo, valor in entidades.items():
            if valor:
                parametros[f'${campo}'] = valor

        return executor.executar(definicao_tecnica, parametros)

    def _formatar_resposta(self, consulta: str, resultado_execucao: Dict) -> str:
        """Formata resposta baseada nos dados retornados."""
        dados = resultado_execucao.get('dados', [])
        total = resultado_execucao.get('total', 0)

        if total == 0:
            return "Nao encontrei resultados para sua consulta."

        # Formata resumo
        linhas = [f"Encontrei {total} resultado(s):\n"]

        # Lista primeiros itens (max 10)
        for i, item in enumerate(dados[:10], 1):
            if isinstance(item, dict):
                # Tenta formatar de forma legivel
                partes = []
                for chave, valor in item.items():
                    if valor is not None:
                        partes.append(f"{chave}: {valor}")
                linhas.append(f"{i}. {' | '.join(partes[:4])}")  # Max 4 campos por linha
            else:
                linhas.append(f"{i}. {item}")

        if total > 10:
            linhas.append(f"\n... e mais {total - 10} resultado(s)")

        return "\n".join(linhas)

    def _salvar_loader_pendente(
        self,
        consulta: str,
        codigo_gerado: Dict,
        usuario: str,
        erro_execucao: str = None,
        resultado_execucao: Dict = None
    ) -> Optional[int]:
        """Salva loader como pendente de revisao."""
        try:
            from ..models import CodigoSistemaGerado
            from app import db
            from app.utils.timezone import agora_brasil

            # Serializa definicao_tecnica se for dict
            definicao = codigo_gerado.get('definicao_tecnica')
            if isinstance(definicao, dict):
                definicao = json.dumps(definicao, ensure_ascii=False)

            # Gera nome unico para evitar duplicatas
            nome_base = codigo_gerado.get('nome', f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            nome_final = nome_base

            # Verifica se ja existe loader com mesmo nome
            existente = CodigoSistemaGerado.query.filter_by(nome=nome_base).first()
            if existente:
                # Adiciona timestamp para tornar unico
                nome_final = f"{nome_base}_{datetime.now().strftime('%H%M%S')}"
                logger.info(f"[AUTO_LOADER] Nome '{nome_base}' ja existe, usando '{nome_final}'")

            codigo = CodigoSistemaGerado(
                nome=nome_final,
                tipo_codigo='loader',
                dominio=codigo_gerado.get('dominio', 'carteira'),
                gatilhos=codigo_gerado.get('gatilhos', [consulta[:50]]),
                definicao_tecnica=definicao,
                models_referenciados=codigo_gerado.get('models_referenciados'),
                campos_referenciados=codigo_gerado.get('campos_referenciados'),
                descricao_claude=codigo_gerado.get('descricao_claude', f"Auto-gerado para: {consulta}"),
                exemplos_uso=[consulta],
                ativo=False,  # NAO ativa automaticamente
                validado=False,
                criado_por=f"auto:{usuario}",
                # Campos para rastreabilidade
                variacoes=json.dumps({
                    'auto_gerado': True,
                    'erro_execucao': erro_execucao,
                    'resultado_sucesso': resultado_execucao.get('sucesso') if resultado_execucao else None,
                    'total_resultados': resultado_execucao.get('total') if resultado_execucao else None
                }, ensure_ascii=False)
            )

            db.session.add(codigo)
            db.session.commit()

            logger.info(f"[AUTO_LOADER] Loader #{codigo.id} salvo como PENDENTE_REVISAO")
            return codigo.id

        except Exception as e:
            logger.error(f"[AUTO_LOADER] Erro ao salvar loader: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return None


# Singleton
_auto_loader_service: Optional[AutoLoaderService] = None


def get_auto_loader_service() -> AutoLoaderService:
    """Retorna instancia singleton do AutoLoaderService."""
    global _auto_loader_service
    if _auto_loader_service is None:
        _auto_loader_service = AutoLoaderService()
    return _auto_loader_service


def tentar_responder_automaticamente(
    consulta: str,
    intencao: Dict[str, Any],
    usuario_id: int = None,
    usuario: str = "sistema",
    conhecimento_negocio: str = None
) -> Dict[str, Any]:
    """
    Funcao de conveniencia para tentar responder automaticamente.

    NOVO v3.5.2: Aceita conhecimento_negocio para evitar recarregar.
    """
    return get_auto_loader_service().tentar_responder(
        consulta, intencao, usuario_id, usuario, conhecimento_negocio
    )
