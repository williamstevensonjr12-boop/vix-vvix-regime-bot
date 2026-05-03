"""
gap_go_universe.py — Universe of small/mid-cap stocks known for gapping.
Shared between live trading (gap_go_live.py) and backtests.
No heavy imports — safe to import anywhere.
"""
_RAW = [
    # ── Biotech / Pharma ──────────────────────────────────────────────────────
    "SAVA", "RXRX", "PRAX", "ACLX", "RETA", "VERA", "ETNB", "ARQT",
    "NUVL", "TPTX", "KYMR", "DNLI", "ARVN", "RCUS", "RAPT", "RLAY",
    "ZNTL", "CGON", "IMCR", "ALNY", "SRPT", "EXEL", "ALLO", "PTGX",
    "AVXL", "ALDX", "ADMA", "BCRX", "SUPN", "XNCR", "YMAB",
    "MGNX", "AGIO", "ACAD", "FOLD", "RARE", "KRYS", "INSM", "HRMY",
    "VKTX", "TMDX", "GKOS", "OCUL", "CARA", "PRTA", "RVNC", "LNTH",
    "PBYI", "APLT", "CRVS", "AMRN", "ARDX", "NVAX", "VXRT",
    "AGEN", "FATE", "BLUE", "NTLA", "EDIT", "BEAM", "CRSP", "SEER",
    "MNMD", "ATAI", "KROS", "IMVT", "ITCI", "SAGE", "HALO", "CHRS",
    "ANAB", "OGEN", "OBSV", "IRWD", "MNKD", "NKTR", "PNTM",
    "PTCT", "TBIO", "ACMR", "INVA", "VERV", "RVMD", "REGN", "RGEN",
    "IONS", "MYPS", "CTIC", "HRTX", "AKBA", "ALEC", "ALGS", "ALLK",
    "ALPN", "ALRN", "ALTA", "ALVO", "AMPH", "AMRX", "ANIK", "ANIP",
    "ANNX", "APGE", "APLS", "APRE", "APTO", "APTX", "ARCT",
    "ARGX", "ARIO", "ARIS", "ARIX", "ARRY", "ARTE", "ARWR",
    "ASND", "ASRT", "ASTH", "ATNF", "ATNM", "ATOS", "ATRC", "ATRS",
    "AUTL", "AVGR", "AVIR", "AVRO", "AXNX", "AXSM", "AYTU", "AZTA",
    "BBIO", "BCAB", "BCEL", "BCLI", "BCYC", "BDSI",
    "BGNE", "BHVN", "BIIB", "BIOR", "BIVI", "BLFS", "BLRX",
    "BMRN", "BNGO", "BNTX", "BOLT", "BPMC", "BPTH", "BRAV",
    "BSGM", "BTAI", "BYSI", "CAPR", "CARV", "CASI", "CBMG",
    "CDMO", "CDNA", "CDTX", "CGEN", "CKPT", "CLBS", "CLNN",
    "CLVS", "CMRX", "CNCE", "CNMD", "CNSP", "COCP",
    "CODX", "COLL", "CORT", "CPIX", "CPRX", "CRIS", "CRNX",
    "CRTX", "CTMX", "CYCN", "CYTH", "DARE", "DCPH", "DFFN",
    "DMAC", "DOSE", "DRRX", "DVAX", "DYAI",
    "ECOR", "EIGR", "ELVA", "ENTX", "EPZM", "ERAS",
    "ESPR", "EVFM", "EVGN", "EVLO", "EXAS",
    "FBIO", "FGEN", "FHTX", "FMTX", "FREQ", "FSTX", "FULC", "FWBI",
    "GALT", "GENE", "GERN", "GHRS", "GLPG", "GMDA",
    "GNLN", "GNPX", "GOVX", "GTHX", "HARP", "HBIO",
    "HEPA", "HGEN", "HLVX", "HOOK", "HOTH", "HTBX", "HTGM",
    "IMAB", "IMCC", "IMMP", "IMNN", "INCY", "INFU",
    "INMD", "INNT", "INOD", "INSG", "IPIX", "IPSC", "ISEE", "ISPC",
    "ITOS", "IVVD", "JAGX", "JANX", "JNCE", "KALA", "KALV",
    "KDNY", "KLDO", "KNSA", "KPTI", "KRTX", "KZIA",
    "LBPH", "LGND", "LIFW", "LMNL", "LPCN", "LPTX",
    "LQDA", "LRMR", "LTRN", "LUMO", "LVTX", "LYRA",
    "MACK", "MARK", "MBVX", "MDGL", "MDNA", "MEIP", "MESO",
    "MGTX", "MIRM", "MIST", "MLTX", "MNPR",
    "MORF", "MRNA", "MRTX", "MRUS", "MTNB",
    "MYOV", "NBTX", "NMTR", "NNOX", "NPCE", "NRBO", "NRIX", "NRXP",
    "NTRB", "NVCR", "NVET", "NYMX", "OCGN",
    "OMIC", "OMGA", "ONCR", "ONCT", "ONCY", "ONTF",
    "OPGN", "OPRA", "ORGO", "ORMP", "OSUR", "OTLK", "OVID",
    "PASG", "PCSA", "PCVX", "PDYN", "PGEN", "PHGE", "PHIO",
    "PHVS", "PIXY", "PLRX", "PLSE", "PMVP", "POLB",
    "PRME", "PRQR", "PRTK", "PRVB", "PTLO",
    "PYXS", "QNRX", "RDVT", "RIGL", "RMBL", "RNAZ",
    "RNLX", "RNXT", "RPRX", "RPTX", "RYTM",
    "SBIG", "SGEN", "SGMO", "SHPH", "SIGA",
    "SILK", "SINT", "SIOX", "SLDB", "SLGL", "SLNM", "SMMT", "SNOA",
    "SONN", "SPPI", "SPRO", "SPRX", "SRTX", "STOK", "STRO", "STSA",
    "SURF", "SVRA", "SWAV", "SYRS", "TALS", "TBPH", "TCRR", "TELA",
    "TENX", "TGTX", "THRX", "TMBR", "TNXP", "TPTX",
    "TRIL", "TRMI", "TRNX", "TRVI", "TVTX", "TYRA",
    "URGN", "UTHR", "VBIV", "VCEL", "VERV", "VERB",
    "VLRS", "VNDA", "VNRX", "VRCA", "VRDN", "VRTX", "VSTM",
    "VTRS", "VYNT", "WINT", "XBIT", "XELA", "XENE",
    "XERS", "XFOR", "XLRN", "XTLB", "YMTX", "ZDGE",
    "ZEAL", "ZLAB", "ZNTL", "ZSAN",
    # ── AI / Small-cap Tech ───────────────────────────────────────────────────
    "BBAI", "SOUN", "RGTI", "IONQ", "QMCO", "KULR", "CRKN",
    "AEYE", "AEVA", "LIDR", "OUST", "GFAI", "AIXI", "RCAT",
    "LAZR", "VLDR", "PAYO", "ALLT",
    # ── Crypto / Bitcoin mining ───────────────────────────────────────────────
    "MARA", "RIOT", "CLSK", "CIFR", "HUT", "HIVE", "WULF", "APLD",
    "IREN", "BTBT", "GREE",
    # ── EV / Clean energy / Space ─────────────────────────────────────────────
    "NKLA", "GOEV", "FFIE", "SOLO", "IDEX", "EVGO", "CHPT",
    "BLNK", "SPCE", "JOBY", "ACHR", "LILM", "PTRA", "MVST",
    "RIVN", "LCID", "NIO", "XPEV",
    # ── Small-cap Fintech / Financial ─────────────────────────────────────────
    "DAVE", "HIMS", "CLOV", "BARK", "LMND", "OPEN", "RDFN",
    "UPST", "AFRM", "SOFI",
    # ── Meme / High-volatility ────────────────────────────────────────────────
    "GME", "AMC", "KOSS", "BB", "NOK", "MVIS", "SNDL", "TLRY",
    "ATER", "NEGG", "MULN",
    # ── Small-cap Energy ──────────────────────────────────────────────────────
    "INDO", "CPE", "BORR", "RIG", "NINE",
    # ── Other known gappers ───────────────────────────────────────────────────
    "SDC", "SKLZ", "GRAB", "CANO", "WISH", "EXPR", "DKNG",
    "HOOD", "PLTR", "SMCI", "COIN", "SQ", "SNAP", "ROKU",
    "SHOP", "NET", "LYFT",
]

# Deduplicate preserving order
_seen: set = set()
UNIVERSE: list[str] = [x for x in _RAW if not (_seen.__contains__(x) or _seen.add(x))]  # type: ignore[func-returns-value]
