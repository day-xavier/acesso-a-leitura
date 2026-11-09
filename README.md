# Análise de dados sobre o acesso à leitura na região Nordeste do Brasil

O projeto pretende analisar dados relacionados ao acesso à leitura na região Nordeste, com ênfase em fatores socioeconômicos que podem influenciar a constância em ler, com o objetivo de identificar padrões e desigualdades e apoiar conclusões baseadas em dados.

## Participantes
- Dayanna Hevellyn Ferreira Xavier
- Pedro Henrique de Macedo Alves
- Sophia de Carvalho Beltrão
- Yuri Augusto Cardoso de Melo

---

## Conjunto de dados

Os dados combinam três dimensões do acesso à leitura: **condições socioeconômicas da população**, **oferta de bibliotecas** e **preço dos livros**.

Os **dados censitários** vêm do Censo Demográfico 2022 do IBGE, o mais recente disponível, e trazem para cada município a população, a taxa de alfabetização, o nível de instrução e a renda domiciliar per capita. Eles mostram o perfil socioeconômico de quem pode (ou não) ter acesso à leitura.

O **cadastro de bibliotecas** do Sistema Nacional de Bibliotecas Públicas (SNBP 2025-2026) lista as bibliotecas públicas e comunitárias de cada município, com tipo, vínculo e endereço. No Nordeste são 1.655 bibliotecas em 1.095 municípios.

Os **dados de livros** foram coletados na Amazon Brasil (busca por gênero, lista de mais vendidos e página de cada livro) e em uma livraria física. Trazem preço, gênero, formato, avaliações e outras informações dos livros, servindo de referência para comparar o custo da leitura com a renda da população.

Os arquivos do Censo e do SNBP abrangem todo o Brasil. O recorte para a região Nordeste (municípios com código IBGE iniciado em 2: MA, PI, CE, RN, PB, PE, AL, SE e BA, 1.794 municípios) será feito na etapa de limpeza, mantendo os arquivos originais intactos.

**Link dos dados:** [Pasta no Google Drive](https://drive.google.com/drive/folders/1s_wec3xD50dsSyjNUdQBhCb587kY3pND)

| Arquivo | Fonte | Linhas | Descrição |
|---|---|---|---|
| `data/censo2022_populacao.csv` | IBGE – SIDRA, tabela 4709 | 5.570 municípios | População residente |
| `data/censo2022_alfabetizacao.csv` | IBGE – SIDRA, tabela 9543 | 5.570 municípios | Taxa de alfabetização (15 anos ou mais) |
| `data/censo2022_escolaridade.csv` | IBGE – SIDRA, tabela 10061 | 5.570 municípios | Distribuição por nível de instrução (18 anos ou mais) |
| `data/censo2022_renda.csv` | IBGE – SIDRA, tabela 10295 | 5.570 municípios × 2 variáveis | Rendimento domiciliar per capita médio e mediano |
| `data/cadastrodebibliotecas-snbp2025-2026.xlsx` | SNBP / Biblioteca Nacional | 4.691 bibliotecas | Cadastro de bibliotecas públicas e comunitárias |
| `data/livros_busca.csv` | Amazon Brasil (busca) | 1.007 livros | Livros encontrados na busca por gênero |
| `data/livros_bestsellers.csv` | Amazon Brasil (mais vendidos) | 100 livros | Ranking dos livros mais vendidos |
| `data/livros_amazon.csv` | Amazon Brasil (página do livro) | 1.007 livros | Detalhes de cada livro |
| `data/LOJA_FISICA.csv` | Leitura (Livraria física) | 95 livros | Preços em loja física |

---

## Processo de coleta

### Dados censitários (IBGE)
Os dados foram baixados manualmente no **SIDRA** (sidra.ibge.gov.br), o sistema de tabelas do IBGE, entre 7 e 8 de novembro de 2026. Em cada tabela foram feitas as mesmas escolhas:

1. **Variável:** apenas a de interesse (ex.: "Taxa de alfabetização das pessoas de 15 anos ou mais").
2. **Ano:** 2022.
3. **Filtros** (sexo, cor ou raça, grupo de idade): somente a categoria **Total**, para obter o valor do município inteiro.
   - Na tabela 10061, foram marcadas as 4 categorias de **nível de instrução**, que são o dado de interesse.
4. **Unidade territorial:** todos os municípios do Brasil (5.570).
5. **Download:** formato CSV (BR), download imediato, com as opções "Exibir códigos dos territórios" e "Exibir nomes dos territórios" marcadas.

A conferência após o download mostrou 5.570 municípios em cada arquivo, sem valores faltantes. A soma da população é de 203.080.756 pessoas, igual ao total oficial do Censo 2022.

### Cadastro de bibliotecas (SNBP)
Planilha do cadastro de bibliotecas do Sistema Nacional de Bibliotecas Públicas, edição 2025-2026, baixada em 07 de novembro de 2026, através do Portal de Dados do Ministério da Cultura (dados.cultura.gov.br).

### Livros da Amazon
Coletados por raspagem (web scraping) com **Python**, **Playwright** e **BeautifulSoup**, em três etapas:

1. `playwrightBusca_amazon.py`: pesquisa livros por termos de gênero (romance, ficção, fantasia, suspense, autoajuda etc.), percorre as páginas de resultado e salva título, preço, nota e número de avaliações em `livros_busca.csv`.
2. `bestsellers_scraping.py`: coleta as duas páginas da lista de mais vendidos em livros e salva a posição no ranking em `livros_bestsellers.csv`.
3. `playwright_amazon.py`: abre a página de cada livro coletado nas etapas anteriores e extrai editora, ano, gênero, formato, idioma e número de páginas, gerando `livros_amazon.csv`.

Os scripts usam pausas aleatórias entre as páginas e salvam o progresso aos poucos, para reduzir bloqueios. Quando a Amazon pedia CAPTCHA, ele era resolvido manualmente na janela do navegador.

### Loja física
Preços anotados manualmente na livraria Leitura, em João Pessoa-PB, entre os dias 01 e 08 de novembro de 2026. Livros sem preço disponível foram marcados com `X`.

---

## Dicionário de dados

### `censo2022_populacao.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| Cód. | Código IBGE do município (7 dígitos) | 2611606 |
| Município | Nome do município e sigla da UF | Recife (PE) |
| 2022 | População residente em 2022 (pessoas) | 1488920 |

### `censo2022_alfabetizacao.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| Cód. | Código IBGE do município | 2611606 |
| Município | Nome do município e sigla da UF | Recife (PE) |
| Idade | Grupo de idade (sempre "Total") | Total |
| Total | Taxa de alfabetização das pessoas de 15 anos ou mais (%) | 94,52 |

### `censo2022_escolaridade.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| Cód. | Código IBGE do município | 2611606 |
| Município | Nome do município e sigla da UF | Recife (PE) |
| Sexo | Sempre "Total" | Total |
| Cor ou raça | Sempre "Total" | Total |
| Total | Soma das categorias (sempre 100%) | 100,00 |
| Sem instrução e fundamental incompleto | % das pessoas de 18 anos ou mais | 22,75 |
| Fundamental completo e médio incompleto | % das pessoas de 18 anos ou mais | 12,28 |
| Médio completo e superior incompleto | % das pessoas de 18 anos ou mais | 38,85 |
| Superior completo | % das pessoas de 18 anos ou mais | 26,12 |

### `censo2022_renda.csv`
O arquivo tem dois blocos, um embaixo do outro: o primeiro com o rendimento **médio** e o segundo com o **mediano**.

| Coluna | Descrição | Exemplo |
|---|---|---|
| Cód. | Código IBGE do município | 2611606 |
| Município | Nome do município e sigla da UF | Recife (PE) |
| Grupo de idade | Sempre "Total" | Total |
| Total (bloco 1) | Rendimento nominal **médio** mensal domiciliar per capita (R$) | 2284,77 |
| Total (bloco 2) | Rendimento nominal **mediano** mensal domiciliar per capita (R$) | 970,67 |

> Observação: os arquivos do SIDRA têm cabeçalho em várias linhas, notas de rodapé no final, separador `;` e vírgula como separador decimal.

### `cadastrodebibliotecas-snbp2025-2026.xlsx`
| Coluna | Descrição | Exemplo |
|---|---|---|
| Região | Grande região do país | Nordeste |
| UF | Nome do estado por extenso | PERNAMBUCO |
| NOME MUNICIPIO | Nome do município | RECIFE |
| VINCULO | Esfera responsável: municipal, estadual, distrital ou comunitária | MUNICIPAL |
| TIPO BIBLIOTECA | Pública ou comunitária | PÚBLICA |
| NOME DA BIBLIOTECA | Nome da biblioteca | BIBLIOTECA AFRANIO GODOY |
| ENDEREÇO | Endereço | Av. Aníbal Benévolo, S/N |
| BAIRRO | Bairro (183 registros sem bairro) | Linha do Tiro |
| CEP | CEP | 21131-000 |

### `livros_busca.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| asin | Código do produto na Amazon | 6555607289 |
| titulo | Título do livro | Melhor do que nos filmes |
| preco_reais | Preço na listagem (R$) | 36.3 |
| nota | Avaliação média (0 a 5) | 4.8 |
| n_avaliacoes | Número de avaliações exibido na busca | 168 |
| termo_busca | Termo usado na pesquisa | romance |
| url | Link do livro | https://www.amazon.com.br/.../dp/6555607289 |

### `livros_bestsellers.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| ID | Código do produto na Amazon | 8551009834 |
| Rank | Posição na lista de mais vendidos | 1 |
| Título | Título do livro | O massacre da família Hope |
| Preço | Preço (R$) | 40.77 |
| Nota | Avaliação média (0 a 5) | 4.7 |
| Qtd Avaliações | Número de avaliações | 475 |
| URL | Link do livro | https://www.amazon.com.br/.../dp/8551009834 |

### `livros_amazon.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| ID | Código do produto na Amazon | 6555607289 |
| Título | Título do livro | Melhor do que nos filmes |
| Editora | Editora | Intrínseca |
| Ano_Publicação | Ano de publicação | 2023 |
| Preço | Preço na página do livro (R$) | 36.3 |
| Gênero | Categoria do livro na Amazon | Comédia Romântica |
| Formato | Capa comum, capa dura, e-book, audiolivro etc. | Capa comum |
| idioma | Idioma | Português |
| numero_paginas | Número de páginas | 352 |
| avaliacao | Avaliação média (0 a 5) | 4.8 |
| qtd_avaliacoes | Número total de avaliações | 16806 |
| url | Link do livro | https://www.amazon.com.br/dp/6555607289 |

### `LOJA_FISICA.csv`
| Coluna | Descrição | Exemplo |
|---|---|---|
| TITULO | Título do livro | Verity |
| PREÇO | Preço na loja (R$); `X` quando não havia preço | 64,90 |