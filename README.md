# CraftHub CTF — Project A (Stages 1 & 2)

A Minecraft-server-portal web CTF. This project covers **Stage 1 (login brute-force)**
and **Stage 2 (union-based SQLi)**. Stage 3 lives in the separate `trade-site` project.

> This README is author-facing. It is **not served** by the app — players never see it.

## Run

```bash
cd crafthub
docker compose up --build
```

Then open <http://localhost:8080>. First boot waits for MySQL to come up (a few seconds).

Edit `config.py` and restart just the web container to apply changes:

```bash
docker compose restart web
```

## Pictures to download (optional, flavor only)

The app works fully without images (the entity grid is text). For the hand-made look,
drop these PNGs into `app/static/img/` with these exact filenames:

| filename | what | where to get it |
|---|---|---|
| `logo.png` | small square server logo (e.g. a grass block) | any free Minecraft block render / your own |
| `hero.png` | a wide landscape/build screenshot (~320px wide) | a Minecraft screenshot or free render |

Good free sources: your own in-game screenshots, or openly-licensed Minecraft render
packs. Keep them small (< 500 KB each).

## Stage 1 — the login screenshot clue (you make this)

1. Start the stack, open <http://localhost:8080/login>.
2. In the **Username** field type the admin handle from `config.py` (`ADMIN_USERNAME`,
   default `CraftLord`).
3. In the **Password** field type the admin password — it renders as dots.
4. Screenshot the filled-in form. Hand that image to players. They read the username
   and must brute-force the 4-digit password.

## Author walkthrough (the intended solution)

**Stage 1 — FLAG1**
- From the screenshot the player knows the username; the password is a 4-digit number.
- Burp Intruder on `POST /login` (payload `0000`–`9999`); the success response redirects
  to `/dashboard` (different length/status than the "Invalid username or password." page).
- Logging in as the admin shows **FLAG1** on the dashboard.
- Trap: `/register` always answers `สมัครมาทำอะไรเอ็งจะมาหาอะไรรึ` and the account it makes
  is a non-admin dead end.

**Stage 2 — FLAG2**
- As admin, go to `/admin/players`. The `search` parameter is injectable (union-based).
- Find column count: `x' ORDER BY 7-- -` errors, `6` is fine → **6 columns**
  (id, name, type, world, level, secret_key).
- Recon: `x' UNION SELECT table_name,2,3,4,5,6 FROM information_schema.tables WHERE table_schema=database()-- -`
  reveals the `npcs` table (not shown in the normal grid).
- Dump it: `x' UNION SELECT id,name,role,world,level,secret_key FROM npcs-- -`
  → the card shows Level 999 and the villager's `secret_key` under the **Secret** field.
- Discover the profile URL by clicking **View profile** on any normal card
  (`/admin/npc?key=<md5(name)[:12]>`); every card also shows its own key in the Secret field.
- Open the hidden profile with the dumped key: `/admin/npc?key=<secret_key>`.
- Click **Trade** (`&trade=1`) → **FLAG2**. The flag is rendered only on the Trade click,
  so dumping the table does not leak it.
- The NPC profile reveals `TRADE_SITE_URL` → the bridge to Stage 3.

## Notes
- No solution hints live in any client-inspectable code: no flags, no giveaway comments,
  no hidden endpoints in JS. Flags and logic are server-side only.
- Flask runs with `debug=False`; the only intentional leak is the MySQL error echoed on
  the search page (needed for guided union-based SQLi).
