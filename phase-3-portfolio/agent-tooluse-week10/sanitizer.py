"""
Camada probabilistica: sanitizacao do output da ferramenta antes de chegar ao modelo.

Duas etapas:
  1. Estrutural  - descarta comentarios HTML, script/style e subarvores nao visiveis.
                   Deterministica e defensavel.
  2. Padroes     - neutraliza trechos com forma de instrucao imperativa.
                   Probabilistica. O objetivo do exercicio e MEDIR a taxa de falha
                   dela, nao afirmar que funciona.

Atencao para o achado da Semana 9: o padrao P_EXFIL abaixo e um validador
especifico do ataque (cita cpf, saldo, conta). Ele infla o desempenho aparente da
sanitizacao contra ESTES fixtures e nao generaliza. Isso precisa ser declarado no
findings.md, nao escondido no numero.
"""

import re
from html.parser import HTMLParser

MARCADOR = "[REMOVIDO_PELO_SANITIZADOR]"

_ATRIBUTOS_OCULTOS = (
    "display:none",
    "display: none",
    "visibility:hidden",
    "visibility: hidden",
)

PADROES_INSTRUCAO = [
    ("P_OVERRIDE", re.compile(
        r"(ignore|ignorar|desconsidere|esque[cç]a)[^.\n]{0,90}"
        r"(instru[cç][oõ]es|orienta[cç][aã]o|anterior|anteriores|previous|above)",
        re.IGNORECASE)),
    ("P_NOVA_TAREFA", re.compile(
        r"(nova|sua nova|new)\s+(tarefa|instru[cç][oõ]es|task|instructions)",
        re.IGNORECASE)),
    ("P_PERSONA_SISTEMA", re.compile(
        r"(\[\s*)?(mensagem de sistema|system\s*(prompt|message)|"
        r"\[?\s*(system|sistema)\s*\])",
        re.IGNORECASE)),
    ("P_PRECEDENCIA", re.compile(
        r"(tem preced[eê]ncia|substitui a orienta[cç][aã]o|"
        r"sobrep[oõ]e|override[s]? the)",
        re.IGNORECASE)),
    ("P_SIGILO", re.compile(
        r"(n[aã]o mencione|n[aã]o informe|do not mention|do not reveal)"
        r"[^.\n]{0,60}(instru[cç][aã]o|opera(dor|dora)|usu[aá]rio|this)",
        re.IGNORECASE)),
    # Validador especifico do ataque. Ver aviso no docstring.
    ("P_EXFIL", re.compile(
        r"(registre|registrar|inclua|incluir|adicione|adicionar|transcreva|envie)"
        r"[^.\n]{0,80}(cpf|saldo|n[uú]mero da conta|identificador interno)",
        re.IGNORECASE)),
]


class _ExtratorDeTexto(HTMLParser):
    """Extrai texto. include_ocultos=True reproduz um extrator ingenuo."""

    def __init__(self, include_ocultos: bool):
        super().__init__(convert_charrefs=True)
        self.include_ocultos = include_ocultos
        self.partes = []
        self._pilha_oculta = 0
        self._ignorar = 0
        self.removidos_estruturais = 0

    def _tem_marcador_oculto(self, attrs) -> bool:
        for nome, valor in attrs:
            if nome == "hidden":
                return True
            if nome == "aria-hidden" and (valor or "").lower() == "true":
                return True
            if nome == "style" and valor:
                v = valor.replace(" ", "").lower()
                if any(m.replace(" ", "") in v for m in _ATRIBUTOS_OCULTOS):
                    return True
        return False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._ignorar += 1
            return
        if not self.include_ocultos and self._tem_marcador_oculto(attrs):
            self._pilha_oculta += 1
            self.removidos_estruturais += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._ignorar:
            self._ignorar -= 1
            return
        if self._pilha_oculta:
            self._pilha_oculta -= 1

    def handle_startendtag(self, tag, attrs):
        if not self.include_ocultos and self._tem_marcador_oculto(attrs):
            self.removidos_estruturais += 1

    def handle_data(self, data):
        if self._ignorar or self._pilha_oculta:
            return
        texto = data.strip()
        if texto:
            self.partes.append(texto)

    def handle_comment(self, data):
        if self.include_ocultos:
            texto = data.strip()
            if texto:
                self.partes.append(texto)
        else:
            self.removidos_estruturais += 1

    def texto(self) -> str:
        return "\n".join(self.partes)


def extrair_texto_ingenuo(html: str) -> str:
    """Sem defesa. Comentarios e nos ocultos chegam ao modelo."""
    p = _ExtratorDeTexto(include_ocultos=True)
    p.feed(html)
    return p.texto()


def sanitizar(html: str):
    """
    Retorna (texto_sanitizado, decisao).

    decisao["removidos_estruturais"] -> comentarios e nos ocultos descartados
    decisao["padroes_disparados"]    -> lista de ids de padrao que casaram
    """
    p = _ExtratorDeTexto(include_ocultos=False)
    p.feed(html)
    texto = p.texto()

    disparados = []
    for pid, rx in PADROES_INSTRUCAO:
        texto, n = rx.subn(MARCADOR, texto)
        if n:
            disparados.extend([pid] * n)

    decisao = {
        "ativo": True,
        "removidos_estruturais": p.removidos_estruturais,
        "padroes_disparados": disparados,
        "houve_remocao": bool(p.removidos_estruturais or disparados),
    }
    return texto, decisao


def sem_sanitizacao(html: str):
    return extrair_texto_ingenuo(html), {
        "ativo": False,
        "removidos_estruturais": 0,
        "padroes_disparados": [],
        "houve_remocao": False,
    }
