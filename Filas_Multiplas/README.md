# Simulador de rede de filas

O programa simula redes de filas G/G/c/K por eventos discretos. Cada fila pode
ter servidores, capacidade e intervalo de atendimento proprios. A simulacao
comeca com todas as filas vazias e termina ao consumir a quantidade configurada
de numeros pseudoaleatorios.

## Execucao

Requer Python 3 e PyYAML. No diretorio do projeto, execute:

```bash
python3 fila_multiplas.py tandem.yml
```

O arquivo `tandem.yml` e o cenario solicitado: Fila1 G/G/2/3, chegadas em
[1, 5], atendimento em [4, 5], seguida por Fila2 G/G/1/5, atendimento em
[1, 3]. A primeira chegada ocorre em 2.5 e a transferencia de Fila1 para
Fila2 tem probabilidade 1.0.

## Formato do YAML

`simulation.random_numbers` define o orcamento de aleatorios e `seed` torna o
resultado reproduzivel. `external_arrivals` contem somente as filas que recebem
clientes de fora da rede. Cada fila em `queues` define `servers`, `capacity` e
`service_interval: [minimo, maximo]`; omita `capacity` para capacidade infinita.

As arestas em `network` definem o roteamento:

```yaml
network:
  - source: Recepcao
    target: Pagamento
    probability: 0.8
  - source: Recepcao
    target: Suporte
    probability: 0.2
```

As probabilidades de saida de uma fila devem somar no maximo 1. A parcela que
falta representa clientes que deixam a rede. Uma unica rota com probabilidade
1.0 e uma transferencia deterministica e nao consome um aleatorio.

O relatorio apresenta tempo global, quantidade de aleatorios usada, tempo e
probabilidade de cada estado e perdas por fila.