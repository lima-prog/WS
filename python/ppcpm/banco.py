"""
Acesso ao banco (Supabase, projeto "SISTEMA PCP") pela API REST.

As regras de segurança do banco continuam valendo: cada leitura usa o token do
usuário que fez login no sistema (o mesmo login da tela do HTML).
Tabelas: ops, apontamentos, perfis, solicitacoes, preferencias, historico, planilhas, planilhas_versoes.
"""
from __future__ import annotations

import requests

from .config import SUPABASE_CHAVE_PUBLICA, SUPABASE_URL


def _cabecalho(token: str) -> dict:
    return {"apikey": SUPABASE_CHAVE_PUBLICA, "Authorization": f"Bearer {token}"}


def ler_tabela(tabela: str, token: str, filtro: str = "select=*") -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{tabela}?{filtro}", headers=_cabecalho(token), timeout=20)
    r.raise_for_status()
    return r.json()


def ler_ops(token: str) -> list[dict]:
    return ler_tabela("ops", token)
