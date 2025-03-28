import google.generativeai as genai
import configparser
import argparse
from pathlib import Path
import sys
import time
import random

from rich.console import Console
from rich.markdown import Markdown
from rich.progress import track
from rich.panel import Panel
from rich import print as rprint

# Constante para o tamanho máximo de cada bloco enviado à API
MAX_CHUNK_SIZE = 4900  # Um pouco abaixo de 5000 para segurança com metadados/prompts

console = Console()


def ler_config(config_path: Path) -> configparser.ConfigParser:
    """Lê o arquivo de configuração."""
    if not config_path.is_file():
        rprint(
            Panel(
                f"[bold]Erro:[/bold] 📄 Arquivo de configuração não encontrado: [cyan]{config_path}[/cyan]\n"
                f"[bold]Crie um 'config.ini' com [gemini], api_key=SUA_CHAVE e model_name=seu_modelo.[/bold]",
                title="[bold red]❌ Falha na Configuração[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def configurar_gemini(api_key: str):
    """Configura a API do GenerativeAI com a chave fornecida."""
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        rprint(
            Panel(
                f"[bold]Erro ao configurar a API Gemini:[/bold] {e}\n"
                f"[bold]🔑 Verifique se a sua API Key está correta no 'config.ini'.[/bold]",
                title="[bold red]❌ Falha na Configuração da API[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)


def carregar_markdown(filepath: Path) -> str:
    """Carrega o conteúdo de um arquivo Markdown."""
    if not filepath.is_file():
        rprint(
            Panel(
                f"[bold]Erro:[/bold] 📂 Arquivo de entrada não encontrado: [cyan]{filepath}[/cyan]",
                title="[bold red]❌ Erro de Entrada[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        rprint(
            Panel(
                f"[bold]Erro ao ler o arquivo {filepath}:[/bold] {e}",
                title="[bold red]❌ Erro de Leitura[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)


def _quebrar_paragrafo_longo(paragrafo: str, max_size: int) -> list[str]:
    """
    Quebra um parágrafo único que excede max_size em múltiplos blocos.
    Tenta quebrar em pontos naturais (fim de linha/sentença, espaço) antes de cortar.
    """
    pedacos = []
    inicio = 0
    while inicio < len(paragrafo):
        # Define o fim ideal do pedaço
        fim = min(inicio + max_size, len(paragrafo))
        pedaco_atual = paragrafo[inicio:fim]

        # Se não for o último pedaço, tenta quebrar em fim de sentença ou linha
        if fim < len(paragrafo):
            # Procura pelo último \n ou . ? ! antes do fim
            ponto_quebra_linha = pedaco_atual.rfind("\n")
            ponto_quebra_sentenca = max(
                pedaco_atual.rfind("."),
                pedaco_atual.rfind("?"),
                pedaco_atual.rfind("!"),
            )

            # Usa o melhor ponto de quebra encontrado dentro do pedaço
            ponto_quebra = max(ponto_quebra_linha, ponto_quebra_sentenca)

            if ponto_quebra > -1:
                # Ajusta o fim para quebrar após o ponto/linha + 1
                fim = inicio + ponto_quebra + 1
                pedaco_atual = paragrafo[inicio:fim]
            # Se não achou ponto bom, usa quebra por espaço para evitar cortar palavra
            elif " " in pedaco_atual:
                espaco_antes = pedaco_atual.rfind(" ")
                # Garante que o espaço não seja o primeiro caractere para evitar loop infinito
                if espaco_antes > 0:
                    fim = (
                        inicio + espaco_antes + 1
                    )  # Quebra *antes* do espaço para não incluí-lo
                    pedaco_atual = paragrafo[inicio:fim]
                # else: usa o 'fim' original (corte pode acontecer no meio da palavra)
            # else: usa o 'fim' original (corte bruto)

        pedaco_limpo = pedaco_atual.strip()
        if pedaco_limpo:  # Adiciona apenas se não for vazio após strip
            pedacos.append(pedaco_limpo)
        inicio = fim  # Próximo pedaço começa onde este terminou

    return pedacos


def dividir_texto_em_blocos(texto: str, max_size: int) -> list[str]:
    """
    Divide o texto em blocos menores que max_size.
    Tenta preservar parágrafos e quebrar blocos longos de forma inteligente.
    """
    paragrafos = texto.split("\n\n")
    blocos = []
    bloco_atual = ""

    for p in paragrafos:
        p_limpo = p.strip()
        if not p_limpo:  # Pula parágrafos vazios
            continue

        tamanho_p = len(p_limpo)
        tamanho_bloco_atual = len(bloco_atual)

        # Caso 1: Parágrafo muito longo (maior que o limite por si só)
        if tamanho_p > max_size:
            # Salva o bloco que estava sendo construído (se houver)
            if bloco_atual:
                blocos.append(bloco_atual)
                bloco_atual = ""
            # Quebra o parágrafo longo e adiciona seus pedaços como blocos separados
            pedacos_paragrafo = _quebrar_paragrafo_longo(p_limpo, max_size)
            blocos.extend(
                pedacos_paragrafo
            )  # Adiciona todos os pedaços à lista principal

        # Caso 2: Bloco atual está vazio
        elif not bloco_atual:
            # Inicia o bloco atual com este parágrafo
            bloco_atual = p_limpo

        # Caso 3: Bloco atual existe, verificar se o parágrafo cabe
        # Adiciona 2 caracteres para o separador '\n\n'
        elif tamanho_bloco_atual + len("\n\n") + tamanho_p <= max_size:
            # Adiciona o parágrafo ao bloco atual
            bloco_atual += "\n\n" + p_limpo

        # Caso 4: Bloco atual existe, mas o parágrafo não cabe mais
        else:
            # Finaliza o bloco atual
            blocos.append(bloco_atual)
            # Inicia um novo bloco com o parágrafo atual
            bloco_atual = p_limpo

    # Adiciona o último bloco que estava sendo construído (se houver)
    if bloco_atual:
        blocos.append(bloco_atual)

    # A verificação final para quebras brutas extras pode ser removida ou mantida
    # como uma segurança extra, mas a lógica de _quebrar_paragrafo_longo
    # já deveria lidar com isso corretamente. Vamos mantê-la por segurança.
    blocos_finais = []
    for b in blocos:
        if len(b) > max_size:
            # Se algum bloco ainda for muito grande (caso extremo), quebra bruto
            for i in range(0, len(b), max_size):
                bloco_final_pedaco = b[i : i + max_size].strip()
                if bloco_final_pedaco:
                    blocos_finais.append(bloco_final_pedaco)
        elif b:  # Adiciona apenas se não for vazio
            blocos_finais.append(b)

    return blocos_finais


def traduzir_blocos(
    blocos: list[str], model: genai.GenerativeModel, idioma_destino: str
) -> list[str]:
    """Traduz uma lista de blocos de texto usando o modelo Gemini."""
    blocos_traduzidos = []
    total = len(blocos)
    # Usando a barra de progresso do rich com descrição dinâmica
    for i, bloco in enumerate(
        track(
            blocos,
            description=f"[cyan]🌐 Traduzindo {total} blocos para {idioma_destino}...[/cyan]",
            console=console,
        )
    ):
        # Mensagem específica para cada bloco (opcional, pode ser removida se a barra for suficiente)
        # console.print(f"[blue]Processando bloco {i+1}/{total} ({len(bloco)} caracteres)...[/blue]")

        prompt = f"Traduza o seguinte texto Markdown para {idioma_destino}. Mantenha a formatação original do Markdown, incluindo blocos de código, listas, cabeçalhos, etc., o máximo possível. Não adicione introduções ou conclusões à tradução, apenas traduza o texto fornecido:\n\n---\n{bloco}\n---"

        tentativas = 3
        delay = 2  # segundos
        for tentativa in range(tentativas):
            try:
                response = model.generate_content(prompt)
                # Verifica se a resposta tem partes e texto
                if response.parts:
                    traducao = response.text
                    blocos_traduzidos.append(traducao)
                    # console.print(f"[green]Bloco {i+1} traduzido.[/green]") # Opcional, barra de progresso já indica
                    break
                elif response.candidates and response.candidates[0].content.parts:
                    traducao = response.candidates[0].content.text
                    blocos_traduzidos.append(traducao)
                    # console.print(f"[green]Bloco {i+1} traduzido (via candidato).[/green]") # Opcional
                    break
                else:
                    console.print(
                        f"[yellow]⚠️ Aviso: Resposta inesperada para bloco {i+1} (tentativa {tentativa+1}). Sem conteúdo útil.[/yellow]"
                    )
                    if tentativa < tentativas - 1:
                        console.print(
                            f"[yellow]⏳ Aguardando {int(delay)}s antes de tentar novamente...[/yellow]"
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        rprint(
                            Panel(
                                f"Não foi possível extrair tradução para o bloco {i+1} após {tentativas} tentativas.\n"
                                f"Resposta final recebida: {response}",
                                title=f"[bold red]❌ Erro de Tradução (Bloco {i+1})[/bold red]",
                                border_style="red",
                                expand=False,
                            )
                        )
                        blocos_traduzidos.append(
                            f"### [ERRO NA TRADUÇÃO - SEM CONTEÚDO OBTIDO APÓS RETENTATIVAS]\n\n{bloco}\n\n###"
                        )

            except Exception as e:
                error_message = f"Erro na API ao traduzir bloco {i+1} (tentativa {tentativa+1}): {e}"
                console.print(
                    f"[yellow]⚠️ {error_message}[/yellow]"
                )  # Aviso durante retentativas

                if "API key not valid" in str(e):
                    rprint(
                        Panel(
                            "Erro crítico: A chave da API não é válida.\n🔑 Verifique 'config.ini'.",
                            title="[bold red]❌ Erro de Autenticação API[/bold red]",
                            border_style="red",
                            expand=False,
                        )
                    )
                    sys.exit(1)

                is_rate_limit = "resource_exhausted" in str(e).lower() or "429" in str(
                    e
                )

                if tentativa < tentativas - 1:
                    wait_time = delay * (2**tentativa)  # Backoff exponencial mais claro
                    console.print(
                        f"[yellow]⏳ Aguardando {int(wait_time)}s antes de tentar novamente...[/yellow]"
                        + (" (Limite de taxa 📈)" if is_rate_limit else "")
                    )
                    time.sleep(wait_time)
                else:  # Última tentativa falhou
                    title_suffix = (
                        "Limite de Taxa Excedido" if is_rate_limit else "Erro na API"
                    )
                    rprint(
                        Panel(
                            f"Falha ao traduzir o bloco {i+1} após {tentativas} tentativas.\n"
                            f"Último erro: {e}",
                            title=f"[bold red]❌ {title_suffix} (Bloco {i+1})[/bold red]",
                            border_style="red",
                            expand=False,
                        )
                    )
                    error_tag = "LIMITE DE TAXA" if is_rate_limit else f"ERRO API: {e}"
                    blocos_traduzidos.append(
                        f"### [ERRO NA TRADUÇÃO - {error_tag}]\n\n{bloco}\n\n###"
                    )
                    break  # Sai do loop de tentativas para este bloco

        # Pequeno delay opcional entre chamadas bem-sucedidas para evitar sobrecarregar a API
        # time.sleep(0.5) # Reduzido ou removido se a API estiver estável

    return blocos_traduzidos


def salvar_traducao(filepath: Path, blocos_traduzidos: list[str]):
    """Junta os blocos traduzidos e salva no arquivo de saída."""
    conteudo_final = "\n\n".join(blocos_traduzidos)
    try:
        filepath.write_text(conteudo_final, encoding="utf-8")
        console.print(
            f"[bold green]✅ Tradução salva com sucesso em:[/bold green] [cyan]{filepath}[/cyan]"
        )
    except IOError as e:
        rprint(
            Panel(
                f"[bold]Erro ao salvar arquivo de saída {filepath}:[/bold] {e}",
                title="[bold red]❌ Erro de Escrita[/bold red]",
                border_style="red",
                expand=False,
            )
        )


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Traduz um arquivo Markdown usando a API Gemini.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # Mostra os padrões na ajuda
    )
    parser.add_argument(
        "arquivo_entrada", help="Caminho para o arquivo Markdown de entrada (.md)."
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Caminho para o arquivo de saída. Se não especificado, imprime na tela.",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default="Português Brasileiro",
        help="Idioma de destino para a tradução.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.ini",
        help="Caminho para o arquivo de configuração.",
    )
    args = parser.parse_args()

    input_path = Path(args.arquivo_entrada)
    config_path = Path(args.config)
    idioma_destino = args.lang

    # --- Configuração ---
    config = ler_config(config_path)
    # Lê a string de chaves separadas por vírgula
    api_keys_str = config.get("gemini", "api_keys", fallback="")
    model_name = config.get("gemini", "model_name", fallback="gemini-1.5-flash")

    # Divide a string em uma lista, remove espaços em branco e filtra chaves vazias
    api_keys_list = [key.strip() for key in api_keys_str.split(",") if key.strip()]

    # Valida se a lista de chaves não está vazia ou contém placeholders
    placeholders = [
        "SUA_API_KEY_AQUI",
        "CHAVE_API_1",
        "CHAVE_API_2",
        "CHAVE_API_3_ETC",
    ]  # Adicione outros placeholders se usar
    if not api_keys_list or any(key in placeholders for key in api_keys_list):
        rprint(
            Panel(
                f"🔑 Nenhuma chave de API válida encontrada em 'api_keys' no arquivo [cyan]{config_path}[/cyan].\n"
                "Por favor, adicione suas chaves da API Gemini separadas por vírgula.",
                title="[bold red]❌ API Keys Ausentes ou Inválidas[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)

    # Escolhe aleatoriamente uma chave da lista
    try:
        selected_api_key = random.choice(api_keys_list)
        console.print("[green]🔑 Chave de API selecionada aleatoriamente.[/green]")
    except IndexError:
        # Segurança extra, embora a validação anterior deva pegar isso
        rprint(
            Panel(
                f"🔑 Erro inesperado: A lista de chaves de API está vazia após o processamento em [cyan]{config_path}[/cyan].",
                title="[bold red]❌ Erro Interno - Chaves API[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)

    configurar_gemini(selected_api_key)  # Usa a chave selecionada
    try:
        model = genai.GenerativeModel(model_name)
        console.print(
            f"[green]✨ Modelo Gemini inicializado:[/green] [bold magenta]{model_name}[/bold magenta]"
        )
    except Exception as e:
        rprint(
            Panel(
                f"[bold]Erro ao inicializar o modelo Gemini '{model_name}':[/bold] {e}\n"
                f"⚙️ Verifique o nome do modelo em [cyan]{config_path}[/cyan] e sua conexão.",
                title="[bold red]❌ Falha na Inicialização do Modelo[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        sys.exit(1)

    # --- Leitura e Processamento ---
    console.print(f"[blue]📄 Carregando arquivo:[/blue] [cyan]{input_path}[/cyan]")
    conteudo_original = carregar_markdown(input_path)
    if conteudo_original is None:
        sys.exit(1)  # Erro já foi impresso por carregar_markdown

    total_caracteres = len(conteudo_original)
    console.print(
        f"[green]👍 Arquivo carregado:[/green] {total_caracteres} caracteres."
    )

    console.print(
        f"[blue]✂️ Dividindo texto em blocos (máx ~{MAX_CHUNK_SIZE} caracteres)...[/blue]"
    )
    blocos = dividir_texto_em_blocos(conteudo_original, MAX_CHUNK_SIZE)

    if not blocos:
        console.print(
            "[yellow]⚠️ Aviso:[/yellow] Nenhum conteúdo textual significativo encontrado para traduzir."
        )
        sys.exit(0)

    console.print(
        f"[green]🧩 Texto pronto:[/green] {len(blocos)} blocos para tradução."
    )

    # --- Tradução ---
    console.print(
        f"[blue]➡️ Iniciando tradução para:[/blue] [bold]{idioma_destino}[/bold]"
    )
    blocos_traduzidos = traduzir_blocos(blocos, model, idioma_destino)

    # --- Saída ---
    if args.output:
        output_path = Path(args.output)
        # Garante que o diretório de saída exista
        output_path.parent.mkdir(parents=True, exist_ok=True)
        salvar_traducao(output_path, blocos_traduzidos)
    else:
        console.rule("[bold blue]📜 Tradução Completa (Saída no Console)", style="blue")
        for i, bloco in enumerate(blocos_traduzidos):
            rprint(Markdown(bloco))
            if i < len(blocos_traduzidos) - 1:  # Adiciona separador visual entre blocos
                console.print("---", style="dim cyan")
        console.rule("[bold blue]🏁 Fim da Tradução", style="blue")


if __name__ == "__main__":
    main()
