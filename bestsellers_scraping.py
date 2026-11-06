import random
import re
import time
 
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright
 
# Adicione outras categorias aqui (copie a URL do navegador).
# Cada URL gera as páginas 1 e 2.
URLS = [
    "https://www.amazon.com.br/gp/bestsellers/books",
]
PAGINAS = [1, 2]
PAUSA = (8, 15)  # segundos entre páginas
 
 
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
 
 
def extrair_asin(href):
    m = re.search(r"/dp/([A-Z0-9]{10})", href or "")
    return m.group(1) if m else None
 
 
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
 
 
def rolar(page, vezes=8):
    """Rola a página para carregar os itens que aparecem aos poucos."""
    for _ in range(vezes):
        page.mouse.wheel(0, 2500)
        time.sleep(random.uniform(0.8, 1.5))
 
 
def extrair_item(item):
    link = item.select_one("a[href*='/dp/']")
    img = item.select_one("img")
    rank = item.select_one("span.zg-bdg-text")
    nota = item.select_one("span.a-icon-alt")
    preco = item.select_one("span.a-price, span[class*='price']")
    avaliacoes = item.select_one("a[href*='product-reviews'] span")
 
    titulo = img.get("alt") if img and img.get("alt") else None
    if not titulo and link:
        titulo = link.get_text(strip=True)
 
    return {
        "asin": extrair_asin(link["href"]) if link else None,
        "rank": rank.get_text(strip=True).lstrip("#") if rank else None,
        "titulo": titulo,
        "preco_reais": limpar_preco(preco.get_text(" ", strip=True)) if preco else None,
        "nota": limpar_nota(nota.get_text()) if nota else None,
        "n_avaliacoes": limpar_inteiro(avaliacoes.get_text()) if avaliacoes else None,
        "url": "https://www.amazon.com.br" + link["href"].split("?")[0] if link else None,
    }
 
 
def main():
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
            for base in URLS:
                for pg in PAGINAS:
                    url = f"{base}?pg={pg}"
                    print(f"Coletando: {url}")
                    if not abrir(page, url, "div#gridItemRoot"):
                        print("  sem resultados nessa página")
                        continue
                    rolar(page)
                    soup = BeautifulSoup(page.content(), "html.parser")
                    itens = soup.select("div#gridItemRoot")
                    print(f"  {len(itens)} livros encontrados")
                    livros.extend(extrair_item(i) for i in itens)
                    time.sleep(random.uniform(*PAUSA))
        except KeyboardInterrupt:
            print("\nInterrompido. Salvando o que já foi coletado.")
        finally:
            contexto.close()
 
    df = pd.DataFrame(livros)
    if df.empty:
        print("Nenhum livro coletado. Confira o bloqueio ou os seletores.")
        return
 
    df = df.dropna(subset=["titulo"]).drop_duplicates(subset=["asin"])
    df.to_csv("livros_bestsellers.csv", index=False, encoding="utf-8-sig")
    print(f"{len(df)} livros salvos em livros_bestsellers.csv")
    print(df.head())
 
 
if __name__ == "__main__":
    main()