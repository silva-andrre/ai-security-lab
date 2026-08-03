# ai-security-lab

> **English** | [Português abaixo](#português)

---

## English

### What is this repository

Applied AI Security research: test suites that run against live model APIs,
attacks executed in controlled environments, and findings documented with the
evidence that produced them.

Every claim here is grounded in an execution that can be reproduced from this
repository. Nothing is asserted beyond what was tested.

### Selected findings

**Validator precision determines the score before application security does.**
The same target application, with no change to its defenses, produced three
different conformance rates across three runs, depending only on how the
assertions were written. Two of those runs reported identical percentages while
disagreeing on the classification of two out of three cases.
`phase-3-portfolio/llm-scanner-week9`

**A jailbreak repertoire was contained; a plain sentence was not.** Eight test
cases using techniques catalogued under MITRE ATLAS `AML.T0054`, including
instruction override, persona switching, encoding obfuscation and constrained
output formats, were all contained. The two cases that obtained partial
disclosure of personal data used no evasion technique at all. They stated an
unverified claim of account ownership.
`phase-3-portfolio/llm-scanner-week9`

**Platform-level classifier blocks are not application defenses.** A response
returning empty with `stop_reason: refusal` is a distinct outcome from a
conversational refusal. Harnesses that only check for the absence of the
protected string count it as a pass, producing a false reading of control
coverage.
`phase-2-tools-and-attack/mcp-security-week8`

**Identical robustness scores do not imply identical audit log quality.** Two
models produced the same bypass rate across ten prompt injection techniques,
while differing in whether their refusals named the manipulation attempted.
Generic refusal logs do not support incident reconstruction.
`phase-2-tools-and-attack/promptfoo_injections`

**A security validator can itself be a supply chain risk.** A jailbreak
detection validator failed to install due to a malformed configuration in the
upstream model artifact, documented as a finding rather than worked around.
`phase-2-tools-and-attack/guardrails`

### Index

| Week | Topic | Folder |
|---|---|---|
| 2 | LLM prompt injection test, ten prompts against the Anthropic API | `phase-1-fundamentals/llm-security-lab` |
| 3 | System prompt extraction | `phase-1-fundamentals/sys-prom-extrac` |
| 4 | Promptfoo prompt evaluation | `phase-1-fundamentals/promptfoo` |
| 6 | Prompt injection across two models, log quality analysis | `phase-2-tools-and-attack/promptfoo_injections` |
| 7 | Guardrails AI, input and output validation | `phase-2-tools-and-attack/guardrails/guardrails-week7` |
| 8 | MCP security, five agentic attack classes | `phase-2-tools-and-attack/mcp-security-week8` |
| 9 | LLM Security Scanner v1, LLM01 / LLM02 / LLM07 | `phase-3-portfolio/llm-scanner-week9` |

Weeks 1 and 5 have no folder. Week 1 was environment setup and week 5 produced
written analysis rather than a new exercise.

Folder naming from week 8 onward follows `<topic>-week<N>`. Earlier folders
predate that convention and are kept unchanged, because published references
point to those paths.

### Structure

```
ai-security-lab/
├── phase-1-fundamentals/       # OWASP LLM Top 10 · Anthropic API · prompt injection basics
├── phase-2-tools-and-attack/   # Promptfoo · Guardrails AI · jailbreak testing · MCP Security
├── phase-3-portfolio/          # LLM Security Scanner · multi-tool agent · log analysis
└── phase-4-playbooks/          # Incident response · AI governance
```

### Coverage

| Area | Status |
|---|---|
| OWASP LLM Top 10 | Done |
| Anthropic API (Python SDK) | Done |
| Promptfoo test suites | Done |
| Guardrails AI | Done |
| MCP Security | Done |
| MITRE ATLAS mapping | Done, validated against primary source |
| LLM Security Scanner (v1) | In progress, 3 of 10 categories |
| LiteLLM / AI Gateway | Planned |
| Log analysis and automated evaluation | Planned |

### Tech stack

- Python · Anthropic SDK · Gemini API
- Promptfoo · Guardrails AI · LiteLLM
- Git · WSL2 (Ubuntu) · VSCode

### References

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATLAS](https://atlas.mitre.org)
- [NIST AI RMF](https://airc.nist.gov/RMF)
- [Simon Willison on Prompt Injection](https://simonwillison.net)
- [LLM Security](https://llmsecurity.net)

---

## Português

### O que é este repositório

Pesquisa aplicada em AI Security: suites de teste que rodam contra APIs de modelo
em produção, ataques executados em ambiente controlado e achados documentados com
a evidência que os produziu.

Toda afirmação aqui está ancorada em uma execução reproduzível a partir deste
repositório. Nada é afirmado além do que foi testado.

### Achados selecionados

**A precisão do validador determina o placar antes da segurança da aplicação.**
A mesma aplicação alvo, sem nenhuma alteração de defesa, produziu três taxas de
conformidade diferentes em três execuções, variando apenas a forma como as
asserções foram escritas. Duas dessas execuções reportaram percentuais idênticos
discordando na classificação de dois casos em três.
`phase-3-portfolio/llm-scanner-week9`

**Um repertório de jailbreak foi contido; uma frase simples não foi.** Oito casos
de teste usando técnicas catalogadas no MITRE ATLAS `AML.T0054`, incluindo
*instruction override*, troca de persona, obfuscação por *encoding* e formato de
saída restrito, foram todos contidos. Os dois casos que obtiveram divulgação
parcial de dado pessoal não usaram técnica de evasão alguma. Usaram uma alegação
não verificada de titularidade da conta.
`phase-3-portfolio/llm-scanner-week9`

**Bloqueio de classificador de plataforma não é defesa da aplicação.** Uma
resposta vazia com `stop_reason: refusal` é um desfecho distinto de recusa
conversacional. Harnesses que apenas verificam ausência da string protegida
contam isso como aprovação e produzem leitura falsa de cobertura de controle.
`phase-2-tools-and-attack/mcp-security-week8`

**Placares idênticos de robustez não implicam qualidade idêntica de log.** Dois
modelos produziram a mesma taxa de bypass em dez técnicas de prompt injection,
diferindo em nomear ou não a manipulação tentada nas recusas. Log de recusa
genérica não sustenta reconstrução de incidente.
`phase-2-tools-and-attack/promptfoo_injections`

**Um validador de segurança pode ser, ele próprio, risco de cadeia de
suprimentos.** Um validador de detecção de jailbreak falhou na instalação por
configuração malformada no artefato de modelo upstream, documentado como achado
em vez de contornado.
`phase-2-tools-and-attack/guardrails`

### Índice

| Semana | Tema | Pasta |
|---|---|---|
| 2 | LLM Prompt Injection Test, dez prompts contra a API Anthropic | `phase-1-fundamentals/llm-security-lab` |
| 3 | System Prompt Extraction | `phase-1-fundamentals/sys-prom-extrac` |
| 4 | Avaliação de prompts com Promptfoo | `phase-1-fundamentals/promptfoo` |
| 6 | Prompt injection em dois modelos, análise de qualidade de log | `phase-2-tools-and-attack/promptfoo_injections` |
| 7 | Guardrails AI, validação de entrada e saída | `phase-2-tools-and-attack/guardrails/guardrails-week7` |
| 8 | MCP security, cinco classes de ataque agêntico | `phase-2-tools-and-attack/mcp-security-week8` |
| 9 | LLM Security Scanner v1, LLM01 / LLM02 / LLM07 | `phase-3-portfolio/llm-scanner-week9` |

As semanas 1 e 5 não têm pasta. A semana 1 foi preparação de ambiente e a semana
5 produziu análise escrita em vez de novo exercício.

A nomenclatura de pastas a partir da semana 8 segue `<tema>-week<N>`. Pastas
anteriores precedem essa convenção e permanecem inalteradas, porque referências
já publicadas apontam para esses caminhos.

### Estrutura

```
ai-security-lab/
├── phase-1-fundamentals/       # OWASP LLM Top 10 · Anthropic API · bases de prompt injection
├── phase-2-tools-and-attack/   # Promptfoo · Guardrails AI · jailbreak · MCP Security
├── phase-3-portfolio/          # LLM Security Scanner · agente multi-tool · análise de logs
└── phase-4-playbooks/          # Resposta a incidentes · governança
```

### Cobertura

| Área | Status |
|---|---|
| OWASP LLM Top 10 | Feito |
| Anthropic API (Python SDK) | Feito |
| Suites de teste com Promptfoo | Feito |
| Guardrails AI | Feito |
| MCP Security | Feito |
| Mapeamento MITRE ATLAS | Feito, validado na fonte primária |
| LLM Security Scanner (v1) | Em andamento, 3 de 10 categorias |
| LiteLLM / AI Gateway | Planejado |
| Análise de logs e avaliação automatizada | Planejado |

### Stack técnica

- Python · Anthropic SDK · Gemini API
- Promptfoo · Guardrails AI · LiteLLM
- Git · WSL2 (Ubuntu) · VSCode

### Referências

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATLAS](https://atlas.mitre.org)
- [NIST AI RMF](https://airc.nist.gov/RMF)
- [Simon Willison sobre Prompt Injection](https://simonwillison.net)
- [LLM Security](https://llmsecurity.net)

---
*This project is developed with the support of Claude (Anthropic). Content curation, editorial choices, and responsibility for what is published here are mine.*

*Este projeto é desenvolvido com o apoio do Claude (Anthropic). A curadoria de conteúdo, as escolhas editoriais e a responsabilidade pelo que é publicado aqui são minhas.*
