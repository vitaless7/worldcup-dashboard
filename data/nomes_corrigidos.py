"""
Correção de acentos perdidos em WorldCupPlayers.csv.

O CSV é UTF-8 válido, mas 1.442 caracteres acentuados já chegaram destruídos da
fonte: cada letra virou U+FFFD (o caractere de substituição, exibido como "�").
A informação foi perdida antes do arquivo existir — nenhuma escolha de encoding
recupera. Afeta 97 nomes de jogadores e 5 de técnicos.

Este mapa é uma curadoria manual e auditável: cada entrada restaura uma grafia
verificável publicamente. Nomes sobre os quais não há certeza foram
DELIBERADAMENTE deixados de fora e continuam exibindo "�" — é preferível um dado
visivelmente incompleto a um dado inventado.

Fora do mapa por incerteza: LAM�, �ELIGA, D�INI?, PENS�E, MAHOUV�.
"""

JOGADORES = {
    # --- Artilheiros (aparecem nos gráficos) ---
    "M�LLER": "MÜLLER",
    "PEL� (Edson Arantes do Nascimento)": "PELÉ (Edson Arantes do Nascimento)",
    "SCH�RRLE": "SCHÜRRLE",
    "ROM�RIO (Rom�rio de Souza Faria)": "ROMÁRIO (Romário de Souza Faria)",
    "�ZIL": "ÖZIL",
    "G�TZE": "GÖTZE",
    "PERI�I?": "PERIŠIĆ",
    "SIM�O": "SIMÃO",
    "MAND�UKI?": "MANDŽUKIĆ",
    "CH. AR�NGUIZ": "CH. ARÁNGUIZ",
    "MATTH�US": "MATTHÄUS",
    "KAK�": "KAKÁ",
    "D�EKO": "DŽEKO",
    "URE�A M.": "UREÑA M.",
    "Hugo S�NCHEZ": "Hugo SÁNCHEZ",
    "IBI�EVI?": "IBIŠEVIĆ",
    "ALLB�CK": "ALLBÄCK",
    "VR�AJEVI?": "VRŠAJEVIĆ",
    "Z� ROBERTO": "ZÉ ROBERTO",

    # --- Demais jogadores ---
    "CA�IZARES": "CAÑIZARES",
    "H�SSLER": "HÄSSLER",
    "BJ�RNEBYE": "BJØRNEBYE",
    "Z� CARLOS": "ZÉ CARLOS",
    "GON�ALVES": "GONÇALVES",
    "GROD�S": "GRODÅS",
    "SOLSKJ�R": "SOLSKJÆR",
    "�STENSTAD": "ØSTENSTAD",
    "ACU�A": "ACUÑA",
    "CASTA�EDA": "CASTAÑEDA",
    "WOM�": "WOMÉ",
    "ETAM�": "ETAMÉ",
    "OLEMB�": "OLEMBÉ",
    "ETXEBERR�A": "ETXEBERRÍA",
    "VER�N": "VERÓN",
    "BOLA�O": "BOLAÑO",
    "K�PKE": "KÖPKE",
    "W�RNS": "WÖRNS",
    "UMA�A M.": "UMAÑA M.",
    "BOLA�OS C.": "BOLAÑOS C.",
    "NU�EZ V.": "NÚÑEZ V.",
    "C�CERES": "CÁCERES",
    "CA�IZA": "CAÑIZA",
    "NU�EZ": "NÚÑEZ",
    "CABA�AS": "CABAÑAS",
    "ALVB�GE": "ALVBÅGE",
    "K�LLSTR�M": "KÄLLSTRÖM",
    "JO�O RICARDO": "JOÃO RICARDO",
    "ANDR� MACANGA": "ANDRÉ MACANGA",
    "AKW�": "AKWÁ",
    "Z� KALANGA": "ZÉ KALANGA",
    "LOC�": "LOCÓ",
    "FL�VIO": "FLÁVIO",
    "M�RIO": "MÁRIO",
    "ZUBERB�HLER": "ZUBERBÜHLER",
    "L�CIO": "LÚCIO",
    "LUIS�O": "LUISÃO",
    "�ULER": "ŠULER",
    "MATAV�": "MATAVŽ",
    "MILIJA�": "MILIJAŠ",
    "�IGI?": "ŽIGIĆ",
    "TO�I?": "TOŠIĆ",
    "KIE�LING": "KIESSLING",
    "S�RENSEN": "SØRENSEN",
    "KJ�R": "KJÆR",
    "J�RGENSEN": "JØRGENSEN",
    "GR�NKJ�R": "GRØNKJÆR",
    "KR�LDRUP": "KRØLDRUP",
    "F. COENTR�O": "F. COENTRÃO",
    "JOSU�": "JOSUÉ",
    "PIQU�": "PIQUÉ",
    "W�LFLI": "WÖLFLI",
    "SUBA�I?": "SUBAŠIĆ",
    "J�": "JÔ",
    "C. PE�A": "C. PEÑA",
    "JAVI MART�NEZ": "JAVI MARTÍNEZ",
    "F�BREGAS": "FÀBREGAS",
    "GUTI�RREZ": "GUTIÉRREZ",
    "C. ZU�IGA": "C. ZÚÑIGA",
    "R. MU�OZ": "R. MUÑOZ",
    "B�RKI": "BÜRKI",
    "SCH�R": "SCHÄR",
    "KOLA�INAC": "KOLAŠINAC",
    "BE�I?": "BEŠIĆ",
    "MUJD�A": "MUJDŽA",
    "VRANJE�": "VRANJEŠ",
    "SU�I?": "SUŠIĆ",
    "�UNJI?": "ŠUNJIĆ",
    "VI�?A": "VIŠĆA",
    "HAD�I?": "HADŽIĆ",
    "H�WEDES": "HÖWEDES",
    "GRO�KREUTZ": "GROSSKREUTZ",
    "�DER": "ÉDER",
}

TECNICOS = {
    "Sven-G�ran ERIKSSON (SWE)": "Sven-Göran ERIKSSON (SWE)",
    "J�rgen KLINSMANN (GER)": "Jürgen KLINSMANN (GER)",
    "Lars LAGERB�CK (SWE)": "Lars LAGERBÄCK (SWE)",
    "Jos� P�KERMAN (ARG)": "José PÉKERMAN (ARG)",
    "Carlos QUEIR�S (POR)": "Carlos QUEIRÓS (POR)",
}
