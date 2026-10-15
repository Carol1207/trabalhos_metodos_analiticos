# Roteiro do vídeo — T2: Central de Suporte de TI

Apresentação: [`apresentacao_T2.pptx`](apresentacao_T2.pptx) (12 slides)
Duração estimada: **10 a 11 minutos**
Falas divididas entre três integrantes (**A**, **B** e **C**). Ajuste a divisão conforme o grupo.

Dica de gravação: deixe o terminal aberto em outra janela. No slide 6 dá para
mostrar rapidamente o simulador rodando (`python T2/t2_simulador.py T2/t2_modelo.yml`).

---

## Slide 1 — Capa · ~30 s · Integrante A

> Olá! Nós somos Pedro e Carol, e este é o Trabalho 2 de Métodos Analíticos.
> Escolhemos modelar uma **central de suporte de TI** como uma rede de filas e
> analisá-la por simulação, usando o simulador que o próprio grupo desenvolveu.
> A ideia é a mesma do módulo M9: simular a situação atual, encontrar o gargalo,
> propor uma melhoria e comparar os dois cenários.

## Slide 2 — Realidade simulada · ~1 min · Integrante A

> A central tem três níveis de atendimento.
> No **N1, a triagem**, um atendente registra o chamado e resolve os casos simples,
> como troca de senha. Ele atende em 1 a 2,5 minutos; 60% dos chamados terminam
> ali e 40% sobem para o N2.
> No **N2**, um técnico diagnostica problemas de máquina, software e rede, em 4 a 7
> minutos. Depois do atendimento, 45% são resolvidos, 25% sobem para a engenharia
> e 30% **voltam para a triagem**, por exemplo para contato com o usuário.
> No **N3**, dois engenheiros cuidam de servidores e falhas complexas, em 6 a 12
> minutos. Só 20% terminam ali: 80% **voltam para o N2**, porque o técnico precisa
> aplicar a correção na máquina do usuário.
> Chega um chamado novo a cada 2 a 4 minutos, e cada nível tem um limite de
> chamados abertos. Se um chamado chega a um nível lotado, ele é perdido.

## Slide 3 — Modelo da rede · ~1 min · Integrante A

> Este é o modelo. As chegadas externas entram só no N1, com intervalo uniforme
> entre 2 e 4 minutos.
> Na notação de Kendall, o N1 é uma **G/G/1/8**: um servidor e capacidade 8.
> O N2 é **G/G/1/5** e o N3 é **G/G/2/6**, com dois servidores.
> As setas contínuas são o fluxo para frente, com 0,40 do N1 para o N2 e 0,25 do
> N2 para o N3. As tracejadas são os **retornos**: 0,30 do N2 para o N1 e 0,80 do
> N3 para o N2. Por causa deles a rede não é tandem: um chamado pode passar
> várias vezes pela mesma fila.
> Simulamos com as filas vazias, a primeira chegada em 2,0 e 100 mil números
> aleatórios por execução. Todos os resultados são a média de 5 sementes.

## Slide 4 — Carga esperada · ~50 s · Integrante B

> Antes de simular, fizemos uma verificação analítica com as equações de tráfego.
> Resolvendo o sistema, o N2 recebe 0,196 cliente por minuto. Com 5,5 minutos de
> atendimento médio, a utilização esperada é **1,078: maior que 1**. Ou seja, o
> técnico recebe mais trabalho do que consegue fazer.
> Como a capacidade é finita, a fila não cresce para sempre: ela enche e passa a
> perder chamados. Já o N3 tem carga de só 22%. A simulação vai confirmar isso.

## Slide 5 — Probabilidades dos estados · ~1 min · Integrante B

> Aqui está a distribuição de probabilidades de cada fila.
> O N1 fica vazio ou com um chamado em 91% do tempo: está tranquilo.
> O N2 tem o comportamento oposto. A probabilidade cresce até o estado 4, e a fila
> fica **cheia, no estado 5, em 13% do tempo**. Todo chamado que chega nesse
> momento é perdido.
> E o N3 fica completamente vazio em 65% do tempo.

## Slide 6 — Índices de desempenho · ~1 min · Integrante B

> Com a distribuição calculamos os índices. A população é a média dos estados
> ponderada pela probabilidade. A utilização considera quantos servidores estão
> ocupados. A vazão são os atendimentos concluídos pelo tempo total. E o tempo
> de resposta vem da Lei de Little: W igual a N sobre X.
> A linha destacada é o N2: **93,5% de utilização**, tempo de resposta de 16,6
> minutos, dos quais 11 são só espera, e 1.142 chamados perdidos por execução.
> Olhando a central inteira: 5,2% de todos os chamados abertos são perdidos, e um
> chamado fica em média 11,9 minutos no sistema.

*(Opcional: mostrar o simulador rodando no terminal por ~15 s.)*

## Slide 7 — Gargalo · ~50 s · Integrante B

> O diagnóstico é claro: o **N2 é o gargalo**. O técnico está ocupado 93,5% do
> tempo, o chamado espera 11 minutos na fila, o dobro do próprio atendimento, e
> 9,3% dos chamados que chegam ao N2 são perdidos.
> O problema piora por causa dos retornos: o N2 recebe os chamados do N1 e
> também 80% de tudo que passa pelo N3.
> Enquanto isso, a engenharia tem só 19% de utilização: os dois engenheiros
> ficam parados 81% do tempo.

## Slide 8 — Proposta de melhoria · ~1 min · Integrante C

> A proposta é **remanejar um engenheiro do N3 para o N2**, sem contratar ninguém.
> A equipe continua com 4 pessoas.
> No desenho, em verde, estão os parâmetros alterados: o N2 passa de 1 para **2
> servidores** e o limite de chamados abertos sobe de **5 para 8**, virando uma
> G/G/2/8. O N3 passa de 2 para **1 servidor**, virando G/G/1/6.
> Tempos de atendimento, chegadas e probabilidades de roteamento continuam iguais.
> Refazendo a conta, a carga do N2 cai para 0,54 e a do N3 sobe para 0,44: as
> duas filas ficam estáveis.

## Slide 9 — Comparação por fila · ~1 min · Integrante C

> Comparando fila a fila: a utilização do N2 cai de 93% para 54%, e a do N3 sobe
> de 19% para 44%. A carga ficou mais equilibrada.
> No N2, o tempo de resposta cai 63%, de 16,6 para 6,1 minutos. A espera na fila
> cai 95% e **as perdas zeram**. A vazão do N2 até aumenta 15%, porque agora
> nenhum chamado é descartado.
> O custo aparece no N3: o tempo de resposta sobe de 9 para 12,3 minutos, com 3
> minutos de espera. É uma piora aceitável, porque o N3 continua longe da
> saturação e só cerca de 5% dos chamados passam por ele.

## Slide 10 — Comparação da rede · ~50 s · Integrante C

> No gráfico, a distribuição do N2 antes e depois. Antes, a probabilidade se
> concentrava nos estados altos. Agora a fila passa a maior parte do tempo com 0,
> 1 ou 2 chamados.
> Na central inteira, as perdas caem de 5,2% para praticamente zero. O tempo médio
> de um chamado no sistema cai de 11,9 para **7,8 minutos, 34% menos**, e a
> central passa a resolver todos os chamados que recebe.

## Slide 11 — Validação do simulador · ~50 s · Integrante A

> Como usamos o nosso próprio simulador, conferimos os resultados com o simulador
> oficial do módulo M3.
> Os dois usam geradores aleatórios diferentes, então não dá para comparar uma
> execução com outra. Rodamos cada um com 20 sementes e comparamos as médias, no
> modelo do hospital do M9 e nos nossos dois modelos.
> **Em todos os estados de todas as filas, a diferença ficou abaixo de um
> desvio-padrão.** As perdas também batem: 1.159 contra 1.154 no N2. E as
> utilizações simuladas coincidem com as equações de tráfego.

## Slide 12 — Conclusões · ~1 min · Integrante A (ou todos)

> Para concluir:
> Primeiro, a simulação encontrou o gargalo no N2, que acumulava os
> escalonamentos do N1 e os retornos do N3.
> Segundo, só remanejando a equipe, as perdas zeraram e o tempo médio de um
> chamado caiu 34%, sem nenhum custo de contratação.
> Terceiro, o custo dessa mudança no N3 foi pequeno e aceitável.
> E, como próximo passo: se a demanda crescer uns 45%, o N1 passa a ser o novo
> gargalo. Reduzir o retorno da engenharia para o técnico, por exemplo com
> correções remotas, aliviaria ainda mais o N2.
> Obrigado!
