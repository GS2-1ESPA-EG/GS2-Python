"""
core/consumption.py
-------------------
Registro de consumo de itens (UC03).

Cada vez que um astronauta consome um item, geramos um registro
imutável no histórico. O histórico nunca é editado depois — é
auditoria de bordo. Em produção, esses registros são sincronizados
com a terra na primeira janela de comunicação disponível.
"""

import uuid

from core.storage import load_json, save_json
from core import items as items_core
from utils.dates import now_iso


FILENAME = "consumption.json"


def list_all() -> list[dict]:
    """Retorna todos os registros de consumo."""
    data = load_json(FILENAME, default=[])
    return data if isinstance(data, list) else []


def list_by_item(item_id: str) -> list[dict]:
    """Histórico de consumo de um item específico."""
    return [r for r in list_all() if r.get("item_id") == item_id]


def list_by_astronaut(astronaut_id: str) -> list[dict]:
    """Consumos registrados por um astronauta."""
    return [r for r in list_all() if r.get("astronaut_id") == astronaut_id]


def list_recent(limit: int = 20) -> list[dict]:
    """Últimos N consumos, ordenados do mais recente para o mais antigo."""
    records = list_all()
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


def register(item_id: str, quantity_consumed: int,
             astronaut_id: str, notes: str = "") -> dict:
    """
    Registra um consumo e atualiza o estoque do item.

    Esta é uma operação composta: cria o registro de consumo E
    decrementa a quantidade do item correspondente. Se o item não
    existir ou se a quantidade exceder o estoque, levanta ValueError
    sem persistir nada.
    """
    if quantity_consumed <= 0:
        raise ValueError("Quantidade consumida deve ser maior que zero.")

    item = items_core.find_by_id(item_id)
    if not item:
        raise ValueError(f"Item {item_id} não encontrado.")

    current = item.get("quantity", 0)
    if quantity_consumed > current:
        raise ValueError(
            f"Estoque insuficiente: disponível {current}, "
            f"requisitado {quantity_consumed}."
        )

    # Cria registro
    record = {
        "id": str(uuid.uuid4())[:12],
        "item_id": item_id,
        "item_name": item["name"],   # snapshot, mesmo se item for renomeado
        "quantity_consumed": quantity_consumed,
        "unit": item.get("unit", ""),
        "astronaut_id": astronaut_id,
        "notes": notes,
        "timestamp": now_iso(),
    }

    # Persiste o registro
    records = list_all()
    records.append(record)
    save_json(FILENAME, records)

    # Atualiza estoque
    items_core.update_quantity(item_id, current - quantity_consumed)

    return record


def total_consumed(item_id: str) -> int:
    """Soma total já consumido de um item específico."""
    return sum(r["quantity_consumed"] for r in list_by_item(item_id))


def daily_consumption_rate(item_id: str, days: int = 7) -> float:
    """
    Taxa média de consumo diário de um item nos últimos N dias.
    Útil como input bruto para a IA preditiva (que vive em terra).
    """
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = list_by_item(item_id)

    relevant = []
    for r in records:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts >= cutoff:
                relevant.append(r)
        except (ValueError, KeyError):
            continue

    if not relevant:
        return 0.0

    total = sum(r["quantity_consumed"] for r in relevant)
    return total / days
