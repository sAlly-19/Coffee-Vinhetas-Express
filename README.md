# Coffee Vinhetas Express

**Processador desktop Windows de alta velocidade para inserção automatizada de vinhetas de áudio com Ducking inteligente.**

Desenvolvido por **Café - Sistemas & Softwares**.

---

## Principais Recursos

- **Inserção em massa com paralelismo real**: processa dezenas ou centenas de músicas, podcasts e sets de DJ simultaneamente via `FFmpeg`, sem travar a interface.
- **Ducking inteligente**: atenua suavemente o volume da música durante a vinheta usando envelope controlado (precisão percentual) ou compressão *sidechain*, com controle de *Attack* e *Release*.
- **Editor visual de corte de vinheta**: recorte não destrutivo de início e fim com alças arrastáveis na waveform, detecção automática de silêncio, micro-fade suave de 20 ms nas bordas e opção de exportar a vinheta cortada.
- **Repetição automática**: ideal para sets longos e mixes, com detecção de conflitos de intervalo.
- **Prévia em tempo real**: ouça o ponto exato de entrada da vinheta com o ducking aplicado antes de iniciar o lote.
- **100% offline e seguro**: nunca modifica os arquivos originais — os resultados são salvos na subpasta `COM_VINHETA`, preservando metadados musicais (artista, título, álbum).
- **Histórico persistente e múltiplos formatos**: suporte a `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac` e `.aac`, com exportação em MP3 (320/256 kbps), AAC (256 kbps), WAV PCM e FLAC.

---

## Requisitos

- **Windows 10 / 11**
- **Python 3.11+**
- **FFmpeg** e **FFprobe** disponíveis no `PATH` (ou configuráveis pela aba *Configurações* dentro do app)

---

## Instalação e Execução

```bash
# Clone o repositório
git clone <URL_DO_REPOSITORIO>
cd "Coffee Vinhetas Express"

# (Opcional) Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute o aplicativo
python main.py
```

---

## Testes Automatizados

```bash
python -m unittest discover -s tests -v
```

---

## Empacotamento (Executável Windows)

```bash
pip install pyinstaller
pyinstaller CoffeeVinhetasExpress.spec
```

O executável será gerado em `dist/CoffeeVinhetasExpress/`.

---

## Estrutura do Projeto

```text
Coffee Vinhetas Express/
├── main.py                      # Ponto de entrada da aplicação
├── pyproject.toml               # Metadados e dependências do projeto
├── requirements.txt             # Dependências Python
├── CoffeeVinhetasExpress.spec   # Configuração de build PyInstaller
├── src/coffee_vinhetas/
│   ├── app.py                   # Bootstrap do QApplication e tema
│   ├── assets/                  # Recursos visuais embutidos
│   ├── core/                    # Motor DSP/FFmpeg, modelos, settings e histórico
│   ├── workers/                 # QThreads (análise, varredura, prévia e lote)
│   └── ui/                      # Interface PySide6 (tema, widgets, páginas e diálogos)
└── tests/                       # Testes unitários (DSP, workers e UI)
```

---

<sub>**Café - Sistemas & Softwares**</sub>
