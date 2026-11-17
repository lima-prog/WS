"""Pasta de DADOS compartilhada do PPCP (a ppcp_dxf_ferramentas do servidor) — vem de PPCP_DADOS (motor.py)."""
import os

RAIZ_DADOS = os.environ.get("PPCP_DADOS", "").strip().strip('"') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "dados_locais", "producao")
