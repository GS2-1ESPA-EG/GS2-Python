"""
core/sync.py
------------
Exportação de período offline para sincronização via MQTT.

CONTEXTO ARQUITETURAL

O CLI Python é uma das três interfaces de bordo do OrbitStock:

  1. App principal (React no tablet) — uso normal
  2. Sistema embarcado (ESP32 + Gateway MQTT) — telemetria automática
  3. CLI Python (este sistema) — backup quando o App principal cai

Em condições normais, o App principal publica cada operação via MQTT,
e o Gateway de bordo a transmite para terra. Quando o App principal
está fora do ar, o astronauta opera pelo CLI, mas o CLI não fala MQTT
diretamente (e nem deveria, para manter a separação de
responsabilidades exigida pela disciplina de Computational Thinking).

Quando o sistema principal volta, em vez de pedir para o astronauta
re-registrar tudo manualmente, o CLI EXPORTA um arquivo no formato
"mqtt_envelope" que o Gateway de bordo pode consumir e publicar como
se fossem mensagens normais.

FORMATO DO ENVELOPE

O envelope contém uma lista de mensagens, cada uma com:
  - topic: tópico MQTT de destino
  - payload: dado da mensagem
  - qos: nível de qualidade (1 = at least once, suficiente para sync)
  - retain: false (mensagens históricas não devem ser retidas)

O Gateway de bordo (entrega Edge Computing) lê o envelope, publica
cada mensagem na ordem original (preserva timestamps) e move o
envelope para a pasta `processed/`. A partir desse momento, a Terra
recebe normalmente como se nunca tivesse havido pane.

VANTAGEM DESSA ABORDAGEM

- CLI escreve apenas JSON local (atende à disciplina de Python)
- Gateway lida com MQTT e banco de dados (atende à disciplina de Edge)
- O astronauta clica UMA vez em "Exportar" e tudo flui automaticamente
- Cada disciplina mantém sua stack ideal sem comprometer o produto
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core import spacecraft as sc_core
from core import items as items_core
from core import compartments as comp_core
from core import consumption as cons_core
from core import alerts as alerts_core
from core.storage import DATA_DIR
from utils.dates import now_iso, parse_iso


# Onde os envelopes são salvos
EXPORT_DIR = DATA_DIR.parent / "exports"


# ============================================================
# Identificação do período offline
# ============================================================

def _get_last_sync_timestamp() -> str | None:
    """
    Retorna o timestamp da última exportação bem-sucedida.
    Se nunca houve exportação, retorna None (exporta tudo).
    """
    sync_state_file = DATA_DIR / "_sync_state.json"
    if not sync_state_file.exists():
        return None
    try:
        with open(sync_state_file, "r", encoding="utf-8") as fp:
            state = json.load(fp)
        return state.get("last_export_at")
    except (json.JSONDecodeError, OSError):
        return None


def _set_last_sync_timestamp(timestamp: str) -> None:
    """Persiste o timestamp da última exportação."""
    sync_state_file = DATA_DIR / "_sync_state.json"
    state = {"last_export_at": timestamp}
    with open(sync_state_file, "w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2)


def _is_after(timestamp: str, cutoff: str | None) -> bool:
    """
    Retorna True se `timestamp` é posterior a `cutoff`.
    Se cutoff for None, retorna True (sem cutoff, tudo passa).
    """
    if not cutoff:
        return True
    try:
        return parse_iso(timestamp) > parse_iso(cutoff)
    except (ValueError, TypeError):
        return True


# ============================================================
# Construção das mensagens MQTT
# ============================================================

def _build_consumption_message(record: dict, spacecraft_id: str) -> dict:
    """
    Converte um registro de consumo em uma mensagem MQTT.

    Tópico: orbitstock/<spacecraft_id>/consumption
    Esse é o mesmo tópico que o App principal publicaria em condições
    normais. O Gateway processa do mesmo jeito.
    """
    return {
        "topic": f"orbitstock/{spacecraft_id}/consumption",
        "payload": {
            "id": record["id"],
            "item_id": record["item_id"],
            "item_name": record.get("item_name", ""),
            "quantity_consumed": record["quantity_consumed"],
            "unit": record.get("unit", ""),
            "astronaut_id": record["astronaut_id"],
            "notes": record.get("notes", ""),
            "timestamp": record["timestamp"],
            "source": "cli_offline",   # marca a origem para auditoria
        },
        "qos": 1,
        "retain": False,
    }


def _build_alert_ack_message(alert: dict, spacecraft_id: str) -> dict:
    """
    Converte uma confirmação de alerta em mensagem MQTT.

    Tópico: orbitstock/<spacecraft_id>/alerts/ack
    Confirmações geradas offline precisam chegar à terra para que o
    engenheiro de missão saiba que o astronauta viu o alerta.
    """
    return {
        "topic": f"orbitstock/{spacecraft_id}/alerts/ack",
        "payload": {
            "alert_id": alert["id"],
            "alert_type": alert.get("type", ""),
            "acknowledged_by": alert.get("acknowledged_by", ""),
            "acknowledged_at": alert.get("acknowledged_at", ""),
            "source": "cli_offline",
        },
        "qos": 1,
        "retain": False,
    }


def _build_item_state_message(item: dict, spacecraft_id: str) -> dict:
    """
    Snapshot do estado atual de um item, para reconciliação.

    Tópico: orbitstock/<spacecraft_id>/items/<item_id>/state
    Mesmo que cada consumo individual seja transmitido como mensagem
    separada, enviar o estado final consolidado serve como "ground truth"
    para a Terra confirmar que o estoque calculado bate.
    """
    return {
        "topic": f"orbitstock/{spacecraft_id}/items/{item['id']}/state",
        "payload": {
            "id": item["id"],
            "name": item["name"],
            "quantity": item["quantity"],
            "quantity_initial": item.get("quantity_initial", item["quantity"]),
            "unit": item.get("unit", ""),
            "compartment_id": item.get("compartment_id", ""),
            "expiry_date": item.get("expiry_date", ""),
            "snapshot_at": now_iso(),
            "source": "cli_offline",
        },
        "qos": 1,
        "retain": True,   # estado final é retido (último write wins)
    }


# ============================================================
# Geração do envelope
# ============================================================

def build_envelope(include_full_state_snapshot: bool = True) -> dict:
    """
    Constrói o envelope MQTT com todas as operações desde a última
    exportação.

    Args:
        include_full_state_snapshot: se True, inclui também o estado
            consolidado de todos os itens no fim (útil pra reconciliação
            na terra). Default: True.

    Returns:
        dict com o envelope completo, pronto pra ser serializado em JSON.
    """
    spacecraft = sc_core.get_spacecraft()
    if not spacecraft:
        raise ValueError(
            "Não há cápsula cadastrada. Configure a cápsula antes de exportar."
        )
    spacecraft_id = spacecraft["id"]

    cutoff = _get_last_sync_timestamp()
    messages = []

    # 1. Consumos do período
    new_consumptions = [
        r for r in cons_core.list_all()
        if _is_after(r["timestamp"], cutoff)
    ]
    for record in new_consumptions:
        messages.append(_build_consumption_message(record, spacecraft_id))

    # 2. Alertas confirmados no período
    acknowledged_alerts = [
        a for a in alerts_core.list_all()
        if a.get("acknowledged") and _is_after(
            a.get("acknowledged_at", ""), cutoff
        )
    ]
    for alert in acknowledged_alerts:
        messages.append(_build_alert_ack_message(alert, spacecraft_id))

    # 3. Snapshot final do estado dos itens (opcional)
    if include_full_state_snapshot:
        for item in items_core.list_all():
            messages.append(_build_item_state_message(item, spacecraft_id))

    # Envelope final
    envelope = {
        "envelope_id": str(uuid.uuid4()),
        "envelope_version": "1.0",
        "spacecraft_id": spacecraft_id,
        "mission_name": spacecraft.get("mission_name", ""),
        "generated_at": now_iso(),
        "cutoff_timestamp": cutoff,
        "message_count": len(messages),
        "stats": {
            "consumptions": len(new_consumptions),
            "alert_acks": len(acknowledged_alerts),
            "item_states": (len(items_core.list_all())
                            if include_full_state_snapshot else 0),
        },
        "messages": messages,
    }

    return envelope


# ============================================================
# Exportação para disco
# ============================================================

def export_envelope(include_full_state_snapshot: bool = True) -> Path:
    """
    Gera o envelope e salva em disco.

    Returns:
        Path do arquivo gerado. O arquivo fica em `exports/` com nome
        no formato `mqtt_envelope_YYYYMMDD_HHMMSS_<uuid8>.json`.
    """
    envelope = build_envelope(include_full_state_snapshot)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_id = envelope["envelope_id"][:8]
    filename = f"mqtt_envelope_{timestamp}_{short_id}.json"
    filepath = EXPORT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(envelope, fp, indent=2, ensure_ascii=False)

    # Atualiza o cutoff para o timestamp desta exportação
    _set_last_sync_timestamp(envelope["generated_at"])

    return filepath


# ============================================================
# Preview (sem persistir)
# ============================================================

def preview_export() -> dict:
    """
    Retorna estatísticas do que SERIA exportado, sem gerar arquivo
    nem atualizar o cutoff. Útil pra mostrar ao operador antes de
    confirmar.
    """
    envelope = build_envelope(include_full_state_snapshot=True)
    return {
        "spacecraft_id": envelope["spacecraft_id"],
        "cutoff_timestamp": envelope["cutoff_timestamp"],
        "stats": envelope["stats"],
        "total_messages": envelope["message_count"],
    }


def list_previous_exports() -> list[dict]:
    """
    Lista os envelopes já exportados (em ordem cronológica reversa).
    Cada item contém metadados básicos para exibição.
    """
    if not EXPORT_DIR.exists():
        return []

    results = []
    for filepath in sorted(EXPORT_DIR.glob("mqtt_envelope_*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as fp:
                envelope = json.load(fp)
            results.append({
                "filename": filepath.name,
                "filepath": str(filepath),
                "generated_at": envelope.get("generated_at", "?"),
                "message_count": envelope.get("message_count", 0),
                "stats": envelope.get("stats", {}),
                "size_kb": filepath.stat().st_size / 1024,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return results
