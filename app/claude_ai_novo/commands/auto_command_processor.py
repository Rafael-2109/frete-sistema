"""
🤖 AUTO COMMAND PROCESSOR - Processamento Automático de Comandos
==============================================================

Módulo responsável por processamento automático e inteligente de comandos.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from app.claude_ai_novo.commands.base_command import BaseCommand

logger = logging.getLogger(__name__)

class AutoCommandProcessor(BaseCommand):
    """
    Processador automático de comandos que detecta e executa comandos naturais.
    
    Responsabilidades:
    - Detecção automática de comandos em texto natural
    - Processamento inteligente de comandos
    - Execução de comandos compostos
    - Validação de segurança
    - Histórico de comandos
    """
    
    def __init__(self):
        """Inicializa o processador automático de comandos."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info("🤖 AutoCommandProcessor inicializado")
        
        # Registro de comandos disponíveis
        self.command_registry = {}
        self.command_patterns = {}
        self.command_history = []
        
        # Configurações de segurança
        self.security_config = {
            'max_commands_per_request': 5,
            'allowed_command_types': ['query', 'report', 'analyze', 'export'],
            'forbidden_patterns': ['delete', 'drop', 'truncate', 'remove_all'],
            'require_confirmation': ['bulk_update', 'mass_delete', 'system_config']
        }
        
        # Inicializar comandos padrão
        self._initialize_default_commands()
    
    def process_natural_command(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa comando em linguagem natural.
        
        Args:
            text: Texto contendo comando natural
            context: Contexto da execução
            
        Returns:
            Resultado do processamento
        """
        try:
            result = {
                'timestamp': datetime.now().isoformat(),
                'input_text': text,
                'processing_type': 'natural_command',
                'status': 'success',
                'detected_commands': [],
                'executed_commands': [],
                'results': [],
                'security_checks': []
            }
            
            # Detectar comandos no texto
            detected_commands = self._detect_commands(text)
            result['detected_commands'] = detected_commands
            
            if not detected_commands:
                result['status'] = 'no_commands_found'
                result['message'] = 'Nenhum comando detectado no texto'
                return result
            
            # Validar segurança
            security_result = self._validate_security(detected_commands)
            result['security_checks'] = security_result
            
            if not security_result['passed']:
                result['status'] = 'security_failed'
                result['message'] = security_result['message']
                return result
            
            # Executar comandos
            for command in detected_commands:
                execution_result = self._execute_command(command, context)
                result['executed_commands'].append({
                    'command': command,
                    'result': execution_result
                })
                result['results'].append(execution_result)
            
            # Registrar no histórico
            self._record_command_execution(text, detected_commands, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento de comando natural: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'input_text': text,
                'processing_type': 'natural_command',
                'status': 'error',
                'error': str(e)
            }
    
    def register_command(self, command_name: str, handler: Callable, patterns: List[str], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra um novo comando.
        
        Args:
            command_name: Nome do comando
            handler: Função que executa o comando
            patterns: Padrões de detecção
            metadata: Metadados do comando
            
        Returns:
            True se registrado com sucesso
        """
        try:
            self.command_registry[command_name] = {
                'handler': handler,
                'patterns': patterns,
                'metadata': metadata or {},
                'registered_at': datetime.now().isoformat()
            }
            
            # Registrar padrões
            for pattern in patterns:
                if pattern not in self.command_patterns:
                    self.command_patterns[pattern] = []
                self.command_patterns[pattern].append(command_name)
            
            self.logger.info(f"✅ Comando '{command_name}' registrado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar comando '{command_name}': {e}")
            return False
    
    def get_command_suggestions(self, partial_text: str) -> List[Dict[str, Any]]:
        """
        Gera sugestões de comandos baseadas no texto parcial.
        
        Args:
            partial_text: Texto parcial
            
        Returns:
            Lista de sugestões
        """
        try:
            suggestions = []
            text_lower = partial_text.lower()
            
            # Buscar comandos que correspondem ao texto parcial
            for command_name, command_info in self.command_registry.items():
                patterns = command_info['patterns']
                metadata = command_info['metadata']
                
                # Verificar se algum padrão corresponde
                for pattern in patterns:
                    if any(word in text_lower for word in pattern.lower().split()):
                        suggestions.append({
                            'command': command_name,
                            'pattern': pattern,
                            'description': metadata.get('description', ''),
                            'example': metadata.get('example', ''),
                            'confidence': self._calculate_suggestion_confidence(text_lower, pattern)
                        })
                        break
            
            # Ordenar por confiança
            suggestions.sort(key=lambda x: x['confidence'], reverse=True)
            
            return suggestions[:5]  # Limitar a 5 sugestões
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar sugestões: {e}")
            return []
    
    def get_command_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém histórico de comandos executados.
        
        Args:
            limit: Limite de comandos a retornar
            
        Returns:
            Histórico de comandos
        """
        return self.command_history[-limit:]
    
    def validate_command_syntax(self, command_text: str) -> Dict[str, Any]:
        """
        Valida sintaxe de um comando.
        
        Args:
            command_text: Texto do comando
            
        Returns:
            Resultado da validação
        """
        try:
            validation = {
                'timestamp': datetime.now().isoformat(),
                'command_text': command_text,
                'is_valid': False,
                'detected_commands': [],
                'syntax_errors': [],
                'suggestions': []
            }
            
            # Detectar comandos
            detected_commands = self._detect_commands(command_text)
            validation['detected_commands'] = detected_commands
            
            if not detected_commands:
                validation['syntax_errors'].append("Nenhum comando válido detectado")
                validation['suggestions'] = self.get_command_suggestions(command_text)
                return validation
            
            # Validar cada comando detectado
            for command in detected_commands:
                command_errors = self._validate_command_syntax(command)
                validation['syntax_errors'].extend(command_errors)
            
            validation['is_valid'] = len(validation['syntax_errors']) == 0
            
            return validation
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de sintaxe: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'command_text': command_text,
                'is_valid': False,
                'error': str(e)
            }
    
    def _initialize_default_commands(self):
        """Inicializa comandos padrão."""
        # Comando de consulta
        self.register_command(
            'query_data',
            self._handle_query_command,
            ['consultar', 'mostrar', 'listar', 'ver', 'buscar'],
            {
                'description': 'Consulta dados no sistema',
                'example': 'consultar pedidos do cliente X',
                'type': 'query'
            }
        )
        
        # Comando de relatório
        self.register_command(
            'generate_report',
            self._handle_report_command,
            ['relatório', 'gerar', 'exportar', 'planilha'],
            {
                'description': 'Gera relatórios e exportações',
                'example': 'gerar relatório de vendas',
                'type': 'report'
            }
        )
        
        # Comando de análise
        self.register_command(
            'analyze_data',
            self._handle_analyze_command,
            ['analisar', 'análise', 'examinar', 'avaliar'],
            {
                'description': 'Realiza análises de dados',
                'example': 'analisar tendências de vendas',
                'type': 'analyze'
            }
        )
        
        # Comando de status
        self.register_command(
            'check_status',
            self._handle_status_command,
            ['status', 'situação', 'estado', 'verificar'],
            {
                'description': 'Verifica status do sistema',
                'example': 'verificar status do sistema',
                'type': 'status'
            }
        )
    
    def _detect_commands(self, text: str) -> List[Dict[str, Any]]:
        """Detecta comandos no texto."""
        detected_commands = []
        text_lower = text.lower()
        
        # Buscar padrões de comandos
        for pattern, command_names in self.command_patterns.items():
            if pattern.lower() in text_lower:
                for command_name in command_names:
                    command_info = self.command_registry[command_name]
                    
                    # Extrair parâmetros do comando
                    parameters = self._extract_parameters(text, pattern)
                    
                    detected_commands.append({
                        'command': command_name,
                        'pattern': pattern,
                        'parameters': parameters,
                        'confidence': self._calculate_detection_confidence(text_lower, pattern),
                        'metadata': command_info['metadata']
                    })
        
        # Remover duplicatas e ordenar por confiança
        unique_commands = {}
        for cmd in detected_commands:
            key = cmd['command']
            if key not in unique_commands or cmd['confidence'] > unique_commands[key]['confidence']:
                unique_commands[key] = cmd
        
        return sorted(unique_commands.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _extract_parameters(self, text: str, pattern: str) -> Dict[str, Any]:
        """Extrai parâmetros do comando."""
        parameters = {}
        
        # Extrair entidades comuns
        # Datas
        date_matches = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        if date_matches:
            parameters['dates'] = date_matches
        
        # Números
        number_matches = re.findall(r'\b\d+\b', text)
        if number_matches:
            parameters['numbers'] = number_matches
        
        # Valores monetários
        money_matches = re.findall(r'R\$\s*\d+[,.]?\d*', text)
        if money_matches:
            parameters['values'] = money_matches
        
        # Nomes (palavras capitalizadas)
        name_matches = re.findall(r'\b[A-Z][a-z]+\b', text)
        if name_matches:
            parameters['names'] = name_matches
        
        return parameters
    
    def _validate_security(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida segurança dos comandos."""
        security_result = {
            'passed': True,
            'message': '',
            'checks': []
        }
        
        # Verificar número de comandos
        if len(commands) > self.security_config['max_commands_per_request']:
            security_result['passed'] = False
            security_result['message'] = f"Muitos comandos ({len(commands)} > {self.security_config['max_commands_per_request']})"
            return security_result
        
        # Verificar tipos de comandos
        for command in commands:
            cmd_type = command.get('metadata', {}).get('type', 'unknown')
            if cmd_type not in self.security_config['allowed_command_types']:
                security_result['passed'] = False
                security_result['message'] = f"Tipo de comando não permitido: {cmd_type}"
                return security_result
        
        # Verificar padrões proibidos
        for command in commands:
            pattern = command.get('pattern', '').lower()
            for forbidden in self.security_config['forbidden_patterns']:
                if forbidden in pattern:
                    security_result['passed'] = False
                    security_result['message'] = f"Padrão proibido detectado: {forbidden}"
                    return security_result
        
        return security_result
    
    def _execute_command(self, command: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executa um comando."""
        try:
            command_name = command['command']
            command_info = self.command_registry[command_name]
            handler = command_info['handler']
            
            # Preparar contexto de execução
            execution_context = {
                'command': command,
                'parameters': command.get('parameters', {}),
                'context': context or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Executar comando
            result = handler(execution_context)
            
            return {
                'status': 'success',
                'result': result,
                'execution_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao executar comando '{command_name}': {e}")
            return {
                'status': 'error',
                'error': str(e),
                'execution_time': datetime.now().isoformat()
            }
    
    def _handle_query_command(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Manipula comando de consulta."""
        return {
            'type': 'query',
            'message': 'Comando de consulta executado',
            'parameters': context.get('parameters', {}),
            'data': []
        }
    
    def _handle_report_command(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Manipula comando de relatório."""
        return {
            'type': 'report',
            'message': 'Comando de relatório executado',
            'parameters': context.get('parameters', {}),
            'report_id': f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    def _handle_analyze_command(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Manipula comando de análise."""
        return {
            'type': 'analyze',
            'message': 'Comando de análise executado',
            'parameters': context.get('parameters', {}),
            'analysis_results': {}
        }
    
    def _handle_status_command(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Manipula comando de status."""
        return {
            'type': 'status',
            'message': 'Sistema operacional',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_detection_confidence(self, text: str, pattern: str) -> float:
        """Calcula confiança da detecção."""
        # Confiança baseada na correspondência exata
        if pattern.lower() in text:
            return 1.0
        
        # Confiança baseada em palavras parciais
        pattern_words = pattern.lower().split()
        text_words = text.split()
        
        matches = sum(1 for word in pattern_words if word in text_words)
        return matches / len(pattern_words) if pattern_words else 0.0
    
    def _calculate_suggestion_confidence(self, text: str, pattern: str) -> float:
        """Calcula confiança da sugestão."""
        return self._calculate_detection_confidence(text, pattern)
    
    def _validate_command_syntax(self, command: Dict[str, Any]) -> List[str]:
        """Valida sintaxe de um comando específico."""
        errors = []
        
        # Verificar se o comando tem os campos obrigatórios
        if 'command' not in command:
            errors.append("Campo 'command' obrigatório")
        
        if 'pattern' not in command:
            errors.append("Campo 'pattern' obrigatório")
        
        # Verificar se o comando está registrado
        if command.get('command') not in self.command_registry:
            errors.append(f"Comando '{command.get('command')}' não registrado")
        
        return errors
    
    def _record_command_execution(self, original_text: str, commands: List[Dict[str, Any]], result: Dict[str, Any]):
        """Registra execução de comando no histórico."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'original_text': original_text,
            'commands': commands,
            'result': result,
            'status': result.get('status', 'unknown')
        }
        
        self.command_history.append(record)
        
        # Limitar tamanho do histórico
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]


def get_auto_command_processor() -> AutoCommandProcessor:
    """
    Obtém instância do processador automático de comandos.
    
    Returns:
        Instância do AutoCommandProcessor
    """
    return AutoCommandProcessor() 