# ============================================================
#  CraftHub CTF  -  editable config (Project A: stages 1 & 2)
#  Edit freely, then:  docker compose restart web
# ============================================================

# ---- Flags (format is yours to change) ----
FLAG1 = "LOC9{brute_f0rce_the_4dm1n}"
FLAG2 = "LOC9{un10n_s3lect_the_h1dd3n_npc}"
FLAG3 = "LOC9{g0bust3r_cr4ck_the_z1p}"   # lives in Project B; kept here only for your reference

# ---- Stage 1: the admin account players must brute-force ----
ADMIN_USERNAME  = "inwKrit6969"   # the handle shown in YOUR login screenshot (not literally "admin")
ADMIN_PASSWORD  = "7291"        # numeric; its length must match PASSWORD_DIGITS
PASSWORD_DIGITS = 4             # 4 or 6

# ---- Stage 2: the hidden NPC ----
NPC_NAME       = "Trader_Villager"
NPC_ROLE       = "Server Developer"
NPC_LEVEL      = 999                 # shown in the Level field when the NPC is dumped
NPC_SECRET_KEY = "v1ll4g3r_7a2f9c"   # token the player extracts via SQLi to open the NPC profile

# ---- Stage 3: link to Project B (fill in after you host the trade-site) ----
TRADE_SITE_URL = "http://10.10.30.15"

# ---- Reference only (Project B zip password; not used by this app) ----
ZIP_PASSWORD = "diamond"
