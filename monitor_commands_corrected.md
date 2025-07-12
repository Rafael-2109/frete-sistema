
# Monitor de Sistema Corrigido para seu ambiente

## Para iniciar o Flask:
./venv/Scripts/python.exe run.py

## Para monitorar (após Flask estar rodando):
./venv/Scripts/python.exe app/claude_ai_novo/monitoring/cursor_monitor.py --url http://localhost:5000

## Para validação rápida:
./venv/Scripts/python.exe app/claude_ai_novo/check_status.py

## Para validação completa:
./venv/Scripts/python.exe app/claude_ai_novo/validador_sistema_real.py
