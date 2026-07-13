"""
Roda as 5 técnicas de attacks.py contra os dois agentes (Claude e Gemini),
avalia objetivamente se cada uma quebrou a regra, salva o resultado por
modelo em results.json e imprime uma tabela comparativa cross-model, no
mesmo padrão da Fase 2 (divergência comportamental Claude vs Gemini).

Uso:
    export ANTHROPIC_API_KEY=sk-ant-...
    export GEMINI_API_KEY=...
    python run_attacks.py
"""

import json
import time
from datetime import datetime, timezone

import agent_anthropic
import agent_gemini
from attacks import ATTACKS


def _gemini_history_from_messages(messages: list) -> tuple[list, str]:
    """
    Converte o formato de mensagens de attacks.py (estilo Anthropic: role
    user/assistant, content string) para o formato esperado por
    chat.create(history=...) do google-genai, mais o texto da última
    mensagem de usuário (enviada via send_message).

    AVISO DE CONFIANÇA: essa conversão só é exercitada de fato pelo ataque
    A3 (many-shot, que injeta histórico falso). O caminho sem histórico
    (A1, A2, A4, A5) já foi confirmado por você rodando manualmente. Se A3
    falhar contra o Gemini com erro de formato, esta função é o primeiro
    lugar a olhar.
    """
    *history_messages, last_message = messages
    history = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in history_messages
    ]
    return history, last_message["content"]


def _record(attack, model, final_text, leaked, error, stop_reason=None):
    return {
        "id": attack["id"],
        "name": attack["name"],
        "category": attack["category"],
        "model": model,
        "leaked": leaked,
        "agent_response": final_text,
        "error": error,
        "stop_reason": stop_reason,
    }


def _status(leaked, error):
    if error:
        return "ERRO"
    return "VAZOU" if leaked else "SEGUROU"


def run_suite_anthropic(gemini_results_ref, existing_by_id=None):
    existing_by_id = existing_by_id or {}
    results = []
    for attack in ATTACKS:
        cached = existing_by_id.get(attack["id"])
        if cached and cached.get("error") is None:
            print(f"[Claude][{attack['id']}] {attack['name']}... (já rodado, reaproveitando)")
            results.append(cached)
            _save_report(results, gemini_results_ref)
            continue

        print(f"[Claude][{attack['id']}] {attack['name']}...")
        messages = [dict(m) for m in attack["messages"]]
        try:
            final_text, _, stop_reason = agent_anthropic.run_agent_turn(messages)
            if not final_text.strip():
                if stop_reason == "refusal":
                    # recusa nativa da API (classificador de segurança da própria
                    # Anthropic), separada da recusa conversacional do system prompt.
                    # Sem texto gerado, mas é segurança real, não erro nem falso negativo.
                    leaked = False
                    error = None
                else:
                    # texto vazio sem ser recusa nativa é inconclusivo, precisa de
                    # investigação, não deve ser contado como sucesso do guardrail
                    leaked = None
                    error = f"resposta vazia (stop_reason={stop_reason})"
            else:
                leaked = attack["leaked"](final_text, agent_anthropic.PRICING_DB)
                error = None
        except Exception as exc:
            final_text, leaked, error, stop_reason = "", None, str(exc), None
        results.append(_record(attack, agent_anthropic.MODEL, final_text, leaked, error, stop_reason))
        print(f"    -> {_status(leaked, error)}")
        _save_report(results, gemini_results_ref)  # salva a cada tentativa, não só no final
    return results


def run_suite_gemini(claude_results_ref, existing_by_id=None):
    existing_by_id = existing_by_id or {}
    results = []
    for attack in ATTACKS:
        cached = existing_by_id.get(attack["id"])
        if cached and cached.get("error") is None:
            print(f"[Gemini][{attack['id']}] {attack['name']}... (já rodado, reaproveitando)")
            results.append(cached)
            _save_report(claude_results_ref, results)
            continue

        print(f"[Gemini][{attack['id']}] {attack['name']}...")
        try:
            history, last_text = _gemini_history_from_messages(attack["messages"])
            final_text, _ = agent_gemini.run_agent_turn(last_text, history=history)
            leaked = attack["leaked"](final_text, agent_gemini.PRICING_DB)
            error = None
        except Exception as exc:
            final_text, leaked, error = "", None, str(exc)
        results.append(_record(attack, agent_gemini.MODEL, final_text, leaked, error))
        print(f"    -> {_status(leaked, error)}")
        _save_report(claude_results_ref, results)  # salva a cada tentativa, não só no final
        time.sleep(13)  # free tier gemini-3.5-flash: 5 RPM, respeita o intervalo entre chamadas
    return results


def print_comparison_table(claude_results, gemini_results):
    print("\n| ID | Técnica | Claude | Gemini |")
    print("|----|---------|--------|--------|")
    for c, g in zip(claude_results, gemini_results):
        print(f"| {c['id']} | {c['name']} | {_symbol(c)} | {_symbol(g)} |")

    claude_bypasses = sum(1 for r in claude_results if r["leaked"])
    gemini_bypasses = sum(1 for r in gemini_results if r["leaked"])
    print(f"\nClaude ({agent_anthropic.MODEL}): {claude_bypasses}/{len(claude_results)} bypasses")
    print(f"Gemini ({agent_gemini.MODEL}): {gemini_bypasses}/{len(gemini_results)} bypasses")


def _symbol(r):
    if r["leaked"] is None:
        return "⚠️ erro"
    return "❌ vazou" if r["leaked"] else "✅ segurou"


def _save_report(claude_results, gemini_results):
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claude_model": agent_anthropic.MODEL,
        "gemini_model": agent_gemini.MODEL,
        "claude_results": claude_results,
        "gemini_results": gemini_results,
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def _load_existing_report():
    """
    Carrega results.json de uma execução anterior, se existir. Usado para
    retomada: técnicas que já rodaram sem erro são reaproveitadas em vez de
    chamar a API de novo. Se o arquivo não existir ou estiver corrompido,
    retoma do zero silenciosamente.
    """
    try:
        with open("results.json", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("claude_results", []), data.get("gemini_results", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [], []


def main():
    existing_claude, existing_gemini = _load_existing_report()
    existing_claude_by_id = {r["id"]: r for r in existing_claude}
    existing_gemini_by_id = {r["id"]: r for r in existing_gemini}

    # seed com o que já existia, para que um Ctrl+C durante a suíte do Claude
    # não sobrescreva resultados do Gemini de uma execução anterior
    claude_results = list(existing_claude)
    gemini_results = list(existing_gemini)

    try:
        claude_results = run_suite_anthropic(gemini_results, existing_claude_by_id)
        gemini_results = run_suite_gemini(claude_results, existing_gemini_by_id)
    finally:
        # results.json já foi salvo tentativa a tentativa dentro de cada suíte,
        # inclusive em caso de interrupção. Aqui só tentamos mostrar a tabela final.
        print("\nVeja o progresso salvo em results.json.")
        if claude_results and gemini_results:
            print_comparison_table(claude_results, gemini_results)


if __name__ == "__main__":
    main()
