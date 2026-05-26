"""
core/alerts.py
--------------
Geração e gerenciamento de alertas (UC05, UC06).

Tipos de alerta suportados:
- expiry_soon       — item vence em até X dias
- expired           — item já vencido
- low_stock         — quantidade abaixo do threshold configurado
- env_anomaly       — compartimento com leitura ambiental fora da faixa
"""

import uuid

from core.storage import load_json, save_json
from core import items as items_core
from core import compartments as comp_core
from utils.dates import now_iso, days_until


FILENAME = "alerts.json"


# ============================================================
# Leitura
# ============================================================

def list_all() -> list[dict]:
    data = load_json(FILENAME, default=[])
    return data if isinstance(data, list) else []


def list_active() -> list[dict]:
    """Alertas não confirmados (acknowledged=False)."""
    return [a for a in list_all() if not a.get("acknowledged", False)]


def list_by_severity(severity: str) -> list[dict]:
    return [a for a in list_active() if a.get("severity") == severity]


def find_by_id(alert_id: str) -> dict | None:
    for a in list_all():
        if a["id"] == alert_id:
            return a
    return None


# ============================================================
# Geração
# ============================================================

def _create_alert(alert_type: str, severity: str, message: str,
                  item_id: str = None, compartment_id: str = None) -> dict:
    """Helper interno: cria e persiste um alerta."""
    alert = {
        "id": str(uuid.uuid4())[:12],
        "type": alert_type,
        "severity": severity,
        "message": message,
        "item_id": item_id,
        "compartment_id": compartment_id,
        "created_at": now_iso(),
        "acknowledged": False,
        "acknowledged_at": None,
        "acknowledged_by": None,
    }
    alerts = list_all()
    alerts.append(alert)
    save_json(FILENAME, alerts)
    return alert


def generate_automatic_alerts() -> list[dict]:
    """
    Varre o inventário e gera alertas para todas as condições anômalas
    detectadas. Evita duplicar alertas que já existem ativos para a
    mesma condição (mesma combinação tipo + item ou tipo + compartimento).

    Esse é o método principal usado pelo CLI para "atualizar" os alertas
    ativos. Pode ser chamado ao iniciar o programa e periodicamente.
    """
    new_alerts = []
    active = list_active()

    def already_active(alert_type: str, item_id: str = None,
                       compartment_id: str = None) -> bool:
        for a in active:
            if a["type"] != alert_type:
                continue
            if item_id and a.get("item_id") == item_id:
                return True
            if compartment_id and a.get("compartment_id") == compartment_id:
                return True
        return False

    # 1. Itens vencidos
    for item in items_core.list_all():
        try:
            days = days_until(item["expiry_date"])
        except (KeyError, ValueError):
            continue
        if days < 0 and not already_active("expired", item_id=item["id"]):
            a = _create_alert(
                "expired", "critical",
                f"{item['name']} (lote {item.get('lot_number', 'N/A')}) "
                f"venceu há {abs(days)} dias.",
                item_id=item["id"]
            )
            new_alerts.append(a)
        elif 0 <= days <= 30 and not already_active("expiry_soon", item_id=item["id"]):
            severity = "warning" if days > 7 else "critical"
            a = _create_alert(
                "expiry_soon", severity,
                f"{item['name']} vence em {days} dias.",
                item_id=item["id"]
            )
            new_alerts.append(a)

    # 2. Estoque baixo
    for item in items_core.list_low_stock(0.3):
        if already_active("low_stock", item_id=item["id"]):
            continue
        ratio = item["_stock_ratio"]
        severity = "critical" if ratio < 0.15 else "warning"
        a = _create_alert(
            "low_stock", severity,
            f"Estoque de {item['name']} em {int(ratio*100)}% "
            f"({item['quantity']}/{item['quantity_initial']} {item.get('unit','')}).",
            item_id=item["id"]
        )
        new_alerts.append(a)

    # 3. Anomalias ambientais
    for compartment in comp_core.list_all():
        if not comp_core.is_out_of_range(compartment):
            continue
        if already_active("env_anomaly", compartment_id=compartment["id"]):
            continue
        temp = compartment.get("current_temp")
        a = _create_alert(
            "env_anomaly", "critical",
            f"Compartimento {compartment['id']} ({compartment['name']}): "
            f"temperatura {temp}°C fora da faixa "
            f"({compartment['temp_min']}–{compartment['temp_max']}°C).",
            compartment_id=compartment["id"]
        )
        new_alerts.append(a)

    return new_alerts


# ============================================================
# Confirmação
# ============================================================

def acknowledge(alert_id: str, astronaut_id: str) -> dict:
    """Marca um alerta como confirmado (UC06)."""
    alerts = list_all()
    for a in alerts:
        if a["id"] == alert_id:
            if a.get("acknowledged"):
                raise ValueError("Alerta já foi confirmado.")
            a["acknowledged"] = True
            a["acknowledged_at"] = now_iso()
            a["acknowledged_by"] = astronaut_id
            save_json(FILENAME, alerts)
            return a
    raise ValueError(f"Alerta {alert_id} não encontrado.")
