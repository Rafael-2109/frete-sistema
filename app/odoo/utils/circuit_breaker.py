"""
Circuit Breaker para Odoo
==========================

Implementação conservadora de Circuit Breaker para proteger o sistema
quando o Odoo está offline, evitando timeouts longos e travamentos.

CONFIGURAÇÃO ULTRA CONSERVADORA:
- 5 falhas consecutivas para abrir (não 3)
- 8 segundos de timeout por chamada (generoso)
- Testa a cada 30s se Odoo voltou
- 1 sucesso fecha o circuit imediatamente

Autor: Sistema de Fretes
Data: 2025-11-05
"""

import time
import logging
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados do Circuit Breaker"""
    CLOSED = "CLOSED"      # Normal - chamadas passam
    OPEN = "OPEN"          # Bloqueado - não tenta Odoo
    HALF_OPEN = "HALF_OPEN"  # Testando - permite 1 tentativa


class OdooCircuitBreaker:
    """
    Circuit Breaker conservador para conexões Odoo

    Configuração conservadora para evitar falsos positivos:
    - 5 falhas consecutivas (não 3)
    - 8s timeout (generoso)
    - Testa recuperação a cada 30s
    - 1 sucesso fecha circuit
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: int = 30,
        success_threshold: int = 1,
        timeout_per_call: int = 8,
        auto_reset_after: int = 120
    ):
        """
        Args:
            failure_threshold: Falhas consecutivas para abrir circuit (padrão: 5)
            timeout_duration: Segundos até tentar novamente (padrão: 30)
            success_threshold: Sucessos para fechar circuit (padrão: 1)
            timeout_per_call: Timeout em segundos por chamada (padrão: 8)
            auto_reset_after: Segundos sem erros para resetar contador (padrão: 120)
        """
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.success_threshold = success_threshold
        self.timeout_per_call = timeout_per_call
        self.auto_reset_after = auto_reset_after

        # Estado interno
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None
        self._lock = threading.Lock()

        # Estatísticas
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._times_opened = 0

        logger.info(
            f"🔧 Circuit Breaker inicializado: "
            f"threshold={failure_threshold}, "
            f"timeout={timeout_duration}s, "
            f"call_timeout={timeout_per_call}s"
        )

    @property
    def state(self) -> CircuitState:
        """Estado atual do circuit"""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Circuit está fechado (funcionando normal)?"""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Circuit está aberto (bloqueado)?"""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Circuit está testando?"""
        return self._state == CircuitState.HALF_OPEN

    def _should_attempt_reset(self) -> bool:
        """Verifica se deve tentar resetar circuit após timeout"""
        if self._state != CircuitState.OPEN:
            return False

        if not self._opened_at:
            return False

        elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
        return elapsed >= self.timeout_duration

    def _should_auto_reset_counters(self) -> bool:
        """Verifica se deve resetar contadores por inatividade de erros"""
        if not self._last_failure_time:
            return False

        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.auto_reset_after

    def _record_success(self):
        """Registra sucesso"""
        with self._lock:
            self._last_success_time = datetime.utcnow()
            self._total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.info(
                    f"✅ Circuit HALF_OPEN: Sucesso {self._success_count}/{self.success_threshold}"
                )

                if self._success_count >= self.success_threshold:
                    self._close_circuit()

            elif self._state == CircuitState.CLOSED:
                # Resetar contador de falhas após sucesso
                if self._failure_count > 0:
                    logger.info(
                        f"🔄 Circuit CLOSED: Resetando contador de falhas "
                        f"({self._failure_count} → 0) após sucesso"
                    )
                    self._failure_count = 0

    def _record_failure(self, error: Exception):
        """Registra falha"""
        with self._lock:
            self._last_failure_time = datetime.utcnow()
            self._total_failures += 1

            # Verifica se é um erro grave (timeout ou conexão recusada)
            error_str = str(error).lower()
            is_serious_error = any(
                keyword in error_str
                for keyword in ['timeout', 'timed out', 'connection refused', 'connection reset']
            )

            if not is_serious_error:
                logger.warning(
                    f"⚠️ Circuit: Erro não crítico ignorado: {error.__class__.__name__}"
                )
                return

            if self._state == CircuitState.HALF_OPEN:
                logger.error(
                    f"❌ Circuit HALF_OPEN: Falhou no teste de recuperação. "
                    f"Voltando para OPEN por mais {self.timeout_duration}s"
                )
                self._open_circuit()

            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.warning(
                    f"⚠️ Circuit CLOSED: Falha {self._failure_count}/{self.failure_threshold} "
                    f"(erro: {error.__class__.__name__})"
                )

                if self._failure_count >= self.failure_threshold:
                    self._open_circuit()

    def _open_circuit(self):
        """Abre o circuit (bloqueia chamadas)"""
        self._state = CircuitState.OPEN
        self._opened_at = datetime.utcnow()
        self._times_opened += 1

        logger.error(
            f"🔴 Circuit ABERTO! Odoo considerado offline. "
            f"Próxima tentativa em {self.timeout_duration}s. "
            f"(Total de aberturas: {self._times_opened})"
        )

    def _close_circuit(self):
        """Fecha o circuit (volta ao normal)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

        logger.info(
            f"🟢 Circuit FECHADO! Odoo voltou ao normal. "
            f"Estatísticas: {self._total_successes} sucessos, "
            f"{self._total_failures} falhas, "
            f"{self._times_opened} aberturas"
        )

    def _half_open_circuit(self):
        """Coloca circuit em modo teste"""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0

        logger.info(
            f"🟡 Circuit HALF_OPEN (testando). "
            f"Permitindo 1 tentativa para verificar se Odoo voltou..."
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executa função protegida pelo circuit breaker

        Args:
            func: Função a ser executada
            *args, **kwargs: Argumentos da função

        Returns:
            Resultado da função

        Raises:
            Exception: Se circuit estiver aberto ou função falhar
        """
        with self._lock:
            self._total_calls += 1

            # Auto-reset de contadores se passou tempo sem erros
            if self._should_auto_reset_counters():
                logger.info(
                    f"🔄 Auto-reset: {self.auto_reset_after}s sem erros. "
                    f"Resetando contador ({self._failure_count} → 0)"
                )
                self._failure_count = 0

            # Verificar se deve tentar resetar
            if self._should_attempt_reset():
                self._half_open_circuit()

            # Bloquear se circuit estiver aberto
            if self._state == CircuitState.OPEN:
                time_remaining = self.timeout_duration - (
                    datetime.utcnow() - self._opened_at
                ).total_seconds()

                raise Exception(
                    f"Circuit Breaker ABERTO: Odoo indisponível. "
                    f"Tentando novamente em {int(time_remaining)}s"
                )

        # Executar função
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    def get_status(self) -> dict:
        """Retorna status detalhado do circuit breaker"""
        with self._lock:
            time_since_last_failure = None
            if self._last_failure_time:
                time_since_last_failure = (
                    datetime.utcnow() - self._last_failure_time
                ).total_seconds()

            time_until_retry = None
            if self._state == CircuitState.OPEN and self._opened_at:
                elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
                time_until_retry = max(0, self.timeout_duration - elapsed)

            return {
                'state': self._state.value,
                'is_healthy': self._state == CircuitState.CLOSED,
                'failure_count': self._failure_count,
                'failure_threshold': self.failure_threshold,
                'success_count': self._success_count,
                'total_calls': self._total_calls,
                'total_successes': self._total_successes,
                'total_failures': self._total_failures,
                'times_opened': self._times_opened,
                'time_since_last_failure': time_since_last_failure,
                'time_until_retry': time_until_retry,
                'opened_at': self._opened_at.isoformat() if self._opened_at else None,
                'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
                'last_success_time': self._last_success_time.isoformat() if self._last_success_time else None,
            }

    def reset(self):
        """Reseta manualmente o circuit breaker"""
        with self._lock:
            logger.warning("⚠️ RESET MANUAL do Circuit Breaker")
            self._close_circuit()


# Instância global do circuit breaker para Odoo
_odoo_circuit_breaker: Optional[OdooCircuitBreaker] = None


def get_circuit_breaker() -> OdooCircuitBreaker:
    """Retorna instância global do circuit breaker"""
    global _odoo_circuit_breaker

    if _odoo_circuit_breaker is None:
        _odoo_circuit_breaker = OdooCircuitBreaker(
            failure_threshold=5,      # 5 falhas consecutivas
            timeout_duration=30,      # Testa a cada 30s
            success_threshold=1,      # 1 sucesso fecha
            timeout_per_call=8,       # 8s por chamada
            auto_reset_after=120      # Reset após 2min sem erros
        )

    return _odoo_circuit_breaker


def with_circuit_breaker(func: Callable) -> Callable:
    """
    Decorator para proteger funções com circuit breaker

    Uso:
        @with_circuit_breaker
        def buscar_dados_odoo():
            # código que acessa Odoo
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        circuit = get_circuit_breaker()
        return circuit.call(func, *args, **kwargs)

    return wrapper
