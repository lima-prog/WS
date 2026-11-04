# Bibliotecas por seção do SISTEMA - PPCPM

Gerado por `gerar_python.py` a partir de `ppcpm/bibliotecas.py`.

**Hoje o sistema abre sem nenhuma biblioteca** (só o Python). As bibliotecas abaixo são para os programas
que vão sendo passados para Python. Instale uma vez em cada PC com `INSTALAR_BIBLIOTECAS.bat`
(ou sem internet, com a pasta `pacotes`, veja o README).

## Por seção

| Seção do sistema | Arquivo | Bibliotecas |
|---|---|---|
| Núcleo — Login, Tela inicial, banco Supabase, Arquivos do PC (pastas e compactados) e atualização automática | `nucleo.txt` | nenhuma obrigatória (opcional: py7zr, rarfile, waitress) |
| Produção › Agrupador ¦ Base | `pg2.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, pypdf, pdfplumber |
| Produção › Roteirização produção | `pg3.txt` | pandas, openpyxl, XlsxWriter |
| Produção › Impressão Casada - ERP | `pg4.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, pypdf, pdfplumber, reportlab |
| Produção › Impressão Casada ¦ Multi obra | `pg5.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, pypdf, pdfplumber, reportlab |
| Produção › Impressão Grupo - LIC | `pg6.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, pypdf, pdfplumber, reportlab |
| Produção › Impressão - FLUXO 04 | `pg7.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, pypdf, pdfplumber, reportlab |
| Processo de validação › Análise da DBF X Focco - ERP | `pg1.txt` | pandas, openpyxl, XlsxWriter, xlrd, pyxlsb, dbfread, lxml, pypdf, pdfplumber |
| Produção › Relatórios dos fluxos | `pg13.txt` | pandas, openpyxl, XlsxWriter, xlrd, lxml, ezdxf |
| Gerenciador de Roteiros › Alteração de Roteiros | `pg10.txt` | pandas, openpyxl, XlsxWriter, xlrd |
| Gerenciador de Roteiros › Acesso ao Intranet | `pg11.txt` | requests |
| Área de impressão › Impressão de Etiquetas | `pg12.txt` | pandas, openpyxl, xlrd, dbfread, reportlab, pywin32 |

## O que cada biblioteca faz

| Biblioteca | Para que serve no sistema |
|---|---|
| `py7zr` | Abrir arquivos compactados .7z como pasta |
| `rarfile` | Abrir arquivos .rar como pasta (precisa do 7-Zip ou WinRAR no PC) |
| `waitress` | Servidor mais forte quando muitos usuários acessam pela rede |
| `pandas` | Tabelas: ler, cruzar, somar e filtrar planilhas e DBF com rapidez |
| `openpyxl` | Ler e gravar Excel .xlsx (mantém abas e formatação) |
| `XlsxWriter` | Gerar o Excel de saída com cores (verde/vermelho), larguras e filtros |
| `xlrd` | Ler Excel antigo .xls |
| `pyxlsb` | Ler Excel binário .xlsb |
| `dbfread` | Ler arquivos .DBF (CNC/ERP) |
| `pypdf` | Juntar, separar e reordenar páginas de PDF (ordens, impressão casada) |
| `pdfplumber` | Ler texto e tabelas de dentro do PDF (conferência do PDF gerado) |
| `reportlab` | Gerar PDF (etiquetas centralizadas, relatórios) |
| `lxml` | Ler o export do FOCCO que vem como .xls em HTML |
| `ezdxf` | Ler os arquivos DXF roteirizados (peças, medidas) direto no Python |
| `requests` | Enviar arquivos para a Intranet PCP |
| `pywin32` | Imprimir direto na Zebra ZD220 (ZPL) e listar impressoras do Windows |
