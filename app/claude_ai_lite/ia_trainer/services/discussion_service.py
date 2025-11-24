"""
DiscussionService - Modo Discussao Avancada com Autonomia Ampliada.

Este servico permite discussoes aprofundadas sobre codigos gerados,
com capacidade de:
1. Ver conversas anteriores e aprendizados
2. Acessar banco de dados para consultas
3. Ver e ajustar codigos gerados
4. Postura critica e sugestiva
5. Validar campos contra CLAUDE.md

Criado em: 24/11/2025
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app import db

logger = logging.getLogger(__name__)


class DiscussionService:
    """
    Servico para discussoes avancadas sobre codigos do IA Trainer.

    Possui autonomia ampliada para:
    - Consultar banco de dados
    - Ver codigos gerados e historico
    - Sugerir correcoes
    - Validar contra CLAUDE.md
    """

    def __init__(self):
        self._client = None
        self._claude_md_cache = None

    def _get_client(self):
        """Lazy loading do cliente Claude."""
        if self._client is None:
            from ...claude_client import get_claude_client
            self._client = get_claude_client()
        return self._client

    def iniciar_discussao(
        self,
        codigo_id: int = None,
        sessao_id: int = None,
        contexto_adicional: str = None
    ) -> Dict[str, Any]:
        """
        Inicia uma nova discussao sobre um codigo ou sessao.

        Args:
            codigo_id: ID do codigo a discutir (opcional)
            sessao_id: ID da sessao a discutir (opcional)
            contexto_adicional: Contexto extra fornecido pelo usuario

        Returns:
            Dict com contexto completo para discussao
        """
        contexto = {
            'codigo': None,
            'sessao': None,
            'historico_debate': [],
            'aprendizados_relacionados': [],
            'campos_claude_md': {},
            'analise_inicial': None
        }

        # Carrega codigo se especificado
        if codigo_id:
            contexto['codigo'] = self._carregar_codigo(codigo_id)

        # Carrega sessao se especificada
        if sessao_id:
            contexto['sessao'] = self._carregar_sessao(sessao_id)

        # Carrega aprendizados relacionados
        contexto['aprendizados_relacionados'] = self._carregar_aprendizados_relacionados(
            contexto.get('codigo'), contexto.get('sessao')
        )

        # Carrega campos do CLAUDE.md para validacao
        contexto['campos_claude_md'] = self._carregar_campos_referencia()

        # Faz analise inicial automatica
        if contexto['codigo'] or contexto['sessao']:
            contexto['analise_inicial'] = self._analisar_automatico(contexto)

        return {
            'sucesso': True,
            'contexto': contexto
        }

    def discutir(
        self,
        mensagem: str,
        codigo_id: int = None,
        sessao_id: int = None,
        modo: str = 'critico'
    ) -> Dict[str, Any]:
        """
        Processa uma mensagem de discussao com autonomia ampliada.

        Args:
            mensagem: Mensagem/pergunta do usuario
            codigo_id: ID do codigo sendo discutido
            sessao_id: ID da sessao sendo discutida
            modo: 'critico' (questiona tudo), 'colaborativo' (ajuda), 'tecnico' (foca em codigo)

        Returns:
            Dict com resposta, sugestoes e possiveis acoes
        """
        # Monta contexto completo
        contexto = self._montar_contexto_completo(codigo_id, sessao_id)

        # Monta prompt de sistema com autonomia
        prompt_sistema = self._montar_prompt_sistema_discussao(modo, contexto)

        # Monta mensagem com contexto
        prompt_usuario = self._montar_prompt_usuario(mensagem, contexto)

        # Chama Claude
        client = self._get_client()
        resposta_raw = client.completar(prompt_usuario, prompt_sistema, use_cache=False)

        # Parseia resposta estruturada
        resultado = self._parsear_resposta_discussao(resposta_raw)

        # Se Claude propôs codigo_corrigido E temos codigo_id, cria proposta automaticamente
        if resultado.get('sucesso') and resultado.get('codigo_corrigido') and codigo_id:
            proposta = self._criar_proposta_automatica(codigo_id, resultado['codigo_corrigido'], mensagem)
            if proposta.get('sucesso'):
                resultado['aguardando_aprovacao'] = True
                resultado['proposta_id'] = proposta['proposta_id']
                resultado['comparativo'] = proposta['comparativo']

        return resultado

    def _criar_proposta_automatica(
        self,
        codigo_id: int,
        codigo_corrigido: Any,
        mensagem_original: str
    ) -> Dict[str, Any]:
        """
        Cria proposta de correcao automaticamente quando Claude sugere codigo_corrigido.
        """
        # Prepara correcoes baseado no codigo_corrigido
        correcoes = {}

        # Se codigo_corrigido e um dict (JSON do loader), atualiza definicao_tecnica
        if isinstance(codigo_corrigido, dict):
            correcoes['definicao_tecnica'] = codigo_corrigido

            # Extrai campos_retorno para atualizar campos_referenciados
            if 'campos_retorno' in codigo_corrigido:
                correcoes['campos_referenciados'] = codigo_corrigido['campos_retorno']

        elif isinstance(codigo_corrigido, str):
            # Se e string, assume que e a definicao_tecnica inteira
            correcoes['definicao_tecnica'] = codigo_corrigido

        if not correcoes:
            return {'sucesso': False, 'erro': 'Codigo corrigido vazio ou invalido'}

        # Cria proposta usando metodo existente
        motivo = f"Correcao sugerida via discussao: {mensagem_original[:100]}"
        return self.propor_correcao(codigo_id, correcoes, motivo)

    def validar_codigo_contra_claude_md(self, codigo_id: int) -> Dict[str, Any]:
        """
        Valida um codigo gerado contra o CLAUDE.md.

        Verifica se todos os campos referenciados existem e estao corretos.
        """
        from .models import CodigoSistemaGerado

        codigo = CodigoSistemaGerado.query.get(codigo_id)
        if not codigo:
            return {'sucesso': False, 'erro': 'Codigo nao encontrado'}

        campos_referencia = self._carregar_campos_referencia()
        erros = []
        avisos = []

        # Pega campos referenciados no codigo
        campos_usados = codigo.campos_referenciados or []
        models_usados = codigo.models_referenciados or []

        # Valida cada campo
        for campo in campos_usados:
            encontrado = False
            for model, campos_model in campos_referencia.items():
                if campo in campos_model:
                    encontrado = True
                    break

            if not encontrado:
                erros.append({
                    'tipo': 'campo_inexistente',
                    'campo': campo,
                    'mensagem': f"Campo '{campo}' NAO existe no CLAUDE.md. Verifique o nome correto."
                })

                # Sugere campos similares
                sugestoes = self._sugerir_campos_similares(campo, campos_referencia)
                if sugestoes:
                    erros[-1]['sugestoes'] = sugestoes

        # Valida definicao tecnica se for loader
        if codigo.tipo_codigo == 'loader':
            erros_loader = self._validar_loader_campos(codigo.definicao_tecnica, campos_referencia)
            erros.extend(erros_loader)

        return {
            'sucesso': len(erros) == 0,
            'codigo_id': codigo_id,
            'nome': codigo.nome,
            'erros': erros,
            'avisos': avisos,
            'campos_validados': len(campos_usados),
            'total_erros': len(erros)
        }

    def propor_correcao(
        self,
        codigo_id: int,
        correcoes: Dict[str, Any],
        motivo: str
    ) -> Dict[str, Any]:
        """
        Propoe correcoes para um codigo (NAO aplica ainda - aguarda aprovacao).

        Retorna comparativo ANTES/DEPOIS para aprovacao do usuario.

        Args:
            codigo_id: ID do codigo
            correcoes: Dict com campos a corrigir
            motivo: Motivo da correcao

        Returns:
            Dict com comparativo antes/depois para aprovacao
        """
        from ..models import CodigoSistemaGerado

        codigo = CodigoSistemaGerado.query.get(codigo_id)
        if not codigo:
            return {'sucesso': False, 'erro': 'Codigo nao encontrado'}

        # Monta comparativo ANTES/DEPOIS
        comparativo = {
            'codigo_id': codigo_id,
            'nome': codigo.nome,
            'motivo': motivo,
            'campos': []
        }

        for campo, valor_novo in correcoes.items():
            valor_atual = getattr(codigo, campo, None)

            # Formata para exibicao
            if campo == 'definicao_tecnica':
                # Tenta formatar JSON se possivel
                try:
                    if isinstance(valor_atual, str):
                        valor_atual_fmt = json.dumps(json.loads(valor_atual), indent=2, ensure_ascii=False)
                    else:
                        valor_atual_fmt = json.dumps(valor_atual, indent=2, ensure_ascii=False) if valor_atual else 'null'
                except (json.JSONDecodeError, TypeError, ValueError):
                    valor_atual_fmt = str(valor_atual)

                try:
                    if isinstance(valor_novo, str):
                        valor_novo_fmt = json.dumps(json.loads(valor_novo), indent=2, ensure_ascii=False)
                    else:
                        valor_novo_fmt = json.dumps(valor_novo, indent=2, ensure_ascii=False) if valor_novo else 'null'
                except (json.JSONDecodeError, TypeError, ValueError):
                    valor_novo_fmt = str(valor_novo)
            else:
                valor_atual_fmt = json.dumps(valor_atual, ensure_ascii=False) if valor_atual else 'null'
                valor_novo_fmt = json.dumps(valor_novo, ensure_ascii=False) if valor_novo else 'null'

            comparativo['campos'].append({
                'campo': campo,
                'antes': valor_atual_fmt,
                'depois': valor_novo_fmt,
                'mudou': valor_atual_fmt != valor_novo_fmt
            })

        # Armazena proposta para aplicacao posterior
        proposta_id = f"proposta_{codigo_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        comparativo['proposta_id'] = proposta_id
        comparativo['correcoes_raw'] = correcoes
        comparativo['aguardando_aprovacao'] = True

        # Armazena em cache temporario (sessao)
        if not hasattr(self, '_propostas_pendentes'):
            self._propostas_pendentes = {}
        self._propostas_pendentes[proposta_id] = comparativo

        return {
            'sucesso': True,
            'aguardando_aprovacao': True,
            'proposta_id': proposta_id,
            'comparativo': comparativo,
            'mensagem': 'Proposta de correcao gerada. Aguardando sua aprovacao para aplicar.'
        }

    def aplicar_correcao_aprovada(
        self,
        proposta_id: str,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Aplica uma correcao que foi APROVADA pelo usuario.

        Args:
            proposta_id: ID da proposta aprovada
            usuario: Usuario aprovando

        Returns:
            Dict com resultado da aplicacao
        """
        from ..models import CodigoSistemaGerado
        from .codigo_loader import invalidar_cache

        # Busca proposta
        if not hasattr(self, '_propostas_pendentes'):
            return {'sucesso': False, 'erro': 'Nenhuma proposta pendente'}

        proposta = self._propostas_pendentes.get(proposta_id)
        if not proposta:
            return {'sucesso': False, 'erro': f'Proposta {proposta_id} nao encontrada ou ja aplicada'}

        codigo_id = proposta['codigo_id']
        correcoes = proposta['correcoes_raw']
        motivo = proposta['motivo']

        codigo = CodigoSistemaGerado.query.get(codigo_id)
        if not codigo:
            return {'sucesso': False, 'erro': 'Codigo nao encontrado'}

        # Cria versao antes de modificar
        codigo.criar_versao(motivo, usuario)

        # Aplica correcoes
        campos_atualizados = []

        if 'definicao_tecnica' in correcoes:
            nova_definicao = correcoes['definicao_tecnica']
            if isinstance(nova_definicao, dict):
                nova_definicao = json.dumps(nova_definicao, ensure_ascii=False)
            codigo.definicao_tecnica = nova_definicao
            campos_atualizados.append('definicao_tecnica')

        if 'campos_referenciados' in correcoes:
            codigo.campos_referenciados = correcoes['campos_referenciados']
            campos_atualizados.append('campos_referenciados')

        if 'gatilhos' in correcoes:
            codigo.gatilhos = correcoes['gatilhos']
            campos_atualizados.append('gatilhos')

        if 'descricao_claude' in correcoes:
            codigo.descricao_claude = correcoes['descricao_claude']
            campos_atualizados.append('descricao_claude')

        codigo.atualizado_por = usuario
        db.session.commit()

        # Invalida cache
        invalidar_cache()

        # Remove proposta aplicada
        del self._propostas_pendentes[proposta_id]

        return {
            'sucesso': True,
            'codigo_id': codigo_id,
            'campos_atualizados': campos_atualizados,
            'versao_atual': codigo.versao_atual,
            'mensagem': f"Correcao APROVADA e aplicada com sucesso! Codigo {codigo.nome} agora na versao {codigo.versao_atual}"
        }

    def rejeitar_correcao(self, proposta_id: str) -> Dict[str, Any]:
        """
        Rejeita uma proposta de correcao.

        Args:
            proposta_id: ID da proposta a rejeitar

        Returns:
            Dict com confirmacao
        """
        if not hasattr(self, '_propostas_pendentes'):
            return {'sucesso': False, 'erro': 'Nenhuma proposta pendente'}

        if proposta_id in self._propostas_pendentes:
            del self._propostas_pendentes[proposta_id]
            return {
                'sucesso': True,
                'mensagem': 'Proposta rejeitada. Nenhuma alteracao foi feita.'
            }

        return {'sucesso': False, 'erro': 'Proposta nao encontrada'}

    def listar_propostas_pendentes(self) -> Dict[str, Any]:
        """Lista todas as propostas de correcao pendentes."""
        if not hasattr(self, '_propostas_pendentes'):
            self._propostas_pendentes = {}

        return {
            'sucesso': True,
            'total': len(self._propostas_pendentes),
            'propostas': list(self._propostas_pendentes.values())
        }

    def listar_codigos_com_problemas(self) -> Dict[str, Any]:
        """
        Lista todos os codigos que podem ter problemas.

        Verifica campos inexistentes, sintaxe errada, etc.
        """
        from ..models import CodigoSistemaGerado

        codigos = CodigoSistemaGerado.query.all()
        problemas = []

        campos_referencia = self._carregar_campos_referencia()

        for codigo in codigos:
            validacao = self._validar_codigo_rapido(codigo, campos_referencia)
            if validacao['erros']:
                problemas.append({
                    'codigo_id': codigo.id,
                    'nome': codigo.nome,
                    'tipo': codigo.tipo_codigo,
                    'ativo': codigo.ativo,
                    'erros': validacao['erros']
                })

        return {
            'sucesso': True,
            'total_codigos': len(codigos),
            'total_com_problemas': len(problemas),
            'problemas': problemas
        }

    def consultar_banco(self, consulta_descricao: str) -> Dict[str, Any]:
        """
        Permite consultar dados do banco via descricao em linguagem natural.

        SEGURANCA: Apenas SELECT, com limite de resultados.
        """
        # Gera SQL seguro via Claude
        prompt = f"""Gere uma consulta SQL APENAS SELECT para: "{consulta_descricao}"

Tabelas disponiveis:
- codigo_sistema_gerado (id, nome, tipo_codigo, definicao_tecnica, ativo, gatilhos, campos_referenciados)
- sessao_ensino_ia (id, pergunta_original, decomposicao, status, historico_debate)
- claude_perguntas_nao_respondidas (id, consulta, intencao_detectada, dominio_detectado, status)

Retorne APENAS o SQL, sem explicacoes. Maximo 100 resultados (use LIMIT).
NAO use UPDATE, DELETE, INSERT, DROP ou qualquer comando de escrita."""

        client = self._get_client()
        sql = client.completar(prompt, "Voce gera SQL seguro. Apenas SELECT.", use_cache=False)

        # Remove markdown se houver
        sql = sql.strip()
        if sql.startswith('```'):
            linhas = sql.split('\n')
            sql = '\n'.join(linhas[1:-1])

        # Valida que e SELECT
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith('SELECT'):
            return {'sucesso': False, 'erro': 'Apenas consultas SELECT sao permitidas'}

        # Verifica comandos proibidos
        proibidos = ['UPDATE', 'DELETE', 'INSERT', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE']
        for cmd in proibidos:
            if cmd in sql_upper:
                return {'sucesso': False, 'erro': f'Comando {cmd} nao permitido'}

        # Executa
        try:
            from sqlalchemy import text
            resultado = db.session.execute(text(sql)).fetchall()

            # Converte para lista de dicts
            dados = []
            for row in resultado[:100]:
                if hasattr(row, '_asdict'):
                    dados.append(row._asdict())
                elif hasattr(row, '_mapping'):
                    dados.append(dict(row._mapping))
                else:
                    dados.append(dict(row))

            return {
                'sucesso': True,
                'sql_executado': sql,
                'total': len(dados),
                'dados': dados
            }

        except Exception as e:
            return {'sucesso': False, 'erro': str(e), 'sql_tentado': sql}

    # ==========================================
    # METODOS PRIVADOS
    # ==========================================

    def _carregar_codigo(self, codigo_id: int) -> Optional[Dict]:
        """Carrega codigo completo com historico."""
        from ..models import CodigoSistemaGerado, VersaoCodigoGerado

        codigo = CodigoSistemaGerado.query.get(codigo_id)
        if not codigo:
            return None

        dados = codigo.to_dict()

        # Adiciona versoes anteriores
        versoes = VersaoCodigoGerado.query.filter_by(
            codigo_id=codigo_id
        ).order_by(VersaoCodigoGerado.versao.desc()).limit(5).all()

        dados['versoes_anteriores'] = [
            {
                'versao': v.versao,
                'definicao_tecnica': v.definicao_tecnica[:200] + '...' if len(v.definicao_tecnica) > 200 else v.definicao_tecnica,
                'motivo': v.motivo_alteracao,
                'criado_em': v.criado_em.isoformat() if v.criado_em else None
            }
            for v in versoes
        ]

        return dados

    def _carregar_sessao(self, sessao_id: int) -> Optional[Dict]:
        """Carrega sessao completa com debate."""
        from ..models import SessaoEnsinoIA

        sessao = SessaoEnsinoIA.query.get(sessao_id)
        if not sessao:
            return None

        return sessao.to_dict()

    def _carregar_aprendizados_relacionados(
        self,
        codigo: Optional[Dict],
        sessao: Optional[Dict]
    ) -> List[Dict]:
        """Carrega aprendizados relacionados ao codigo/sessao."""
        from ..models import CodigoSistemaGerado

        relacionados = []

        # Se temos um codigo, busca outros do mesmo dominio
        if codigo and codigo.get('dominio'):
            similares = CodigoSistemaGerado.query.filter_by(
                dominio=codigo['dominio'],
                ativo=True
            ).filter(
                CodigoSistemaGerado.id != codigo.get('id')
            ).limit(5).all()

            for s in similares:
                relacionados.append({
                    'id': s.id,
                    'nome': s.nome,
                    'tipo': s.tipo_codigo,
                    'gatilhos': s.gatilhos,
                    'relacao': 'mesmo_dominio'
                })

        return relacionados

    def _carregar_campos_referencia(self) -> Dict[str, List[str]]:
        """
        Carrega campos do CLAUDE.md para validacao.

        Retorna dict: {model_name: [campo1, campo2, ...]}
        """
        if self._claude_md_cache:
            return self._claude_md_cache

        campos = {
            # CarteiraPrincipal - campos principais
            'CarteiraPrincipal': [
                'num_pedido', 'cod_produto', 'nome_produto', 'cnpj_cpf',
                'raz_social', 'raz_social_red', 'municipio', 'estado',
                'expedicao', 'agendamento', 'protocolo', 'agendamento_confirmado',
                'data_entrega', 'data_entrega_pedido', 'observ_ped_1',
                'qtd_produto_pedido', 'qtd_saldo_produto_pedido', 'qtd_cancelada_produto_pedido',
                'preco_produto_pedido', 'vendedor', 'equipe_vendas',
                'separacao_lote_id', 'pedido_cliente', 'saldo_estoque_pedido',
                'menor_estoque_produto_d7', 'tags_pedido',
                'cnpj_endereco_ent', 'empresa_endereco_ent', 'cep_endereco_ent',
                'nome_cidade', 'cod_uf', 'bairro_endereco_ent', 'rua_endereco_ent',
                'endereco_ent', 'telefone_endereco_ent'
            ],
            # Separacao
            'Separacao': [
                'separacao_lote_id', 'num_pedido', 'cod_produto', 'nome_produto',
                'qtd_saldo', 'valor_saldo', 'peso', 'pallet',
                'pedido_cliente', 'cnpj_cpf', 'raz_social_red',
                'nome_cidade', 'cod_uf', 'data_pedido', 'expedicao',
                'agendamento', 'protocolo', 'tipo_envio', 'observ_ped_1',
                'roteirizacao', 'rota', 'sub_rota',
                'status', 'nf_cd', 'sincronizado_nf', 'numero_nf'
            ],
            # Pedido (VIEW)
            'Pedido': [
                'separacao_lote_id', 'num_pedido', 'status', 'nf', 'nf_cd',
                'cnpj_cpf', 'raz_social_red', 'nome_cidade', 'cod_uf',
                'cidade_normalizada', 'uf_normalizada', 'codigo_ibge',
                'data_pedido', 'expedicao', 'agendamento', 'data_embarque', 'protocolo',
                'valor_saldo_total', 'pallet_total', 'peso_total',
                'transportadora', 'valor_frete', 'valor_por_kg',
                'modalidade', 'melhor_opcao', 'valor_melhor_opcao', 'lead_time'
            ],
            # CadastroPalletizacao
            'CadastroPalletizacao': [
                'cod_produto', 'nome_produto', 'palletizacao', 'peso_bruto',
                'altura_cm', 'largura_cm', 'comprimento_cm',
                'tipo_embalagem', 'tipo_materia_prima', 'categoria_produto',
                'subcategoria', 'linha_producao', 'ativo'
            ]
        }

        self._claude_md_cache = campos
        return campos

    def _sugerir_campos_similares(self, campo_errado: str, campos_referencia: Dict) -> List[str]:
        """Sugere campos similares ao campo errado."""
        import difflib

        todos_campos = []
        for campos in campos_referencia.values():
            todos_campos.extend(campos)

        # Busca campos similares
        similares = difflib.get_close_matches(campo_errado, todos_campos, n=3, cutoff=0.4)
        return similares

    def _validar_loader_campos(self, definicao_tecnica: str, campos_referencia: Dict) -> List[Dict]:
        """Valida campos dentro da definicao de um loader."""
        erros = []

        try:
            if isinstance(definicao_tecnica, str):
                definicao = json.loads(definicao_tecnica)
            else:
                definicao = definicao_tecnica

            # Verifica campos_retorno
            for campo in definicao.get('campos_retorno', []):
                campo_limpo = campo.split('.')[-1] if '.' in campo else campo
                encontrado = False
                for campos in campos_referencia.values():
                    if campo_limpo in campos:
                        encontrado = True
                        break
                if not encontrado:
                    erros.append({
                        'tipo': 'campo_retorno_inexistente',
                        'campo': campo,
                        'mensagem': f"Campo '{campo}' em campos_retorno NAO existe",
                        'sugestoes': self._sugerir_campos_similares(campo_limpo, campos_referencia)
                    })

            # Verifica filtros
            for filtro in definicao.get('filtros', []):
                campo = filtro.get('campo', '')
                campo_limpo = campo.split('.')[-1] if '.' in campo else campo
                encontrado = False
                for campos in campos_referencia.values():
                    if campo_limpo in campos:
                        encontrado = True
                        break
                if not encontrado:
                    erros.append({
                        'tipo': 'campo_filtro_inexistente',
                        'campo': campo,
                        'mensagem': f"Campo '{campo}' em filtros NAO existe",
                        'sugestoes': self._sugerir_campos_similares(campo_limpo, campos_referencia)
                    })

        except json.JSONDecodeError:
            erros.append({
                'tipo': 'json_invalido',
                'mensagem': 'definicao_tecnica nao e um JSON valido'
            })

        return erros

    def _validar_codigo_rapido(self, codigo, campos_referencia: Dict) -> Dict:
        """Validacao rapida de um codigo."""
        erros = []

        # Valida campos referenciados
        for campo in (codigo.campos_referenciados or []):
            # Remove prefixo do modelo se existir (ex: "CarteiraPrincipal.num_pedido" -> "num_pedido")
            campo_limpo = campo.split('.')[-1] if '.' in campo else campo
            encontrado = False
            for campos in campos_referencia.values():
                if campo_limpo in campos:
                    encontrado = True
                    break
            if not encontrado:
                erros.append(f"Campo '{campo_limpo}' inexistente")

        # Valida loader se aplicavel
        if codigo.tipo_codigo == 'loader':
            erros_loader = self._validar_loader_campos(codigo.definicao_tecnica, campos_referencia)
            for e in erros_loader:
                erros.append(e.get('mensagem', str(e)))

        return {'erros': erros}

    def _montar_contexto_completo(self, codigo_id: int = None, sessao_id: int = None) -> Dict:
        """Monta contexto completo para discussao."""
        contexto = {
            'codigo': None,
            'sessao': None,
            'campos_referencia': self._carregar_campos_referencia()
        }

        if codigo_id:
            contexto['codigo'] = self._carregar_codigo(codigo_id)
        if sessao_id:
            contexto['sessao'] = self._carregar_sessao(sessao_id)

        return contexto

    def _montar_prompt_sistema_discussao(self, modo: str, contexto: Dict) -> str:
        """Monta prompt de sistema para discussao."""

        modo_instrucoes = {
            'critico': """MODO CRITICO:
- Questione tudo que parecer suspeito
- Aponte erros claramente
- Seja direto e tecnico""",

            'colaborativo': """MODO COLABORATIVO:
- Ajude a entender o problema
- Explique conceitos
- Sugira melhorias construtivamente""",

            'tecnico': """MODO TECNICO:
- Foque em codigo e implementacao
- Mostre exemplos concretos
- Explique decisoes tecnicas"""
        }

        campos_str = json.dumps(contexto.get('campos_referencia', {}), indent=2, ensure_ascii=False)

        return f"""Voce e um assistente conversacional para discutir codigos do IA Trainer.

{modo_instrucoes.get(modo, modo_instrucoes['critico'])}

=== CAMPOS VALIDOS (CLAUDE.md) ===
{campos_str}

=== FORMATO DE RESPOSTA OBRIGATORIO ===
Retorne SEMPRE um JSON valido com esta estrutura:
{{
    "resposta": "Sua resposta CONVERSACIONAL aqui. Responda diretamente o que o usuario perguntou. Seja natural como num chat. Pode ser longa e detalhada.",
    "erros_encontrados": ["lista de erros se houver, ou array vazio"],
    "sugestoes": ["lista de sugestoes se houver, ou array vazio"],
    "codigo_corrigido": null,
    "proximos_passos": ["o que fazer a seguir, ou array vazio"]
}}

IMPORTANTE:
1. O campo "resposta" deve conter sua CONVERSA com o usuario - responda a pergunta dele!
2. Se ele perguntar algo, responda no campo "resposta"
3. Se encontrar erros no codigo, liste em "erros_encontrados" E mencione na "resposta"
4. Campos inexistentes sao ERROS - aponte claramente
5. Use "codigo_corrigido" apenas quando propor uma correcao completa

Retorne APENAS o JSON, sem texto antes ou depois."""

    def _montar_prompt_usuario(self, mensagem: str, contexto: Dict) -> str:
        """Monta prompt do usuario com contexto."""
        partes = [f"MENSAGEM DO USUARIO:\n{mensagem}"]

        if contexto.get('codigo'):
            codigo = contexto['codigo']
            partes.append(f"""
=== CODIGO SENDO DISCUTIDO ===
ID: {codigo.get('id')}
Nome: {codigo.get('nome')}
Tipo: {codigo.get('tipo_codigo')}
Ativo: {codigo.get('ativo')}
Gatilhos: {codigo.get('gatilhos')}
Campos Referenciados: {codigo.get('campos_referenciados')}

Definicao Tecnica:
{codigo.get('definicao_tecnica')}
=== FIM DO CODIGO ===""")

        if contexto.get('sessao'):
            sessao = contexto['sessao']
            partes.append(f"""
=== SESSAO RELACIONADA ===
ID: {sessao.get('id')}
Pergunta Original: {sessao.get('pergunta_original')}
Status: {sessao.get('status')}
=== FIM DA SESSAO ===""")

        return "\n\n".join(partes)

    def _analisar_automatico(self, contexto: Dict) -> Dict:
        """Faz analise automatica do contexto."""
        erros = []
        avisos = []

        if contexto.get('codigo'):
            codigo = contexto['codigo']

            # Valida campos
            for campo in (codigo.get('campos_referenciados') or []):
                encontrado = False
                for campos in contexto['campos_claude_md'].values():
                    if campo in campos:
                        encontrado = True
                        break
                if not encontrado:
                    erros.append(f"Campo '{campo}' nao existe no CLAUDE.md")

        return {
            'erros': erros,
            'avisos': avisos,
            'total_erros': len(erros)
        }

    def _parsear_resposta_discussao(self, resposta: str) -> Dict[str, Any]:
        """Parseia resposta do Claude."""
        try:
            # Tenta parsear como JSON
            resposta_limpa = resposta.strip()
            if resposta_limpa.startswith('```'):
                linhas = resposta_limpa.split('\n')
                resposta_limpa = '\n'.join(linhas[1:-1])

            resultado = json.loads(resposta_limpa)
            resultado['sucesso'] = True
            resultado['formato'] = 'json'
            return resultado

        except json.JSONDecodeError:
            # Retorna como texto
            return {
                'sucesso': True,
                'formato': 'texto',
                'resposta': resposta,
                'analise': resposta
            }
