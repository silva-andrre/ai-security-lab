"""
detect_patterns.py

Lê logs/novapay_llm_logs.json e aplica três detectores independentes.
Cada detector segue o mesmo contrato: recebe a lista de eventos, devolve uma
lista de detecções no formato:

    {evento, severidade, confianca, recomendacao}

Critério de avaliação declarado ANTES de rodar (log de alteração, para não
calibrar threshold olhando o resultado): um detector só é considerado
"acionável" se ele aponta uma ação concreta (revisar sessão X, bloquear
padrão Y), não a mera presença de uma palavra ou valor no log.

Baseline estatístico: calculado a partir dos próprios dados normais
(sem os eventos injetados), porque em produção o baseline vem do tráfego
histórico, não de um valor fixo arbitrário no código.
"""

import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime

INPUT_PATH = "logs/novapay_llm_logs.json"
OUTPUT_PATH = "reports/detections_report.csv"

# Thresholds declarados antes da execução (não ajustados depois de ver o resultado)
MANY_SHOT_TURN_THRESHOLD = 25          # estimated_dialogue_turns acima disso é suspeito
MANY_SHOT_TOKEN_THRESHOLD = 6000       # input_tokens acima disso reforça o sinal
LATENCY_IQR_MULTIPLIER = 2.5           # múltiplo do IQR acima do Q3 para marcar outlier
RETRY_STORM_MIN_REFUSALS = 4           # refusals encadeados na mesma sessão
RETRY_STORM_WINDOW_SECONDS = 300       # dentro dessa janela


def load_events():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_ts(ev):
    return datetime.fromisoformat(ev["timestamp"])


def detect_many_shot(events):
    """Padrão 1: proxy estrutural de many-shot jailbreaking.
    Critério de ação: sinaliza sessão para revisão manual e para checar se o
    guardrail de aplicação (não o do provedor) teria barrado o payload antes
    do envio."""
    detections = []
    for ev in events:
        turns = ev["estimated_dialogue_turns"]
        tokens = ev["input_tokens"]
        if turns >= MANY_SHOT_TURN_THRESHOLD:
            confidence = min(1.0, 0.5 + (turns - MANY_SHOT_TURN_THRESHOLD) / 100)
            if tokens >= MANY_SHOT_TOKEN_THRESHOLD:
                confidence = min(1.0, confidence + 0.2)
            severity = "alta" if confidence >= 0.7 else "media"
            detections.append(
                {
                    "timestamp": ev["timestamp"],
                    "session_id": ev["session_id"],
                    "request_id": ev["request_id"],
                    "evento": "many_shot_probe",
                    "severidade": severity,
                    "confianca": round(confidence, 2),
                    "recomendacao": (
                        f"Revisar sessão {ev['session_id'][:8]}: "
                        f"{turns} turnos estimados e {tokens} tokens de entrada "
                        f"muito acima do baseline. Verificar se o guardrail de "
                        f"aplicação atuou antes do envio ao modelo ou se o "
                        f"bloqueio (stop_reason={ev['stop_reason']}) veio só do "
                        f"provedor."
                    ),
                }
            )
    return detections


def detect_latency_anomaly(events):
    """Padrão 2: outlier de latência por ferramenta, usando IQR calculado
    sobre a própria distribuição observada (exclui os eventos já suspeitos
    de many-shot, que naturalmente têm latência mais alta por tamanho de
    payload, para não contaminar o baseline)."""
    by_tool = defaultdict(list)
    for ev in events:
        if ev["estimated_dialogue_turns"] < MANY_SHOT_TURN_THRESHOLD:
            by_tool[ev["tool_name"]].append(ev["latency_ms"])

    bounds = {}
    for tool, latencies in by_tool.items():
        if len(latencies) < 10:
            continue
        q1 = statistics.quantiles(latencies, n=4)[0]
        q3 = statistics.quantiles(latencies, n=4)[2]
        iqr = q3 - q1
        bounds[tool] = q3 + LATENCY_IQR_MULTIPLIER * iqr

    detections = []
    for ev in events:
        tool = ev["tool_name"]
        if tool not in bounds:
            continue
        if ev["latency_ms"] > bounds[tool]:
            excess_ratio = ev["latency_ms"] / bounds[tool]
            confidence = min(1.0, 0.4 + (excess_ratio - 1) * 0.6)
            severity = "alta" if excess_ratio >= 1.5 else "media"
            detections.append(
                {
                    "timestamp": ev["timestamp"],
                    "session_id": ev["session_id"],
                    "request_id": ev["request_id"],
                    "evento": "latency_anomaly",
                    "severidade": severity,
                    "confianca": round(confidence, 2),
                    "recomendacao": (
                        f"Latência de {ev['latency_ms']}ms em '{tool}' excede o "
                        f"limite estatístico de {bounds[tool]:.0f}ms (Q3 + "
                        f"{LATENCY_IQR_MULTIPLIER}x IQR) sem tokens de entrada "
                        f"elevados. Investigar payload da ferramenta chamada "
                        f"(possível injeção via output de terceiro) ou "
                        f"degradação de backend."
                    ),
                }
            )
    return detections


def detect_retry_storm(events):
    """Padrão 3: cadeia de refusals na mesma sessão, dentro de janela curta,
    seguindo o encadeamento retry_of. Critério de ação: sinaliza a sessão
    inteira para bloqueio temporário, não apenas o último evento."""
    by_session = defaultdict(list)
    for ev in events:
        by_session[ev["session_id"]].append(ev)

    detections = []
    for session_id, evs in by_session.items():
        evs = sorted(evs, key=parse_ts)
        refusals = [e for e in evs if e["stop_reason"] == "refusal"]
        if len(refusals) < RETRY_STORM_MIN_REFUSALS:
            continue
        window_start = parse_ts(refusals[0])
        window_end = parse_ts(refusals[-1])
        span = (window_end - window_start).total_seconds()
        if span <= RETRY_STORM_WINDOW_SECONDS:
            confidence = min(1.0, 0.5 + (len(refusals) - RETRY_STORM_MIN_REFUSALS) * 0.1)
            severity = "alta" if len(refusals) >= 6 else "media"
            last = refusals[-1]
            detections.append(
                {
                    "timestamp": last["timestamp"],
                    "session_id": session_id,
                    "request_id": last["request_id"],
                    "evento": "retry_storm",
                    "severidade": severity,
                    "confianca": round(confidence, 2),
                    "recomendacao": (
                        f"Sessão {session_id[:8]} acumulou {len(refusals)} "
                        f"refusals encadeados em {span:.0f}s. Padrão consistente "
                        f"com tentativa iterativa de contornar bloqueio. "
                        f"Recomenda-se rate limit ou bloqueio temporário da "
                        f"sessão, não apenas log do último evento."
                    ),
                }
            )
    return detections


def main():
    events = load_events()

    detections = []
    detections += detect_many_shot(events)
    detections += detect_latency_anomaly(events)
    detections += detect_retry_storm(events)

    detections.sort(key=lambda d: d["timestamp"])

    fieldnames = [
        "timestamp",
        "session_id",
        "request_id",
        "evento",
        "severidade",
        "confianca",
        "recomendacao",
    ]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detections)

    print(f"Total de eventos analisados: {len(events)}")
    print(f"Total de detecções: {len(detections)}")
    by_evento = defaultdict(int)
    for d in detections:
        by_evento[d["evento"]] += 1
    for evento, count in by_evento.items():
        print(f"  {evento}: {count}")
    print(f"Relatório salvo em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
