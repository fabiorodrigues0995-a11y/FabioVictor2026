
import json
import socket
import argparse
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import (
    Request,
    HTTPRedirectHandler,
    build_opener,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data.json"
USER_AGENT = "MostreSuaEmpresa-LinkChecker/1.0"


class NoRedirectHandler(HTTPRedirectHandler):
    """Permite registrar redirecionamentos sem segui-los automaticamente."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_urls(file_path=DATA_FILE):
    """Carrega as URLs do arquivo JSON."""
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("O arquivo data.json deve conter uma lista.")

    urls = []

    for item in data:
        if not isinstance(item, dict):
            continue

        url = item.get("url")

        if isinstance(url, str) and url.strip():
            urls.append({
                "name": item.get("name", "Sem nome"),
                "url": url.strip(),
            })

    return urls


def request_url(url, method, timeout):
    """Executa uma requisição e retorna seu status HTTP."""
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT},
        method=method,
    )

    opener = build_opener(NoRedirectHandler())

    with opener.open(request, timeout=timeout) as response:
        return response.status


def check_url(url, timeout=10):
    """Classifica o resultado da verificação de uma URL."""
    try:
        try:
            status = request_url(url, "HEAD", timeout)
        except HTTPError as error:
            status = error.code

            # Alguns servidores não aceitam o método HEAD.
            if status in (403, 405, 501):
                try:
                    status = request_url(url, "GET", timeout)
                except HTTPError as get_error:
                    status = get_error.code

        if 200 <= status < 300:
            return "ATIVO", status

        if 300 <= status < 400:
            return "REDIRECIONAMENTO", status

        return "FALHA HTTP", status

    except HTTPError as error:
        if 300 <= error.code < 400:
            return "REDIRECIONAMENTO", error.code

        return "FALHA HTTP", error.code

    except URLError as error:
        reason = error.reason

        if isinstance(reason, (socket.timeout, TimeoutError)):
            return "TIMEOUT", str(reason)

        if isinstance(reason, socket.gaierror):
            return "ERRO DNS", str(reason)

        return "ERRO DE CONEXÃO", str(reason)

    except (socket.timeout, TimeoutError):
        return "TIMEOUT", "Tempo limite excedido"

    except (ValueError, OSError) as error:
        return "ERRO", str(error)


def main():
    parser = argparse.ArgumentParser(
        description="Verifica os links cadastrados em data.json."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
        help="Tempo máximo de espera em segundos (padrão: 10).",
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout deve ser maior que zero.")

    try:
        urls = load_urls()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Erro ao ler {DATA_FILE}: {error}")
        return 1

    if not urls:
        print("Nenhuma URL válida foi encontrada em data.json.")
        return 1

    totals = {
        "ATIVO": 0,
        "REDIRECIONAMENTO": 0,
        "FALHA HTTP": 0,
        "TIMEOUT": 0,
        "ERRO DNS": 0,
        "ERRO DE CONEXÃO": 0,
        "ERRO": 0,
    }

    print(f"Verificando {len(urls)} URLs...\n")

    for item in urls:
        status, detail = check_url(item["url"], args.timeout)
        totals[status] = totals.get(status, 0) + 1

        print(
            f"[{status}] {item['name']} - "
            f"{item['url']} (HTTP: {detail})"
        )

    print("\n--- RESUMO ---")

    for status, total in totals.items():
        print(f"{status}: {total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
