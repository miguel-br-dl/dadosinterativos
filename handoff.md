# Handoff — Projeto WebBolão Animado

## Objetivo

Criar um site/aplicação que gera uma visualização interativa e exportável em vídeo mostrando a evolução da classificação de um bolão da Copa de 2026.

A ideia visual é inspirada em vídeos de “bar chart race”: participantes aparecem em ranking, com posição, nome, avatar e pontos. Conforme os dias avançam, eles sobem e descem em uma animação suave, criando um “balé” de posições.

## Contexto

- Data atual informada: `2026-06-28`.
- Início do bolão: `2026-06-11`.
- Total de participantes: `27`.
- Fonte dos dados: WebBolão.
- Página de classificação: `https://www.webbolao.com.br/14/app/classificacaoUserFut`.
- O WebBolão permite consultar a classificação dia a dia.

## Decisões Já Tomadas

### Arquitetura Geral

Separar o projeto em dois processos:

1. **Scraper/coletor**
   - Acessa o WebBolão.
   - Busca classificações dia a dia.
   - Salva os dados em arquivos locais.

2. **Renderizador/animação**
   - Lê os dados salvos.
   - Gera visualização interativa.
   - Exporta vídeo.

Essa separação evita que a geração do vídeo dependa diretamente da disponibilidade do site.

### Persistência dos Dados

- Os snapshots históricos não precisam ser baixados novamente, pois os dados de dias passados não mudam.
- O snapshot do dia atual deve poder ser sobrescrito, porque os pontos podem mudar ao longo do dia.
- Sugestão de estrutura:

```text
data/
  raw/
    2026-06-11.html
    2026-06-12.html
  snapshots/
    2026-06-11.csv
    2026-06-12.csv
  avatars/
    user-123.png
    user-456.png
```

### Intervalo de Datas

- O scraper deve buscar por padrão de `2026-06-11` até “hoje”.
- Deve aceitar flags como:

```bash
--start 2026-06-11
--end 2026-06-28
```

- Dias já coletados devem ser pulados.
- O dia atual deve ser atualizado/sobrescrito.

### Avatares

- Os participantes podem ter avatares cadastrados no WebBolão.
- O scraper deve baixar os avatares a cada execução.
- A razão: se alguém trocar o avatar, a visualização pega a versão mais recente automaticamente.
- Participantes sem avatar devem receber fallback visual consistente, idealmente com iniciais e cor fixa.

### Identificador dos Participantes

- Preferência: usar um `userId` estável vindo do WebBolão, se existir.
- Se não houver `userId`, usar nome normalizado como fallback.
- Motivo: nomes podem mudar, conter acentos ou duplicar.

Ainda falta confirmar onde o `userId` aparece no HTML autenticado:

- link da lupa;
- URL do perfil;
- URL do avatar;
- atributo `onclick`;
- algum campo escondido na tabela.

### Animação

- A visualização deve usar interpolação suave entre os dias.
- Os dados reais continuam sendo diários, mas o movimento entre um dia e outro deve ser contínuo.
- Cada dia pode durar algo como 1–2 segundos no vídeo.

## Investigação Técnica Feita

- Login via `requests` com email + senha funciona diretamente — sem reCAPTCHA bloqueando.
- Fluxo: GET `/login` → extrai `_token` → POST com email/password → sessão autenticada.
- Credenciais ficam no `.env` (`login` e `password`).

### Estrutura do HTML autenticado

A página `/14/app/classificacaoUserFut` renderiza a tabela server-side.

Cada linha de participante:
- **userId**: primeiro argumento de `onclick="mostraApostas(userId, bolaoId, ...)"`
- **posição**: `<td style="text-align:right">N</td>` dentro da nested table
- **avatar**: `<img class="avatar" src="..." title="Nome Completo">`
- **nome curto**: `<span class="apenome">Nome</span>`
- **pontos**: cinco `<td class="pontos">` consecutivos: pts_total, na_rodada, moscas, ares, jsa
- **percentual**: `<div class="progress">N%</div>`

### Filtro de período (chave para snapshots históricos)

O filtro de data funciona via **POST** com `filtro=1` e os campos abaixo obrigatórios:

```
POST /14/app/classificacaoUserFut
bolao=13694
inF=s
filtro=1
filtroInicioData=10/06/2026   (fixo — dia anterior ao bolão)
filtroFimData=DD/MM/AAAA      (varia: o "dia do gráfico")
filtroInicioFaseRodada=1
filtroFimFaseRodada=9
```

Resultado: pontos **acumulados** de todos os participantes até `filtroFimData`.

Os campos `filtroInicioFaseRodada` e `filtroFimFaseRodada` precisam estar presentes (mesmo com filtro=1), senão a resposta retorna vazia.

## `.env`

```env
login=seu@email.com
password=suasenha
```

Não commitar o `.env`. O scraper lê essas duas chaves diretamente.

## Campos Desejados no CSV

Campos mínimos por snapshot diário:

```csv
date,position,user_id,name,points,moscas,ares,jsa,percent,avatar_url,avatar_path
```

Campos vindos da captura de exemplo:

- `position`;
- `name`;
- `points`;
- `moscas`;
- `ares`;
- `jsa`;
- `percent`.

## Próximas Perguntas do Grilling

Continuar a partir daqui, uma pergunta por vez.

### Próxima Pergunta Sugerida

Como você prefere fornecer a sessão autenticada ao scraper?

Recomendação: usar um arquivo local `.env` com cookies copiados manualmente do navegador, por ser simples, auditável e suficiente para começar.

Opções prováveis:

1. `.env` com cookies copiados manualmente.
2. Arquivo `cookies.txt` exportado por extensão do navegador.
3. Automação com Playwright abrindo navegador real para login manual.

## Ideia de Stack

Ainda não decidido, mas uma stack provável:

- Scraper: Python com `requests`, `beautifulsoup4`, `pandas`/`csv`.
- Frontend: HTML/CSS/JS ou Vite.
- Animação: D3.js ou Canvas.
- Exportação de vídeo:
  - primeira opção: renderizar frames com Playwright/Chromium;
  - depois montar MP4 com `ffmpeg`.

## Observações Visuais

Referência enviada:

- Vídeo vertical estilo “Dados Interativos”.
- Fundo escuro.
- Ranking animado.
- Ano/data em destaque.
- Fonte dos dados no rodapé.
- Barras ou linhas horizontais com avatares/nomes/pontos.

Para o WebBolão, a composição sugerida:

- título: “Corrida do Bolão da Copa 2026”;
- subtítulo: “Classificação dia a dia”;
- lista/ranking com 27 participantes;
- avatar circular;
- nome;
- posição;
- pontos;
- data grande no canto inferior direito;
- fonte: WebBolão.

## Estado do Repositório

- `scraper.py` — implementado e funcional. Coleta 27 participantes por dia.
- `data/snapshots/` — CSVs de 2026-06-11 a 2026-06-28 já coletados (18 dias).
- `data/avatars/` — avatares baixados (exceto padrao.jpg e avatar de JP com URL com espaço).
- Frontend — ainda não implementado.

## Nota sobre o vídeo

O vídeo usará apenas **pts** (pontos acumulados totais) como campo animado.
Os demais campos (moscas, ares, jsa, %) estão nos CSVs mas não serão exibidos na animação.
