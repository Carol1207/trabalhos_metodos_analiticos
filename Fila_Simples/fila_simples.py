import math

# G/G/c/K
# chegadas/saidas/servidores/capacidade_max

# PARAMETROS GERADOR

a = 1664525
c = 1013904223
M = 2 ** 32
previous = 123456789

count = 100000

# PARAMETROS FILA

K = 5
servidores = 1 # 1 para G/G/1/5, 2 para G/G/2/5

TIPO_CHEGADA = 1
TIPO_SAIDA = 2

tempo_global = 0.0
tempo_ultimo_evento = 0.0
clientes_fila = 0
clientes_perdidos = 0

tempo_acumulado = [0.0] * (K + 1)
agendador = []


def NextRandom():
    global previous, count
    previous = ((a * previous) + c) % M
    count -= 1
    return float(previous) / M


def Uniforme(minimo, maximo):
    return minimo + (maximo - minimo) * NextRandom()

# FUNCOES AUX

def AtualizarTemposAcumulados():
    global tempo_global, tempo_ultimo_evento, clientes_fila, tempo_acumulado
    tempo_decorrido = tempo_global - tempo_ultimo_evento
    tempo_acumulado[clientes_fila] += tempo_decorrido
    tempo_ultimo_evento = tempo_global

def NextEvent():
    global tempo_global, agendador
    agendador.sort(key=lambda x: x[0])
    evento = agendador.pop(0)
    tempo_global = evento[0]
    return evento[1]

# FUNCOES EVENTOS

def CHEGADA():
    global clientes_fila, clientes_perdidos, tempo_global, K, servidores

    AtualizarTemposAcumulados()

    if clientes_fila < K:
        clientes_fila += 1
        if clientes_fila <= servidores:
            tempo_proxima_saida = tempo_global + Uniforme(3.0, 5.0)
            agendador.append([tempo_proxima_saida, TIPO_SAIDA])

    else:
        clientes_perdidos += 1

    if count > 0:
        tempo_proxima_chegada = tempo_global + Uniforme(2.0, 5.0)
        agendador.append([tempo_proxima_chegada, TIPO_CHEGADA])

def SAIDA():
    global clientes_fila, tempo_global, servidores

    AtualizarTemposAcumulados()

    if clientes_fila > 0:
        clientes_fila -= 1

    if clientes_fila >= servidores:
        tempo_proxima_saida = tempo_global + Uniforme(3.0, 5.0)
        agendador.append([tempo_proxima_saida, TIPO_SAIDA])

# LOOP PRINCIPAL

def main():
    global agendador, tempo_global, count
    agendador.append([3.0, TIPO_CHEGADA]) # 1o cliente chega no tempo 3

    while count > 0 and len(agendador) > 0:
        tipo_evento = NextEvent()

        if tipo_evento == TIPO_CHEGADA:
            CHEGADA()
        elif tipo_evento == TIPO_SAIDA:
            SAIDA()

# CALCULOS

    print(f"RESULTADOS DA SIMULAÇÃO DE FILA (G/G/{servidores}/5)")
    print(f"Tempo total de simulação: {tempo_global:.2f}")
    print(f"Capacidade máxima da fila: {K}")
    print("\nEstado     | Tempo acumulado | Probabilidade")

    for i in range(K + 1):
        probab = (tempo_acumulado[i] / tempo_global) * 100
        print(f"Fila em {i:2d} | {tempo_acumulado[i]:15.2f} | {probab:6.2f}%")

if __name__ == "__main__":
    main()