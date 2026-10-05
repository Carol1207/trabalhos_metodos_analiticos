# Simulador de redes de filas

Simulador de eventos discretos para redes de filas G/G/c/K com qualquer
topologia. Cada fila tem servidores, capacidade e intervalo de atendimento
próprios e pode receber chegadas de fora da rede. Depois do atendimento, cada
cliente vai para outra fila (inclusive a mesma) ou sai da rede, conforme
probabilidades configuráveis.

O modelo é lido de um arquivo `.yml` no mesmo formato do simulador do módulo 3
(`modelo_referencia/simulator.jar`). O mesmo arquivo roda nos dois simuladores
e, com a mesma semente, os resultados são idênticos.

## Requisitos

- Python 3.8 ou superior
- PyYAML

## Como executar

No diretório do projeto:

```bash
pip install pyyaml
python3 t1_simulador_completo.py t1_modelo.yml
```

`t1_modelo.yml` é a rede pedida no enunciado: três filas, filas vazias no
início, primeira chegada em 2.0 e 100000 aleatórios. Os resultados estão em
[RESULTADOS.md](RESULTADOS.md).

## Formato do modelo

```yaml
!PARAMETERS                # linha exigida pelo simulador de referencia
arrivals:                  # filas com chegadas externas e instante da 1a chegada
   Fila1: 2.0

queues:
   Fila1:
      servers: 1           # numero de servidores
      minArrival: 2.0      # intervalo entre chegadas externas
      maxArrival: 4.0
      minService: 1.0      # tempo de atendimento
      maxService: 2.0
   Fila2:
      servers: 2
      capacity: 5          # omita (ou use -1) para capacidade infinita
      minService: 4.0
      maxService: 6.0
   Fila3:
      servers: 2
      capacity: 10         
      minService: 5.0
      maxService: 15.0

network:                   # roteamento depois do atendimento
-  source: Fila1
   target: Fila2
   probability: 0.2
-  source: Fila1
   target: Fila3
   probability: 0.8
-  source: Fila2
   target: Fila1
   probability: 0.3
-  source: Fila2
   target: Fila3
   probability: 0.5
-  source: Fila3
   target: Fila2
   probability: 0.7

rndnumbersPerSeed: 100000  # aleatorios por execucao (padrao: 100000)
seeds:                     # uma execucao por semente
- 123456789
```

- `queues` aceita qualquer número de filas. `minArrival` e `maxArrival` só são
  necessários nas filas listadas em `arrivals`.
- `network` aceita qualquer número de rotas, inclusive de uma fila para ela
  mesma e de volta para filas anteriores. As probabilidades de cada origem
  somam no máximo 1, e o que falta é a saída da rede. Uma fila sem rotas manda
  todos os clientes para fora.
- Com `seeds`, cada semente é uma execução independente com
  `rndnumbersPerSeed` aleatórios. Sem `seeds`, a simulação usa, em ordem, os
  valores da lista `rndnumbers` (uma única execução).

Se o modelo tiver erros (fila inexistente, probabilidades somando mais que 1,
campo obrigatório faltando etc.), o programa informa o campo e termina com
código 1.

## Regras da simulação

- Os aleatórios vêm de um gerador congruente linear `x = (a*x + c) mod M`, com
  `a = 25214903917`, `c = 11` e `M = 2^48`. O gerador começa em `x = semente` e
  devolve `x / M`.
- Os tempos são sorteados com `min + (max - min) * U`.
- Quando um atendimento começa, o destino do cliente é sorteado antes do tempo
  de atendimento. Numa chegada externa, o tempo até a próxima chegada é
  sorteado por último.
- As rotas são testadas em ordem crescente de probabilidade. Uma rota única com
  probabilidade 1 não consome aleatório.
- Um cliente que chega a uma fila cheia é perdido.
- Eventos no mesmo instante são tratados na ordem em que foram agendados.
- A simulação começa com as filas vazias e termina quando o último aleatório é
  usado. O tempo global é o do evento que usou esse aleatório.

## Saída

Para cada fila, o relatório mostra o tempo acumulado e a probabilidade de cada
estado (número de clientes na fila) e o número de clientes perdidos. No fim,
mostra o tempo global da simulação. No início há uma linha por execução com a
semente, os aleatórios usados, o tempo global e as perdas. Com várias sementes,
as tabelas mostram a média das execuções.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `t1_simulador_completo.py` | simulador genérico de redes de filas |
| `t1_modelo.yml` | rede do enunciado |
| `RESULTADOS.md` | resultados da simulação de `t1_modelo.yml` |
| `fila_simples.py` | versão anterior: uma fila, com os parâmetros no código |
| `fila_multiplas.py`, `tandem.yml` | versão anterior: filas em tandem, com YAML em formato próprio (`python3 fila_multiplas.py tandem.yml`) |