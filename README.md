# Bolão da Copa 2026 — Corrida Animada

Visualização interativa do ranking dia a dia do bolão da Copa do Mundo 2026.  
Estilo *bar chart race*: os boleiros sobem e descem conforme acumulam pontos.

**[▶ Ver ao vivo](https://SEU_USER.github.io/dadosinterativos/)**

![screenshot](docs/avatars/screenshot-preview.png)

---

## O que é

Um site estático que anima a classificação de um bolão do WebBolão — um por dia, do início da Copa até hoje. Cada boleiro tem avatar, nome e pontuação acumulada. Você escolhe quantos exibir (Top 5, 10, 15, 20 ou todos), assiste à corrida e pode exportar como imagem ou vídeo MP4.

## Funcionalidades

- **Animação diária** com transição suave entre as posições
- **Avatares reais** dos participantes (fallback com iniciais coloridas)
- **Seletor Top N** — mostre só os N primeiros
- **📷 Foto** — baixa o frame atual como PNG
- **⏺ Gravar MP4** — exporta o vídeo completo em 16:9 direto no navegador
- **Controles** de play/pause, avanço e velocidade (1×, 1.5×, 2×, 3×)

## Estrutura

```
docs/              ← site estático (GitHub Pages)
  index.html       ← toda a lógica de visualização
  data.json        ← snapshots gerados pelo build_data.py
  avatars/         ← fotos dos boleiros

data/
  snapshots/       ← um CSV por dia com a classificação
  avatars/         ← fotos originais baixadas pelo scraper

scraper.py         ← coleta dados do WebBolão (roda local)
build_data.py      ← gera docs/data.json e copia avatares
atualizar.sh       ← script diário de atualização
```

---

## Como atualizar (uso próprio)

### Pré-requisitos

```bash
pyenv local 3.10.20
python -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 python-dotenv
```

Crie um arquivo `.env` na raiz (não commitado):

```env
login=seu@email.com
password=suasenha
```

### Atualização diária

```bash
./atualizar.sh 29/06      # substitua pelo dia atual no formato dd/mm
```

O script autentica no WebBolão, coleta a classificação acumulada até a data informada, atualiza os CSVs e regenera o site em `docs/`.

Em seguida, publique:

```bash
git add docs/ data/snapshots/ data/avatars/
git commit -m "atualiza bolão 29/06"
git push
```

O GitHub Pages publica automaticamente em ~30 segundos.

### Parâmetros do scraper (uso avançado)

```bash
python scraper.py --end 2026-07-15          # coleta até uma data específica
python scraper.py --start 2026-06-20        # reprocessa a partir de uma data
python scraper.py --force                   # sobrescreve todos os dias existentes
python scraper.py --no-avatars              # pula download de avatares
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Scraper | Python · requests · BeautifulSoup |
| Site | HTML + CSS + JavaScript (sem framework) |
| Animação | CSS transitions + canvas (para o vídeo) |
| Dados | JSON estático gerado localmente |
| Hospedagem | GitHub Pages |

---

## Fonte dos dados

Classificação extraída do [WebBolão](https://www.webbolao.com.br) — bolão privado, Copa do Mundo 2026.
