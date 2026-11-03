"""
Acesso ao banco (Supabase, projeto "SISTEMA PCP") pela API REST.

Usa só o que já vem com o Python (urllib), sem instalar nada.
As regras de segurança do banco continuam valendo: cada leitura usa o token do
usuário que fez login no sistema (o mesmo login da tela do HTML).
Tabelas: ops, apontamentos, perfis, solicitacoes, preferencias, historico, planilhas, planilhas_versoes.
"""
from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .config import SUPABASE_CHAVE_PUBLICA, SUPABASE_URL


def ler_tabela(tabela: str, token: str, filtro: str = "select=*") -> list[dict]:
    pedido = Request(
        f"{SUPABASE_URL}/rest/v1/{tabela}?{filtro}",
        headers={"apikey": SUPABASE_CHAVE_PUBLICA, "Authorization": f"Bearer {token}"},
    )
    with urlopen(pedido, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def ler_ops(token: str) -> list[dict]:
    return ler_tabela("ops", token)
