"""
utils/dates.py
--------------
Funções auxiliares para manipulação de datas no contexto da missão.

Em uma cápsula em órbita, todas as datas são tratadas em UTC para evitar
ambiguidade — o conceito de "fuso horário" não faz sentido em microgravidade.
"""

from datetime import datetime, timezone


def now_iso() -> str:
    """Timestamp atual no formato ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    """
    Converte string ISO 8601 para datetime.
    Aceita tanto formatos com timezone quanto sem (assume UTC se ausente).
    """
    if not s:
        raise ValueError("Data vazia")
    # fromisoformat aceita ambos os casos no Python 3.11+
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def days_until(date_str: str) -> int:
    """
    Calcula quantos dias faltam até a data informada.
    Retorna número negativo se a data já passou.
    """
    target = parse_iso(date_str)
    now = datetime.now(timezone.utc)
    delta = target - now
    return delta.days


def format_date_br(date_str: str) -> str:
    """Formata uma data ISO no padrão brasileiro DD/MM/YYYY."""
    try:
        dt = parse_iso(date_str)
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str  # devolve original se não conseguir parsear


def format_datetime_br(date_str: str) -> str:
    """Formata um timestamp no padrão DD/MM/YYYY HH:MM."""
    try:
        dt = parse_iso(date_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return date_str
