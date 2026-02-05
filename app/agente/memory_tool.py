"""
Database Memory Tool para Claude Agent SDK.

Implementação da Memory Tool da Anthropic usando banco de dados SQLAlchemy
em vez de filesystem local.

Referência: https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool

Uso:
    from app.agente.memory_tool import DatabaseMemoryTool

    # Criar instância para um usuário específico
    memory = DatabaseMemoryTool(user_id=123, app=flask_app)

    # Usar com o SDK da Anthropic
    runner = client.beta.messages.tool_runner(
        model="claude-sonnet-4-5-20250929",
        tools=[memory],
        ...
    )
"""

from typing import List, Optional
from typing_extensions import override

from anthropic.lib.tools import BetaAbstractMemoryTool
from anthropic.types.beta import (
    BetaMemoryTool20250818ViewCommand,
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818RenameCommand,
    BetaMemoryTool20250818StrReplaceCommand,
)


# System prompt recomendado para uso com Memory Tool
MEMORY_SYSTEM_PROMPT = """Você tem acesso a uma ferramenta de memória persistente.

DIRETRIZES DE USO:
- NÃO armazene o histórico da conversa (isso já é feito automaticamente)
- NÃO mencione a ferramenta de memória ao usuário, a menos que perguntem
- ARMAZENE fatos sobre o usuário e suas preferências
- ANTES de responder, verifique a memória para ajustar profundidade técnica e estilo
- MANTENHA as memórias atualizadas - remova informações desatualizadas, adicione novos detalhes

FORMATO RECOMENDADO:
Use XML estruturado para organizar as memórias:

<user>
    <name>Nome do Usuário</name>
    <role>Cargo/Função</role>
    <preferences>
        <communication>direto e objetivo</communication>
        <detail_level>alto</detail_level>
    </preferences>
</user>

<context>
    <company>Informações da empresa</company>
    <domain>Área de atuação</domain>
</context>

<learned>
    <terms>Termos específicos aprendidos</terms>
    <patterns>Padrões identificados</patterns>
</learned>
"""


class DatabaseMemoryTool(BetaAbstractMemoryTool):
    """
    Implementação da Memory Tool usando banco de dados PostgreSQL.

    Cada usuário tem sua própria árvore de memórias isolada.
    As memórias persistem entre sessões de chat.

    Estrutura de paths:
        /memories/              # Raiz (sempre existe)
        /memories/user.xml      # Informações do usuário
        /memories/context/      # Diretório de contexto
        /memories/learned/      # Coisas aprendidas
    """

    def __init__(self, user_id: int, app=None):
        """
        Inicializa a Memory Tool para um usuário específico.

        Args:
            user_id: ID do usuário no banco de dados
            app: Flask app (opcional, usa current_app se não fornecido)
        """
        super().__init__()
        self.user_id = user_id
        self._app = app

    def _get_app_context(self):
        """Obtém o contexto do Flask app."""
        if self._app:
            return self._app.app_context()
        else:
            from flask import current_app
            return current_app.app_context()

    def _validate_path(self, path: str) -> str:
        """
        Valida e normaliza o path.

        Args:
            path: Path a validar

        Returns:
            Path normalizado

        Raises:
            ValueError: Se o path for inválido
        """
        if not path:
            raise ValueError("Path não pode ser vazio")

        if not path.startswith('/memories'):
            raise ValueError(f"Path deve começar com /memories, recebido: {path}")

        # Previne path traversal
        if '..' in path:
            raise ValueError(f"Path não pode conter '..': {path}")

        # Normaliza múltiplas barras
        while '//' in path:
            path = path.replace('//', '/')

        # Remove barra final (exceto para /memories)
        if path != '/memories' and path.endswith('/'):
            path = path.rstrip('/')

        return path

    @override
    def view(self, command: BetaMemoryTool20250818ViewCommand) -> str:
        """
        Visualiza conteúdo de arquivo ou lista diretório.

        Args:
            command: Comando view com path e view_range opcional

        Returns:
            Conteúdo do arquivo ou listagem do diretório
        """
        from .models import AgentMemory
        from app import db

        path = self._validate_path(command.path)

        with self._get_app_context():
            memory = AgentMemory.get_by_path(self.user_id, path)

            # Caso especial: /memories é sempre um diretório virtual
            if path == '/memories':
                items = AgentMemory.list_directory(self.user_id, path)
                if not items:
                    return f"Directory: {path}\n(empty)"

                lines = [f"Directory: {path}"]
                for item in sorted(items, key=lambda x: x.path):
                    name = item.path.split('/')[-1]
                    suffix = '/' if item.is_directory else ''
                    lines.append(f"- {name}{suffix}")
                return "\n".join(lines)

            if not memory:
                raise RuntimeError(f"Path não encontrado: {path}")

            # Se for diretório, lista conteúdo
            if memory.is_directory:
                items = AgentMemory.list_directory(self.user_id, path)
                if not items:
                    return f"Directory: {path}\n(empty)"

                lines = [f"Directory: {path}"]
                for item in sorted(items, key=lambda x: x.path):
                    name = item.path.split('/')[-1]
                    suffix = '/' if item.is_directory else ''
                    lines.append(f"- {name}{suffix}")
                return "\n".join(lines)

            # É um arquivo, retorna conteúdo
            content = memory.content or ""
            lines = content.splitlines()

            # Aplica view_range se especificado
            view_range = command.view_range
            if view_range:
                start_line = max(1, view_range[0]) - 1
                end_line = len(lines) if view_range[1] == -1 else view_range[1]
                lines = lines[start_line:end_line]
                start_num = start_line + 1
            else:
                start_num = 1

            # Formata com números de linha
            numbered_lines = [f"{i + start_num:4d}: {line}" for i, line in enumerate(lines)]
            return "\n".join(numbered_lines)

    @override
    def create(self, command: BetaMemoryTool20250818CreateCommand) -> str:
        """
        Cria novo arquivo de memória.

        Args:
            command: Comando create com path e file_text

        Returns:
            Mensagem de sucesso
        """
        from .models import AgentMemory, AgentMemoryVersion
        from app import db

        path = self._validate_path(command.path)

        with self._get_app_context():
            # Verifica se já existe
            existing = AgentMemory.get_by_path(self.user_id, path)
            if existing:
                # Salvar versão anterior antes de atualizar
                if existing.content is not None:
                    AgentMemoryVersion.save_version(
                        memory_id=existing.id,
                        content=existing.content,
                        changed_by='claude'
                    )

                # Atualiza conteúdo se já existe
                existing.content = command.file_text
                existing.is_directory = False
            else:
                # Cria novo
                AgentMemory.create_file(self.user_id, path, command.file_text)

            db.session.commit()
            return f"Arquivo criado com sucesso em {path}"

    @override
    def str_replace(self, command: BetaMemoryTool20250818StrReplaceCommand) -> str:
        """
        Substitui texto em arquivo existente.

        Args:
            command: Comando str_replace com path, old_str e new_str

        Returns:
            Mensagem de sucesso

        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se texto não encontrado ou não é único
        """
        from .models import AgentMemory, AgentMemoryVersion
        from app import db

        path = self._validate_path(command.path)

        with self._get_app_context():
            memory = AgentMemory.get_by_path(self.user_id, path)

            if not memory:
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")

            if memory.is_directory:
                raise ValueError(f"Não é possível editar um diretório: {path}")

            content = memory.content or ""
            count = content.count(command.old_str)

            if count == 0:
                raise ValueError(f"Texto não encontrado em {path}")
            elif count > 1:
                raise ValueError(f"Texto aparece {count} vezes em {path}. Deve ser único.")

            # Salvar versão anterior antes de editar
            if content:
                AgentMemoryVersion.save_version(
                    memory_id=memory.id,
                    content=content,
                    changed_by='claude'
                )

            memory.content = content.replace(command.old_str, command.new_str)
            db.session.commit()

            return f"Arquivo {path} editado com sucesso"

    @override
    def insert(self, command: BetaMemoryTool20250818InsertCommand) -> str:
        """
        Insere texto em linha específica.

        Args:
            command: Comando insert com path, insert_line e insert_text

        Returns:
            Mensagem de sucesso
        """
        from .models import AgentMemory, AgentMemoryVersion
        from app import db

        path = self._validate_path(command.path)

        with self._get_app_context():
            memory = AgentMemory.get_by_path(self.user_id, path)

            if not memory:
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")

            if memory.is_directory:
                raise ValueError(f"Não é possível editar um diretório: {path}")

            content = memory.content or ""
            lines = content.splitlines()

            insert_line = command.insert_line
            if insert_line < 0 or insert_line > len(lines):
                raise ValueError(f"Linha inválida {insert_line}. Deve ser 0-{len(lines)}")

            # Salvar versão anterior antes de inserir
            if content:
                AgentMemoryVersion.save_version(
                    memory_id=memory.id,
                    content=content,
                    changed_by='claude'
                )

            lines.insert(insert_line, command.insert_text.rstrip('\n'))
            memory.content = '\n'.join(lines) + '\n'

            db.session.commit()
            return f"Texto inserido na linha {insert_line} em {path}"

    @override
    def delete(self, command: BetaMemoryTool20250818DeleteCommand) -> str:
        """
        Deleta arquivo ou diretório.

        Args:
            command: Comando delete com path

        Returns:
            Mensagem de sucesso
        """
        from .models import AgentMemory
        from app import db

        path = self._validate_path(command.path)

        if path == '/memories':
            raise ValueError("Não é possível deletar o diretório raiz /memories")

        with self._get_app_context():
            memory = AgentMemory.get_by_path(self.user_id, path)

            if not memory:
                raise FileNotFoundError(f"Path não encontrado: {path}")

            tipo = "Diretório" if memory.is_directory else "Arquivo"
            count = AgentMemory.delete_by_path(self.user_id, path)

            db.session.commit()
            return f"{tipo} deletado: {path}" + (f" ({count} itens)" if count > 1 else "")

    @override
    def rename(self, command: BetaMemoryTool20250818RenameCommand) -> str:
        """
        Renomeia arquivo ou diretório.

        Args:
            command: Comando rename com old_path e new_path

        Returns:
            Mensagem de sucesso
        """
        from .models import AgentMemory
        from app import db

        old_path = self._validate_path(command.old_path)
        new_path = self._validate_path(command.new_path)

        with self._get_app_context():
            # Verifica se origem existe
            source = AgentMemory.get_by_path(self.user_id, old_path)
            if not source:
                raise FileNotFoundError(f"Path de origem não encontrado: {old_path}")

            # Verifica se destino já existe
            dest = AgentMemory.get_by_path(self.user_id, new_path)
            if dest:
                raise ValueError(f"Destino já existe: {new_path}")

            success = AgentMemory.rename(self.user_id, old_path, new_path)
            if not success:
                raise RuntimeError(f"Falha ao renomear {old_path}")

            db.session.commit()
            return f"Renomeado {old_path} para {new_path}"

    @override
    def clear_all_memory(self) -> str:
        """
        Limpa todas as memórias do usuário.

        Returns:
            Mensagem de sucesso
        """
        from .models import AgentMemory
        from app import db

        with self._get_app_context():
            count = AgentMemory.clear_all_for_user(self.user_id)
            db.session.commit()
            return f"Todas as memórias limpas ({count} itens removidos)"


def get_memory_tool_for_user(user_id: int, app=None) -> DatabaseMemoryTool:
    """
    Factory function para criar Memory Tool para um usuário.

    Args:
        user_id: ID do usuário
        app: Flask app (opcional)

    Returns:
        DatabaseMemoryTool configurada
    """
    return DatabaseMemoryTool(user_id=user_id, app=app)
