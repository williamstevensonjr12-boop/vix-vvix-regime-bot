"""
gap_go_universe.py — Universe of small/mid-cap stocks known for gapping.
Shared between live trading (gap_go_live.py) and backtests.
No heavy imports — safe to import anywhere.
"""
_RAW = [
    # ── Biotech / Pharma ──────────────────────────────────────────────────────
    "SAVA", "RXRX", "PRAX", "VERA", "ARQT",
    "NUVL", "KYMR", "DNLI", "ARVN", "RCUS", "RLAY",
    "ZNTL", "CGON", "IMCR", "ALNY", "SRPT", "EXEL", "ALLO", "PTGX",
    "AVXL", "ALDX", "ADMA", "BCRX", "SUPN", "XNCR",
    "MGNX", "AGIO", "ACAD", "RARE", "KRYS", "INSM", "HRMY",
    "VKTX", "TMDX", "GKOS", "OCUL", "PRTA", "LNTH",
    "PBYI", "CRVS", "AMRN", "ARDX", "NVAX", "VXRT",
    "AGEN", "FATE", "NTLA", "EDIT", "BEAM", "CRSP", "SEER",
    "ATAI", "KROS", "IMVT", "HALO", "CHRS",
    "ANAB", "OGEN", "IRWD", "MNKD", "NKTR",
    "PTCT", "TBIO", "ACMR", "INVA", "RVMD", "REGN", "RGEN",
    "IONS", "MYPS", "HRTX", "AKBA", "ALEC", "ALGS",
    "ALVO", "AMPH", "AMRX", "ANIK", "ANIP",
    "ANNX", "APGE", "APLS", "APRE", "ARCT",
    "ARGX", "ARIS", "ARRY", "ARWR",
    "ASND", "ASRT", "ASTH", "ATNM", "ATOS", "ATRC",
    "AUTL", "AVIR", "AXSM", "AYTU", "AZTA",
    "BBIO", "BCAB", "BCLI", "BCYC",
    "BHVN", "BIIB", "BIVI", "BLFS", "BLRX",
    "BMRN", "BNGO", "BNTX", "BOLT", "BPTH", "BRAV",
    "BTAI", "BYSI", "CAPR", "CARV",
    "CDNA", "CGEN", "CLNN",
    "CNMD", "CNSP", "COCP",
    "CODX", "COLL", "CORT", "CPIX", "CPRX", "CRIS", "CRNX",
    "CTMX", "CYCN", "DARE",
    "DMAC", "DYAI",
    "ECOR", "ELVA", "ENTX", "ERAS",
    "ESPR", "EVFM", "EVGN", "EVLO",
    "FBIO", "FHTX", "FULC",
    "GALT", "GERN", "GHRS", "GLPG",
    "GNLN", "GNPX", "GOVX", "HBIO",
    "HEPA", "HOOK", "HOTH",
    "IMCC", "IMMP", "IMNN", "INCY", "INFU",
    "INMD", "INOD", "INSG", "IPIX", "IPSC", "ISPC",
    "IVVD", "JAGX", "JANX", "KALA", "KALV",
    "KLDO", "KNSA", "KPTI", "KZIA",
    "LGND", "LPCN",
    "LQDA", "LRMR", "LTRN", "LYRA",
    "MARK", "MDGL", "MEIP", "MESO",
    "MGTX", "MIRM", "MIST", "MLTX", "MNPR",
    "MRNA", "MTNB",
    "NBTX", "NNOX", "NPCE", "NRIX", "NRXP",
    "NTRB", "NVCR", "OCGN",
    "ONCY",
    "OPGN", "OPRA", "ORGO", "ORMP", "OSUR", "OTLK", "OVID",
    "PASG", "PCSA", "PCVX", "PDYN", "PGEN", "PHGE", "PHIO",
    "PHVS", "PLRX", "PLSE", "PMVP",
    "PRME", "PRQR", "PTLO",
    "PYXS", "QNRX", "RDVT", "RIGL", "RNAZ",
    "RNXT", "RPRX", "RYTM",
    "SBIG", "SGMO", "SHPH", "SIGA",
    "SINT", "SLDB", "SLGL", "SLNM", "SMMT", "SNOA",
    "SPRO", "SPRX", "STOK", "STRO",
    "SVRA", "SYRS", "TBPH", "TELA",
    "TENX", "TGTX", "TNXP",
    "TRVI", "TVTX", "TYRA",
    "URGN", "UTHR", "VCEL",
    "VLRS", "VNDA", "VNRX", "VRCA", "VRDN", "VRTX", "VSTM",
    "VTRS", "WINT", "XBIT", "XELA", "XENE",
    "XERS", "XFOR", "XTLB", "ZDGE",
    "ZLAB", "ZNTL",
    # ── AI / Small-cap Tech ───────────────────────────────────────────────────
    "BBAI", "SOUN", "RGTI", "IONQ", "QMCO", "KULR", "CRKN",
    "AEYE", "AEVA", "LIDR", "OUST", "GFAI", "AIXI", "RCAT",
    "PAYO", "ALLT",
    # ── Crypto / Bitcoin mining ───────────────────────────────────────────────
    "MARA", "RIOT", "CLSK", "CIFR", "HUT", "HIVE", "WULF", "APLD",
    "IREN", "BTBT", "GREE",
    # ── EV / Clean energy / Space ─────────────────────────────────────────────
    "EVGO", "CHPT",
    "BLNK", "SPCE", "JOBY", "ACHR", "MVST",
    "RIVN", "LCID", "NIO", "XPEV",
    # ── Small-cap Fintech / Financial ─────────────────────────────────────────
    "DAVE", "HIMS", "CLOV", "BARK", "LMND", "OPEN",
    "UPST", "AFRM", "SOFI",
    # ── Meme / High-volatility ────────────────────────────────────────────────
    "GME", "AMC", "KOSS", "BB", "NOK", "MVIS", "SNDL", "TLRY",
    "ATER", "NEGG",
    # ── Small-cap Energy ──────────────────────────────────────────────────────
    "INDO", "BORR", "RIG", "NINE",
    # ── Other known gappers ───────────────────────────────────────────────────
    "SKLZ", "GRAB", "DKNG",
    "HOOD", "PLTR", "SMCI", "COIN", "SNAP", "ROKU",
    "SHOP", "NET", "LYFT",
]

# Deduplicate preserving order
_seen: set = set()
UNIVERSE: list[str] = [x for x in _RAW if not (_seen.__contains__(x) or _seen.add(x))]  # type: ignore[func-returns-value]
