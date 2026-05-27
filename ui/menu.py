"""
ui/menu.py
----------
Sistema de menus interativos do CLI.

Cada função `menu_*` corresponde a uma tela do programa. As funções
retornam normalmente; o controle de fluxo (ir para outra tela, voltar)
é feito pelo loop em main.py.
"""

from core import spacecraft as sc_core
from core import compartments as comp_core
from core import items as items_core
from core import consumption as cons_core
from core import alerts as alerts_core
from core import sync as sync_core
from core.storage import health_check, DataFileCorruptedError, StorageError
from ui import display, prompts
from ui.display import Color, colored
from utils.dates import format_date_br, format_datetime_br, days_until


# ============================================================
# Tela inicial
# ============================================================

def show_banner() -> None:
    """Exibe o banner de boas-vindas."""
    display.clear_screen()
    sc = sc_core.get_spacecraft()
    subtitle = ""
    if sc:
        subtitle = (
            f"{sc['id']} · Missão {sc['mission_name']} · "
            f"Tripulação: {sc['crew_size']} · Status: {sc['status']}"
        )
    else:
        subtitle = "Sistema não inicializado — cadastre a cápsula no menu Configuração"

    display.banner("OrbitStock — Sistema CLI de Bordo (Backup Offline)", subtitle)


def main_menu() -> str:
    """
    Renderiza o menu principal e retorna a opção escolhida.
    """
    show_banner()

    # Mostra contadores rápidos
    stats = items_core.get_stats()
    active_alerts = alerts_core.list_active()
    critical_alerts = [a for a in active_alerts if a["severity"] == "critical"]

    print(colored("  Status do inventário", Color.CYAN, bold=True))
    print(f"    Itens cadastrados   : {stats['total_items']}")
    print(f"    Total de unidades   : {stats['total_quantity']}")
    expiring_color = Color.YELLOW if stats["expiring_soon"] > 0 else Color.GREEN
    print(f"    Próximos do vencim. : "
          f"{colored(str(stats['expiring_soon']), expiring_color)}")
    low_color = Color.YELLOW if stats["low_stock"] > 0 else Color.GREEN
    print(f"    Estoque baixo       : "
          f"{colored(str(stats['low_stock']), low_color)}")
    alerts_color = Color.RED if critical_alerts else (
        Color.YELLOW if active_alerts else Color.GREEN
    )
    print(f"    Alertas ativos      : "
          f"{colored(str(len(active_alerts)), alerts_color, bold=bool(critical_alerts))}"
          f" ({len(critical_alerts)} críticos)")

    print()
    print(colored("  Menu principal", Color.CYAN, bold=True))
    print()
    print("    [1] Consultar inventário")
    print("    [2] Buscar item")
    print("    [3] Registrar consumo")
    print("    [4] Cadastrar novo item")
    print("    [5] Compartimentos")
    print("    [6] Alertas ativos")
    print("    [7] Histórico de consumo")
    print("    [8] Estatísticas do inventário")
    print("    [9] Sincronizar com MQTT (exportar período offline)")
    print("    [C] Configuração / Manutenção")
    print("    [0] Sair")
    print()

    return prompts.ask_text("Opção", required=True)


# ============================================================
# 1. Consultar inventário
# ============================================================

def screen_list_inventory() -> None:
    display.clear_screen()
    display.banner("Inventário de bordo", "UC01 — Consultar item do inventário")

    items = items_core.list_all()
    if not items:
        display.info("Nenhum item cadastrado ainda.")
        display.pause()
        return

    # Filtros
    print(colored("  Filtrar por:", Color.CYAN))
    print("    [1] Todos os itens")
    print("    [2] Por compartimento")
    print("    [3] Por categoria")
    print("    [4] Críticos")
    filter_opt = prompts.ask_text("  Opção", default="1")

    if filter_opt == "2":
        comps = comp_core.list_all()
        if not comps:
            display.warning("Nenhum compartimento cadastrado.")
            display.pause()
            return
        comp_ids = [c["id"] for c in comps]
        chosen = prompts.ask_choice("Compartimento", comp_ids)
        items = items_core.list_by_compartment(chosen)
    elif filter_opt == "3":
        chosen = prompts.ask_choice("Categoria", items_core.VALID_CATEGORIES)
        items = items_core.list_by_category(chosen)
    elif filter_opt == "4":
        items = [i for i in items if i.get("criticality") == "critical"]

    if not items:
        display.info("Nenhum item encontrado com esse filtro.")
        display.pause()
        return

    _render_items_table(items)
    display.pause()


def _render_items_table(items: list[dict]) -> None:
    """Renderiza uma tabela formatada de itens."""
    headers = ["ID", "Nome", "Cat.", "Comp.", "Qtd", "Validade", "Crit."]
    rows = []
    for item in items:
        try:
            days = days_until(item["expiry_date"])
            if days < 0:
                expiry_str = colored(f"VENCIDO ({abs(days)}d)", Color.RED, bold=True)
            elif days <= 30:
                expiry_str = colored(f"{format_date_br(item['expiry_date'])} ({days}d)",
                                     Color.YELLOW)
            else:
                expiry_str = format_date_br(item["expiry_date"])
        except (KeyError, ValueError):
            expiry_str = "-"

        # Cor por criticidade
        crit = item.get("criticality", "medium")
        crit_color = display.color_by_criticality(crit)
        crit_str = colored(crit.upper()[:4], crit_color, bold=(crit == "critical"))

        # Quantidade com cor
        qty = item.get("quantity", 0)
        initial = item.get("quantity_initial", 1)
        _, qty_color = display.stock_status(qty, initial)
        qty_str = colored(f"{qty}/{initial} {item.get('unit','')[:3]}", qty_color)

        rows.append([
            item["id"][:14],
            item["name"][:24],
            item.get("category", "?")[:8],
            item.get("compartment_id", "-")[:6],
            qty_str,
            expiry_str,
            crit_str,
        ])

    display.print_table(headers, rows)


# ============================================================
# 2. Buscar item
# ============================================================

def screen_search() -> None:
    display.clear_screen()
    display.banner("Busca de item", "UC02 — Buscar por nome, categoria ou ID")

    term = prompts.ask_text("Termo de busca", required=True)
    results = items_core.search(term)

    print()
    if not results:
        display.info(f"Nenhum item encontrado para '{term}'.")
    else:
        display.success(f"{len(results)} resultado(s) encontrado(s):")
        print()
        _render_items_table(results)

    display.pause()


# ============================================================
# 3. Registrar consumo
# ============================================================

def screen_register_consumption() -> None:
    display.clear_screen()
    display.banner("Registrar consumo", "UC03 — Atualizar estoque após uso")

    item_id = prompts.ask_text("ID do item")
    item = items_core.find_by_id(item_id)
    if not item:
        display.error(f"Item '{item_id}' não encontrado.")
        display.pause()
        return

    print()
    print(colored(f"  Item: {item['name']}", Color.CYAN, bold=True))
    print(f"  Estoque atual: {item['quantity']} {item.get('unit','')}")
    print(f"  Compartimento: {item.get('compartment_id', '-')}")
    print()

    quantity = prompts.ask_int(
        "Quantidade a consumir",
        min_value=1,
        max_value=item["quantity"]
    )
    astronaut = prompts.ask_text("Identificação do astronauta (ex.: AST-01)")
    notes = prompts.ask_text("Observações (opcional)", required=False)

    try:
        record = cons_core.register(item_id, quantity, astronaut, notes)
        display.success(
            f"Consumo registrado: {quantity} {item.get('unit','')} de {item['name']}."
        )
        new_qty = item["quantity"] - quantity
        display.info(f"Novo estoque: {new_qty} {item.get('unit','')}")
        display.info(f"ID do registro: {record['id']}")
    except ValueError as e:
        display.error(str(e))

    display.pause()


# ============================================================
# 4. Cadastrar novo item
# ============================================================

def screen_create_item() -> None:
    display.clear_screen()
    display.banner("Cadastrar item", "Adicionar item ao inventário de bordo")

    # Verifica se há compartimentos disponíveis
    comps = comp_core.list_all()
    if not comps:
        display.error("Cadastre ao menos um compartimento antes (menu 5).")
        display.pause()
        return

    try:
        item_id = prompts.ask_text("ID do item (ex.: INS-2026-04)")
        if items_core.find_by_id(item_id):
            display.error(f"Já existe item com ID {item_id}.")
            display.pause()
            return

        name = prompts.ask_text("Nome do item")
        category = prompts.ask_choice("Categoria", items_core.VALID_CATEGORIES)

        comp_ids = [c["id"] for c in comps]
        compartment_id = prompts.ask_choice("Compartimento", comp_ids)

        quantity = prompts.ask_int("Quantidade", min_value=1)
        unit = prompts.ask_choice("Unidade", items_core.VALID_UNITS)
        expiry = prompts.ask_date("Validade")
        criticality = prompts.ask_choice(
            "Criticidade", items_core.VALID_CRITICALITIES, default="medium"
        )
        requires_refrig = prompts.ask_yes_no("Requer refrigeração?", default=False)
        lot = prompts.ask_text("Número do lote (opcional)", required=False)

        item = items_core.create(
            item_id=item_id, name=name, category=category,
            compartment_id=compartment_id, quantity=quantity, unit=unit,
            expiry_date=expiry, criticality=criticality,
            requires_refrigeration=requires_refrig, lot_number=lot,
        )
        display.success(f"Item {item['id']} cadastrado.")
    except ValueError as e:
        display.error(str(e))

    display.pause()


# ============================================================
# 5. Compartimentos
# ============================================================

def screen_compartments() -> None:
    while True:
        display.clear_screen()
        display.banner("Compartimentos", "Gestão dos compartimentos físicos")

        comps = comp_core.list_all()
        if comps:
            headers = ["ID", "Nome", "Categoria", "Temp.", "Umid.", "Estado"]
            rows = []
            for c in comps:
                temp_str = ("-" if c["current_temp"] is None
                            else f"{c['current_temp']}°C")
                hum_str = ("-" if c["current_humidity"] is None
                           else f"{c['current_humidity']}%")
                limits = f"({c['temp_min']}-{c['temp_max']}°C)"
                if comp_core.is_out_of_range(c):
                    state = colored("FORA DA FAIXA", Color.RED, bold=True)
                elif c["current_temp"] is None:
                    state = colored("SEM LEITURA", Color.DIM)
                else:
                    state = colored("OK", Color.GREEN)
                rows.append([c["id"], c["name"][:20], c["category"],
                             f"{temp_str} {limits}", hum_str, state])
            display.print_table(headers, rows)
        else:
            display.info("Nenhum compartimento cadastrado.")

        print()
        print("    [1] Cadastrar novo")
        print("    [2] Atualizar leitura ambiental")
        print("    [3] Remover compartimento")
        print("    [0] Voltar")
        opt = prompts.ask_text("  Opção", default="0")

        if opt == "0":
            return
        elif opt == "1":
            _create_compartment()
        elif opt == "2":
            _update_compartment_reading()
        elif opt == "3":
            _delete_compartment()


def _create_compartment() -> None:
    try:
        cid = prompts.ask_text("ID (ex.: M-03)")
        name = prompts.ask_text("Nome (ex.: Médico refrigerado)")
        category = prompts.ask_choice("Categoria", comp_core.VALID_CATEGORIES)
        temp_min = prompts.ask_float("Temperatura mínima (°C)")
        temp_max = prompts.ask_float("Temperatura máxima (°C)")
        hum_max = prompts.ask_float("Umidade máxima (%)", default=80.0)
        comp_core.create(cid, name, category, temp_min, temp_max, hum_max)
        display.success(f"Compartimento {cid} cadastrado.")
    except ValueError as e:
        display.error(str(e))
    display.pause()


def _update_compartment_reading() -> None:
    comps = comp_core.list_all()
    if not comps:
        display.warning("Nenhum compartimento para atualizar.")
        display.pause()
        return
    ids = [c["id"] for c in comps]
    cid = prompts.ask_choice("Compartimento", ids)
    temp = prompts.ask_float("Temperatura medida (°C)")
    hum = prompts.ask_float("Umidade medida (%)", default=50.0)
    try:
        comp_core.update_reading(cid, temp, hum)
        display.success("Leitura atualizada.")
    except ValueError as e:
        display.error(str(e))
    display.pause()


def _delete_compartment() -> None:
    cid = prompts.ask_text("ID do compartimento a remover")
    # Verifica itens associados
    items_in_comp = items_core.list_by_compartment(cid)
    if items_in_comp:
        display.warning(
            f"Há {len(items_in_comp)} itens nesse compartimento. "
            "Remova-os antes."
        )
        display.pause()
        return
    if prompts.confirm_destructive(f"Remover compartimento {cid}?"):
        if comp_core.delete(cid):
            display.success("Removido.")
        else:
            display.error("Compartimento não encontrado.")
    display.pause()


# ============================================================
# 6. Alertas
# ============================================================

def screen_alerts() -> None:
    display.clear_screen()
    display.banner("Alertas ativos", "UC05 / UC06 — Receber e confirmar alertas")

    # Regenera alertas a partir do estado atual
    new = alerts_core.generate_automatic_alerts()
    if new:
        display.info(f"{len(new)} novo(s) alerta(s) gerado(s) na verificação.")
        print()

    active = alerts_core.list_active()
    if not active:
        display.success("Nenhum alerta ativo. Sistema nominal.")
        display.pause()
        return

    # Ordena: críticos primeiro
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    active.sort(key=lambda a: severity_order.get(a["severity"], 99))

    for a in active:
        sev_color = display.color_by_severity(a["severity"])
        print(colored(
            f"  [{a['id']}] {a['severity'].upper()} · {a['type']}",
            sev_color, bold=True
        ))
        print(f"      {a['message']}")
        print(colored(
            f"      Criado em {format_datetime_br(a['created_at'])}",
            Color.DIM
        ))
        print()

    print()
    if prompts.ask_yes_no("Confirmar algum alerta?", default=False):
        alert_id = prompts.ask_text("ID do alerta")
        astronaut = prompts.ask_text("Identificação do astronauta")
        try:
            alerts_core.acknowledge(alert_id, astronaut)
            display.success("Alerta confirmado.")
        except ValueError as e:
            display.error(str(e))

    display.pause()


# ============================================================
# 7. Histórico de consumo
# ============================================================

def screen_consumption_history() -> None:
    display.clear_screen()
    display.banner("Histórico de consumo", "Últimos 20 registros")

    records = cons_core.list_recent(20)
    if not records:
        display.info("Nenhum consumo registrado ainda.")
        display.pause()
        return

    headers = ["ID", "Quando", "Item", "Qtd", "Por"]
    rows = []
    for r in records:
        rows.append([
            r["id"][:10],
            format_datetime_br(r["timestamp"]),
            r.get("item_name", r["item_id"])[:24],
            f"{r['quantity_consumed']} {r.get('unit','')}",
            r["astronaut_id"][:8],
        ])
    display.print_table(headers, rows)
    display.pause()


# ============================================================
# 8. Estatísticas
# ============================================================

def screen_stats() -> None:
    display.clear_screen()
    display.banner("Estatísticas do inventário", "Visão agregada")

    stats = items_core.get_stats()

    display.section("Totais")
    print(f"    Itens cadastrados : {stats['total_items']}")
    print(f"    Total de unidades : {stats['total_quantity']}")
    print(f"    Próx. do vencim.  : {stats['expiring_soon']}")
    print(f"    Estoque baixo     : {stats['low_stock']}")

    display.section("Por categoria")
    if stats["by_category"]:
        for cat, count in sorted(stats["by_category"].items(),
                                 key=lambda x: -x[1]):
            bar = "█" * min(count, 30)
            print(f"    {cat:14} {count:3}  {colored(bar, Color.BLUE)}")
    else:
        print(colored("    (sem dados)", Color.DIM))

    display.section("Por criticidade")
    if stats["by_criticality"]:
        for crit in ["critical", "high", "medium", "low"]:
            if crit in stats["by_criticality"]:
                count = stats["by_criticality"][crit]
                c = display.color_by_criticality(crit)
                bar = "█" * min(count, 30)
                print(f"    {crit:8} {count:3}  {colored(bar, c)}")
    else:
        print(colored("    (sem dados)", Color.DIM))

    display.section("Compartimentos")
    comps = comp_core.list_all()
    print(f"    Total : {len(comps)}")
    out_of_range = sum(1 for c in comps if comp_core.is_out_of_range(c))
    if out_of_range:
        print(colored(f"    Fora da faixa : {out_of_range}", Color.RED, bold=True))

    display.pause()


# ============================================================
# 9. Sincronização com MQTT (exportar período offline)
# ============================================================

def screen_sync() -> None:
    display.clear_screen()
    display.banner(
        "Sincronização com MQTT",
        "Exportar período offline para o Gateway de bordo"
    )

    print(colored("  Como funciona:", Color.CYAN, bold=True))
    print()
    print("  Em condições normais, o App principal publica cada operação")
    print("  diretamente via MQTT. Quando o App está offline e a tripulação")
    print("  opera por este CLI, as operações ficam acumuladas localmente.")
    print()
    print("  Esta função GERA um envelope MQTT consolidado com tudo o que")
    print("  foi feito desde a última sincronização. O Gateway de bordo")
    print("  (camada Edge Computing) consome o envelope e publica cada")
    print("  mensagem como se nunca tivesse havido pane.")
    print()

    # Verifica se há cápsula cadastrada
    sc = sc_core.get_spacecraft()
    if not sc:
        display.error(
            "Cápsula ainda não cadastrada. Use 'Configuração' antes de exportar."
        )
        display.pause()
        return

    # Preview do que vai exportar
    try:
        preview = sync_core.preview_export()
    except ValueError as e:
        display.error(str(e))
        display.pause()
        return

    display.section("Período a sincronizar")
    cutoff = preview["cutoff_timestamp"]
    if cutoff:
        print(f"    Desde: {format_datetime_br(cutoff)}")
    else:
        print(colored("    Desde: (primeira exportação, inclui tudo)", Color.DIM))

    display.section("Conteúdo do envelope")
    stats = preview["stats"]
    print(f"    Consumos registrados   : {stats['consumptions']}")
    print(f"    Alertas confirmados    : {stats['alert_acks']}")
    print(f"    Snapshots de itens     : {stats['item_states']}")
    print(colored(
        f"    Total de mensagens MQTT: {preview['total_messages']}",
        Color.CYAN, bold=True
    ))

    # Histórico de exportações anteriores
    previous = sync_core.list_previous_exports()
    if previous:
        display.section(f"Exportações anteriores ({len(previous)})")
        for p in previous[:3]:
            print(f"    {p['filename']}")
            print(colored(
                f"      Gerado em {format_datetime_br(p['generated_at'])} "
                f"· {p['message_count']} mensagens · {p['size_kb']:.1f} KB",
                Color.DIM
            ))
        if len(previous) > 3:
            print(colored(f"    (... e mais {len(previous) - 3})", Color.DIM))

    print()
    if preview["total_messages"] == 0:
        display.info("Nada novo para exportar desde a última sincronização.")
        display.pause()
        return

    if not prompts.ask_yes_no(
        "Gerar envelope MQTT e marcar período como sincronizado?",
        default=True
    ):
        display.info("Exportação cancelada. Cutoff não foi alterado.")
        display.pause()
        return

    try:
        filepath = sync_core.export_envelope(include_full_state_snapshot=True)
        display.success("Envelope MQTT gerado.")
        print()
        display.info(f"Arquivo: {filepath.name}")
        display.info(f"Local:   {filepath.parent}")
        print()
        print(colored("  Próximo passo:", Color.CYAN, bold=True))
        print("    O Gateway de bordo (sistema embarcado) detectará o envelope")
        print("    em exports/ e publicará as mensagens via MQTT na próxima")
        print("    janela de comunicação. Nenhuma ação manual adicional é")
        print("    necessária.")
    except (ValueError, OSError) as e:
        display.error(f"Falha ao exportar: {e}")

    display.pause()


# ============================================================
# C. Configuração / Manutenção
# ============================================================

def screen_config() -> None:
    while True:
        display.clear_screen()
        display.banner("Configuração / Manutenção", "Setup e diagnóstico do sistema")

        sc = sc_core.get_spacecraft()
        if sc:
            display.section("Cápsula cadastrada")
            print(f"    ID            : {sc['id']}")
            print(f"    Missão        : {sc['mission_name']}")
            print(f"    Tripulação    : {sc['crew_size']} pessoas")
            print(f"    Status        : {sc['status']}")
            print(f"    Início missão : {format_datetime_br(sc.get('mission_start',''))}")
        else:
            display.warning("Cápsula ainda não cadastrada.")

        print()
        print("    [1] Cadastrar/atualizar cápsula")
        print("    [2] Diagnóstico de arquivos de dados")
        print("    [3] Popular com dados de exemplo (Dragon C209)")
        print("    [0] Voltar")

        opt = prompts.ask_text("  Opção", default="0")
        if opt == "0":
            return
        elif opt == "1":
            _setup_spacecraft()
        elif opt == "2":
            _show_health_check()
        elif opt == "3":
            _seed_demo_data()


def _setup_spacecraft() -> None:
    existing = sc_core.get_spacecraft()
    if existing:
        display.info("Cápsula já cadastrada. Atualizando...")
        crew = prompts.ask_int(
            "Tamanho da tripulação",
            min_value=1, default=existing["crew_size"]
        )
        status = prompts.ask_choice(
            "Status", sc_core.VALID_STATUSES, default=existing["status"]
        )
        sc_core.update_spacecraft(crew_size=crew, status=status)
        display.success("Cápsula atualizada.")
    else:
        sid = prompts.ask_text("ID da cápsula (ex.: DRAGON-C209)")
        mission = prompts.ask_text("Nome da missão (ex.: CRS-31)")
        crew = prompts.ask_int("Tamanho da tripulação", min_value=1)
        status = prompts.ask_choice(
            "Status", sc_core.VALID_STATUSES, default="in_transit"
        )
        sc_core.create_spacecraft(sid, mission, crew, status)
        display.success("Cápsula cadastrada.")
    display.pause()


def _show_health_check() -> None:
    print()
    display.section("Diagnóstico dos arquivos de dados")
    report = health_check()

    data_dir = report.pop("_data_dir", "?")
    display.info(f"Diretório: {data_dir}")
    print()

    for fname, status in report.items():
        if "OK" in status:
            display.success(f"{fname}: {status}")
        elif "CORROMPIDO" in status:
            display.error(f"{fname}: {status}")
        elif "ausente" in status:
            display.info(f"{fname}: {status}")
        else:
            display.warning(f"{fname}: {status}")
    display.pause()


def _seed_demo_data() -> None:
    if not prompts.confirm_destructive(
        "Isso vai cadastrar dados de exemplo (apaga registros existentes)."
    ):
        return
    try:
        from seed_data import seed
        seed()
        display.success("Dados de exemplo carregados.")
    except Exception as e:
        display.error(f"Falha ao carregar dados: {e}")
    display.pause()
