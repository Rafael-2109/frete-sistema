"""Registry de falante do turno (Fase B Task B2 — teams-melhorias).

Motivo: hooks do SDK vivem em CLOSURE criada no turno que CONECTOU o client do
pool (client_pool reusa sem reaplicar hooks) -> user_name/user_id congelados no
1o falante. Em grupos do Teams, memorias do 1o falante eram injetadas nos turnos
dos outros. O registry module-level keyed por our_session_id e atualizado a cada
turno; os hooks fazem lookup dinamico com FALLBACK para a closure (web 1:1
inalterado quando registry vazio).
"""


class TestTurnContextRegistry:
    def test_set_get_clear(self):
        from app.agente.sdk.turn_context_registry import (
            set_turn_user, get_turn_user, clear_turn_user,
        )
        set_turn_user('sess-abc', 42, 'Marcus')
        assert get_turn_user('sess-abc') == (42, 'Marcus')
        set_turn_user('sess-abc', 7, 'Rafael')  # turno seguinte sobrescreve
        assert get_turn_user('sess-abc') == (7, 'Rafael')
        clear_turn_user('sess-abc')
        assert get_turn_user('sess-abc') is None

    def test_none_session_id_e_noop(self):
        from app.agente.sdk.turn_context_registry import (
            set_turn_user, get_turn_user, clear_turn_user,
        )
        set_turn_user(None, 1, 'X')   # nao explode
        assert get_turn_user(None) is None
        clear_turn_user(None)         # nao explode

    def test_sessoes_isoladas(self):
        from app.agente.sdk.turn_context_registry import (
            set_turn_user, get_turn_user, clear_turn_user,
        )
        set_turn_user('s1', 1, 'A')
        set_turn_user('s2', 2, 'B')
        assert get_turn_user('s1') == (1, 'A')
        assert get_turn_user('s2') == (2, 'B')
        clear_turn_user('s1')
        clear_turn_user('s2')

    def test_resolve_turn_user_fallback_closure(self):
        """Helper de resolucao: registry vazio -> valores da closure (web)."""
        from app.agente.sdk.turn_context_registry import (
            resolve_turn_user, set_turn_user, clear_turn_user,
        )
        # Sem registro: fallback
        assert resolve_turn_user('sess-x', 10, 'Closure') == (10, 'Closure')
        # Com registro: falante do turno
        set_turn_user('sess-x', 99, 'Turno')
        try:
            assert resolve_turn_user('sess-x', 10, 'Closure') == (99, 'Turno')
        finally:
            clear_turn_user('sess-x')
        # session_id None: fallback
        assert resolve_turn_user(None, 10, 'Closure') == (10, 'Closure')
