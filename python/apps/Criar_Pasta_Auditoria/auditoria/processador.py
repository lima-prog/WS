# -*- coding: utf-8 -*-
"""
Motor de processamento da aba Criar Pasta / Auditoria: cria a estrutura
de pastas de um lote (com resgate automático da LOTE 9999), audita a
LOTE 9999 contra a planilha, e move pastas de OF entre lotes.

Sem nenhuma dependência de PyQt5 — a tela (`aba.py`) chama essas funções e
decide sozinha como mostrar o resultado, igual ao padrão de
`corte/processador.py`.

Extraído de `cria_pasta_auditoria.py`, mesma lógica linha por linha.
"""
import os
import shutil

from nucleo.caminhos import PASTA_PAI
from nucleo.logging_config import logger

from auditoria import banco
from auditoria.utilitarios import (
    NOME_PASTA_9999,
    encontrar_arquivo_xlsx,
    ler_ofs_da_planilha,
    ler_todas_as_linhas_planilha,
    ler_linhas_busca_planilha,
    normalizar_codigo,
    mapear_pastas_por_codigo,
    mapear_pastas_por_codigo_multi,
    obter_pasta_9999,
    listar_pastas_mes,
    indexar_estrutura_multi,
    obter_mtime,
)

# Versão desta ferramenta e arquivo de versão mais recente, na mesma pasta
# compartilhada do banco de dados (PASTA_PAI — já é frozen-aware, ver
# nucleo/caminhos.py). Pra "lançar uma atualização", edita o número dentro
# de versao.txt nessa pasta.
VERSAO_ATUAL = "1.1.0"  # mesma numeração do script original (cria_pasta_auditoria.py v2)
VERSAO_ARQUIVO = os.path.join(PASTA_PAI, "versao.txt")


def verificar_nova_versao() -> dict:
    """
    Compara VERSAO_ATUAL com o conteúdo de versao.txt. Não lança exceção:
    qualquer problema de acesso ao arquivo é reportado em "erro" e tratado
    como "sem novidade", pra nunca travar a abertura da aba.
    """
    resultado = {"tem_nova": False, "versao_disponivel": None, "erro": None}
    try:
        if not os.path.isfile(VERSAO_ARQUIVO):
            return resultado
        with open(VERSAO_ARQUIVO, "r", encoding="utf-8") as f:
            versao_disponivel = f.read().strip()
        if not versao_disponivel:
            return resultado
        resultado["versao_disponivel"] = versao_disponivel
        if versao_disponivel != VERSAO_ATUAL:
            resultado["tem_nova"] = True
    except OSError as e:
        resultado["erro"] = str(e)
    return resultado


# ── criação de pastas (com resgate da 9999) ─────────────────────────────


def processar(diretorio_planilha: str, lote: str, local_salvar: str, raizes: list = None) -> dict:
    """
    Lê a planilha, cria a estrutura de pastas do lote e salva no banco.
    Antes de criar cada pasta de OF do zero, verifica (por código
    normalizado) se ela já existe dentro de alguma pasta buffer LOTE 9999
    — de QUALQUER diretório raiz cadastrado em Configurações — se existir,
    MOVE de lá para o lote novo em vez de criar vazia.
    Retorna um dict estruturado com os resultados.
    """
    raizes = raizes or []
    if not os.path.exists(diretorio_planilha):
        return {"ok": False, "msg": f"Diretório não encontrado:\n{diretorio_planilha}"}
    caminho_xlsx = encontrar_arquivo_xlsx(diretorio_planilha)
    if not caminho_xlsx:
        return {"ok": False, "msg": f"Nenhum arquivo .xlsx encontrado em:\n{diretorio_planilha}"}
    if not lote.strip():
        return {"ok": False, "msg": "Informe o número do LOTE."}
    try:
        ofs_lote = ler_ofs_da_planilha(caminho_xlsx, lote)
    except Exception as e:
        logger.error(f"Erro ao ler planilha (criar pastas): {e}")
        return {"ok": False, "msg": f"Erro ao abrir a planilha:\n{e}"}

    nome_pasta_lote = f"LOTE {str(lote).strip()}"
    pasta_lote = os.path.join(local_salvar, nome_pasta_lote)
    os.makedirs(pasta_lote, exist_ok=True)

    # Junta as pastas 9999 de TODAS as raízes cadastradas num único mapa de
    # resgate (código -> caminho físico). Se o mesmo código existir em mais
    # de uma raiz, a primeira encontrada vence.
    raizes_validas = [r for r in raizes if r and os.path.isdir(r)]
    raizes_sem_9999 = []
    mapa_9999 = {}
    for raiz in raizes_validas:
        pasta_9999_raiz = obter_pasta_9999(raiz)
        if not os.path.isdir(pasta_9999_raiz):
            raizes_sem_9999.append(raiz)
            continue
        for codigo, caminho in mapear_pastas_por_codigo(pasta_9999_raiz).items():
            if codigo not in mapa_9999:
                mapa_9999[codigo] = caminho

    criadas = 0
    existentes = 0
    resgatadas = 0
    falhas_mover = []
    for of_str in ofs_lote:
        caminho_of = os.path.join(pasta_lote, of_str)
        if os.path.exists(caminho_of):
            existentes += 1
            continue
        codigo = normalizar_codigo(of_str)
        origem = mapa_9999.get(codigo)
        if origem and os.path.isdir(origem):
            try:
                shutil.move(origem, caminho_of)
                resgatadas += 1
            except Exception as e:
                logger.error(f"Erro ao resgatar {of_str} da 9999: {e}")
                falhas_mover.append(f"{of_str} ({e})")
                os.makedirs(caminho_of, exist_ok=True)
                criadas += 1
        else:
            os.makedirs(caminho_of)
            criadas += 1

    inseridos_db, ignorados_db = banco.salvar_pacotes(str(lote).strip(), ofs_lote)

    aviso_9999 = None
    if not raizes:
        aviso_9999 = f"Nenhum diretório raiz cadastrado — resgate da {NOME_PASTA_9999} não foi verificado."
    elif not raizes_validas:
        aviso_9999 = "Nenhum dos diretórios raiz cadastrados foi encontrado no disco."
    elif len(raizes_sem_9999) == len(raizes_validas):
        aviso_9999 = f"Nenhuma pasta '{NOME_PASTA_9999}' encontrada entre as {len(raizes_validas)} raiz(es) cadastrada(s)."
    elif raizes_sem_9999:
        aviso_9999 = (
            f"{len(raizes_sem_9999)} de {len(raizes_validas)} raiz(es) cadastrada(s) "
            f"não têm pasta '{NOME_PASTA_9999}'."
        )

    vazio = (criadas == 0 and existentes == 0 and resgatadas == 0)
    return {
        "ok": True,
        "vazio": vazio,
        "pasta_lote": pasta_lote,
        "total_ofs": len(ofs_lote),
        "resgatadas": resgatadas,
        "criadas": criadas,
        "existentes": existentes,
        "inseridos_db": inseridos_db,
        "ignorados_db": ignorados_db,
        "aviso_9999": aviso_9999,
        "falhas_mover": falhas_mover,
    }


# ── auditoria da LOTE 9999 ──────────────────────────────────────────────


def auditar_lote_9999(diretorio_planilha: str, raizes: list) -> dict:
    """
    Confronta, pra cada OF que tem alguma relação com uma pasta LOTE 9999
    (de QUALQUER raiz cadastrada em Configurações) ou que exista fisicamente
    em qualquer lugar da estrutura sem ter registro na planilha, duas
    informações:
        - o que a planilha diz (lote_planilha)
        - onde a pasta está de verdade (lugar)
    Varre TODAS as raízes cadastradas juntas — uma OF perdida na 9999 de
    uma raiz, ou largada solta num lote qualquer de qualquer raiz, aparece
    do mesmo jeito, não importa em qual raiz esteja.
    Resume isso num único veredito por linha (diagnostico):
        "bate"          -> planilha diz 9999 e a pasta está numa LOTE 9999.
        "lugar_errado"  -> planilha e pasta física divergem (nas duas direções:
                            planilha diz 9999 mas pasta está em outro lote, OU
                            planilha diz outro lote mas a pasta está numa 9999).
        "nao_encontrada"-> planilha diz 9999 mas a pasta não existe em lugar nenhum.
        "sem_registro"  -> a pasta existe fisicamente (numa 9999 ou em qualquer
                            outro lote de qualquer raiz) mas a OF não existe em
                            nenhuma linha da planilha, em lugar nenhum.
        "duplicada"     -> a MESMA OF tem pasta física em mais de um lugar ao
                            mesmo tempo (ex.: uma cópia na LOTE 9999 e outra
                            já dentro do lote real, ou duas cópias em lotes
                            diferentes) — a linha traz todos os lugares onde
                            ela foi encontrada, pra decidir manualmente qual
                            cópia é a certa (nunca move nada sozinho aqui,
                            porque mover uma por cima da outra arriscaria
                            perder conteúdo).
    Retorna um dict estruturado (para montar o dashboard na interface).
    """
    if not diretorio_planilha or not os.path.exists(diretorio_planilha):
        return {"ok": False, "msg": "Diretório/arquivo da planilha não encontrado."}
    caminho_xlsx = encontrar_arquivo_xlsx(diretorio_planilha)
    if not caminho_xlsx:
        return {"ok": False, "msg": f"Nenhum arquivo .xlsx encontrado em:\n{diretorio_planilha}"}

    raizes_entrada = raizes or []
    raizes_invalidas = [r for r in raizes_entrada if not r or not os.path.isdir(r)]
    raizes_validas = [r for r in raizes_entrada if r and os.path.isdir(r)]
    if not raizes_validas:
        return {"ok": False, "msg": "Cadastre ao menos um Diretório raiz válido em Configurações para auditar."}

    try:
        todas_linhas_planilha = ler_todas_as_linhas_planilha(caminho_xlsx)
    except Exception as e:
        logger.error(f"Erro ao ler planilha (auditoria): {e}")
        return {"ok": False, "msg": f"Erro ao abrir a planilha:\n{e}"}

    ofs_9999 = [of_trecho for lote, of_trecho in todas_linhas_planilha if lote == "9999"]
    if not ofs_9999:
        return {"ok": False, "msg": "Nenhuma linha com LOTE 9999 encontrada na planilha."}

    # Código -> (lote, of_trecho) da 1ª ocorrência na planilha inteira (não só
    # as linhas do 9999). É o que permite dizer a que lote uma pasta que está
    # fisicamente numa 9999, mas não é marcada como 9999 na planilha, pertence
    # — ou dizer que ela não existe em nenhuma linha da planilha de jeito nenhum.
    mapa_codigo_lote = {}
    mapa_codigo_of_texto = {}
    for lote, of_trecho in todas_linhas_planilha:
        codigo = normalizar_codigo(of_trecho)
        if codigo and codigo not in mapa_codigo_lote:
            mapa_codigo_lote[codigo] = lote
            mapa_codigo_of_texto[codigo] = of_trecho

    # Agrupa as linhas do 9999 por código normalizado, porque a mesma OF pode
    # aparecer em mais de uma linha (ex: itens/trechos diferentes da mesma
    # obra) — isso é o que costuma explicar "40 linhas x 35 pastas".
    grupos = {}
    ordem = []
    for of_str in ofs_9999:
        codigo = normalizar_codigo(of_str)
        if codigo not in grupos:
            grupos[codigo] = []
            ordem.append(codigo)
        grupos[codigo].append(of_str)
    duplicadas = [
        {"codigo": codigo, "ocorrencias": grupos[codigo]}
        for codigo in ordem if len(grupos[codigo]) > 1
    ]

    # Varre TODAS as raízes cadastradas e monta locais_por_codigo: código ->
    # LISTA de TODOS os lugares físicos onde uma pasta com esse código foi
    # encontrada (9999 de qualquer raiz + qualquer LOTE real de qualquer
    # raiz). Precisa ser uma lista, não um valor único: se guardássemos só
    # "o primeiro lugar encontrado" (como a versão antiga fazia), duas
    # cópias físicas da MESMA OF em dois lugares ao mesmo tempo — ex.: uma
    # pasta esquecida na 9999 e outra já dentro do lote real — nunca
    # apareceriam como problema, porque a segunda pasta encontrada era
    # simplesmente descartada em silêncio. É exatamente isso que permite
    # detectar duplicidade física abaixo.
    locais_por_codigo = {}
    raizes_info = []
    total_lotes_escaneados = 0
    qtd_pastas_mes_total = 0
    pastas_com_erro = []
    for raiz in raizes_validas:
        pasta_9999_raiz = obter_pasta_9999(raiz)
        existe_9999 = os.path.isdir(pasta_9999_raiz)
        raizes_info.append({"raiz": raiz, "pasta_9999": pasta_9999_raiz, "existe": existe_9999})
        if existe_9999:
            for codigo, caminhos in mapear_pastas_por_codigo_multi(pasta_9999_raiz).items():
                for caminho in caminhos:
                    locais_por_codigo.setdefault(codigo, []).append({
                        "tipo": "9999", "caminho": caminho, "raiz": raiz,
                        "lugar": f"{NOME_PASTA_9999}  ·  {raiz}",
                    })
        indice_raiz, total_lotes_raiz, erros_raiz = indexar_estrutura_multi(
            raiz, ignorar=pasta_9999_raiz if existe_9999 else None
        )
        total_lotes_escaneados += total_lotes_raiz
        pastas_com_erro.extend(erros_raiz)
        qtd_pastas_mes_total += len(listar_pastas_mes(raiz))
        for codigo, ocorrencias in indice_raiz.items():
            for caminho_lote, pasta_mes, caminho_of_real in ocorrencias:
                lugar = f"{os.path.basename(pasta_mes)} / {os.path.basename(caminho_lote)}  ·  {raiz}"
                locais_por_codigo.setdefault(codigo, []).append({
                    "tipo": "lote", "caminho": caminho_of_real, "raiz": raiz,
                    "lugar": lugar,
                })

    total_pastas_fisicas_9999 = sum(
        1 for locais in locais_por_codigo.values()
        if any(loc["tipo"] == "9999" for loc in locais)
    )

    bate = []
    lugar_errado = []
    nao_encontradas = []
    sem_registro = []
    duplicadas_fisicas = []
    linhas = []  # uma linha por OF única — base da tabela na interface
    codigos_ja_vistos = set()

    def _registrar_duplicada(of_texto, n_ocorrencias, lote_planilha, locais):
        # Nunca decide sozinho qual cópia é a certa — só reporta todos os
        # lugares onde a OF foi encontrada, pra resolver na mão (ver
        # botões "📂 Mover para..." por local, em auditoria/aba.py).
        duplicadas_fisicas.append({
            "of": of_texto, "lote_planilha": lote_planilha, "locais": locais,
        })
        linhas.append({
            "of": of_texto, "n_ocorrencias": n_ocorrencias,
            "lote_planilha": lote_planilha,
            "lugar": "\n".join(loc["lugar"] for loc in locais),
            "diagnostico": "duplicada", "caminho_atual": None,
            "locais_duplicados": locais,
        })

    # 1) OFs que a planilha marca como lote 9999 (seguem a ordem da planilha)
    for codigo in ordem:
        ocorrencias = grupos[codigo]
        of_repr = ocorrencias[0]  # nome representativo (1ª ocorrência na planilha)
        n_ocorrencias = len(ocorrencias)
        codigos_ja_vistos.add(codigo)
        locais = locais_por_codigo.get(codigo, [])

        if len(locais) >= 2:
            _registrar_duplicada(of_repr, n_ocorrencias, "9999", locais)
            continue

        loc_9999 = next((l for l in locais if l["tipo"] == "9999"), None)
        if loc_9999:
            bate.append(of_repr)
            linhas.append({
                "of": of_repr, "n_ocorrencias": n_ocorrencias,
                "lote_planilha": "9999", "lugar": loc_9999["lugar"],
                "diagnostico": "bate", "caminho_atual": loc_9999["caminho"],
            })
        elif locais:
            loc = locais[0]
            lugar_errado.append({"of": of_repr, "lote_planilha": "9999", "lugar": loc["lugar"]})
            linhas.append({
                "of": of_repr, "n_ocorrencias": n_ocorrencias,
                "lote_planilha": "9999", "lugar": loc["lugar"],
                "diagnostico": "lugar_errado", "caminho_atual": loc["caminho"],
            })
        else:
            nao_encontradas.append(of_repr)
            linhas.append({
                "of": of_repr, "n_ocorrencias": n_ocorrencias,
                "lote_planilha": "9999", "lugar": None,
                "diagnostico": "nao_encontrada",
            })

    # 2) Pastas que existem fisicamente numa 9999 (de qualquer raiz) mas cujo
    # código não está marcado como lote 9999 na planilha (podem pertencer a
    # outro lote por engano, ou não existir na planilha de jeito nenhum).
    for codigo, locais in locais_por_codigo.items():
        if codigo in codigos_ja_vistos:
            continue
        if not any(l["tipo"] == "9999" for l in locais):
            continue  # não toca a 9999 — tratado no passo 3
        codigos_ja_vistos.add(codigo)
        lote_planilha = mapa_codigo_lote.get(codigo)

        if len(locais) >= 2:
            loc_9999 = next(l for l in locais if l["tipo"] == "9999")
            of_texto = mapa_codigo_of_texto.get(codigo) or os.path.basename(loc_9999["caminho"])
            _registrar_duplicada(of_texto, 1, lote_planilha, locais)
            continue

        loc = locais[0]  # só pode ser tipo "9999" (garantido pelo `any` acima + len==1)
        nome_pasta = os.path.basename(loc["caminho"])
        of_texto = mapa_codigo_of_texto.get(codigo, nome_pasta)
        if lote_planilha:
            lugar_errado.append({"of": of_texto, "lote_planilha": lote_planilha, "lugar": loc["lugar"]})
            diagnostico = "lugar_errado"
        else:
            sem_registro.append(of_texto)
            diagnostico = "sem_registro"
        linhas.append({
            "of": of_texto, "n_ocorrencias": 1,
            "lote_planilha": lote_planilha, "lugar": loc["lugar"],
            "diagnostico": diagnostico, "caminho_atual": loc["caminho"],
        })

    # 3) Pastas que existem fisicamente em qualquer OUTRO lote (fora das
    # 9999, em qualquer raiz), sem nenhum código já visto nos passos 1/2 —
    # ou seja, nenhuma ocorrência delas toca a 9999 em lugar nenhum.
    # Se a OF já tem registro em algum lote da planilha, fica de fora: isso
    # não é um problema de "sem registro"/duplicidade desta tela, é
    # auditoria de outro lote, fora do escopo — mesmo com 2+ cópias físicas
    # (decidir qual delas é a "oficial" dependeria de auditar aquele outro
    # lote por completo, não só o que sobra da 9999).
    for codigo, locais in locais_por_codigo.items():
        if codigo in codigos_ja_vistos:
            continue
        codigos_ja_vistos.add(codigo)
        if mapa_codigo_lote.get(codigo) is not None:
            continue

        if len(locais) >= 2:
            of_texto = os.path.basename(locais[0]["caminho"])
            _registrar_duplicada(of_texto, 1, None, locais)
            continue

        loc = locais[0]
        nome_pasta = os.path.basename(loc["caminho"])
        sem_registro.append(nome_pasta)
        linhas.append({
            "of": nome_pasta, "n_ocorrencias": 1,
            "lote_planilha": None, "lugar": loc["lugar"],
            "diagnostico": "sem_registro", "caminho_atual": loc["caminho"],
        })

    return {
        "ok": True,
        "total_linhas": len(ofs_9999),
        "total_unicas": len(ordem),
        "total_pastas_fisicas": total_pastas_fisicas_9999,
        "bate": bate,
        "lugar_errado": lugar_errado,
        "nao_encontradas": nao_encontradas,
        "sem_registro": sem_registro,
        "duplicadas": duplicadas,
        "duplicadas_fisicas": duplicadas_fisicas,
        "linhas": linhas,
        "raizes_info": raizes_info,
        "raizes_invalidas": raizes_invalidas,
        "qtd_pastas_mes_encontradas": qtd_pastas_mes_total,
        "total_lotes_escaneados": total_lotes_escaneados,
        "pastas_com_erro": pastas_com_erro,
    }


# ── base de busca (FASE 2: Buscar por Obra / Buscar por Pacote) ─────────


def importar_planilha_busca(caminho_xlsx: str) -> dict:
    """
    Lê a planilha inteira e recarrega auditoria_registros do zero — base
    usada pelas telas "Buscar por Obra" e "Buscar por Pacote". Chamada pelo
    botão "🔄 Atualizar Base de Busca" em Configurações.
    """
    try:
        linhas = ler_linhas_busca_planilha(caminho_xlsx)
    except Exception as e:
        logger.error(f"Erro ao ler planilha (base de busca): {e}")
        return {"ok": False, "msg": f"Erro ao abrir a planilha:\n{e}"}
    total = banco.substituir_registros(linhas)
    banco.salvar_config("mtime_planilha", obter_mtime(caminho_xlsx))
    return {"ok": True, "msg": f"✅ Base de busca atualizada — {total} registro(s) importado(s).", "total": total}


# ── mover pasta (ação a partir da tela de Auditoria) ────────────────────


def mover_pasta_of(caminho_atual: str, pasta_destino: str) -> dict:
    """
    Move a pasta de uma OF (caminho_atual) para dentro de pasta_destino,
    mantendo o nome original da pasta. Cria pasta_destino se não existir.
    Nunca sobrescreve: se já existir uma pasta com o mesmo nome no destino,
    aborta com erro em vez de arriscar misturar conteúdo.
    """
    if not caminho_atual or not os.path.isdir(caminho_atual):
        return {"ok": False, "msg": f"A pasta de origem não foi encontrada no disco:\n{caminho_atual}"}
    if os.path.normcase(os.path.abspath(caminho_atual)) == os.path.normcase(os.path.abspath(pasta_destino)):
        return {"ok": False, "msg": "A pasta de origem e a de destino são a mesma coisa."}
    if not os.path.isdir(pasta_destino):
        try:
            os.makedirs(pasta_destino, exist_ok=True)
        except OSError as e:
            return {"ok": False, "msg": f"Não foi possível criar a pasta de destino:\n{e}"}
    nome = os.path.basename(caminho_atual.rstrip("\\/"))
    destino_final = os.path.join(pasta_destino, nome)
    if os.path.exists(destino_final):
        return {
            "ok": False,
            "msg": f"Já existe uma pasta chamada \"{nome}\" em:\n{pasta_destino}\n"
                   "Nada foi movido, pra não arriscar sobrescrever. Resolva manualmente e tente de novo.",
        }
    try:
        shutil.move(caminho_atual, destino_final)
        return {"ok": True, "msg": f"Pasta movida para:\n{destino_final}", "destino": destino_final}
    except Exception as e:
        logger.error(f"Erro ao mover pasta {caminho_atual} -> {pasta_destino}: {e}")
        return {"ok": False, "msg": f"Erro ao mover a pasta:\n{e}"}
