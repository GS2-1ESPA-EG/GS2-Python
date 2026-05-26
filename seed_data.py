"""
seed_data.py
------------
Popula o sistema com dados realistas da Dragon C209 (Missão CRS-31)
para demonstração e testes.

Usa exatamente os mesmos dados que aparecem nos mockups do documento
de Software & TXD: Insulina em M-03 com temperatura alta, água em A-12,
ração em B-04, etc.
"""

from datetime import datetime, timedelta, timezone

from core.storage import save_json
from core import spacecraft as sc_core
from core import compartments as comp_core
from core import items as items_core
from core import consumption as cons_core
from core import alerts as alerts_core


def _iso_in_days(days: int) -> str:
    """Retorna uma data ISO daqui a N dias (negativo para passado)."""
    target = datetime.now(timezone.utc) + timedelta(days=days)
    return target.date().isoformat()


def seed() -> None:
    """Limpa todos os arquivos e cadastra dados de exemplo."""

    # --- 1. Limpa estado anterior ---
    save_json("spacecraft.json", {})
    save_json("compartments.json", [])
    save_json("items.json", [])
    save_json("consumption.json", [])
    save_json("alerts.json", [])

    # --- 2. Cápsula ---
    sc_core.create_spacecraft(
        spacecraft_id="DRAGON-C209",
        mission_name="CRS-31",
        crew_size=4,
        status="in_transit",
    )

    # --- 3. Compartimentos ---
    comp_core.create("A-12", "Reservatório de água", "water",
                     temp_min=4, temp_max=20)
    comp_core.create("B-04", "Estoque seco — alimentos", "food",
                     temp_min=10, temp_max=25)
    comp_core.create("M-03", "Médico refrigerado", "medical",
                     temp_min=2, temp_max=8)
    comp_core.create("T-01", "Ferramentas e EVA", "tools",
                     temp_min=15, temp_max=30)
    comp_core.create("E-05", "Experimentos científicos", "experiments",
                     temp_min=15, temp_max=25)

    # Leituras ambientais simuladas
    comp_core.update_reading("A-12", temp=15.2, humidity=45)
    comp_core.update_reading("B-04", temp=21.8, humidity=38)
    # M-03 com temperatura ACIMA do limite — vai gerar alerta crítico
    comp_core.update_reading("M-03", temp=12.5, humidity=52)
    comp_core.update_reading("T-01", temp=22.0, humidity=40)
    comp_core.update_reading("E-05", temp=20.5, humidity=42)

    # --- 4. Itens ---
    # Água
    items_core.create(
        item_id="H2O-082", name="Água potável (bolsas 2L)",
        category="water", compartment_id="A-12",
        quantity=84, unit="unidades", expiry_date=_iso_in_days(365 * 2),
        criticality="critical", lot_number="H2O-2026-Q2",
    )
    # Alimentos
    items_core.create(
        item_id="FD-203", name="Ração liofilizada (pacotes 350g)",
        category="food", compartment_id="B-04",
        quantity=22, unit="pacotes", expiry_date=_iso_in_days(90),
        criticality="high", lot_number="FD-2026-08",
    )
    items_core.create(
        item_id="FD-210", name="Barras energéticas",
        category="food", compartment_id="B-04",
        quantity=48, unit="unidades", expiry_date=_iso_in_days(180),
        criticality="medium", lot_number="FD-2026-04",
    )
    # Médicos
    items_core.create(
        item_id="INS-2026-04", name="Insulina (ampolas 10ml)",
        category="medical", compartment_id="M-03",
        quantity=6, unit="ampolas", expiry_date=_iso_in_days(240),
        criticality="critical", requires_refrigeration=True,
        lot_number="INS-2026-04",
    )
    items_core.create(
        item_id="MED-AAS-12", name="AAS 100mg (cartelas)",
        category="medical", compartment_id="M-03",
        quantity=20, unit="unidades", expiry_date=_iso_in_days(720),
        criticality="medium", lot_number="MED-2025-12",
    )
    items_core.create(
        item_id="MED-EPI-01", name="Epinefrina (auto-injetor)",
        category="medical", compartment_id="M-03",
        quantity=2, unit="unidades", expiry_date=_iso_in_days(10),  # vence em 10d!
        criticality="critical", requires_refrigeration=True,
        lot_number="EPI-2026-03",
    )
    # Ferramentas / EVA
    items_core.create(
        item_id="TLS-MM-01", name="Multímetro de bordo",
        category="tools", compartment_id="T-01",
        quantity=2, unit="unidades", expiry_date=_iso_in_days(365 * 5),
        criticality="medium", lot_number="TLS-2025",
    )
    items_core.create(
        item_id="EVA-O2-04", name="Cilindro O2 EVA (3h)",
        category="tools", compartment_id="T-01",
        quantity=4, unit="unidades", expiry_date=_iso_in_days(365),
        criticality="critical", lot_number="EVA-2026-Q1",
    )
    # Experimentos
    items_core.create(
        item_id="EXP-CRY-08", name="Amostra criogênica",
        category="experiments", compartment_id="E-05",
        quantity=12, unit="unidades", expiry_date=_iso_in_days(60),
        criticality="high", requires_refrigeration=True,
        lot_number="EXP-CRY-2026",
    )

    # Item com ESTOQUE BAIXO — gera alerta
    # (já criado: FD-203 com 22/22 não é baixo, vamos consumir um pouco)

    # --- 5. Histórico de consumo (algum) ---
    cons_core.register("H2O-082", 16, "AST-01", "Consumo dia 1")
    cons_core.register("H2O-082", 18, "AST-02", "Consumo dia 1 (continuação)")
    cons_core.register("FD-203", 6, "AST-01", "Refeição completa, 4 pessoas")
    cons_core.register("FD-203", 10, "AST-03", "Refeição + estoque ESC")
    cons_core.register("INS-2026-04", 2, "AST-04", "Tripulante diabético tipo 1")
    cons_core.register("FD-210", 12, "AST-02", "Snacks turno noturno")

    # --- 6. Gera alertas a partir do estado ---
    alerts_core.generate_automatic_alerts()


if __name__ == "__main__":
    seed()
    print("Dados de exemplo carregados com sucesso.")
    print()
    print("Sugestão: inicie o CLI com `python3 main.py`")
