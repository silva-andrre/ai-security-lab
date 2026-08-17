# Análise de Logs de LLM — Semana 11

Exercício da Fase 3 do portfólio: detecção de padrões de ataque em logs simulados de um agente de suporte via LLM, usando o NovaPay (alvo controlado fictício) como cenário.

## Objetivo

Definir um schema de log para um agente de LLM em produção que capture sinal suficiente para detecção de abuso sem armazenar conteúdo sensível de prompt, e implementar três detectores independentes sobre esse log. Depois, testar esses detectores contra tráfego com ruído legítimo, não só contra ataque isolado, porque é essa a pergunta que interessa para quem vai confiar no detector em produção.

## Como rodar

```bash
python3 generate_logs.py    # gera logs/novapay_llm_logs.json
python3 detect_patterns.py  # gera reports/detections_report.csv
```

## O que é logado, e por quê

O schema deliberadamente não guarda texto de prompt ou resposta. Em uma fintech regulada, log de LLM com conteúdo de conversa é log com potencial dado financeiro de cliente dentro, e isso muda a superfície de risco do próprio sistema de observabilidade. Os campos escolhidos (`estimated_dialogue_turns`, `input_tokens`, `latency_ms`, `stop_reason`, `retry_of`) são metadados estruturais, computados pela camada de aplicação antes do envio ao modelo, suficientes para os três detectores abaixo.

Detalhe do schema e do racional completo de cada campo está documentado no topo de `generate_logs.py`.

## Detectores implementados

1. **many_shot_probe**: contagem estrutural de turnos de diálogo (proxy de many-shot jailbreaking) muito acima do baseline, reforçada por `input_tokens` elevado.
2. **latency_anomaly**: outlier estatístico de latência por ferramenta (Q3 + 2.5x IQR), calculado sobre o próprio tráfego observado.
3. **retry_storm**: cadeia de `refusal` na mesma sessão, encadeada via `retry_of`, dentro de janela de 5 minutos.

Critérios de detecção declarados e commitados antes de rodar o script contra os dados, para não calibrar threshold olhando o resultado (ver comentário no topo de `detect_patterns.py`).

## Resultado

O primeiro teste rodou os três detectores contra 374 eventos, sendo 364 de tráfego limpo e 10 injetados em três padrões de ataque conhecidos. Resultado: 6 detecções, zero falso positivo. Esse número não significa muito sozinho: dado sintético limpo é estatisticamente separável por desenho, e qualquer detector baseado em outlier tende a acertar 100% contra ele.

O teste que importa veio depois, com dois tipos de ruído legítimo adicionados ao tráfego normal e o volume dobrado para 784 eventos: 7% dos eventos passaram a ter `refusal` legítimo (usuário pedindo algo fora do escopo do agente, não ataque), 5% passaram a ter latência de cauda gorda legítima (lentidão real de backend), e 15 sessões de usuário genuinamente frustrado foram injetadas, cada uma com 3 a 5 `refusal` encadeados em janela curta, reformulando a mesma pergunta sem intenção de ataque.

Contra esse tráfego, os três detectores tiveram 43 detecções no total, e a precisão caiu de forma desigual entre eles:

| Detector | Detecções | Verdadeiro positivo | Precisão |
|---|---|---|---|
| many_shot_probe | 1 | 1 | 100% |
| latency_anomaly | 30 | 4 | ~13% |
| retry_storm | 12 | 1 | ~8% |

`many_shot_probe` se manteve limpo porque o sinal que ele usa (turnos estruturais de diálogo muito acima do baseline) não tem equivalente plausível em tráfego legítimo simulado. `latency_anomaly` e `retry_storm` colapsaram porque dependem de um único sinal com um único threshold, e ruído legítimo modesto já basta para cruzar esse threshold quase tantas vezes quanto o ataque real.

Achado adicional, presente nas duas rodadas: o evento de many-shot probe disparou ao mesmo tempo `many_shot_probe` e `latency_anomaly`, porque o mesmo payload malicioso se manifesta em mais de uma dimensão do log simultaneamente. Sem agrupar detecções por `request_id` antes da triagem, um único evento malicioso vira dois incidentes na fila de quem investiga.

## Lição aprendida

Um detector que roda limpo contra dado de teste não diz nada sobre a taxa real de falso positivo em produção, porque dado de teste tende a ser mais separável do que tráfego real. A pergunta operacional relevante não é "o detector pega o ataque", os três pegam. É "quantas vezes um analista vai investigar um usuário confuso pensando que é um atacante", e para dois dos três detectores aqui, a resposta com este nível de ruído é: na maioria das vezes.

Isso não é peculiaridade deste exercício. É a razão pela qual threshold de detecção de segurança em qualquer sistema, LLM ou não, precisa ser validado contra ruído representativo antes de virar critério de bloqueio automático, e não só contra o cenário de ataque que motivou construir o detector.

## Caminho de maturidade técnica (não implementado neste exercício)

O objetivo desta semana foi expor o problema de precisão sob ruído, não resolvê-lo. Para quem quiser pegar este scanner e evoluir para uma versão mais robusta, os pontos concretos de partida são:

1. **retry_storm**: hoje decide só por contagem e janela de tempo. Um sinal de diversidade entre tentativas (por exemplo, distância de embedding entre os prompts consecutivos da sessão, calculada e descartada pela aplicação, nunca armazenada como texto) separaria reformulação genuína, que tende a variar de tópico, de iteração de jailbreak, que tende a reaproveitar estrutura.
2. **latency_anomaly**: o IQR está segmentado só por ferramenta. Segmentar também por faixa de tamanho de payload, ou exigir anomalia sustentada em mais de um evento consecutivo da mesma sessão em vez de disparar por evento isolado, reduziria o disparo por lentidão pontual de backend.
3. **Correlação entre detectores**: severidade alta deveria depender de mais de um sinal concordando, não de um detector isolado cruzar o próprio threshold. O achado do many-shot probe disparando dois detectores ao mesmo tempo é evidência a favor disso, não contra: correlação é informação, não redundância.
4. **Validação contínua**: rodar o scanner como sinal consultivo contra tráfego de sombra em produção, com incidentes rotulados manualmente, antes de qualquer automação de bloqueio. Threshold calibrado uma vez contra dado sintético não se sustenta sozinho.

## Abordagens descartadas

- Logar o prompt bruto para permitir detecção por conteúdo. Descartado por risco de PII em log de fintech; o proxy estrutural (`estimated_dialogue_turns`) cobre o mesmo sinal sem esse custo.
- IP do usuário em texto claro para correlação entre sessões. Fora do escopo deste exercício; em produção entraria hasheado.
- Threshold único global de latência, em vez de por ferramenta. Descartado porque `kb_search` e `chat_completion` têm distribuições de latência muito diferentes por natureza.