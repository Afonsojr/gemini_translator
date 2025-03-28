# Tradutor de Markdown com Gemini API

[![Repositório GitHub](https://img.shields.io/badge/GitHub-Repositório-blue?logo=github)](https://github.com/Afonsojr/gemini_translator.git)

Este script Python utiliza a API Generative AI do Google (Gemini) para traduzir arquivos de texto formatados em Markdown (`.md`) para diferentes idiomas, esforçando-se para manter a formatação original.

## ✨ Recursos Principais

*   **Tradução via API Gemini:** Conecta-se à API do Google para realizar as traduções.
*   **Suporte a Múltiplos Idiomas:** Permite especificar o idioma de destino desejado.
*   **Preservação de Formatação:** Tenta manter a estrutura do Markdown (cabeçalhos, listas, blocos de código, negrito, itálico, etc.) durante a tradução.
*   **Divisão Inteligente de Texto:** Quebra automaticamente textos longos em blocos menores para respeitar os limites de tamanho da API, tentando preservar parágrafos e sentenças.
*   **Suporte a Múltiplas API Keys:** Permite configurar várias chaves de API no `config.ini` e seleciona uma aleatoriamente a cada execução, ajudando na distribuição de carga ou uso de diferentes contas.
*   **Tratamento de Erros e Retentativas:** Implementa lógica para tentar novamente em caso de falhas na API (como limites de taxa), com um tempo de espera crescente (backoff exponencial).
*   **Interface de Linha de Comando (CLI):** Fácil de usar através do terminal com argumentos para especificar arquivos, idioma e configuração.
*   **Feedback Visual:** Utiliza a biblioteca `rich` para exibir mensagens coloridas e uma barra de progresso durante a tradução.

## ⚙️ Requisitos

*   Python 3.7 ou superior.
*   Bibliotecas Python: `google-generativeai`, `rich`.
*   Uma ou mais chaves de API válidas do Google AI Studio (para acesso aos modelos Gemini).

## 🚀 Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Afonsojr/gemini_translator.git
    cd gemini_translator
    ```

2.  **Instale as dependências usando `uv`:**
    (Certifique-se de ter o `uv` instalado: https://github.com/astral-sh/uv)
    ```bash
    uv pip install google-generativeai rich
    ```
    *Alternativamente, se houver um `requirements.txt` ou `pyproject.toml` configurado, você pode usar `uv pip sync`.*

## 🔧 Configuração

1.  **Renomeie o arquivo template:** No diretório do projeto, renomeie o arquivo `base.ini` para `config.ini`. O `base.ini` serve como um modelo.
    ```bash
    # No Linux/macOS
    mv base.ini config.ini
    # No Windows (Command Prompt)
    rename base.ini config.ini
    # No Windows (PowerShell)
    Rename-Item base.ini config.ini
    ```

2.  **Adicione suas configurações ao `config.ini`:** Abra o `config.ini` e edite o conteúdo, substituindo pelos seus dados:

    ```ini
    [gemini]
    # Cole suas chaves de API do Google AI Studio aqui, separadas por vírgula
    # Exemplo: api_keys = CHAVE_API_1,CHAVE_API_2
    api_keys = SUA_API_KEY_1,SUA_API_KEY_2

    # Modelo Gemini a ser utilizado (ex: gemini-1.5-flash, gemini-pro, gemini-1.0-pro)
    # Verifique os modelos disponíveis na documentação do Google AI
    model_name = gemini-1.5-flash
    ```

    *   **`api_keys`**: Insira uma ou mais chaves de API que você gerou no Google AI Studio. Se tiver mais de uma, separe-as por vírgula (`,`). O script escolherá uma aleatoriamente.
    *   **`model_name`**: Especifique o nome do modelo Gemini que deseja usar. Consulte a documentação da API Gemini para nomes de modelos válidos e disponíveis.

## ▶️ Uso

Execute o script a partir do seu terminal usando `uv run`.

**Sintaxe básica:**

```bash
uv run python tradutor_md.py <arquivo_entrada.md> [opções]
```

**Argumentos:**

*   `arquivo_entrada`: (Obrigatório) Caminho para o arquivo Markdown que você deseja traduzir.

**Opções:**

*   `-o, --output <arquivo_saida.md>`: Caminho para o arquivo onde a tradução será salva. Se omitido, a tradução será impressa diretamente no console.
*   `-l, --lang <idioma>`: Idioma de destino para a tradução. (Padrão: "Português Brasileiro"). Use nomes de idiomas claros (ex: "Inglês", "Espanhol", "Francês").
*   `-c, --config <caminho_config.ini>`: Caminho para o arquivo de configuração. (Padrão: "config.ini").
*   `-h, --help`: Mostra a mensagem de ajuda com todas as opções.

**Exemplos:**

1.  **Traduzir `meu_doc.md` para Português Brasileiro e imprimir no console:**
    ```bash
    uv run python tradutor_md.py meu_doc.md
    ```

2.  **Traduzir `readme_en.md` para Espanhol e salvar como `readme_es.md`:**
    ```bash
    uv run python tradutor_md.py readme_en.md -l "Espanhol" -o readme_es.md
    ```

3.  **Traduzir `info.md` para Inglês usando um arquivo de configuração diferente:**
    ```bash
    uv run python tradutor_md.py info.md -l "Inglês" -c /caminho/para/meu_gemini_config.ini -o info_en.md
    ```

## 📄 Licença

(Opcional) Adicione informações sobre a licença do seu projeto aqui, se aplicável. Por exemplo: MIT License.

## 🙌 Contribuição

(Opcional) Adicione diretrizes sobre como outros podem contribuir para o seu projeto.
