"""
core/compartments.py
--------------------
Gestão dos compartimentos físicos da cápsula.

Cada compartimento tem limites ambientais (temperatura e umidade) e
recebe atualizações periódicas dos sensores ESP32 (ou cadastros manuais
via CLI quando o app embarcado está offline).
"""

from core.storage import load_json, save_json
from utils.dates import now_iso


FILENAME = "compartments.json"

VALID_CATEGORIES = ["medical", "food", "water", "tools", "experiments", "personal"]


# ============================================================
# Leitura
# ============================================================

def list_all() -> list[dict]:
    """Retorna todos os compartimentos cadastrados."""
    data = load_json(FILENAME, default=[])
    return data if isinstance(data, list) else []


def find_by_id(compartment_id: str) -> dict | None:
    """Busca um compartimento pelo ID. Retorna None se não existir."""
    for c in list_all():
        if c["id"] == compartment_id:
            return c
    return None


def list_by_category(category: str) -> list[dict]:
    """Filtra compartimentos por categoria."""
    return [c for c in list_all() if c.get("category") == category]


# ============================================================
# Escrita
# ============================================================

def save_all(compartments: list[dict]) -> None:
    """Salva a lista inteira de compartimentos."""
    save_json(FILENAME, compartments)


def create(compartment_id: str, name: str, category: str,
           temp_min: float, temp_max: float,
           humidity_max: float = 80.0) -> dict:
    """
    Cria um novo compartimento.
    Levanta ValueError se já existir um com o mesmo ID.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoria inválida: {category}. "
            f"Use uma de: {', '.join(VALID_CATEGORIES)}"
        )

    if find_by_id(compartment_id):
        raise ValueError(f"Já existe compartimento com ID {compartment_id}.")

    if temp_min >= temp_max:
        raise ValueError("temp_min deve ser menor que temp_max.")

    compartment = {
        "id": compartment_id,
        "name": name,
        "category": category,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "humidity_max": humidity_max,
        "current_temp": None,
        "current_humidity": None,
        "last_reading_at": None,
        "created_at": now_iso(),
    }

    compartments = list_all()
    compartments.append(compartment)
    save_all(compartments)
    return compartment


def update_reading(compartment_id: str, temp: float, humidity: float) -> dict:
    """
    Atualiza a última leitura ambiental de um compartimento.
    Em produção, esse método seria chamado pelo handler MQTT.
    No CLI offline, pode ser invocado manualmente.
    """
    compartments = list_all()
    for c in compartments:
        if c["id"] == compartment_id:
            c["current_temp"] = temp
            c["current_humidity"] = humidity
            c["last_reading_at"] = now_iso()
            save_all(compartments)
            return c
    raise ValueError(f"Compartimento {compartment_id} não encontrado.")


def delete(compartment_id: str) -> bool:
    """
    Remove um compartimento. Retorna True se removeu, False se não existia.
    NOTA: não verifica se há itens associados — quem chama é responsável.
    """
    compartments = list_all()
    new_list = [c for c in compartments if c["id"] != compartment_id]
    if len(new_list) == len(compartments):
        return False
    save_all(new_list)
    return True


# ============================================================
# Análise
# ============================================================

def is_out_of_range(compartment: dict) -> bool:
    """
    Verifica se um compartimento está com leitura ambiental fora da faixa.
    Retorna False também quando ainda não há leitura registrada.
    """
    temp = compartment.get("current_temp")
    humidity = compartment.get("current_humidity")

    if temp is None:
        return False

    if temp < compartment["temp_min"] or temp > compartment["temp_max"]:
        return True

    if humidity is not None and humidity > compartment.get("humidity_max", 100):
        return True

    return False
