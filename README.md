# OrbitStock : Sistema CLI de Bordo

Sistema de gestão de inventário para a Cápsula Dragon, com mecanismo de
sincronização explícita para o sistema MQTT/Edge.

Entrega da disciplina **Computational Thinking with Python**.
Global Solution 2026, FIAP Engenharia de Software.

---

## Equipe

- **Enrico Dellatorre** : RM566824
- **Gustavo Hiruo** : RM567625

---

## O que é

O OrbitStock CLI é a ferramenta Python de gestão de inventário usada em
três momentos distintos da missão:

### 1. Pré-lançamento (em terra)
Engenheiros de missão cadastram a carga completa, definem compartimentos
e limites ambientais, geram o manifesto inicial. Tudo é persistido em
JSON e seguirá com a cápsula.

### 2. Como backup de bordo durante a missão
Se o app principal (React no tablet do astronauta) falhar por qualquer
motivo, a tripulação acessa este terminal e mantém o inventário
operacional. Todas as operações ficam registradas em arquivos JSON
locais.

### 3. Sincronização com a Terra via MQTT
Quando o sistema principal volta a operar, o astronauta clica em
"Sincronizar com MQTT" e o CLI gera um **envelope MQTT** consolidado
com tudo o que aconteceu offline. O Gateway de bordo (entrega de Edge
Computing) consome esse envelope e publica cada mensagem como se nunca
tivesse havido pane. Nenhum registro precisa ser refeito manualmente.

---

## Por que essa arquitetura

A separação CLI (JSON) ↔ Gateway (MQTT) ↔ Terra (FIWARE) tem três
benefícios concretos:

1. **CLI escreve apenas JSON local**: respeita a rubrica de
   Computational Thinking (manipulação de arquivos), sem precisar
   conhecer MQTT.
2. **Gateway lida com mensageria e banco de dados**: é a stack adequada
   da disciplina de Edge Computing, que pode usar SQLite e MQTT
   diretamente.
3. **O astronauta age uma vez**: registra no CLI durante a pane, clica
   em sincronizar quando o app voltar. O sistema completo se reconcilia
   sozinho.

Cada disciplina mantém sua stack ideal sem comprometer a coerência do
produto.

---

## Como executar

Requer **Python 3.10+**. Nenhuma dependência externa (só biblioteca padrão).

```bash
cd orbitstock_cli

# (1) popule com dados de exemplo da Dragon C209
python3 seed_data.py

# (2) rode o CLI
python3 main.py
```

---

## Estrutura do projeto

```
orbitstock_cli/
├── main.py                  # entry point (loop do menu principal)
├── seed_data.py             # popula com dados realistas da Dragon C209
├── README.md
│
├── core/                    # regras de negócio (CRUD por entidade)
│   ├── storage.py           # read/write JSON com escrita atômica e backup
│   ├── spacecraft.py        # gestão da cápsula
│   ├── compartments.py      # compartimentos físicos
│   ├── items.py             # inventário (entidade principal)
│   ├── consumption.py       # histórico de consumo
│   ├── alerts.py            # geração e ACK de alertas
│   └── sync.py              # exportação MQTT para o Gateway de bordo
│
├── ui/                      # camada de apresentação
│   ├── menu.py              # telas do menu interativo
│   ├── prompts.py           # input com validação
│   └── display.py           # cores ANSI, tabelas, banners
│
├── utils/
│   └── dates.py             # manipulação de datas em UTC
│
├── data/                    # persistência local (criado em runtime)
│   ├── spacecraft.json
│   ├── compartments.json
│   ├── items.json
│   ├── consumption.json
│   ├── alerts.json
│   ├── _sync_state.json     # cutoff da última exportação
│   └── _backups/            # backups automáticos antes de cada escrita
│
└── exports/                 # envelopes MQTT exportados (criado em runtime)
    └── mqtt_envelope_YYYYMMDD_HHMMSS_<id>.json
```

---

## Formato do envelope MQTT

Quando o astronauta exporta o período offline, é gerado um arquivo JSON
com a seguinte estrutura:

```json
{
  "envelope_id": "uuid",
  "envelope_version": "1.0",
  "spacecraft_id": "DRAGON-C209",
  "mission_name": "CRS-31",
  "generated_at": "2026-05-27T03:25:51+00:00",
  "cutoff_timestamp": "2026-05-26T22:00:00+00:00",
  "message_count": 18,
  "stats": {
    "consumptions": 8,
    "alert_acks": 1,
    "item_states": 9
  },
  "messages": [
    {
      "topic": "orbitstock/DRAGON-C209/consumption",
      "payload": {
        "id": "...",
        "item_id": "H2O-082",
        "quantity_consumed": 5,
        "astronaut_id": "AST-01",
        "timestamp": "2026-05-26T23:42:00+00:00",
        "source": "cli_offline"
      },
      "qos": 1,
      "retain": false
    },
    ...
  ]
}
```

O Gateway de bordo lê esse arquivo, itera sobre `messages` e publica
cada uma usando seu próprio cliente MQTT. Mensagens com
`source: cli_offline` ficam marcadas na auditoria do FIWARE em terra.

### Tipos de mensagem geradas

| Tópico                                           | Quando                              | QoS | Retain |
| ------------------------------------------------ | ----------------------------------- | --- | ------ |
| `orbitstock/<sc_id>/consumption`                 | Para cada consumo registrado offline | 1   | false  |
| `orbitstock/<sc_id>/alerts/ack`                  | Para cada alerta confirmado offline  | 1   | false  |
| `orbitstock/<sc_id>/items/<item_id>/state`       | Snapshot final do estado de cada item | 1  | true   |

---

## Modelo de dados (JSONs locais)

### spacecraft.json (registro único)
```json
{
  "id": "DRAGON-C209",
  "mission_name": "CRS-31",
  "crew_size": 4,
  "status": "in_transit"
}
```

### items.json (lista, entidade principal)
```json
{
  "id": "INS-2026-04",
  "name": "Insulina (ampolas 10ml)",
  "compartment_id": "M-03",
  "quantity": 6,
  "quantity_initial": 12,
  "expiry_date": "2027-01-22",
  "criticality": "critical"
}
```

Demais entidades: `compartments.json`, `consumption.json`, `alerts.json`.
Detalhamento completo no código (`core/*.py`).

---

## Conceitos de Computational Thinking aplicados

| Conceito                    | Onde aparece                                        |
| --------------------------- | --------------------------------------------------- |
| Listas                      | items, compartments, alerts, consumption, messages  |
| Dicionários                 | cada entidade individual; envelope MQTT             |
| Funções                     | 70+ funções organizadas por responsabilidade        |
| Manipulação de arquivos     | `core/storage.py` (read/write JSON com escrita atômica) |
| Tratamento de exceções      | `StorageError`, `DataFileCorruptedError`, `ValueError` |
| Decomposição                | core (lógica), ui (apresentação), utils (helpers)   |
| Abstração                   | `cell()`, `colored()`, `ask_choice()`, `build_envelope()` |
| Algoritmos                  | busca, filtros, taxa de consumo, detecção de alertas, diferencial por cutoff |

---

## Casos de uso atendidos

Do documento de Software & TXD:

- **UC01** : Consultar itens do inventário
- **UC02** : Buscar item por nome/categoria/ID
- **UC03** : Registrar consumo
- **UC04** : Localizar item (compartimento físico)
- **UC05** : Receber alertas
- **UC06** : Confirmar recebimento de alertas
- **UC12** : Cadastrar carga pré-lançamento
- **UC13** : Configurar limites de alerta (via cadastro de compartimentos)
- **UC14** : Exportar relatório de missão (via sincronização MQTT)

---

## Comandos úteis

```bash
# Resetar e popular novamente
rm -rf data/ exports/ && python3 seed_data.py

# Conferir tamanho dos arquivos de dados
ls -lh data/ exports/

# Inspecionar um envelope MQTT gerado
python3 -m json.tool exports/mqtt_envelope_*.json | less
```

---

## Licença

Projeto acadêmico desenvolvido para a Global Solution 2026 da FIAP.
Sem fins comerciais.
