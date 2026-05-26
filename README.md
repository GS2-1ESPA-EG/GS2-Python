# OrbitStock — Sistema CLI de Bordo

Sistema de backup offline para gestão de inventário da Cápsula Dragon.
Entrega da disciplina **Computational Thinking with Python** —
Global Solution 2026, FIAP Engenharia de Software (1º ano).

---

## Equipe

- **Enrico Dellatorre** — RM566824
- **Gustavo Hiruo** — RM567625

---

## O que é?

O OrbitStock CLI é o sistema **de backup offline** que roda dentro da
Cápsula Dragon. Se o app principal (React no tablet) falhar por queda de
energia, problema de software ou perda do dispositivo, a tripulação ainda
pode operar o inventário inteiro através deste programa Python rodando
diretamente em terminal.

Ele cobre os principais casos de uso definidos no documento de Software & TXD:

- **UC01** — Consultar itens do inventário
- **UC02** — Buscar item por nome/categoria/ID
- **UC03** — Registrar consumo
- **UC04** — Localizar item (compartimento físico)
- **UC05** — Receber alertas
- **UC06** — Confirmar recebimento de alertas

Mais funcionalidades de gestão (compartimentos, estatísticas, manutenção).

---

## Como executar

Requer **Python 3.10+** (usa `type | None` e f-strings modernas).
Nenhuma dependência externa — só biblioteca padrão.

```bash
# 1. Entre na pasta
cd orbitstock_cli

# 2. (Recomendado) Popule com dados de exemplo da Dragon C209
python3 seed_data.py

# 3. Rode o CLI
python3 main.py
```

---

## Estrutura do projeto

```
orbitstock_cli/
├── main.py                  # Entry point — loop do menu principal
├── seed_data.py             # Popula com dados realistas da Dragon C209
├── README.md                # Este arquivo
│
├── core/                    # Regras de negócio (CRUD por entidade)
│   ├── storage.py           # Read/write JSON, exceções, backup automático
│   ├── spacecraft.py        # Gestão da cápsula
│   ├── compartments.py      # Compartimentos físicos
│   ├── items.py             # Inventário (entidade principal)
│   ├── consumption.py       # Histórico de consumo
│   └── alerts.py            # Geração e ACK de alertas
│
├── ui/                      # Camada de apresentação
│   ├── menu.py              # Telas do menu interativo
│   ├── prompts.py           # Input com validação
│   └── display.py           # Cores ANSI, tabelas, banners
│
├── utils/                   # Utilitários
│   └── dates.py             # Manipulação de datas em UTC
│
└── data/                    # Persistência (criado em runtime)
    ├── spacecraft.json
    ├── compartments.json
    ├── items.json
    ├── consumption.json
    ├── alerts.json
    └── _backups/            # Backups automáticos antes de cada escrita
```

---

## Modelo de dados

### Spacecraft (registro único)
```json
{
  "id": "DRAGON-C209",
  "mission_name": "CRS-31",
  "mission_start": "2026-05-26T14:00:00+00:00",
  "crew_size": 4,
  "status": "in_transit"
}
```

### Compartment (lista)
```json
{
  "id": "M-03",
  "name": "Médico refrigerado",
  "category": "medical",
  "temp_min": 2, "temp_max": 8,
  "humidity_max": 60,
  "current_temp": 12.5,
  "current_humidity": 52,
  "last_reading_at": "2026-05-26T22:14:00+00:00"
}
```

### Item (lista — a maior estrutura)
```json
{
  "id": "INS-2026-04",
  "name": "Insulina (ampolas 10ml)",
  "category": "medical",
  "compartment_id": "M-03",
  "quantity": 6,
  "quantity_initial": 12,
  "unit": "ampolas",
  "expiry_date": "2027-01-22",
  "criticality": "critical",
  "requires_refrigeration": true,
  "lot_number": "INS-2026-04"
}
```

### ConsumptionRecord (lista, imutável)
```json
{
  "id": "abc123def456",
  "item_id": "H2O-082",
  "item_name": "Água potável",
  "quantity_consumed": 16,
  "unit": "unidades",
  "astronaut_id": "AST-01",
  "notes": "Consumo dia 1",
  "timestamp": "2026-05-26T18:42:00+00:00"
}
```

### Alert (lista)
```json
{
  "id": "xyz789ghi012",
  "type": "env_anomaly",
  "severity": "critical",
  "message": "Compartimento M-03: 12.5°C fora da faixa (2-8°C).",
  "item_id": null,
  "compartment_id": "M-03",
  "created_at": "2026-05-26T22:14:00+00:00",
  "acknowledged": false,
  "acknowledged_at": null,
  "acknowledged_by": null
}
```

---

## Conceitos de Computational Thinking aplicados

A disciplina pede uso explícito de listas, dicionários, funções, arquivos
e tratamento de exceções. Veja onde cada um está:

| Conceito                  | Onde aparece                                       |
| ------------------------- | -------------------------------------------------- |
| **Listas**                | items, compartments, alerts, consumption — todas  |
| **Dicionários**           | cada entidade individual (item, alerta, etc.)     |
| **Funções**               | dezenas, separadas por responsabilidade (core/, ui/) |
| **Manipulação de arquivos** | core/storage.py — JSON com escrita atômica e backup |
| **Tratamento de exceções** | StorageError, DataFileCorruptedError, ValueError   |
| **Decomposição**          | core/ vs ui/ vs utils/ — separação clara de camadas |
| **Abstração**             | helpers como `cell()`, `colored()`, `ask_choice()` |
| **Reconhecimento de padrões** | mesmo padrão CRUD aplicado a 5 entidades       |
| **Algoritmos**            | busca, filtros, regressão simples em consumption.py |

---

## Tipos de alerta gerados automaticamente

O método `alerts.generate_automatic_alerts()` é executado toda vez que o
menu de Alertas é aberto. Ele detecta as seguintes condições e gera
alertas para cada uma (sem duplicar alertas já ativos):

| Tipo            | Severidade  | Condição                                  |
| --------------- | ----------- | ----------------------------------------- |
| `expired`       | critical    | Item com `expiry_date` no passado         |
| `expiry_soon`   | warning/critical | Vence em até 30 dias (crítico se ≤ 7) |
| `low_stock`     | warning/critical | Estoque ≤ 30% do inicial (crítico ≤ 15%) |
| `env_anomaly`   | critical    | Compartimento fora da faixa de temperatura |

---

## Integração com o sistema OrbitStock completo

Este CLI **não é uma aplicação isolada**. Ele é uma das camadas do
produto OrbitStock, conforme descrito no documento de Software & TXD:

- **Em produção**: o ESP32 publicaria leituras via MQTT, e este CLI seria
  apenas o "modo manual" para quando a tripulação precisa intervir sem
  o app principal.
- **A estrutura JSON** dos arquivos `data/*.json` é compatível com o formato
  NGSI-LD usado pelo FIWARE Orion na entrega de Edge Computing — basta
  envelopar com o cabeçalho do contexto NGSI.
- **O Dashboard React** (entrega de Web Development) poderia consumir
  diretamente esses mesmos arquivos JSON em modo demo, simulando o backend.

---

## Comandos úteis

```bash
# Resetar tudo e popular novamente
rm -rf data/ && python3 seed_data.py

# Ver tamanho dos arquivos de dados
ls -lh data/

# Conferir integridade JSON manualmente
python3 -c "import json; json.load(open('data/items.json'))"
```

---

## Licença / uso acadêmico

Projeto acadêmico desenvolvido para a Global Solution 2026 da FIAP.
Não tem fins comerciais. Inspirado em sistemas reais da NASA (REID, ISS IMS)
e na arquitetura de carga da SpaceX Dragon.
