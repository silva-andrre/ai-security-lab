"""
generate_logs.py

Gera logs simulados de um agente de suporte via LLM da NovaPay (alvo controlado
usado nos exercícios da Fase 3). O objetivo não é simular conteúdo de prompt
(isso levantaria questão de privacidade em log real de produção), mas simular
os METADADOS que uma arquitetura de logging bem desenhada capturaria sem
armazenar o conteúdo da conversa.

Campos logados e a razão de cada um:

- timestamp: obrigatório para qualquer análise de série temporal.
- session_id: correlaciona eventos do mesmo usuário/sessão sem expor identidade.
- request_id: chave única do evento; permite encadear retries.
- retry_of: aponta para o request_id anterior na mesma sessão, quando aplicável.
  Sem isso, uma sequência de tentativas fica invisível como padrão.
- tool_name: qual ferramenta/endpoint foi chamado (chat, busca de pedido,
  reembolso, busca em base de conhecimento). Ferramentas com efeito colateral
  (reembolso) merecem atenção maior que leitura.
- input_tokens / output_tokens: proxy de tamanho do payload sem guardar o texto.
- estimated_dialogue_turns: contagem de marcadores de troca de papel
  (ex.: "user:", "assistant:") detectada pela camada de aplicação ANTES de
  enviar o prompt ao modelo. É a métrica estrutural que usamos como proxy de
  many-shot jailbreaking (Anexo Anthropic, 2024) sem depender do conteúdo.
- latency_ms: tempo de resposta. Anomalia de latência pode indicar payload
  adversarial grande ou abuso de contexto.
- stop_reason: valor cru retornado pela API (end_turn, tool_use, refusal,
  max_tokens). Esse campo é o que, nas semanas 6 e 9, revelou a diferença
  entre bloqueio de guardrail da aplicação e bloqueio do provedor do modelo.
- http_status: status da chamada.

O que foi deliberadamente DESCARTADO do schema, e por quê:
- Texto do prompt ou da resposta: risco de dado sensível de cliente
  (PII financeiro) em log de fintech regulada. estimated_dialogue_turns e
  input_tokens cobrem o sinal necessário para detecção sem esse risco.
- IP bruto do usuário: descartado do exercício por simplicidade; em produção
  entraria hasheado, não em texto claro.
"""

import json
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

TOOLS = ["chat_completion", "order_lookup", "kb_search", "refund_initiate"]
STOP_REASONS_NORMAL = ["end_turn", "tool_use"]

# Ruído adicionado nesta rodada, para testar os detectores fora do cenário
# limpo da primeira versão. Documentado aqui, não escondido no meio do código,
# porque muda a interpretação do resultado.
LEGIT_REFUSAL_RATE = 0.07   # fração de eventos normais que são refusal legítimo
                            # (usuário pediu algo fora do escopo do agente,
                            # ex.: aconselhamento financeiro que o bot não pode dar)
LATENCY_TAIL_RATE = 0.05    # fração de eventos normais com latência de cauda
                            # gorda (lentidão real de backend, sem ataque)

START = datetime(2026, 8, 17, 8, 0, 0)


def new_request_id():
    return str(uuid.uuid4())


def normal_event(ts, session_id, tool_name):
    if random.random() < LEGIT_REFUSAL_RATE:
        stop_reason = "refusal"
    else:
        stop_reason = random.choice(STOP_REASONS_NORMAL)

    if random.random() < LATENCY_TAIL_RATE:
        latency = max(120, int(random.gauss(2400, 900)))
    else:
        latency = max(120, int(random.gauss(650, 140)))

    return {
        "timestamp": ts.isoformat(),
        "session_id": session_id,
        "request_id": new_request_id(),
        "retry_of": None,
        "tool_name": tool_name,
        "input_tokens": random.randint(80, 600),
        "output_tokens": random.randint(40, 400),
        "estimated_dialogue_turns": random.randint(1, 4),
        "latency_ms": latency,
        "stop_reason": stop_reason,
        "http_status": 200,
    }


def build_normal_traffic(n_sessions=360):
    events = []
    t = START
    for _ in range(n_sessions):
        session_id = str(uuid.uuid4())
        n_events = random.randint(1, 3)
        for _ in range(n_events):
            t += timedelta(seconds=random.randint(30, 900))
            tool = random.choices(TOOLS, weights=[0.55, 0.2, 0.15, 0.10])[0]
            events.append(normal_event(t, session_id, tool))
    return events, t


def inject_legit_confused_sessions(t, n=15):
    """Sessões de usuário genuinamente frustrado: pergunta algo fora do
    escopo do agente (ex.: 'me dá uma recomendação de investimento'), recebe
    refusal, reformula, recebe refusal de novo, 3 a 5 vezes seguidas, dentro
    de uma janela curta. Nenhuma intenção de ataque, é fricção real de
    produto. Este é o teste honesto: será que retry_storm consegue separar
    isso de um jailbreak sendo iterado?"""
    events = []
    for _ in range(n):
        session_id = str(uuid.uuid4())
        n_refusals = random.randint(3, 5)
        session_t = t
        for i in range(n_refusals):
            session_t += timedelta(seconds=random.randint(15, 60))
            events.append(
                {
                    "timestamp": session_t.isoformat(),
                    "session_id": session_id,
                    "request_id": new_request_id(),
                    "retry_of": None,
                    "tool_name": "chat_completion",
                    "input_tokens": random.randint(100, 400),
                    "output_tokens": random.randint(20, 80),
                    "estimated_dialogue_turns": random.randint(1, 3),
                    "latency_ms": max(120, int(random.gauss(650, 140))),
                    "stop_reason": "refusal",
                    "http_status": 200,
                }
            )
        t = session_t + timedelta(minutes=random.randint(2, 20))
    return events, t


def inject_many_shot_probe(t):
    """Padrão 1: um único request com contagem estrutural de turnos muito acima
    do baseline (proxy de many-shot jailbreaking), tokens de entrada elevados,
    sem retries. Um evento isolado, difícil de pegar por volume, fácil de
    pegar por estrutura."""
    session_id = str(uuid.uuid4())
    ev = {
        "timestamp": t.isoformat(),
        "session_id": session_id,
        "request_id": new_request_id(),
        "retry_of": None,
        "tool_name": "chat_completion",
        "input_tokens": random.randint(9000, 15000),
        "output_tokens": random.randint(30, 90),
        "estimated_dialogue_turns": random.randint(48, 90),
        "latency_ms": random.randint(2200, 3400),
        "stop_reason": "refusal",
        "http_status": 200,
    }
    return [ev]


def inject_latency_anomaly(t):
    """Padrão 2: latência muito acima do baseline da própria ferramenta,
    sem explicação por tamanho de payload (input/output normais). Simula
    contexto inflado por outros meios (ex.: injeção via tool output) ou
    degradação de backend explorada para reconhecimento de timing."""
    session_id = str(uuid.uuid4())
    events = []
    for i in range(3):
        ts = t + timedelta(seconds=i * 20)
        events.append(
            {
                "timestamp": ts.isoformat(),
                "session_id": session_id,
                "request_id": new_request_id(),
                "retry_of": None,
                "tool_name": "kb_search",
                "input_tokens": random.randint(100, 300),
                "output_tokens": random.randint(50, 150),
                "estimated_dialogue_turns": random.randint(1, 3),
                "latency_ms": random.randint(4800, 7200),
                "stop_reason": "tool_use",
                "http_status": 200,
            }
        )
    return events


def inject_retry_storm(t):
    """Padrão 3: sequência de refusals encadeados via retry_of na mesma
    sessão, em janela curta. Comportamento típico de quem está iterando
    variações de jailbreak até um passar."""
    session_id = str(uuid.uuid4())
    events = []
    prev_id = None
    for i in range(6):
        ts = t + timedelta(seconds=i * 25)
        req_id = new_request_id()
        events.append(
            {
                "timestamp": ts.isoformat(),
                "session_id": session_id,
                "request_id": req_id,
                "retry_of": prev_id,
                "tool_name": "chat_completion",
                "input_tokens": random.randint(300, 700),
                "output_tokens": random.randint(20, 60),
                "estimated_dialogue_turns": random.randint(1, 5),
                "latency_ms": random.randint(400, 900),
                "stop_reason": "refusal",
                "http_status": 200,
            }
        )
        prev_id = req_id
    return events


def main():
    events, t = build_normal_traffic()

    t += timedelta(minutes=3)
    legit_events, t = inject_legit_confused_sessions(t)
    events += legit_events

    t += timedelta(minutes=5)
    events += inject_many_shot_probe(t)

    t += timedelta(minutes=12)
    events += inject_latency_anomaly(t)

    t += timedelta(minutes=8)
    events += inject_retry_storm(t)

    events.sort(key=lambda e: e["timestamp"])

    out_path = "logs/novapay_llm_logs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"{len(events)} eventos gerados em {out_path}")
    print(f"Ruído: {LEGIT_REFUSAL_RATE*100:.0f}% de refusal legítimo em tráfego normal, "
          f"{LATENCY_TAIL_RATE*100:.0f}% de latência de cauda gorda legítima, "
          f"{len(legit_events)} eventos em {15} sessões de usuário frustrado (3-5 refusals cada)")
    print("Padrões de ataque injetados: 1 many-shot probe, 1 latency anomaly (3 eventos), 1 retry storm (6 eventos)")


if __name__ == "__main__":
    main()
