"""
Promptfoo custom prompt function.

Cada cenário de teste define, via vars.messages, a conversa completa
simulando um agente com ferramentas MCP (system prompt + turno do usuário +
chamada de ferramenta já "executada" + retorno da ferramenta, possivelmente
envenenado). vars.messages já chega como lista de dicts (YAML nativo, sem
JSON serializado no meio do teste, o que evitaria escaping frágil). Esta
função só valida a estrutura antes de devolver ao provider da Anthropic.
"""

VALID_ROLES = {"system", "user", "assistant"}


def get_prompt(context: dict):
    vars = context["vars"]
    messages = vars.get("messages")

    if not messages:
        raise ValueError("Cenário sem vars.messages: nada para enviar ao provider.")

    if not isinstance(messages, list):
        raise ValueError("vars.messages deve ser uma lista de mensagens.")

    for m in messages:
        if m.get("role") not in VALID_ROLES:
            raise ValueError(f"Role inválida no cenário: {m.get('role')!r}")
        if "content" not in m:
            raise ValueError("Mensagem sem campo 'content'.")

    return messages