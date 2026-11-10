"""
GERAR BASE PREENCHIDA — feito pelo Python (sem o limite de memória da janela do navegador).

O navegador junta os dados (linhas das DBFs já normalizadas, coluna de fluxo de cada linha, linhas do FOCO)
e manda para cá junto com a planilha base. Aqui a planilha é editada direto no XML, linha por linha:
  - aba DBF: lote (C5), data (C2), dados a partir da linha 10, X das máquinas, fórmulas da linha 10 arrastadas;
  - aba FOCO: linhas do relatório Focco;
  - tabelas dinâmicas: intervalo corrigido e "atualizar ao abrir"; recálculo completo ao abrir.
É a mesma regra do modo do navegador (gerarBasePreenchida), só que sem montar a planilha inteira na memória.
Não usa nenhuma biblioteca de fora (só zipfile/re).
"""
from __future__ import annotations

import io
import re
import unicodedata
import zipfile


class ForaDoPadrao(Exception):
    """A base tem algo que este modo não trata (ex.: fórmula compartilhada mãe numa coluna de dados)."""


# ------------------------------------------------------------------ utilidades
def col_num(letras: str) -> int:
    n = 0
    for ch in letras.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def col_letra(n: int) -> str:
    s = ""
    while n > 0:
        m = (n - 1) % 26
        s = chr(65 + m) + s
        n = (n - 1) // 26
    return s


def ref_cel(ref: str):
    m = re.match(r"^\$?([A-Z]+)\$?(\d+)$", ref or "")
    return (col_num(m.group(1)), int(m.group(2))) if m else None


_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def esc(s: str) -> str:
    return _CTRL.sub("", str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(s: str) -> str:
    return esc(s).replace('"', "&quot;")


def desesc(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def norm(t) -> str:
    t = unicodedata.normalize("NFD", str(t or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").upper().strip()


_RE_REF = re.compile(r"(?<![A-Za-z0-9_.])(\$?)([A-Z]{1,3})(\$?)(\d{1,7})(?![A-Za-z0-9_(!])")


def deslocar_formula(f: str, d_r: int, d_c: int) -> str:
    """Igual ao "arrastar" do Excel: muda as referências relativas (sem $). Não mexe em textos entre aspas."""
    if not d_r and not d_c:
        return f

    def troca(m):
        c_, col, r_, row = m.groups()
        cn, rn = col_num(col), int(row)
        if cn > 16384:
            return m.group(0)
        if not c_:
            cn += d_c
        if not r_:
            rn += d_r
        if cn < 1 or rn < 1 or cn > 16384 or rn > 1048576:
            return "#REF!"
        return f"{c_}{col_letra(cn)}{r_}{rn}"

    out, seg, i, n = [], [], 0, len(f)

    def flush():
        if seg:
            out.append(_RE_REF.sub(troca, "".join(seg)))
            seg.clear()

    while i < n:
        ch = f[i]
        if ch in "\"'":
            flush()
            j = i + 1
            while j < n:
                if f[j] == ch:
                    if j + 1 < n and f[j + 1] == ch:
                        j += 2
                        continue
                    break
                j += 1
            out.append(f[i:j + 1])
            i = j + 1
            continue
        if ch == "[":
            flush()
            d, j = 0, i
            while j < n:
                if f[j] == "[":
                    d += 1
                elif f[j] == "]":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            out.append(f[i:j + 1])
            i = j + 1
            continue
        seg.append(ch)
        i += 1
    flush()
    return "".join(out)


def set_attr_tag(tag: str, nome: str, valor: str) -> str:
    """Coloca/troca um atributo na tag de abertura."""
    if re.search(r"\s" + nome + r'="[^"]*"', tag):
        return re.sub(r"(\s" + nome + r'=")[^"]*(")', lambda m: m.group(1) + valor + m.group(2), tag, count=1)
    fim = len(tag) - (2 if tag.endswith("/>") else 1)
    return tag[:fim] + f' {nome}="{valor}"' + tag[fim:]


# ------------------------------------------------------------------ aba editada em texto
class AbaTexto:
    def __init__(self, xml: str):
        m = re.search(r"<((?:[\w.-]+:)?)sheetData\b[^>]*?(/?)>", xml)
        if not m:
            raise ForaDoPadrao("aba sem sheetData")
        self.P = m.group(1)
        P = self.P
        if m.group(2):          # <sheetData/> vazia
            self.cabeca, corpo, self.cauda = xml[:m.start()] + f"<{P}sheetData>", "", f"</{P}sheetData>" + xml[m.end():]
        else:
            fim = xml.find(f"</{P}sheetData>", m.end())
            if fim < 0:
                raise ForaDoPadrao("sheetData sem fechamento")
            self.cabeca, corpo, self.cauda = xml[:m.end()], xml[m.end():fim], xml[fim:]
        self.rows: dict[int, str] = {}
        ultimo = 0
        for mr in re.finditer(rf"<{re.escape(P)}row\b[^>]*?(?:/>|>.*?</{re.escape(P)}row>)", corpo, re.S):
            t = mr.group(0)
            rr = re.search(r'\sr="(\d+)"', t[:t.index(">")])
            if rr:
                n = int(rr.group(1))
            else:                       # linha sem número: é a seguinte (igual o Excel entende)
                n = ultimo + 1
                t = set_attr_tag(t[:t.index(">") + 1], "r", str(n)) + t[t.index(">") + 1:]
            if n <= ultimo:
                raise ForaDoPadrao("linhas fora de ordem")
            self.rows[n] = t
            ultimo = n
        self.max_row_orig = ultimo
        self.re_cel = re.compile(rf"<{re.escape(P)}c\b[^>]*?(?:/>|>.*?</{re.escape(P)}c>)", re.S)
        self.re_f = re.compile(rf"<{re.escape(P)}f\b")
        self.re_mestre = re.compile(rf"<{re.escape(P)}f\b[^>]*\sref=\"")
        self.max_col = 0
        self.max_row = 0
        self._masters = None

    # --- células de uma linha
    def celulas(self, n: int):
        t = self.rows.get(n)
        cel: dict[int, str] = {}
        if not t:
            return cel
        fe = t.index(">")
        if t[fe - 1] == "/":
            return cel
        fecha = f"</{self.P}row>"
        for mc in self.re_cel.finditer(t, fe + 1, len(t) - len(fecha)):
            c = mc.group(0)
            ref = re.search(r'\sr="\$?([A-Z]+)\$?\d+"', c[:c.index(">")])
            if ref:
                col = col_num(ref.group(1))
            else:                       # célula sem referência: é a coluna seguinte
                col = (max(cel) if cel else 0) + 1
                fe2 = c.index(">")
                c = set_attr_tag(c[:fe2 + 1], "r", f"{col_letra(col)}{n}") + c[fe2 + 1:]
            cel[col] = c
        return cel

    def estilo(self, n: int, col: int):
        c = self.celulas(n).get(col)
        if not c:
            return None
        m = re.search(r'\ss="(\d+)"', c[:c.index(">")])
        return m.group(1) if m else None

    def _attrs(self, t, ref, est):
        if not t:
            return f' r="{ref}"' + (f' s="{est}"' if est else "")
        fim = t.index(">")
        fim = fim - 1 if t[fim - 1] == "/" else fim
        return re.sub(r'\st="[^"]*"', "", t[t.index(" "):fim])

    def montar_celula(self, t, ref, est, valor=None, formula=None, limpar=False):
        P, a = self.P, self._attrs(t, ref, est)
        if limpar:
            return f"<{P}c{a}/>"
        if formula is not None:
            return f"<{P}c{a}><{P}f>{esc(formula)}</{P}f></{P}c>"
        if isinstance(valor, bool):
            valor = int(valor)
        if isinstance(valor, (int, float)):
            txt = repr(valor) if isinstance(valor, float) else str(valor)
            if txt.endswith(".0"):
                txt = txt[:-2]
            return f"<{P}c{a}><{P}v>{txt}</{P}v></{P}c>"
        return f'<{P}c{a} t="inlineStr"><{P}is><{P}t xml:space="preserve">{esc(valor)}</{P}t></{P}is></{P}c>'

    def gravar_linha(self, n: int, cel: dict, mexeu: bool):
        if not mexeu:
            return
        P = self.P
        velha = self.rows.get(n)
        if velha:
            abre = velha[:velha.index(">") + 1]
            if abre.endswith("/>"):
                abre = abre[:-2] + ">"
        else:
            if not cel:
                return
            abre = f'<{P}row r="{n}">'
        abre = re.sub(r'\sspans="[^"]*"', "", abre)
        cols = sorted(cel)
        if cols:
            self.max_col = max(self.max_col, cols[-1])
        self.max_row = max(self.max_row, n)
        self.rows[n] = abre + "".join(cel[c] for c in cols) + f"</{P}row>"

    def set_valor(self, n: int, col: int, valor, est):
        """Uma célula só (cabeçalho)."""
        cel = self.celulas(n)
        t = cel.get(col)
        ref = f"{col_letra(col)}{n}"
        if valor is None or valor == "":
            if not t:
                return
            cel[col] = self.montar_celula(t, ref, None, limpar=True)
        else:
            cel[col] = self.montar_celula(t, ref, est, valor=valor)
        self.gravar_linha(n, cel, True)

    # --- fórmula modelo (linha 10), inclusive fórmula compartilhada
    def formula_modelo(self, n: int, col: int):
        c = self.celulas(n).get(col)
        if not c:
            return None
        m = re.search(rf"<{re.escape(self.P)}f\b([^>]*?)(/?)>(?:(.*?)</{re.escape(self.P)}f>)?", c, re.S)
        if not m:
            return None
        attrs, texto = m.group(1), desesc(m.group(3) or "")
        tipo = re.search(r'\st="([^"]*)"', attrs)
        tipo = tipo.group(1) if tipo else ""
        if tipo in ("array", "dataTable"):
            return None
        if texto:
            return texto
        if tipo == "shared":
            si = re.search(r'\ssi="(\d+)"', attrs)
            if si:
                mestre = self.mestres().get(si.group(1))
                if mestre:
                    r0, c0, txt = mestre
                    return deslocar_formula(txt, n - r0, col - c0)
        return None

    def mestres(self):
        if self._masters is None:
            self._masters = {}
            P = re.escape(self.P)
            re_m = re.compile(rf"<{P}c\b([^>]*)>(?:(?!</{P}c>).)*?<{P}f\b([^>]*\sref=\"[^\"]*\"[^>]*)>([^<]*)</{P}f>", re.S)
            for t in self.rows.values():
                if "ref=" not in t:
                    continue
                for m in re_m.finditer(t):
                    si = re.search(r'\ssi="(\d+)"', m.group(2))
                    rc = re.search(r'\sr="([A-Z]+)(\d+)"', m.group(1))
                    if si and rc:
                        self._masters[si.group(1)] = (int(rc.group(2)), col_num(rc.group(1)), desesc(m.group(3)))
        return self._masters

    def materializar(self, sis: set):
        """Fórmulas compartilhadas cuja "mãe" vai ser sobrescrita: cada célula vira a fórmula escrita por extenso
        (igual o Excel faz quando você apaga a primeira célula de uma fórmula arrastada)."""
        if not sis:
            return
        mestres = self.mestres()
        P = re.escape(self.P)
        re_f = re.compile(rf"<{P}f\b([^>]*?)(?:/>|>([^<]*)</{P}f>)")
        for n in list(self.rows):
            t = self.rows[n]
            if "si=" not in t:
                continue
            cel = self.celulas(n)
            mudou = False
            for col, c in list(cel.items()):
                m = re_f.search(c)
                if not m:
                    continue
                si = re.search(r'\ssi="(\d+)"', m.group(1))
                if not si or si.group(1) not in sis or si.group(1) not in mestres:
                    continue
                r0, c0, txt = mestres[si.group(1)]
                f = txt if (n, col) == (r0, c0) else deslocar_formula(txt, n - r0, col - c0)
                cel[col] = c[:m.start()] + f"<{self.P}f>{esc(f)}</{self.P}f>" + c[m.end():]
                mudou = True
            if mudou:
                velha = self.rows[n]
                abre = velha[:velha.index(">") + 1]
                self.rows[n] = abre + "".join(cel[k] for k in sorted(cel)) + f"</{self.P}row>"

    def sis_mestres_em(self, linhas, cols_ok) -> set:
        """si das fórmulas compartilhadas "mãe" que estão nas células que vão ser sobrescritas."""
        out = set()
        for n in linhas:
            t = self.rows.get(n)
            if not t or "ref=" not in t:
                continue
            for col, c in self.celulas(n).items():
                if cols_ok(n, col) and self.re_mestre.search(c):
                    si = re.search(r'\ssi="(\d+)"', c)
                    if si:
                        out.add(si.group(1))
                    else:   # fórmula de matriz (array) numa coluna de dados: vira valor normal ao sobrescrever
                        pass
        return out

    def finalizar(self) -> str:
        cab = self.cabeca

        def dim(m):
            ref = m.group(2)
            partes = ref.split(":")
            i0 = ref_cel(partes[0]) or (1, 1)
            f0 = ref_cel(partes[-1]) or i0
            return m.group(1) + f"{col_letra(i0[0])}{i0[1]}:{col_letra(max(f0[0], self.max_col))}{max(f0[1], self.max_row)}" + m.group(3)

        cab = re.sub(r'(<(?:[\w.-]+:)?dimension\b[^>]*?\sref=")([^"]*)(")', dim, cab, count=1)
        return cab + "".join(self.rows[n] for n in sorted(self.rows)) + self.cauda


# ------------------------------------------------------------------ a base inteira
def _resolver(base: str, alvo: str) -> str:
    if alvo.startswith("/"):
        return alvo[1:]
    out = []
    for p in (base + alvo).split("/"):
        if p == "..":
            if out:
                out.pop()
        elif p not in (".", ""):
            out.append(p)
    return "/".join(out)


def mapear_abas(z: zipfile.ZipFile):
    wb = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    alvo = {}
    for m in re.finditer(r"<(?:[\w.-]+:)?Relationship\b([^>]*)/?>", rels):
        a = m.group(1)
        i = re.search(r'\sId="([^"]*)"', a)
        t = re.search(r'\sTarget="([^"]*)"', a)
        if i and t:
            alvo[i.group(1)] = desesc(t.group(1))
    abas = {}
    for m in re.finditer(r"<(?:[\w.-]+:)?sheet\b([^>]*)/?>", wb):
        a = m.group(1)
        nome = re.search(r'\sname="([^"]*)"', a)
        rid = re.search(r'\s(?:[\w.-]+:)?id="([^"]*)"', a)
        if nome and rid and rid.group(1) in alvo:
            abas[desesc(nome.group(1))] = _resolver("xl/", alvo[rid.group(1)])
    return wb, rels, abas


def gerar(base: bytes, d: dict, progresso=lambda m: None) -> tuple[bytes, dict]:
    K = d["const"]
    L0 = int(K["LINHA_INICIAL_BASE"])
    COL_FIM = int(K["COL_DBF_FIM"])
    BC, G3M, PUC = int(K["IDX_MAQ_BC"]), int(K["IDX_MAQ_G3M"]), int(K["IDX_MAQ_PERFIL_UC"])
    valores, fluxo = d["valores"], d["fluxoCol"]
    n = len(valores)

    z = zipfile.ZipFile(io.BytesIO(base))
    wb, rels, abas = mapear_abas(z)
    if "DBF" not in abas:
        raise ValueError('a planilha base não tem aba "DBF"')
    novos: dict[str, bytes] = {}
    removidos: set[str] = set()

    # ---------------- aba DBF
    progresso("Lendo a aba DBF…")
    aba = AbaTexto(z.read(abas["DBF"]).decode("utf-8"))
    _cab = {(int(K["LINHA_NUM_PCT"]), int(K["COL_NUM_PCT"])), (int(K["LINHA_DT_REFRESH"]), int(K["COL_DT_REFRESH"]))}
    _fim0 = max(aba.max_row_orig, L0 + n - 1)
    _alvo0 = lambda r, c: (r, c) in _cab or (r >= L0 and (1 <= c <= COL_FIM + 1 or PUC <= c <= G3M))
    aba.materializar(aba.sis_mestres_em([x for x in aba.rows if x in {a for a, _ in _cab} or L0 <= x <= _fim0], _alvo0))
    aba.set_valor(int(K["LINHA_NUM_PCT"]), int(K["COL_NUM_PCT"]), d["lote"], aba.estilo(int(K["LINHA_NUM_PCT"]), int(K["COL_NUM_PCT"])))
    aba.set_valor(int(K["LINHA_DT_REFRESH"]), int(K["COL_DT_REFRESH"]), d["dataHoje"], aba.estilo(int(K["LINHA_DT_REFRESH"]), int(K["COL_DT_REFRESH"])))

    cols_formula = []
    for col in sorted(aba.celulas(L0)):
        if col <= COL_FIM + 1 or PUC <= col <= G3M:
            continue
        t = aba.formula_modelo(L0, col)
        if t:
            cols_formula.append((col, t, aba.estilo(L0, col)))
    estilos = {c: aba.estilo(L0, c) for c in list(range(1, COL_FIM + 2)) + list(range(PUC, G3M + 1))}
    alvo = lambda c: 1 <= c <= COL_FIM + 1 or PUC <= c <= G3M

    fim = max(aba.max_row_orig, L0 + n - 1)
    progresso("Escrevendo a aba DBF…")
    for r in range(L0, fim + 1):
        k = r - L0
        cel = aba.celulas(r)
        mexeu = False

        def setv(c, v, est):
            nonlocal mexeu
            t = cel.get(c)
            ref = f"{col_letra(c)}{r}"
            if v is None or v == "":
                if t:
                    cel[c] = aba.montar_celula(t, ref, None, limpar=True)
                    mexeu = True
                return
            cel[c] = aba.montar_celula(t, ref, est, valor=v)
            mexeu = True

        for c in range(1, COL_FIM + 2):
            setv(c, valores[k][c - 1] if k < n else None, estilos[c])
        for c in range(BC, G3M + 1):
            setv(c, "X" if (k < n and fluxo[k] == c) else None, estilos[c])
        if k < n and fluxo[k] == PUC:
            setv(PUC, "X", estilos[PUC])
        if 0 < k < n and n > 1:
            for col, texto, est in cols_formula:
                t = cel.get(col)
                if t and aba.re_f.search(t):
                    continue
                cel[col] = aba.montar_celula(t, f"{col_letra(col)}{r}", est, formula=deslocar_formula(texto, k, 0))
                mexeu = True
        aba.gravar_linha(r, cel, mexeu)
        if k and k % 5000 == 0:
            progresso(f"Escrevendo a aba DBF… {k}/{fim - L0 + 1}")
    novos[abas["DBF"]] = aba.finalizar().encode("utf-8")
    del aba

    # ---------------- aba FOCO
    foco = d.get("foco") or []
    if foco:
        nome_foco = K["ABA_FOCCO"]
        if nome_foco not in abas:
            raise ValueError(f'a planilha base não tem aba "{nome_foco}"')
        progresso("Escrevendo aba FOCO…")
        af = AbaTexto(z.read(abas[nome_foco]).decode("utf-8"))
        LF, nc, nf = int(K["LINHA_INICIAL_FOCCO"]), int(K["N_COLS_FOCCO"]), len(foco)
        af.materializar(af.sis_mestres_em([x for x in af.rows if x >= LF], lambda r, c: r >= LF and 1 <= c <= nc))
        est = {c: af.estilo(LF, c) for c in range(1, nc + 1)}
        for r in range(LF, max(af.max_row_orig, LF + nf - 1) + 1):
            k = r - LF
            cel = af.celulas(r)
            mexeu = False
            for c in range(1, nc + 1):
                t = cel.get(c)
                v = foco[k][c - 1] if k < nf and c - 1 < len(foco[k]) else None
                ref = f"{col_letra(c)}{r}"
                if v is None or v == "":
                    if t:
                        cel[c] = af.montar_celula(t, ref, None, limpar=True)
                        mexeu = True
                else:
                    cel[c] = af.montar_celula(t, ref, est[c], valor=v)
                    mexeu = True
            af.gravar_linha(r, cel, mexeu)
        novos[abas[nome_foco]] = af.finalizar().encode("utf-8")
        del af

    # ---------------- tabelas dinâmicas
    progresso("Corrigindo intervalo das tabelas dinâmicas…")
    fim_dados = L0 + n - 1

    def ajustar_ref(ref):
        m = re.match(r"^(\$?[A-Z]+\$?\d+):(\$?[A-Z]+)(\$?)(\d+)$", ref or "")
        return f"{m.group(1)}:{m.group(2)}{m.group(3)}{fim_dados}" if m else None

    corrigidos = erros = 0
    nomes_tabela = set()
    nomes = z.namelist()
    for p in [x for x in nomes if re.match(r"^xl/pivotCache/pivotCacheDefinition\d*\.xml$", x, re.I)]:
        try:
            s = z.read(p).decode("utf-8")
            m = re.search(r"<(?:[\w.-]+:)?pivotCacheDefinition\b[^>]*>", s)
            if m:
                tag = set_attr_tag(set_attr_tag(m.group(0), "refreshOnLoad", "1"), "missingItemsLimit", "0")
                s = s[:m.start()] + tag + s[m.end():]
            mw = re.search(r"<(?:[\w.-]+:)?worksheetSource\b[^>]*/?>", s)
            if mw:
                w = mw.group(0)
                ref = re.search(r'\sref="([^"]*)"', w)
                sheet = re.search(r'\ssheet="([^"]*)"', w)
                nome = re.search(r'\sname="([^"]*)"', w)
                if ref and sheet and norm(desesc(sheet.group(1))) == "DBF":
                    nr = ajustar_ref(ref.group(1))
                    if nr:
                        s = s[:mw.start()] + set_attr_tag(w, "ref", nr) + s[mw.end():]
                        corrigidos += 1
                elif nome:
                    nomes_tabela.add(desesc(nome.group(1)))
            novos[p] = s.encode("utf-8")
        except Exception:
            erros += 1
    if nomes_tabela:
        for p in [x for x in nomes if re.match(r"^xl/tables/[^/]+\.xml$", x, re.I)]:
            s = z.read(p).decode("utf-8")
            m = re.search(r"<(?:[\w.-]+:)?table\b[^>]*>", s)
            if not m:
                continue
            tag = m.group(0)
            nm = re.search(r'\sname="([^"]*)"', tag)
            dn = re.search(r'\sdisplayName="([^"]*)"', tag)
            if (nm and desesc(nm.group(1)) in nomes_tabela) or (dn and desesc(dn.group(1)) in nomes_tabela):
                ref = re.search(r'\sref="([^"]*)"', tag)
                nr = ajustar_ref(ref.group(1) if ref else "")
                if nr:
                    s = s[:m.start()] + set_attr_tag(tag, "ref", nr) + s[m.end():]
                    s = re.sub(r'(<(?:[\w.-]+:)?autoFilter\b[^>]*\sref=")[^"]*(")', lambda x: x.group(1) + nr + x.group(2), s, count=1)
                    novos[p] = s.encode("utf-8")
                    corrigidos += 1

        def troca_nome(m):
            nonlocal corrigidos
            pre, attrs, txt = m.group(1), m.group(2), m.group(3)
            nm = re.search(r'\sname="([^"]*)"', attrs)
            if not nm or desesc(nm.group(1)) not in nomes_tabela:
                return m.group(0)
            mm = re.match(r"^('?DBF'?!)(\$?[A-Z]+\$?\d+):(\$?[A-Z]+)(\$?)(\d+)$", txt.strip(), re.I)
            if not mm:
                return m.group(0)
            corrigidos += 1
            return f"<{pre}definedName{attrs}>{mm.group(1)}{mm.group(2)}:{mm.group(3)}{mm.group(4)}{fim_dados}</{pre}definedName>"

        wb = re.sub(r"<((?:[\w.-]+:)?)definedName\b([^>]*)>([^<]*)</(?:[\w.-]+:)?definedName>", troca_nome, wb)

    # ---------------- recálculo completo ao abrir + tira a cadeia de cálculo antiga
    mc = re.search(r"<((?:[\w.-]+:)?)calcPr\b[^>]*?/?>", wb)
    if mc:
        wb = wb[:mc.start()] + set_attr_tag(mc.group(0), "fullCalcOnLoad", "1") + wb[mc.end():]
    else:
        pre = re.search(r"<((?:[\w.-]+:)?)workbook\b", wb).group(1)
        novo = f'<{pre}calcPr fullCalcOnLoad="1"/>'
        ponto = None
        for nome in ("oleSize", "customWorkbookViews", "pivotCaches", "smartTagPr", "smartTagTypes",
                     "webPublishing", "fileRecoveryPr", "webPublishObjects", "extLst"):
            mm = re.search(rf"<(?:[\w.-]+:)?{nome}\b", wb)
            if mm:
                ponto = mm.start()
                break
        if ponto is None:
            ponto = wb.rindex("</")
        wb = wb[:ponto] + novo + wb[ponto:]
    novos["xl/workbook.xml"] = wb.encode("utf-8")
    if "xl/calcChain.xml" in nomes:
        removidos.add("xl/calcChain.xml")
        rels2 = re.sub(r"<(?:[\w.-]+:)?Relationship\b[^>]*Type=\"[^\"]*/calcChain\"[^>]*/>", "", rels)
        novos["xl/_rels/workbook.xml.rels"] = rels2.encode("utf-8")
        ct = z.read("[Content_Types].xml").decode("utf-8")
        ct = re.sub(r'<(?:[\w.-]+:)?Override\b[^>]*PartName="/xl/calcChain\.xml"[^>]*/>', "", ct)
        novos["[Content_Types].xml"] = ct.encode("utf-8")
    pivots = sum(1 for x in nomes if re.match(r"^xl/pivotTables/pivotTable\d*\.xml$", x, re.I))

    # ---------------- arquivo final
    progresso("Compactando o arquivo final…")
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zo:
        for info in z.infolist():
            if info.filename in removidos:
                continue
            dados = novos.get(info.filename)
            if dados is None:
                dados = z.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zo.writestr(zi, dados, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return saida.getvalue(), {"cachesCorrigidos": corrigidos, "cachesErro": erros, "pivots": pivots,
                              "formulasArrastadas": len(cols_formula)}
