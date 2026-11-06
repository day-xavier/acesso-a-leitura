"""
Monta o dataset final de livros da amazon.com.br visitando a página de cada
livro (Playwright) e salva em livros_final.csv.

Colunas geradas:
    id, titulo, editora, ano_publicacao, preco_reais, genero, formato,
    idioma, numero_paginas, avaliacao, qtd_avaliacoes, url

Como funciona:
- Lê os ASINs de livros_busca.csv e/ou livros_bestsellers.csv (rode antes
  os scripts de busca e de mais vendidos).
- Visita a página de cada livro. Editora, ano, idioma e número de páginas
  só existem lá, por isso este script é mais lento que os outros.
- "id" é o ASIN (código único do livro na Amazon).
- "genero" é a última categoria do caminho de navegação da página do livro
  (ex.: Livros > Literatura e Ficção > Romance). Se faltar, usa a coluna
  genero (mais vendidos) ou termo_busca (busca) do CSV de entrada.

Retomada:
- Faz no máximo MAX_POR_EXECUCAO livros por vez, para reduzir bloqueio.
- O CSV é salvo a cada 10 livros. Ao rodar de novo, o script pula os livros
  que já estão em livros_final.csv e continua dali.

O navegador abre numa janela visível. Se aparecer CAPTCHA, VOCÊ resolve na
janela e aperta Enter no terminal para o script continuar.

Instalação (uma vez só):
    pip install playwright beautifulsoup4 pandas
    playwright install chromium

Uso:
    python scraper_detalhes_playwright.py

Observações:
- Nem todo livro informa todos os campos. O que faltar fica vazio.
- Os seletores HTML da Amazon mudam. Se alguma coluna vier sempre vazia,
  inspecione a página de um livro e ajuste extrair_livro().
- A Amazon restringe scraping nos termos de uso. Rode poucas vezes e
  cite no relatório como e quando coletou.
"""

import os
import random
import re
import time

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

ARQUIVOS_ENTRADA = ["livros_busca.csv", "livros_bestsellers.csv"]
SAIDA = "livros_final.csv"
MAX_POR_EXECUCAO = 150
SALVAR_A_CADA = 10
PAUSA = (6, 12)  # segundos entre livros

COLUNAS = [
    "id", "titulo", "editora", "ano_publicacao", "preco_reais", "genero",
    "formato", "idioma", "numero_paginas", "avaliacao", "qtd_avaliacoes", "url",
]

# palavras que indicam o formato do livro -> rótulo que vai para o CSV
FORMATOS = [
    ("kindle", "E-book"),
    ("e-book", "E-book"),
    ("ebook", "E-book"),
    ("audiolivro", "Audiolivro"),
    ("audiobook", "Audiolivro"),
    ("audible", "Audiolivro"),
    ("capa dura", "Capa dura"),
    ("capa comum", "Capa comum"),
    ("brochura", "Brochura"),
    ("bolso", "Edição de bolso"),
    ("espiral", "Espiral"),
]


# ------------------------------ utilidades ------------------------------


def limpar_texto(texto):
    """Remove marcas invisíveis de direção de texto e espaços estranhos."""
    texto = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", texto or "")
    return texto.replace("\xa0", " ").strip()


def limpar_preco(texto):
    """Converte 'R$ 1.234,56' em 1234.56."""
    m = re.search(r"([\d\.]+,\d{2})", texto or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def limpar_nota(texto):
    """Converte '4,7 de 5 estrelas' em 4.7."""
    m = re.search(r"(\d+,\d+|\d+)\s*de\s*5", texto or "")
    return float(m.group(1).replace(",", ".")) if m else None


def limpar_inteiro(texto):
    """Converte '1.234 avaliações' em 1234."""
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


# ------------------------- leitura da página do livro -------------------


def textos_de_detalhes(soup):
    """Junta os textos das seções de detalhes do produto (editora, idioma...)."""
    seletores = ", ".join([
        "#detailBullets_feature_div li",
        "#productDetails_detailBullets_sections1 tr",
        "#productDetails_techSpec_section_1 tr",
        "#rpi-attribute-book_details-language",
        "#rpi-attribute-book_details-publisher",
        "#rpi-attribute-book_details-publication_date",
        "#rpi-attribute-book_details-ebook_pages",
        "#rpi-attribute-book_details-fiona_pages",
    ])
    return [limpar_texto(el.get_text(" ", strip=True)) for el in soup.select(seletores)]


def normalizar_formato(texto):
    """Procura uma palavra de formato (capa dura, kindle...) no texto."""
    baixo = (texto or "").lower()
    for chave, rotulo in FORMATOS:
        if chave in baixo:
            return rotulo
    return None


def descobrir_formato(soup, textos, asin):
    """Descobre o formato do livro: capa comum, capa dura, e-book etc."""
    candidatos = []
    selecionado = soup.select_one(
        "#tmmSwatches .swatchElement.selected, #tmmSwatches .a-button-selected"
    )
    if selecionado:
        candidatos.append(selecionado.get_text(" ", strip=True).split("R$")[0])
    subtitulo = soup.select_one("#productSubtitle")
    if subtitulo:
        candidatos.append(subtitulo.get_text(" ", strip=True))
    # nos detalhes, a linha de páginas costuma trazer o formato ("Capa comum : 288 páginas")
    candidatos.extend(t for t in textos if re.search(r"p[áa]ginas", t, re.I))

    for texto in candidatos:
        rotulo = normalizar_formato(texto)
        if rotulo:
            return rotulo

    if str(asin).startswith("B0"):
        return "E-book (estimado pelo ASIN)"
    return None


def extrair_livro(soup, entrada):
    """Lê uma página de livro e devolve um dicionário com as colunas finais."""
    titulo = soup.select_one("#productTitle")
    preco = (
        soup.select_one("#corePrice_feature_div span.a-offscreen")
        or soup.select_one("span.a-price span.a-offscreen")
    )
    nota = soup.select_one("#acrPopover") or soup.select_one("#averageCustomerReviews span.a-icon-alt")
    qtd = soup.select_one("#acrCustomerReviewText")
    trilha = [limpar_texto(a.get_text()) for a in soup.select("#wayfinding-breadcrumbs_feature_div a")]
    trilha = [t for t in trilha if t]

    textos = textos_de_detalhes(soup)
    editora = ano = idioma = paginas = None
    for t in textos:
        m = re.match(r"^Editora\s*:?\s*(.+)$", t, re.I)
        if m and not editora:
            valor = m.group(1)
            editora = valor.split("(")[0].strip(" ;")
            a = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", valor)
            if a and not ano:
                ano = int(a.group(1))
            continue
        m = re.match(r"^Data da publica[çc][ãa]o\s*:?\s*(.+)$", t, re.I)
        if m and not ano:
            a = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", m.group(1))
            ano = int(a.group(1)) if a else None
            continue
        m = re.match(r"^Idioma\s*:?\s*(.+)$", t, re.I)
        if m and not idioma:
            idioma = m.group(1).strip()
            continue
        m = re.search(r"(\d[\d\.]*)\s*p[áa]ginas", t, re.I)
        if m and not paginas:
            paginas = limpar_inteiro(m.group(1))

    # valores de reserva vindos do CSV de entrada
    genero = trilha[-1] if trilha else None
    if not genero:
        for chave in ("genero", "termo_busca"):
            valor = entrada.get(chave)
            if isinstance(valor, str) and valor and valor != "Não identificado":
                genero = valor
                break

    preco_final = limpar_preco(preco.get_text()) if preco else None
    if not preco_final:  # vazio ou zero (e-book "grátis" no Kindle Unlimited)
        reserva = entrada.get("preco_reais")
        preco_final = float(reserva) if pd.notna(reserva) and float(reserva) > 0 else None

    nota_texto = (nota.get("title") or nota.get_text()) if nota else None
    nota_final = limpar_nota(nota_texto)
    if nota_final is None and pd.notna(entrada.get("nota")):
        nota_final = float(entrada["nota"])

    return {
        "id": entrada["asin"],
        "titulo": titulo.get_text(" ", strip=True) if titulo else entrada.get("titulo"),
        "editora": editora,
        "ano_publicacao": ano,
        "preco_reais": preco_final,
        "genero": genero,
        "formato": descobrir_formato(soup, textos, entrada["asin"]),
        "idioma": idioma,
        "numero_paginas": paginas,
        "avaliacao": nota_final,
        "qtd_avaliacoes": limpar_inteiro(qtd.get_text()) if qtd else None,
        "url": f"https://www.amazon.com.br/dp/{entrada['asin']}",
    }


def carregar_entrada():
    partes = []
    for arq in ARQUIVOS_ENTRADA:
        if os.path.exists(arq):
            partes.append(pd.read_csv(arq, dtype={"asin": str}))
            print(f"Lendo {arq}")
    if not partes:
        print("Nenhum CSV de entrada encontrado. Rode antes o script de busca "
              "ou o de mais vendidos.")
        return None
    df = pd.concat(partes, ignore_index=True)
    df = df.dropna(subset=["asin"]).drop_duplicates(subset=["asin"])
    return df


def salvar(registros):
    df = pd.DataFrame(registros, columns=COLUNAS)
    df.to_csv(SAIDA, index=False, encoding="utf-8-sig")


def main():
    entrada = carregar_entrada()
    if entrada is None:
        return

    registros = []
    if os.path.exists(SAIDA):
        registros = pd.read_csv(SAIDA, dtype={"id": str}).to_dict("records")
    feitos = {r["id"] for r in registros}

    pendentes = [r for r in entrada.to_dict("records") if r["asin"] not in feitos]
    total_pendente = len(pendentes)
    pendentes = pendentes[:MAX_POR_EXECUCAO]
    print(f"{len(feitos)} livros já feitos; {total_pendente} pendentes; "
          f"vou coletar {len(pendentes)} agora.\n")

    if not pendentes:
        print("Nada a fazer.")
        return

    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            "perfil_amazon",
            headless=False,
            locale="pt-BR",
            viewport={"width": 1280, "height": 900},
        )
        page = contexto.pages[0] if contexto.pages else contexto.new_page()

        try:
            for i, linha in enumerate(pendentes, start=1):
                print(f"[{i}/{len(pendentes)}] {linha['asin']}")
                url = f"https://www.amazon.com.br/dp/{linha['asin']}"
                if not abrir(page, url, "#productTitle"):
                    print("  página sem título; pulando")
                    continue
                soup = BeautifulSoup(page.content(), "html.parser")
                registros.append(extrair_livro(soup, linha))

                if i % SALVAR_A_CADA == 0:
                    salvar(registros)
                time.sleep(random.uniform(*PAUSA))
        except KeyboardInterrupt:
            print("\nInterrompido. Salvando o que já foi coletado.")
        finally:
            contexto.close()

    salvar(registros)
    restantes = total_pendente - len(pendentes)
    print(f"\n{len(registros)} livros em {SAIDA}.")
    if restantes > 0:
        print(f"Ainda faltam {restantes}. Rode o script de novo para continuar.")
    df = pd.DataFrame(registros, columns=COLUNAS)
    print(df.head())


if __name__ == "__main__":
    main()