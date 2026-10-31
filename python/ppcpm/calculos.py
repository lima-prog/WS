"""
Regras de cálculo da TELA INICIAL ("Visão geral do dia") em Python.

Mesma lógica da função home() do sistema.js:
    - status da OP: Concluída / Atrasada (prazo vencido) / Em aberto / Em produção
    - "% Porcentagem impresso" = OPs concluídas ÷ total de OPs
    - "Total já realizados"    = soma do campo `feito` (e % sobre a soma de `qtde`)
    - "Obras para impressão"   = obra definida em config (OBRA_IMPRESSAO)
    - "Obras impressas"        = soma de `qtde` das OPs atrasadas
    - "Obras pendente"         = soma de `qtde` das OPs em aberto
"""
from __future__ import annotations

from datetime import date
from typing import Iterable


def status(op: dict, hoje: str | None = None) -> str:
    hoje = hoje or date.today().isoformat()
    if op.get("st") == "Concluída":
        return "Concluída"
    if str(op.get("prazo") or "") < hoje:
        return "Atrasada"
    return op.get("st") or "Em aberto"


def soma(ops: Iterable[dict], campo: str) -> float:
    total = 0.0
    for o in ops:
        try:
            total += float(o.get(campo) or 0)
        except (TypeError, ValueError):
            pass
    return total


def numero_br(n: float) -> str:
    """23232 -> '23.232' (igual ao sistema em português)."""
    return f"{round(n):,}".replace(",", ".")


def resumo_inicio(ops: list[dict], pacote_atual, obra_impressao, hoje: str | None = None) -> dict:
    total_ops = len(ops)
    concluidas = sum(1 for o in ops if status(o, hoje) == "Concluída")
    planejado = soma(ops, "qtde")
    realizado = soma(ops, "feito")
    pct_realizado = round(realizado / planejado * 100) if planejado else 0
    pct_impresso = round(concluidas / (total_ops or 1) * 100) if total_ops else 0
    return {
        "pacote_atual": pacote_atual,
        "porcentagem_impresso": pct_impresso,
        "total_realizados": round(realizado),
        "total_realizados_texto": numero_br(realizado),
        "total_planejado": round(planejado),
        "percentual_realizado": pct_realizado,
        "obras_para_impressao": obra_impressao,
        "obras_impressas": round(soma([o for o in ops if status(o, hoje) == "Atrasada"], "qtde")),
        "obras_pendente": round(soma([o for o in ops if status(o, hoje) == "Em aberto"], "qtde")),
    }
