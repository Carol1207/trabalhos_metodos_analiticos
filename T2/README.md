# Trabalho 2 (T2) - Modelagem e Simulação de Redes de Filas

Este diretório contém a implementação completa, modelos de configuração e documentação analítica do **Trabalho 2 (T2)** da disciplina de Métodos Analíticos (PUCRS).

## Arquivos Disponíveis

- **[t2_simulador.py](t2_simulador.py):** Simulador de redes de filas em Python que processa a sintaxe padrão do YAML (`!PARAMETERS`) e calcula automaticamente:
  - Distribuição de probabilidades dos estados $P(N=n)$
  - Quantidade de perdas e taxa de perda
  - População média no sistema ($N$) e na fila ($N_q$)
  - Utilização dos servidores ($U$)
  - Vazão média ($X$)
  - Tempo de resposta no sistema ($W$) e espera na fila ($W_q$)
  - Índices da rede completa (população, vazão de saída, tempo de permanência e % de clientes perdidos)
  - Média dos resultados sobre todas as sementes listadas em `seeds` no YAML
  - Modo `--compare` para gerar tabela comparativa automática entre modelos
- **[t2_modelo.yml](t2_modelo.yml):** Arquivo de configuração YAML do **Modelo Base (Situação Atual)** com 3 filas e duplo retorno (feedback).
- **[t2_modelo_melhorado.yml](t2_modelo_melhorado.yml):** Arquivo de configuração YAML do **Modelo Otimizado (Situação Futura)** com remanejamento de servidores e balanceamento de carga.
- **[RELATORIO_T2.md](RELATORIO_T2.md):** Relatório técnico completo pronto para entrega, contendo a problemática de Suporte de TI, desenhos da rede (Mermaid e ASCII), notação de Kendall, fórmulas de Little e Análise Operacional, identificação do gargalo, tabela comparativa antes x depois e validação do simulador contra o `simulator.jar`.
- **[apresentacao_T2.pptx](apresentacao_T2.pptx):** Apresentação de 12 slides (capa, realidade simulada, modelo, resultados, gargalo, proposta de melhoria, comparação, validação e conclusões), com notas do apresentador.
- **[ROTEIRO_VIDEO.md](ROTEIRO_VIDEO.md):** Roteiro do vídeo, com a fala e o tempo de cada slide.

---

## Como Executar

### 1. Executar a Simulação do Modelo Base
A partir da pasta raiz ou da pasta `T2`:

```bash
# Executando com o simulador em Python
python T2/t2_simulador.py T2/t2_modelo.yml

# Ou entrando na pasta T2:
cd T2
python t2_simulador.py t2_modelo.yml
```

### 2. Executar a Simulação do Modelo Melhorado
```bash
python T2/t2_simulador.py T2/t2_modelo_melhorado.yml
```

### 3. Gerar a Tabela Comparativa Automática (Antes x Depois)
O simulador possui um modo especial de comparação lado a lado:

```bash
python T2/t2_simulador.py --compare T2/t2_modelo.yml T2/t2_modelo_melhorado.yml
```

### 4. Validar com o Simulador Oficial em Java do Professor (`simulator.jar`)
Os arquivos YAML são 100% compatíveis com o simulador oficial fornecido no módulo M3:

```bash
# Modelo Base
java -jar Modelos_Referencia/simulator.jar run T2/t2_modelo.yml

# Modelo Melhorado
java -jar Modelos_Referencia/simulator.jar run T2/t2_modelo_melhorado.yml
```
