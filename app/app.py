import hashlib
import os
import random
import time

import pymysql
from flask import (
    Flask, request, session, redirect, url_for, render_template, abort
)

import config

app = Flask(__name__)
app.secret_key = "crafthub-session-signing-key-not-a-flag"

DB = dict(
    host="db",
    user="crafthub",
    password="crafthubpass",
    database="crafthub",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)

# The entity list is built from the image files in static/img/mobs/ at startup:
# every <name>.png becomes a card, and a name with no image never appears.
# Card label == filename (minus .png), case-sensitive.
#
# ENTITY_META gives curated (category, world, level) for known names. The category
# is the `type` column and the filter: skin / monster / villager / ore.
# Anything new that isn't listed here is categorized by name (see categorize()).
ENTITY_META = {
    # skin
    "steve": ("skin", "overworld", 42), "alex": ("skin", "overworld", 38),
    "Narutood": ("skin", "overworld", 50), "baby_shark": ("skin", "overworld", 10),
    "ben": ("skin", "overworld", 25), "blue_team": ("skin", "overworld", 30),
    "cat": ("skin", "overworld", 15), "diamond_king": ("skin", "nether", 60),
    "slender": ("skin", "end", 66),
    # monster
    "zombie": ("monster", "overworld", 5), "creeper": ("monster", "overworld", 8),
    "skeleton": ("monster", "overworld", 6), "spider": ("monster", "overworld", 4),
    "witch": ("monster", "overworld", 12), "slime": ("monster", "overworld", 3),
    "iron_golem": ("monster", "overworld", 30), "zombie_villager": ("monster", "overworld", 7),
    "enderman": ("monster", "end", 20), "ender_dragon": ("monster", "end", 99),
    "wither_boss": ("monster", "overworld", 95), "blaze": ("monster", "nether", 16),
    "ghast": ("monster", "nether", 22), "piglin": ("monster", "nether", 14),
    "piglin_brute": ("monster", "nether", 24), "piglin_king": ("monster", "nether", 40),
    "wither_skeleton": ("monster", "nether", 18),
    # villager
    "villager": ("villager", "overworld", 11), "green_villager": ("villager", "overworld", 13),
    "doctor_villager": ("villager", "overworld", 17), "hitman_villager": ("villager", "overworld", 21),
    "millionaire_villager": ("villager", "overworld", 50), "rainbow_villager": ("villager", "overworld", 19),
    "sensei_villager": ("villager", "overworld", 33),
    # ore
    "diamond": ("ore", "overworld", 90), "emerald": ("ore", "overworld", 75),
    "bronze": ("ore", "nether", 40), "silver_ingot": ("ore", "overworld", 55),
}

ORE_NAMES = {"diamond", "emerald", "bronze", "gold", "coal", "lapis", "redstone", "netherite"}


def categorize(name):
    """(category, world, level) for an image name, curated first then inferred."""
    if name in ENTITY_META:
        return ENTITY_META[name]
    n = name.lower()
    if n in ORE_NAMES or n.endswith("_ingot") or n.endswith("_ore"):
        cat = "ore"
    elif n == "villager" or n.endswith("_villager"):
        cat = "villager"
    else:
        cat = "skin"
    return (cat, "overworld", 10 + (len(name) * 7) % 80)


def entity_key(name):
    """Stable per-entity key used in the /admin/npc?key=... profile URL."""
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:12]


def scan_entities(static_folder):
    """One entity per <name>.png in static/img/mobs/ (sorted); label == filename."""
    mobs = os.path.join(static_folder, "img", "mobs")
    rows = []
    try:
        files = sorted(os.listdir(mobs))
    except FileNotFoundError:
        files = []
    for fn in files:
        if fn.startswith(".") or not fn.lower().endswith(".png"):
            continue
        name = fn[:-4]
        cat, world, level = categorize(name)
        rows.append((name, cat, world, level, entity_key(name)))
    return rows


_FIRST = [
    "Liam", "Noah", "Olivia", "Emma", "Ava", "Sophia", "Jackson", "Lucas", "Mia",
    "Ethan", "Mason", "Logan", "Amelia", "Harper", "Evelyn", "Aiden", "James",
    "Benjamin", "Ella", "Grace", "Henry", "Leo", "Zoe", "Nora", "Owen", "Chloe",
    "Isaac", "Lily", "Caleb", "Hannah",
]
_LAST = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Lee", "Martin", "Clark",
    "Lewis", "Walker", "Hall", "Young",
]
_STATUS = ["active", "active", "active", "trial", "inactive", "active", "banned"]


def make_fake_customers(n=100):
    """Deterministic list of fake customers for the admin dashboard."""
    rng = random.Random(1337)
    rows = []
    for i in range(1, n + 1):
        fn, ln = rng.choice(_FIRST), rng.choice(_LAST)
        rows.append({
            "id": i,
            "name": f"{fn} {ln}",
            "email": f"{fn.lower()}.{ln.lower()}{rng.randint(1, 999)}@craftmail.gg",
            "joined": f"{rng.randint(2023, 2025)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "orders": rng.randint(0, 250),
            "status": rng.choice(_STATUS),
        })
    return rows


def get_db():
    return pymysql.connect(**DB)


def init_db():
    conn = None
    last_err = None
    for _ in range(30):
        try:
            conn = get_db()
            break
        except Exception as exc:
            last_err = exc
            time.sleep(2)
    if conn is None:
        raise RuntimeError(f"database not reachable: {last_err}")

    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INT AUTO_INCREMENT PRIMARY KEY,"
            " username VARCHAR(64) UNIQUE,"
            " password VARCHAR(128),"
            " is_admin TINYINT DEFAULT 0)"
        )
        # rebuilt from scratch each boot, so drop to pick up schema changes
        cur.execute("DROP TABLE IF EXISTS entities")
        cur.execute(
            "CREATE TABLE entities ("
            " id INT AUTO_INCREMENT PRIMARY KEY,"
            " name VARCHAR(64),"
            " type VARCHAR(32),"
            " world VARCHAR(32),"
            " level INT,"
            " secret_key VARCHAR(64))"
        )
        cur.execute("DROP TABLE IF EXISTS npcs")
        cur.execute(
            "CREATE TABLE npcs ("
            " id INT AUTO_INCREMENT PRIMARY KEY,"
            " name VARCHAR(64),"
            " role VARCHAR(64),"
            " world VARCHAR(32),"
            " level INT,"
            " secret_key VARCHAR(64))"
        )

        # entities are rebuilt from the images in static/img/mobs/ each boot:
        # every picture becomes a card, names without a picture never appear.
        entities = scan_entities(app.static_folder)
        if entities:
            cur.executemany(
                "INSERT INTO entities (name, type, world, level, secret_key)"
                " VALUES (%s,%s,%s,%s,%s)",
                entities,
            )

        # admin account is config-driven: rebuilt from config on every boot
        cur.execute("DELETE FROM users WHERE is_admin=1")
        cur.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s,%s,1)",
            (config.ADMIN_USERNAME, config.ADMIN_PASSWORD),
        )

        # hidden NPC is config-driven
        cur.execute(
            "INSERT INTO npcs (name, role, world, level, secret_key) VALUES (%s,%s,%s,%s,%s)",
            (config.NPC_NAME, config.NPC_ROLE, "overworld",
             config.NPC_LEVEL, config.NPC_SECRET_KEY),
        )
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shop")
def shop():
    return render_template("shop.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        with conn.cursor() as cur:
            # parameterized on purpose: stage 1 is brute force, not SQLi
            cur.execute(
                "SELECT username, is_admin FROM users WHERE username=%s AND password=%s",
                (username, password),
            )
            row = cur.fetchone()
        conn.close()
        if row:
            session["user"] = row["username"]
            session["is_admin"] = bool(row["is_admin"])
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    taunt = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (%s,%s,0)",
                    (username, password),
                )
            except Exception:
                pass
        conn.close()
        taunt = "สมัครมาทำอะไรเอ็งจะมาหาอะไรรึ"
        return render_template("pwned.html", taunt=taunt)
    return render_template("register.html", taunt=taunt)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    is_admin = session.get("is_admin")
    flag = config.FLAG1 if is_admin else None
    customers = make_fake_customers(100) if is_admin else None
    return render_template(
        "dashboard.html",
        user=session["user"],
        is_admin=is_admin,
        flag=flag,
        customers=customers,
    )


@app.route("/admin/players")
def players():
    if not session.get("is_admin"):
        return redirect(url_for("login"))

    rows = []
    error = None
    conn = get_db()
    if "search" in request.args:
        search = request.args.get("search", "")
        # intentionally vulnerable: union-based SQLi, 6 columns.
        # matches across all displayed columns so ordinary searches behave like a
        # real registry; the injection sits in the first LIKE clause.
        query = (
            "SELECT id, name, type, world, level, secret_key FROM entities "
            "WHERE name LIKE '%" + search + "%'"
            " OR type LIKE '%" + search + "%'"
            " OR world LIKE '%" + search + "%'"
            " OR CAST(id AS CHAR) LIKE '%" + search + "%'"
            " OR CAST(level AS CHAR) LIKE '%" + search + "%'"
        )
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as exc:
            error = str(exc)
    else:
        search = ""
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, type, world, level, secret_key FROM entities")
            rows = cur.fetchall()
    # name -> profile key, so real entity cards can link to their profile page.
    # (kept out of the vulnerable query above so the SQLi stays 5 columns.)
    with conn.cursor() as cur:
        cur.execute("SELECT name, secret_key FROM entities")
        entity_keys = {r["name"]: r["secret_key"] for r in cur.fetchall()}
    conn.close()

    return render_template(
        "players.html", rows=rows, error=error, search=search, entity_keys=entity_keys
    )


@app.route("/admin/npc")
def npc():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    key = request.args.get("key", "")
    conn = get_db()
    with conn.cursor() as cur:
        # the hidden NPC (the SQLi target) lives in npcs; normal entity profiles
        # (reachable by clicking a card) live in entities. Same URL, same key param.
        cur.execute("SELECT * FROM npcs WHERE secret_key=%s", (key,))
        record = cur.fetchone()
        is_special = record is not None
        if not record:
            cur.execute(
                "SELECT id, name, type, world, level FROM entities WHERE secret_key=%s",
                (key,),
            )
            record = cur.fetchone()
    conn.close()
    if not record:
        abort(404)
    trading = is_special and request.args.get("trade") == "1"
    flag = config.FLAG2 if trading else None
    return render_template(
        "npc.html",
        npc=record,
        is_special=is_special,
        trade_url=config.TRADE_SITE_URL,
        key=key,
        flag=flag,
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
