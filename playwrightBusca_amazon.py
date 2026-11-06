
import random
import re
import time
from urllib.parse import quote

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

META = 1000
PAGINAS_POR_TERMO = 7
TERMOS = [
    "romance", "ficção", "fantasia", "suspense", "autoajuda",
    "negócios", "finanças", "biografia", "história", "ciências",
    "tecnologia", "programação", "psicologia", "filosofia", "infantil",
    "juvenil", "quadrinhos", "religião", "culinária", "didáticos",
    "literatura brasileira", "direito", "saúde",
]
PAUSA = (8, 15)  # segundos entre páginas
SELETOR = "div[data-component-type='s-search-result']"


def limpar_preco(texto):
    """Converte 'R$ 1.234,56' em 1234.56."""
    m = re.search(r"([\d\.]+,\d{2})", texto or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def limpar_nota(texto):
    """Converte '4,7 de 5 estrelas' em 4.7."""
    m = re.search(r"(\d+,\d+)", texto or "")
    return float(m.group(1).replace(",", ".")) if m else None


def limpar_inteiro(texto):
    """Converte '1.234' ou '(1.234)' em 1234."""
    digitos = re.sub(r"\D", "", texto or "")
    return int(digitos) if digitos else None


def esta_bloqueado(page):
    """Detecta CAPTCHA ou página de erro da Amazon."""
    titulo = (page.title() or "").lower()
    if "algo deu errado" in titulo or "robot" in titulo:
        return True
    if page.query_selector("input#captchacharacters"):
        return True
    if page.query_selector("form[action*='validateCaptcha']"):
        return True
    return False


def abrir(page, url, seletor):
    """Abre a URL; se bloquear, pede para você resolver e tenta de novo."""
    for _ in range(5):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except PWTimeout:
            print("  página demorou demais; tentando de novo...")
            continue

        if esta_bloqueado(page):
            print("\n  >> A Amazon bloqueou ou pediu CAPTCHA.")
            print("  >> Resolva o CAPTCHA na janela do navegador (se houver).")
            print("  >> Se for só 'Algo deu errado', espere 1 minuto.")
            input("  >> Depois aperte Enter aqui para continuar... ")
            continue

        try:
            page.wait_for_selector(seletor, timeout=15000)
        except PWTimeout:
            return False
        return True

    print("  Não consegui abrir a página depois de várias tentativas.")
    return False


def rolar(page, vezes=4):
    """Rola a página para carregar os itens que aparecem aos poucos."""
    for _ in range(vezes):
        page.mouse.wheel(0, 2500)
        time.sleep(random.uniform(0.8, 1.5))


def extrair_item(item, termo):
    titulo = item.select_one("h2")
    preco = item.select_one("span.a-price span.a-offscreen")
    nota = item.select_one("span.a-icon-alt")
    avaliacoes = item.select_one("span.s-underline-text")
    link = item.select_one("a[href*='/dp/']")

    return {
        "asin": item.get("data-asin"),
        "titulo": titulo.get_text(" ", strip=True) if titulo else None,
        "preco_reais": limpar_preco(preco.get_text()) if preco else None,
        "nota": limpar_nota(nota.get_text()) if nota else None,
        "n_avaliacoes": limpar_inteiro(avaliacoes.get_text()) if avaliacoes else None,
        "termo_busca": termo,
        "url": "https://www.amazon.com.br" + link["href"].split("?")[0] if link else None,
    }


def salvar(livros):
    df = pd.DataFrame(livros)
    if not df.empty:
        df = df.dropna(subset=["titulo"])
        df.to_csv("livros_busca.csv", index=False, encoding="utf-8-sig")
    return df


def main():
    vistos = set()
    livros = []

    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            "perfil_amazon",
            headless=False,
            locale="pt-BR",
            viewport={"width": 1280, "height": 900},
        )
        page = contexto.pages[0] if contexto.pages else contexto.new_page()

        try:
            for termo in TERMOS:
                for pg in range(1, PAGINAS_POR_TERMO + 1):
                    print(f"[{len(livros)}/{META}] '{termo}' página {pg}")
                    url = f"https://www.amazon.com.br/s?k={quote(termo)}&i=stripbooks&page={pg}"
                    if not abrir(page, url, SELETOR):
                        break                       # acabaram as páginas desse termo

                    rolar(page)
                    soup = BeautifulSoup(page.content(), "html.parser")
                    for item in soup.select(SELETOR):
                        dados = extrair_item(item, termo)
                        if dados["asin"] and dados["asin"] not in vistos:
                            vistos.add(dados["asin"])
                            livros.append(dados)

                    salvar(livros)  # salva o progresso a cada página
                    if len(livros) >= META:
                        raise StopIteration
                    time.sleep(random.uniform(*PAUSA))
        except StopIteration:
            print("Meta atingida.")
        except KeyboardInterrupt:
            print("\nInterrompido. Salvando o que já foi coletado.")
        finally:
            contexto.close()

    df = salvar(livros)
    if df.empty:
        print("Nenhum livro coletado. Confira o bloqueio ou os seletores.")
        return
    print(f"{len(df)} livros salvos em livros_busca.csv")
    print(df.head())


if __name__ == "__main__":
    main()