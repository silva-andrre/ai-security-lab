# LLM Prompt Injection Test — Semana 2

Script Python que envia 10 prompts para a API Anthropic (Claude),
incluindo tentativas de prompt injection direta, e salva os resultados em CSV.

## O que este script testa
- Comportamento do modelo frente a instruções de override de sistema
- Tentativas de jailbreak via reformulação de papel
- Extração de system prompt
- Respostas a prompts benignos como baseline

## Como rodar
pip install anthropic
export ANTHROPIC_API_KEY="sua_chave"
python prompt_injection_test.py

## Observações dos resultados

Nenhuma das 10 tentativas foi bem-sucedida. O modelo identificou e recusou
todos os vetores testados, incluindo override direto, reformulação de papel,
instrução oculta e extração de system prompt.

### Por que nenhum ataque funcionou
O Claude é treinado com RLHF e constitutional AI especificamente para resistir
a esses vetores. Os testes foram executados contra o modelo nu, sem aplicação
por cima. Na prática, o alvo não é o modelo em si, mas a aplicação que o utiliza,
com seus prompts customizados, ferramentas conectadas e dados próprios.

### O que tornaria esses ataques mais eficazes
- Injeção indireta via dado processado (e-mail, documento, resultado de busca)
  que o agente consome como parte do fluxo normal
- Contexto longo que dilui a instrução maliciosa entre conteúdo legítimo
- Aplicação com system prompt mal construído que cria contradições exploráveis

### O que este exercício provou
Chamada funcional à API Anthropic, processamento de 10 prompts e análise
de comportamento real do modelo. A resistência observada é esperada para
modelos de fronteira em testes diretos. O vetor relevante em ambientes reais
é a injeção indireta via dados processados por agentes.