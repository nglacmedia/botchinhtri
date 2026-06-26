"""
Nation Roleplay Platform
========================
Single-file launcher: Discord Bot + FastAPI Web Server + WebSocket Hub + SQLite DB
Run: python main.py
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
import discord
from discord.ext import commands, tasks
from fastapi import (Depends, FastAPI, HTTPException, Request, WebSocket,
                     WebSocketDisconnect, status)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "MTQ4MTE0OTM3NzgyNDI5Mjg4NQ.GT9wUL.DgqtpWHwkQ1syOeBtZmjdPIXulezQoCBal6rqk")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY", secrets.token_hex(32))
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
DB_PATH = "nation_roleplay.db"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
BASE_DIR = Path(".")
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("NationRP")

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL,
        roblox_username TEXT,
        api_token TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')),
        last_active TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS nations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        tag TEXT UNIQUE NOT NULL,
        flag_emoji TEXT DEFAULT '🏳️',
        color TEXT DEFAULT '#3498db',
        capital TEXT DEFAULT '',
        population INTEGER DEFAULT 1000000,
        gdp REAL DEFAULT 1000000000.0,
        stability INTEGER DEFAULT 70,
        ideology TEXT DEFAULT 'Dân chủ',
        leader_id INTEGER REFERENCES users(id),
        founded_at TEXT DEFAULT (datetime('now')),
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS nation_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER REFERENCES nations(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        role TEXT DEFAULT 'Công dân',
        rank INTEGER DEFAULT 1,
        joined_at TEXT DEFAULT (datetime('now')),
        UNIQUE(nation_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS governments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER UNIQUE REFERENCES nations(id) ON DELETE CASCADE,
        system TEXT DEFAULT 'Cộng hòa',
        president TEXT DEFAULT '',
        prime_minister TEXT DEFAULT '',
        parliament_seats INTEGER DEFAULT 100,
        ruling_party TEXT DEFAULT '',
        constitution TEXT DEFAULT '',
        tax_rate REAL DEFAULT 0.25,
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS military (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER UNIQUE REFERENCES nations(id) ON DELETE CASCADE,
        army_size INTEGER DEFAULT 0,
        navy_size INTEGER DEFAULT 0,
        airforce_size INTEGER DEFAULT 0,
        nuclear_warheads INTEGER DEFAULT 0,
        defense_budget REAL DEFAULT 0.0,
        military_rank TEXT DEFAULT 'Yếu',
        conscription INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS soldiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER REFERENCES nations(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        rank TEXT DEFAULT 'Binh nhì',
        rank_level INTEGER DEFAULT 1,
        branch TEXT DEFAULT 'Lục quân',
        missions_completed INTEGER DEFAULT 0,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        enlisted_at TEXT DEFAULT (datetime('now')),
        UNIQUE(nation_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS economy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER UNIQUE REFERENCES nations(id) ON DELETE CASCADE,
        balance REAL DEFAULT 50000000.0,
        income_per_hour REAL DEFAULT 10000.0,
        expenses_per_hour REAL DEFAULT 5000.0,
        trade_volume REAL DEFAULT 0.0,
        inflation REAL DEFAULT 2.5,
        unemployment REAL DEFAULT 5.0,
        last_collected TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        balance REAL DEFAULT 5000.0,
        total_earned REAL DEFAULT 0.0,
        last_daily TEXT DEFAULT '2000-01-01'
    );

    CREATE TABLE IF NOT EXISTS territories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER REFERENCES nations(id),
        name TEXT NOT NULL,
        map_x REAL DEFAULT 0,
        map_y REAL DEFAULT 0,
        size REAL DEFAULT 100.0,
        population INTEGER DEFAULT 100000,
        resource TEXT DEFAULT 'Nông nghiệp',
        is_capital INTEGER DEFAULT 0,
        captured_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS alliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        founder_nation_id INTEGER REFERENCES nations(id),
        description TEXT DEFAULT '',
        founded_at TEXT DEFAULT (datetime('now')),
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS alliance_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER REFERENCES alliances(id) ON DELETE CASCADE,
        nation_id INTEGER REFERENCES nations(id) ON DELETE CASCADE,
        role TEXT DEFAULT 'Thành viên',
        joined_at TEXT DEFAULT (datetime('now')),
        UNIQUE(alliance_id, nation_id)
    );

    CREATE TABLE IF NOT EXISTS diplomacy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_a_id INTEGER REFERENCES nations(id),
        nation_b_id INTEGER REFERENCES nations(id),
        status TEXT DEFAULT 'Trung lập',
        established_at TEXT DEFAULT (datetime('now')),
        notes TEXT DEFAULT '',
        UNIQUE(nation_a_id, nation_b_id)
    );

    CREATE TABLE IF NOT EXISTS wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER REFERENCES nations(id),
        defender_id INTEGER REFERENCES nations(id),
        reason TEXT DEFAULT '',
        status TEXT DEFAULT 'Đang diễn ra',
        attacker_casualties INTEGER DEFAULT 0,
        defender_casualties INTEGER DEFAULT 0,
        started_at TEXT DEFAULT (datetime('now')),
        ended_at TEXT
    );

    CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER REFERENCES nations(id),
        assigned_to INTEGER REFERENCES users(id),
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        type TEXT DEFAULT 'Trinh sát',
        reward_money REAL DEFAULT 1000.0,
        reward_xp INTEGER DEFAULT 100,
        status TEXT DEFAULT 'Đang thực hiện',
        created_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nation_id INTEGER REFERENCES nations(id),
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        type TEXT DEFAULT 'Thông báo',
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id INTEGER REFERENCES wars(id),
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        attacker_forces INTEGER DEFAULT 0,
        defender_forces INTEGER DEFAULT 0,
        result TEXT DEFAULT 'Đang diễn ra',
        created_at TEXT DEFAULT (datetime('now')),
        ended_at TEXT
    );

    CREATE TABLE IF NOT EXISTS roblox_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        roblox_place_id TEXT,
        roblox_job_id TEXT,
        data TEXT DEFAULT '{}',
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    conn.commit()
    conn.close()
    log.info("Database initialized.")

# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET HUB
# ─────────────────────────────────────────────────────────────────────────────
class WSHub:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            if ws in self.connections:
                self.connections.remove(ws)

    async def broadcast(self, event: str, data: dict):
        msg = json.dumps({"event": event, "data": data, "ts": time.time()})
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

hub = WSHub()

# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────
class NationCreate(BaseModel):
    name: str
    tag: str
    flag_emoji: Optional[str] = "🏳️"
    color: Optional[str] = "#3498db"
    ideology: Optional[str] = "Dân chủ"
    description: Optional[str] = ""
    api_token: str

class MilitaryUpdate(BaseModel):
    army_size: Optional[int] = None
    navy_size: Optional[int] = None
    airforce_size: Optional[int] = None
    defense_budget: Optional[float] = None
    api_token: str

class DiplomacyAction(BaseModel):
    nation_a_tag: str
    nation_b_tag: str
    status: str
    api_token: str

class WarDeclare(BaseModel):
    attacker_tag: str
    defender_tag: str
    reason: str
    api_token: str

class RobloxSync(BaseModel):
    roblox_api_key: str
    discord_id: str
    data: dict

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def db_fetchone(sql: str, params=()) -> Optional[sqlite3.Row]:
    conn = get_db()
    try:
        row = conn.execute(sql, params).fetchone()
        return row
    finally:
        conn.close()

def db_fetchall(sql: str, params=()) -> list:
    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        return rows
    finally:
        conn.close()

def db_execute(sql: str, params=()) -> int:
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_or_create_user(discord_id: str, username: str) -> sqlite3.Row:
    user = db_fetchone("SELECT * FROM users WHERE discord_id=?", (discord_id,))
    if not user:
        token = secrets.token_hex(24)
        db_execute(
            "INSERT INTO users (discord_id, username, api_token) VALUES (?,?,?)",
            (discord_id, username, token)
        )
        db_execute(
            "INSERT INTO wallets (user_id) SELECT id FROM users WHERE discord_id=?",
            (discord_id,)
        )
        user = db_fetchone("SELECT * FROM users WHERE discord_id=?", (discord_id,))
    return user

def get_user_nation(user_id: int) -> Optional[sqlite3.Row]:
    return db_fetchone("""
        SELECT n.* FROM nations n
        JOIN nation_members nm ON nm.nation_id=n.id
        WHERE nm.user_id=? AND n.is_active=1
    """, (user_id,))

def military_rank_from_size(total: int) -> str:
    if total >= 500000: return "Siêu cường"
    if total >= 200000: return "Cường quốc"
    if total >= 100000: return "Mạnh"
    if total >= 50000: return "Trung bình"
    if total >= 10000: return "Yếu"
    return "Dân quân"

def verify_api_token(token: str) -> Optional[sqlite3.Row]:
    return db_fetchone("SELECT * FROM users WHERE api_token=?", (token,))

# ─────────────────────────────────────────────────────────────────────────────
# DISCORD BOT
# ─────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

def make_embed(title: str, description: str = "", color: int = 0x3498db) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.set_footer(text="🌍 Nation Roleplay Platform")
    e.timestamp = datetime.utcnow()
    return e

# .help
@bot.command(name="help")
async def cmd_help(ctx):
    e = make_embed("📖 Hướng Dẫn Sử Dụng", color=0x9b59b6)
    e.add_field(name="👤 Tài khoản", value=(
        "`.dangky` — Đăng ký tài khoản\n"
        "`.hoso` — Xem hồ sơ cá nhân"
    ), inline=False)
    e.add_field(name="🌍 Quốc gia", value=(
        "`.quocgia [tên]` — Xem thông tin quốc gia\n"
        "`.taoquocgia <tên> <ký_hiệu>` — Thành lập quốc gia\n"
        "`.thamgia <ký_hiệu>` — Tham gia quốc gia\n"
        "`.roiquocgia` — Rời quốc gia"
    ), inline=False)
    e.add_field(name="🏛️ Chính phủ & Quân đội", value=(
        "`.chinhphu` — Xem chính phủ\n"
        "`.quandoi` — Xem thông tin quân đội\n"
        "`.tuyendung <lục/hải/không>` — Tuyển quân\n"
        "`.thangcap @thành_viên` — Thăng cấp binh sĩ\n"
        "`.giangcap @thành_viên` — Giáng cấp binh sĩ"
    ), inline=False)
    e.add_field(name="⚔️ Chiến tranh & Ngoại giao", value=(
        "`.tuyenchien <ký_hiệu>` — Tuyên chiến\n"
        "`.hoabinh <ký_hiệu>` — Đề nghị hòa bình\n"
        "`.lienminh <ký_hiệu>` — Đề nghị liên minh\n"
        "`.chiendich <tên>` — Phát động chiến dịch"
    ), inline=False)
    e.add_field(name="💰 Kinh tế", value=(
        "`.bank` — Xem tài khoản ngân hàng\n"
        "`.luong` — Nhận lương\n"
        "`.daily` — Nhận thưởng hàng ngày"
    ), inline=False)
    e.add_field(name="📋 Nhiệm vụ & Sự kiện", value=(
        "`.sukien` — Xem sự kiện quốc gia\n"
        "`.nhiemvu` — Xem nhiệm vụ của bạn\n"
        "`.bando` — Xem bản đồ thế giới\n"
        "`.thongke` — Thống kê toàn cầu\n"
        "`.caidat` — Cài đặt quốc gia"
    ), inline=False)
    await ctx.send(embed=e)

# .dangky
@bot.command(name="dangky")
async def cmd_dangky(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    e = make_embed("✅ Đăng Ký Thành Công", color=0x2ecc71)
    e.add_field(name="Người dùng", value=ctx.author.mention)
    e.add_field(name="Mã API", value=f"`{user['api_token']}`")
    e.add_field(name="Hướng dẫn", value="Dùng mã API để đồng bộ với Roblox & Website.", inline=False)
    try:
        await ctx.author.send(embed=e)
        await ctx.send(f"✅ {ctx.author.mention} đã đăng ký! Kiểm tra tin nhắn riêng để lấy mã API.")
    except:
        await ctx.send(embed=e)

# .hoso
@bot.command(name="hoso")
async def cmd_hoso(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_or_create_user(str(target.id), target.display_name)
    nation = get_user_nation(user["id"])
    wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    soldier = db_fetchone("SELECT * FROM soldiers WHERE user_id=?", (user["id"],))

    e = make_embed(f"👤 Hồ Sơ: {target.display_name}", color=0x3498db)
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="Quốc gia", value=nation["name"] if nation else "Chưa có", inline=True)
    e.add_field(name="Số dư", value=f"💰 {wallet['balance']:,.0f} VND" if wallet else "—", inline=True)
    if soldier:
        e.add_field(name="Quân hàm", value=f"🎖️ {soldier['rank']} ({soldier['branch']})", inline=True)
        e.add_field(name="Nhiệm vụ hoàn thành", value=str(soldier["missions_completed"]), inline=True)
    e.add_field(name="Tham gia từ", value=user["created_at"][:10], inline=True)
    await ctx.send(embed=e)

# .quocgia
@bot.command(name="quocgia")
async def cmd_quocgia(ctx, *, name: str = None):
    if name:
        nation = db_fetchone("SELECT * FROM nations WHERE name LIKE ? OR tag LIKE ?", (f"%{name}%", name.upper()))
    else:
        user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
        nation = get_user_nation(user["id"])

    if not nation:
        await ctx.send("❌ Không tìm thấy quốc gia.")
        return

    gov = db_fetchone("SELECT * FROM governments WHERE nation_id=?", (nation["id"],))
    mil = db_fetchone("SELECT * FROM military WHERE nation_id=?", (nation["id"],))
    eco = db_fetchone("SELECT * FROM economy WHERE nation_id=?", (nation["id"],))
    member_count = db_fetchone("SELECT COUNT(*) as c FROM nation_members WHERE nation_id=?", (nation["id"],))
    leader = db_fetchone("SELECT username FROM users WHERE id=?", (nation["leader_id"],))

    e = make_embed(f"{nation['flag_emoji']} {nation['name']} [{nation['tag']}]", color=int(nation["color"].replace("#",""), 16))
    e.add_field(name="Lãnh đạo", value=leader["username"] if leader else "—", inline=True)
    e.add_field(name="Thành viên", value=str(member_count["c"]), inline=True)
    e.add_field(name="Dân số", value=f"{nation['population']:,}", inline=True)
    e.add_field(name="GDP", value=f"${nation['gdp']:,.0f}", inline=True)
    e.add_field(name="Thể chế", value=gov["system"] if gov else "—", inline=True)
    e.add_field(name="Ổn định", value=f"{nation['stability']}%", inline=True)
    if mil:
        total = (mil["army_size"] or 0) + (mil["navy_size"] or 0) + (mil["airforce_size"] or 0)
        e.add_field(name="Quân lực", value=f"⚔️ {total:,} ({mil['military_rank']})", inline=True)
    if eco:
        e.add_field(name="Ngân sách", value=f"💰 {eco['balance']:,.0f}", inline=True)
    e.add_field(name="Mô tả", value=nation["description"] or "Chưa có mô tả.", inline=False)
    await ctx.send(embed=e)

# .taoquocgia
@bot.command(name="taoquocgia")
async def cmd_taoquocgia(ctx, name: str = None, tag: str = None, *, extra: str = ""):
    if not name or not tag:
        await ctx.send("❌ Cú pháp: `.taoquocgia <Tên Quốc Gia> <KÝ_HIỆU>`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    existing = get_user_nation(user["id"])
    if existing:
        await ctx.send(f"❌ Bạn đã là thành viên của **{existing['name']}**. Hãy rời quốc gia trước.")
        return
    tag = tag.upper()[:4]
    if db_fetchone("SELECT id FROM nations WHERE tag=?", (tag,)):
        await ctx.send(f"❌ Ký hiệu `{tag}` đã tồn tại.")
        return
    if db_fetchone("SELECT id FROM nations WHERE name=?", (name,)):
        await ctx.send(f"❌ Tên quốc gia `{name}` đã tồn tại.")
        return

    nation_id = db_execute(
        "INSERT INTO nations (name, tag, leader_id) VALUES (?,?,?)",
        (name, tag, user["id"])
    )
    db_execute("INSERT INTO governments (nation_id) VALUES (?)", (nation_id,))
    db_execute("INSERT INTO military (nation_id) VALUES (?)", (nation_id,))
    db_execute("INSERT INTO economy (nation_id) VALUES (?)", (nation_id,))
    db_execute(
        "INSERT INTO nation_members (nation_id, user_id, role, rank) VALUES (?,?,?,?)",
        (nation_id, user["id"], "Quốc trưởng", 10)
    )
    asyncio.create_task(hub.broadcast("nation_created", {"name": name, "tag": tag}))
    e = make_embed(f"🎉 Quốc Gia Mới: {name}", color=0xf39c12)
    e.add_field(name="Ký hiệu", value=tag)
    e.add_field(name="Lãnh đạo", value=ctx.author.mention)
    e.add_field(name="Trạng thái", value="✅ Đã thành lập")
    await ctx.send(embed=e)

# .thamgia
@bot.command(name="thamgia")
async def cmd_thamgia(ctx, tag: str = None):
    if not tag:
        await ctx.send("❌ Cú pháp: `.thamgia <KÝ_HIỆU>`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    existing = get_user_nation(user["id"])
    if existing:
        await ctx.send(f"❌ Bạn đã thuộc quốc gia **{existing['name']}**.")
        return
    nation = db_fetchone("SELECT * FROM nations WHERE tag=? AND is_active=1", (tag.upper(),))
    if not nation:
        await ctx.send(f"❌ Không tìm thấy quốc gia `{tag.upper()}`.")
        return
    db_execute(
        "INSERT OR IGNORE INTO nation_members (nation_id, user_id, role) VALUES (?,?,?)",
        (nation["id"], user["id"], "Công dân")
    )
    db_execute("UPDATE nations SET population=population+50000 WHERE id=?", (nation["id"],))
    asyncio.create_task(hub.broadcast("member_joined", {"nation": nation["name"], "user": ctx.author.display_name}))
    await ctx.send(f"✅ {ctx.author.mention} đã gia nhập **{nation['name']}** [{nation['tag']}]!")

# .roiquocgia
@bot.command(name="roiquocgia")
async def cmd_roiquocgia(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    if nation["leader_id"] == user["id"]:
        await ctx.send("❌ Bạn là lãnh đạo. Hãy chuyển quyền lãnh đạo trước khi rời.")
        return
    db_execute("DELETE FROM nation_members WHERE nation_id=? AND user_id=?", (nation["id"], user["id"]))
    await ctx.send(f"✅ {ctx.author.mention} đã rời **{nation['name']}**.")

# .chinhphu
@bot.command(name="chinhphu")
async def cmd_chinhphu(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    gov = db_fetchone("SELECT * FROM governments WHERE nation_id=?", (nation["id"],))
    if not gov:
        await ctx.send("❌ Quốc gia chưa có chính phủ.")
        return
    e = make_embed(f"🏛️ Chính Phủ: {nation['name']}", color=0x8e44ad)
    e.add_field(name="Thể chế", value=gov["system"], inline=True)
    e.add_field(name="Tổng thống/Chủ tịch", value=gov["president"] or "Trống", inline=True)
    e.add_field(name="Thủ tướng", value=gov["prime_minister"] or "Trống", inline=True)
    e.add_field(name="Đảng cầm quyền", value=gov["ruling_party"] or "Trống", inline=True)
    e.add_field(name="Ghế nghị viện", value=str(gov["parliament_seats"]), inline=True)
    e.add_field(name="Thuế suất", value=f"{gov['tax_rate']*100:.0f}%", inline=True)
    await ctx.send(embed=e)

# .quandoi
@bot.command(name="quandoi")
async def cmd_quandoi(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    mil = db_fetchone("SELECT * FROM military WHERE nation_id=?", (nation["id"],))
    soldiers_count = db_fetchone("SELECT COUNT(*) as c FROM soldiers WHERE nation_id=?", (nation["id"],))
    e = make_embed(f"⚔️ Quân Đội: {nation['name']}", color=0xe74c3c)
    e.add_field(name="Lục quân", value=f"{mil['army_size']:,} quân", inline=True)
    e.add_field(name="Hải quân", value=f"{mil['navy_size']:,} quân", inline=True)
    e.add_field(name="Không quân", value=f"{mil['airforce_size']:,} quân", inline=True)
    e.add_field(name="Vũ khí hạt nhân", value=str(mil["nuclear_warheads"]), inline=True)
    e.add_field(name="Ngân sách quốc phòng", value=f"${mil['defense_budget']:,.0f}", inline=True)
    e.add_field(name="Sức mạnh", value=mil["military_rank"], inline=True)
    e.add_field(name="Binh sĩ đã tuyển", value=str(soldiers_count["c"]), inline=True)
    e.add_field(name="Nghĩa vụ quân sự", value="Có" if mil["conscription"] else "Không", inline=True)
    await ctx.send(embed=e)

# .tuyendung
@bot.command(name="tuyendung")
async def cmd_tuyendung(ctx, branch: str = "lục"):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    branch_map = {"lục": "Lục quân", "hải": "Hải quân", "không": "Không quân"}
    branch_vn = branch_map.get(branch.lower(), "Lục quân")
    existing = db_fetchone("SELECT * FROM soldiers WHERE nation_id=? AND user_id=?", (nation["id"], user["id"]))
    if existing:
        await ctx.send(f"❌ Bạn đã là binh sĩ ({existing['rank']}) trong {existing['branch']}.")
        return
    db_execute(
        "INSERT INTO soldiers (nation_id, user_id, branch) VALUES (?,?,?)",
        (nation["id"], user["id"], branch_vn)
    )
    col_map = {"Lục quân": "army_size", "Hải quân": "navy_size", "Không quân": "airforce_size"}
    db_execute(f"UPDATE military SET {col_map[branch_vn]}={col_map[branch_vn]}+1 WHERE nation_id=?", (nation["id"],))
    await ctx.send(f"✅ {ctx.author.mention} đã gia nhập **{branch_vn}** của {nation['name']} với quân hàm **Binh nhì**!")

RANKS = ["Binh nhì","Binh nhất","Hạ sĩ","Trung sĩ","Thượng sĩ","Thiếu úy","Trung úy","Đại úy","Thiếu tá","Trung tá","Đại tá","Thiếu tướng","Trung tướng","Đại tướng"]

# .thangcap
@bot.command(name="thangcap")
async def cmd_thangcap(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("❌ Cú pháp: `.thangcap @thành_viên`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo quốc gia mới có quyền thăng cấp.")
        return
    target_user = get_or_create_user(str(member.id), member.display_name)
    soldier = db_fetchone("SELECT * FROM soldiers WHERE nation_id=? AND user_id=?", (nation["id"], target_user["id"]))
    if not soldier:
        await ctx.send(f"❌ {member.mention} không phải binh sĩ trong quốc gia.")
        return
    idx = RANKS.index(soldier["rank"]) if soldier["rank"] in RANKS else 0
    if idx >= len(RANKS) - 1:
        await ctx.send(f"❌ {member.mention} đã đạt cấp bậc cao nhất.")
        return
    new_rank = RANKS[idx + 1]
    db_execute("UPDATE soldiers SET rank=?, rank_level=? WHERE id=?", (new_rank, idx+2, soldier["id"]))
    await ctx.send(f"🎖️ {member.mention} đã được thăng cấp lên **{new_rank}**!")

# .giangcap
@bot.command(name="giangcap")
async def cmd_giangcap(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("❌ Cú pháp: `.giangcap @thành_viên`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo quốc gia mới có quyền giáng cấp.")
        return
    target_user = get_or_create_user(str(member.id), member.display_name)
    soldier = db_fetchone("SELECT * FROM soldiers WHERE nation_id=? AND user_id=?", (nation["id"], target_user["id"]))
    if not soldier:
        await ctx.send(f"❌ {member.mention} không phải binh sĩ.")
        return
    idx = RANKS.index(soldier["rank"]) if soldier["rank"] in RANKS else 0
    if idx <= 0:
        await ctx.send(f"❌ {member.mention} đã ở cấp bậc thấp nhất.")
        return
    new_rank = RANKS[idx - 1]
    db_execute("UPDATE soldiers SET rank=?, rank_level=? WHERE id=?", (new_rank, idx, soldier["id"]))
    await ctx.send(f"⬇️ {member.mention} đã bị giáng cấp xuống **{new_rank}**.")

# .bank
@bot.command(name="bank")
async def cmd_bank(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    if not wallet:
        db_execute("INSERT INTO wallets (user_id) VALUES (?)", (user["id"],))
        wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    e = make_embed(f"🏦 Ngân Hàng: {ctx.author.display_name}", color=0xf1c40f)
    e.add_field(name="Số dư", value=f"💰 {wallet['balance']:,.0f} VND", inline=True)
    e.add_field(name="Tổng kiếm được", value=f"💵 {wallet['total_earned']:,.0f} VND", inline=True)
    await ctx.send(embed=e)

# .luong
@bot.command(name="luong")
async def cmd_luong(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    soldier = db_fetchone("SELECT * FROM soldiers WHERE user_id=?", (user["id"],))
    if not soldier:
        await ctx.send("❌ Bạn cần gia nhập quân đội để nhận lương.")
        return
    salary_map = {
        "Binh nhì": 500, "Binh nhất": 600, "Hạ sĩ": 800, "Trung sĩ": 1000,
        "Thượng sĩ": 1200, "Thiếu úy": 1500, "Trung úy": 2000, "Đại úy": 2500,
        "Thiếu tá": 3500, "Trung tá": 5000, "Đại tá": 7000,
        "Thiếu tướng": 10000, "Trung tướng": 15000, "Đại tướng": 25000
    }
    amount = salary_map.get(soldier["rank"], 500)
    db_execute("UPDATE wallets SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
               (amount, amount, user["id"]))
    await ctx.send(f"✅ {ctx.author.mention} đã nhận lương **{amount:,} VND** (Quân hàm: {soldier['rank']})!")

# .daily
@bot.command(name="daily")
async def cmd_daily(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if wallet and wallet["last_daily"] == today:
        await ctx.send("❌ Bạn đã nhận thưởng hàng ngày rồi. Quay lại vào ngày mai!")
        return
    amount = 2000
    db_execute("UPDATE wallets SET balance=balance+?, total_earned=total_earned+?, last_daily=? WHERE user_id=?",
               (amount, amount, today, user["id"]))
    await ctx.send(f"🎁 {ctx.author.mention} đã nhận **{amount:,} VND** thưởng hàng ngày!")

# .sukien
@bot.command(name="sukien")
async def cmd_sukien(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    events = db_fetchall("SELECT * FROM events WHERE nation_id=? ORDER BY created_at DESC LIMIT 10", (nation["id"],))
    if not events:
        await ctx.send("📋 Chưa có sự kiện nào.")
        return
    e = make_embed(f"📋 Sự Kiện: {nation['name']}", color=0x1abc9c)
    for ev in events:
        e.add_field(name=f"[{ev['type']}] {ev['title']}", value=ev["description"][:100] or "—", inline=False)
    await ctx.send(embed=e)

# .nhiemvu
@bot.command(name="nhiemvu")
async def cmd_nhiemvu(ctx):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    missions = db_fetchall(
        "SELECT * FROM missions WHERE assigned_to=? AND status='Đang thực hiện' ORDER BY created_at DESC LIMIT 5",
        (user["id"],)
    )
    if not missions:
        await ctx.send("📋 Bạn không có nhiệm vụ nào đang thực hiện.")
        return
    e = make_embed("🎯 Nhiệm Vụ Của Bạn", color=0xe67e22)
    for m in missions:
        e.add_field(
            name=f"[{m['type']}] {m['title']}",
            value=f"{m['description'][:80]}\n💰 {m['reward_money']:,.0f} VND | ✨ {m['reward_xp']} XP",
            inline=False
        )
    await ctx.send(embed=e)

# .tuyenchien
@bot.command(name="tuyenchien")
async def cmd_tuyenchien(ctx, tag: str = None, *, reason: str = "Không có lý do"):
    if not tag:
        await ctx.send("❌ Cú pháp: `.tuyenchien <KÝ_HIỆU> [lý_do]`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo quốc gia mới có thể tuyên chiến.")
        return
    defender = db_fetchone("SELECT * FROM nations WHERE tag=? AND is_active=1", (tag.upper(),))
    if not defender:
        await ctx.send(f"❌ Không tìm thấy quốc gia `{tag.upper()}`.")
        return
    if defender["id"] == nation["id"]:
        await ctx.send("❌ Không thể tuyên chiến với chính mình.")
        return
    existing_war = db_fetchone(
        "SELECT * FROM wars WHERE ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)) AND status='Đang diễn ra'",
        (nation["id"], defender["id"], defender["id"], nation["id"])
    )
    if existing_war:
        await ctx.send(f"❌ Đã có chiến tranh đang diễn ra với **{defender['name']}**.")
        return
    war_id = db_execute(
        "INSERT INTO wars (attacker_id, defender_id, reason) VALUES (?,?,?)",
        (nation["id"], defender["id"], reason)
    )
    db_execute("UPDATE diplomacy SET status='Chiến tranh' WHERE (nation_a_id=? AND nation_b_id=?) OR (nation_a_id=? AND nation_b_id=?)",
               (nation["id"], defender["id"], defender["id"], nation["id"]))
    asyncio.create_task(hub.broadcast("war_declared", {
        "attacker": nation["name"], "defender": defender["name"], "reason": reason
    }))
    e = make_embed("⚔️ TUYÊN CHIẾN!", color=0xe74c3c)
    e.add_field(name="Bên tấn công", value=f"{nation['flag_emoji']} {nation['name']}", inline=True)
    e.add_field(name="Bên phòng thủ", value=f"{defender['flag_emoji']} {defender['name']}", inline=True)
    e.add_field(name="Lý do", value=reason, inline=False)
    e.add_field(name="Mã chiến tranh", value=f"#{war_id}", inline=True)
    await ctx.send(embed=e)

# .hoabinh
@bot.command(name="hoabinh")
async def cmd_hoabinh(ctx, tag: str = None):
    if not tag:
        await ctx.send("❌ Cú pháp: `.hoabinh <KÝ_HIỆU>`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation:
        await ctx.send("❌ Bạn chưa thuộc quốc gia nào.")
        return
    other = db_fetchone("SELECT * FROM nations WHERE tag=? AND is_active=1", (tag.upper(),))
    if not other:
        await ctx.send(f"❌ Không tìm thấy quốc gia `{tag.upper()}`.")
        return
    war = db_fetchone(
        "SELECT * FROM wars WHERE ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)) AND status='Đang diễn ra'",
        (nation["id"], other["id"], other["id"], nation["id"])
    )
    if not war:
        await ctx.send("❌ Không có chiến tranh đang diễn ra với quốc gia này.")
        return
    db_execute("UPDATE wars SET status='Hòa bình', ended_at=datetime('now') WHERE id=?", (war["id"],))
    asyncio.create_task(hub.broadcast("peace_declared", {"nations": [nation["name"], other["name"]]}))
    await ctx.send(f"🕊️ **{nation['name']}** và **{other['name']}** đã ký kết hòa bình!")

# .lienminh
@bot.command(name="lienminh")
async def cmd_lienminh(ctx, tag: str = None):
    if not tag:
        await ctx.send("❌ Cú pháp: `.lienminh <KÝ_HIỆU>`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo mới có thể đề xuất liên minh.")
        return
    other = db_fetchone("SELECT * FROM nations WHERE tag=? AND is_active=1", (tag.upper(),))
    if not other:
        await ctx.send(f"❌ Không tìm thấy quốc gia `{tag.upper()}`.")
        return
    alliance_name = f"Liên Minh {nation['tag']}-{other['tag']}"
    alliance_id = db_execute(
        "INSERT OR IGNORE INTO alliances (name, founder_nation_id) VALUES (?,?)",
        (alliance_name, nation["id"])
    )
    if alliance_id:
        db_execute("INSERT OR IGNORE INTO alliance_members (alliance_id, nation_id, role) VALUES (?,?,?)",
                   (alliance_id, nation["id"], "Thành lập"))
        db_execute("INSERT OR IGNORE INTO alliance_members (alliance_id, nation_id, role) VALUES (?,?,?)",
                   (alliance_id, other["id"], "Thành viên"))
        await ctx.send(f"🤝 **{nation['name']}** và **{other['name']}** đã thành lập **{alliance_name}**!")
    else:
        await ctx.send("❌ Liên minh đã tồn tại.")

# .chiendich
@bot.command(name="chiendich")
async def cmd_chiendich(ctx, *, campaign_name: str = None):
    if not campaign_name:
        await ctx.send("❌ Cú pháp: `.chiendich <Tên Chiến Dịch>`")
        return
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo quốc gia mới có thể phát động chiến dịch.")
        return
    war = db_fetchone("SELECT * FROM wars WHERE attacker_id=? AND status='Đang diễn ra'", (nation["id"],))
    if not war:
        await ctx.send("❌ Quốc gia của bạn không có chiến tranh đang diễn ra.")
        return
    mil = db_fetchone("SELECT * FROM military WHERE nation_id=?", (nation["id"],))
    total_force = (mil["army_size"] or 0) + (mil["navy_size"] or 0) + (mil["airforce_size"] or 0)
    db_execute(
        "INSERT INTO campaigns (war_id, name, attacker_forces) VALUES (?,?,?)",
        (war["id"], campaign_name, total_force)
    )
    e = make_embed(f"🚀 Chiến Dịch: {campaign_name}", color=0xc0392b)
    e.add_field(name="Quốc gia", value=nation["name"])
    e.add_field(name="Lực lượng triển khai", value=f"{total_force:,} quân")
    e.add_field(name="Trạng thái", value="Đang diễn ra")
    await ctx.send(embed=e)

# .bando
@bot.command(name="bando")
async def cmd_bando(ctx):
    nations = db_fetchall("SELECT name, tag, flag_emoji FROM nations WHERE is_active=1 ORDER BY name LIMIT 20")
    e = make_embed("🗺️ Bản Đồ Thế Giới", color=0x2c3e50)
    if not nations:
        e.description = "Chưa có quốc gia nào. Hãy dùng `.taoquocgia` để bắt đầu!"
    else:
        e.description = "\n".join([f"{n['flag_emoji']} **{n['name']}** `[{n['tag']}]`" for n in nations])
    e.add_field(name="Website", value=f"http://localhost:{WEB_PORT}", inline=False)
    await ctx.send(embed=e)

# .thongke
@bot.command(name="thongke")
async def cmd_thongke(ctx):
    nation_count = db_fetchone("SELECT COUNT(*) as c FROM nations WHERE is_active=1")
    user_count = db_fetchone("SELECT COUNT(*) as c FROM users")
    war_count = db_fetchone("SELECT COUNT(*) as c FROM wars WHERE status='Đang diễn ra'")
    alliance_count = db_fetchone("SELECT COUNT(*) as c FROM alliances WHERE is_active=1")
    e = make_embed("📊 Thống Kê Thế Giới", color=0x34495e)
    e.add_field(name="🌍 Quốc gia", value=str(nation_count["c"]), inline=True)
    e.add_field(name="👥 Người chơi", value=str(user_count["c"]), inline=True)
    e.add_field(name="⚔️ Chiến tranh", value=str(war_count["c"]), inline=True)
    e.add_field(name="🤝 Liên minh", value=str(alliance_count["c"]), inline=True)
    await ctx.send(embed=e)

# .caidat
@bot.command(name="caidat")
async def cmd_caidat(ctx, setting: str = None, *, value: str = None):
    user = get_or_create_user(str(ctx.author.id), ctx.author.display_name)
    nation = get_user_nation(user["id"])
    if not nation or nation["leader_id"] != user["id"]:
        await ctx.send("❌ Chỉ lãnh đạo quốc gia mới có thể cài đặt.")
        return
    if not setting:
        await ctx.send("⚙️ Các cài đặt: `flag <emoji>`, `mota <mô tả>`, `mausac <#hex>`, `thuchanh <chế độ>`")
        return
    if setting == "flag" and value:
        db_execute("UPDATE nations SET flag_emoji=? WHERE id=?", (value, nation["id"]))
        await ctx.send(f"✅ Cập nhật cờ thành công: {value}")
    elif setting == "mota" and value:
        db_execute("UPDATE nations SET description=? WHERE id=?", (value[:500], nation["id"]))
        await ctx.send(f"✅ Cập nhật mô tả thành công.")
    elif setting == "mausac" and value:
        db_execute("UPDATE nations SET color=? WHERE id=?", (value, nation["id"]))
        await ctx.send(f"✅ Cập nhật màu sắc thành công: {value}")
    else:
        await ctx.send("❌ Cài đặt không hợp lệ.")
    asyncio.create_task(hub.broadcast("nation_updated", {"id": nation["id"]}))

@bot.event
async def on_ready():
    log.info(f"Discord Bot: {bot.user} online")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"❌ Lỗi: {str(error)[:200]}")

# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILE GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_static_files():
    STATIC_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)

    # ── index.html ────────────────────────────────────────────────────────────
    html = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nation Roleplay Platform</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0e1a;--card:#111827;--border:#1f2937;--accent:#3b82f6;--accent2:#8b5cf6;--green:#10b981;--red:#ef4444;--yellow:#f59e0b;--text:#f9fafb;--muted:#6b7280}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;min-height:100vh}
#app{display:grid;grid-template-rows:60px 1fr;min-height:100vh}
nav{background:var(--card);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:16px;position:sticky;top:0;z-index:100}
nav h1{font-size:1.1rem;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
nav .nav-links{display:flex;gap:4px;margin-left:16px}
nav .nav-links a{padding:6px 14px;border-radius:8px;color:var(--muted);text-decoration:none;font-size:.875rem;transition:.2s}
nav .nav-links a:hover,nav .nav-links a.active{background:var(--border);color:var(--text)}
nav .status{margin-left:auto;display:flex;align-items:center;gap:8px;font-size:.8rem}
#ws-indicator{width:8px;height:8px;border-radius:50%;background:var(--red)}
#ws-indicator.connected{background:var(--green)}
main{padding:24px;overflow-y:auto}
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.grid-3{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px}
.card h3{font-size:.9rem;color:var(--muted);margin-bottom:12px;text-transform:uppercase;letter-spacing:.05em}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)}
.stat-row:last-child{border:none}
.stat-val{font-weight:600;font-size:1.1rem}
.badge{padding:2px 10px;border-radius:20px;font-size:.75rem;font-weight:600}
.badge-blue{background:rgba(59,130,246,.2);color:var(--accent)}
.badge-green{background:rgba(16,185,129,.2);color:var(--green)}
.badge-red{background:rgba(239,68,68,.2);color:var(--red)}
.badge-yellow{background:rgba(245,158,11,.2);color:var(--yellow)}
.nation-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;cursor:pointer;transition:.2s;position:relative;overflow:hidden}
.nation-card:hover{border-color:var(--accent);transform:translateY(-2px)}
.nation-card .flag{font-size:2.5rem;margin-bottom:8px}
.nation-card h4{font-size:1rem;font-weight:700}
.nation-card .tag{font-size:.75rem;color:var(--muted);margin-top:2px}
.nation-card .accent-bar{position:absolute;top:0;left:0;right:0;height:3px}
.search-bar{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 16px;color:var(--text);width:100%;font-size:.9rem;margin-bottom:16px;outline:none}
.search-bar:focus{border-color:var(--accent)}
.page{display:none}
.page.active{display:block}
#map-container{width:100%;height:500px;background:linear-gradient(135deg,#0d2137,#0a1929);border-radius:12px;position:relative;overflow:hidden;border:1px solid var(--border)}
#map-svg{width:100%;height:100%}
.map-nation{cursor:pointer;transition:.2s}
.map-nation:hover{filter:brightness(1.3)}
.map-tooltip{position:absolute;background:rgba(0,0,0,.9);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:.8rem;pointer-events:none;display:none;z-index:10;min-width:140px}
.war-item{padding:12px;border-radius:8px;border:1px solid rgba(239,68,68,.3);background:rgba(239,68,68,.05);margin-bottom:8px}
.alliance-item{padding:12px;border-radius:8px;border:1px solid rgba(59,130,246,.3);background:rgba(59,130,246,.05);margin-bottom:8px}
.notification{position:fixed;bottom:24px;right:24px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;font-size:.875rem;z-index:999;animation:slideIn .3s ease;max-width:320px}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:none;opacity:1}}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:90%;max-width:520px;max-height:80vh;overflow-y:auto}
.modal h2{margin-bottom:20px;font-size:1.2rem}
.input-group{margin-bottom:14px}
.input-group label{display:block;font-size:.8rem;color:var(--muted);margin-bottom:6px}
.input-group input,.input-group textarea,.input-group select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:.9rem;outline:none}
.input-group input:focus,.input-group textarea:focus{border-color:var(--accent)}
.btn{padding:10px 20px;border-radius:8px;border:none;font-size:.875rem;font-weight:600;cursor:pointer;transition:.2s}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:#2563eb}
.btn-danger{background:var(--red);color:#fff}
.btn-success{background:var(--green);color:#fff}
.btn-sm{padding:6px 12px;font-size:.8rem}
.flex{display:flex;gap:8px;align-items:center}
.flex-end{justify-content:flex-end}
.mt-8{margin-top:8px}
.live-badge{padding:2px 8px;border-radius:20px;background:rgba(239,68,68,.2);color:var(--red);font-size:.7rem;font-weight:700;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.leaderboard-row{display:grid;grid-template-columns:40px 1fr auto;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)}
.leaderboard-row:last-child{border:none}
.rank-num{width:32px;height:32px;border-radius:50%;background:var(--border);display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700}
.rank-num.gold{background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff}
.rank-num.silver{background:linear-gradient(135deg,#9ca3af,#6b7280);color:#fff}
.rank-num.bronze{background:linear-gradient(135deg,#b45309,#92400e);color:#fff}
</style>
</head>
<body>
<div id="app">
<nav>
  <h1>🌍 Nation Roleplay</h1>
  <div class="nav-links">
    <a href="#" class="active" onclick="showPage('dashboard',this)">Dashboard</a>
    <a href="#" onclick="showPage('nations',this)">Quốc Gia</a>
    <a href="#" onclick="showPage('map',this)">Bản Đồ</a>
    <a href="#" onclick="showPage('military',this)">Quân Đội</a>
    <a href="#" onclick="showPage('diplomacy',this)">Ngoại Giao</a>
    <a href="#" onclick="showPage('economy',this)">Kinh Tế</a>
    <a href="#" onclick="showPage('roblox',this)">Roblox API</a>
  </div>
  <div class="status">
    <div id="ws-indicator"></div>
    <span id="ws-text">Đang kết nối...</span>
    <span class="live-badge">LIVE</span>
  </div>
</nav>
<main>
  <!-- DASHBOARD -->
  <div id="page-dashboard" class="page active">
    <div class="grid-3" style="margin-bottom:16px">
      <div class="card">
        <h3>Quốc Gia</h3>
        <div class="stat-val" id="stat-nations">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đang hoạt động</div>
      </div>
      <div class="card">
        <h3>Người Chơi</h3>
        <div class="stat-val" id="stat-users">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đã đăng ký</div>
      </div>
      <div class="card">
        <h3>Chiến Tranh</h3>
        <div class="stat-val" id="stat-wars">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đang diễn ra</div>
      </div>
      <div class="card">
        <h3>Liên Minh</h3>
        <div class="stat-val" id="stat-alliances">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đang hoạt động</div>
      </div>
      <div class="card">
        <h3>Binh Sĩ</h3>
        <div class="stat-val" id="stat-soldiers">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đã tuyển</div>
      </div>
      <div class="card">
        <h3>Nhiệm Vụ</h3>
        <div class="stat-val" id="stat-missions">—</div>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">Đang thực hiện</div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <h3>Bảng Xếp Hạng Quốc Gia</h3>
        <div id="leaderboard-list">Đang tải...</div>
      </div>
      <div class="card">
        <h3>Chiến Tranh Đang Diễn Ra</h3>
        <div id="wars-list">Đang tải...</div>
      </div>
    </div>
  </div>

  <!-- NATIONS -->
  <div id="page-nations" class="page">
    <div class="flex" style="margin-bottom:16px">
      <input type="text" class="search-bar" id="nation-search" placeholder="🔍 Tìm quốc gia..." oninput="filterNations()" style="margin:0;flex:1">
      <button class="btn btn-primary" onclick="openCreateNation()">+ Tạo Quốc Gia</button>
    </div>
    <div class="grid-3" id="nations-grid">Đang tải...</div>
  </div>

  <!-- MAP -->
  <div id="page-map" class="page">
    <div class="card" style="margin-bottom:16px">
      <h3>Bản Đồ Thế Giới Tương Tác</h3>
      <div id="map-container">
        <svg id="map-svg" viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg">
          <rect width="800" height="500" fill="#0d2137"/>
          <!-- Ocean grid -->
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#0a1929" stroke-width="0.5"/>
          </pattern>
          <rect width="800" height="500" fill="url(#grid)"/>
          <text x="400" y="250" fill="rgba(255,255,255,0.1)" font-size="14" text-anchor="middle">Chưa có quốc gia nào trên bản đồ</text>
        </svg>
        <div class="map-tooltip" id="map-tooltip"></div>
      </div>
    </div>
    <div class="card">
      <h3>Lãnh Thổ</h3>
      <div id="territories-list">Đang tải...</div>
    </div>
  </div>

  <!-- MILITARY -->
  <div id="page-military" class="page">
    <div class="grid-2" id="military-grid">Đang tải...</div>
  </div>

  <!-- DIPLOMACY -->
  <div id="page-diplomacy" class="page">
    <div class="grid-2">
      <div class="card">
        <h3>Liên Minh</h3>
        <div id="alliances-list">Đang tải...</div>
      </div>
      <div class="card">
        <h3>Quan Hệ Ngoại Giao</h3>
        <div id="diplomacy-list">Đang tải...</div>
      </div>
    </div>
  </div>

  <!-- ECONOMY -->
  <div id="page-economy" class="page">
    <div class="grid-2" id="economy-grid">Đang tải...</div>
  </div>

  <!-- ROBLOX API -->
  <div id="page-roblox" class="page">
    <div class="grid-2">
      <div class="card">
        <h3>Tài Liệu API Roblox</h3>
        <div style="font-size:.85rem;line-height:1.7;color:var(--muted)">
          <p style="color:var(--text);margin-bottom:12px">Tích hợp dữ liệu Roblox vào hệ thống Nation Roleplay.</p>
          <div style="background:var(--bg);border-radius:8px;padding:12px;margin-bottom:12px;font-family:monospace;font-size:.8rem">
            <div style="color:var(--green)">POST /api/roblox/sync</div>
            <div style="color:var(--muted);margin-top:4px">{</div>
            <div style="color:var(--muted);padding-left:16px">"roblox_api_key": "YOUR_KEY",</div>
            <div style="color:var(--muted);padding-left:16px">"discord_id": "123456789",</div>
            <div style="color:var(--muted);padding-left:16px">"data": {"kills":5,"deaths":2}</div>
            <div style="color:var(--muted)">}</div>
          </div>
          <div style="background:var(--bg);border-radius:8px;padding:12px;margin-bottom:12px;font-family:monospace;font-size:.8rem">
            <div style="color:var(--green)">GET /api/roblox/player/{discord_id}</div>
            <div style="color:var(--muted);margin-top:4px">Lấy dữ liệu người chơi từ Discord ID</div>
          </div>
          <div style="background:var(--bg);border-radius:8px;padding:12px;font-family:monospace;font-size:.8rem">
            <div style="color:var(--green)">GET /api/nations</div>
            <div style="color:var(--muted);margin-top:4px">Danh sách tất cả quốc gia + lãnh thổ</div>
          </div>
        </div>
        <div class="input-group" style="margin-top:16px">
          <label>ROBLOX API KEY (dùng trong game script)</label>
          <input type="text" id="roblox-key-display" value="Nhập Discord ID để xem..." readonly style="font-family:monospace">
        </div>
        <div class="input-group">
          <label>Discord ID</label>
          <input type="text" id="lookup-discord-id" placeholder="Nhập Discord ID của bạn">
        </div>
        <button class="btn btn-primary" onclick="lookupPlayer()">Tra Cứu</button>
        <div id="player-lookup-result" style="margin-top:12px"></div>
      </div>
      <div class="card">
        <h3>Phiên Roblox Đang Hoạt Động</h3>
        <div id="roblox-sessions">Đang tải...</div>
        <div style="margin-top:16px">
          <h3 style="font-size:.9rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">Lua Script Mẫu</h3>
          <pre style="background:var(--bg);border-radius:8px;padding:12px;font-size:.75rem;overflow-x:auto;color:var(--green)">-- Nation Roleplay Sync Script
local API = "http://YOUR_SERVER:8000"
local KEY = "YOUR_ROBLOX_API_KEY"

local function syncPlayer(discordId, data)
  local body = game:GetService("HttpService")
    :JSONEncode({
      roblox_api_key = KEY,
      discord_id = discordId,
      data = data
    })
  local resp = game:GetService("HttpService")
    :PostAsync(API.."/api/roblox/sync", body)
  return resp
end

-- Gọi khi người chơi giết địch
syncPlayer("123456789", {
  kills = 1,
  nation_tag = "VN",
  territory = "Hà Nội"
})</pre>
        </div>
      </div>
    </div>
  </div>
</main>
</div>

<!-- CREATE NATION MODAL -->
<div class="modal-overlay" id="create-modal">
  <div class="modal">
    <h2>🌍 Tạo Quốc Gia Mới</h2>
    <div class="input-group">
      <label>Tên Quốc Gia *</label>
      <input type="text" id="cn-name" placeholder="Ví dụ: Cộng Hòa Việt Nam">
    </div>
    <div class="input-group">
      <label>Ký Hiệu (2-4 chữ cái) *</label>
      <input type="text" id="cn-tag" maxlength="4" placeholder="VN">
    </div>
    <div class="input-group">
      <label>Cờ (Emoji)</label>
      <input type="text" id="cn-flag" placeholder="🏳️" value="🏳️">
    </div>
    <div class="input-group">
      <label>Màu Sắc</label>
      <input type="color" id="cn-color" value="#3b82f6">
    </div>
    <div class="input-group">
      <label>Tư Tưởng</label>
      <select id="cn-ideology">
        <option>Dân chủ</option>
        <option>Cộng sản</option>
        <option>Quân chủ</option>
        <option>Độc tài</option>
        <option>Thần quyền</option>
        <option>Cộng hòa</option>
        <option>Liên bang</option>
      </select>
    </div>
    <div class="input-group">
      <label>Mô Tả</label>
      <textarea id="cn-desc" placeholder="Mô tả ngắn về quốc gia..." rows="3"></textarea>
    </div>
    <div class="input-group">
      <label>API Token (từ lệnh .dangky)</label>
      <input type="text" id="cn-token" placeholder="Mã API của bạn">
    </div>
    <div class="flex flex-end mt-8">
      <button class="btn" onclick="closeModal()" style="background:var(--border)">Hủy</button>
      <button class="btn btn-primary" onclick="submitCreateNation()">Tạo Quốc Gia</button>
    </div>
  </div>
</div>

<!-- NATION DETAIL MODAL -->
<div class="modal-overlay" id="detail-modal">
  <div class="modal">
    <div id="detail-content"></div>
    <div class="flex flex-end mt-8">
      <button class="btn" onclick="closeModal()" style="background:var(--border)">Đóng</button>
    </div>
  </div>
</div>

<script>
const API = '';
let ws = null;
let allNations = [];
let reconnectDelay = 1000;

function showPage(name, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  if (el) el.classList.add('active');
  if (name === 'nations') loadNations();
  if (name === 'map') loadMap();
  if (name === 'military') loadMilitary();
  if (name === 'diplomacy') loadDiplomacy();
  if (name === 'economy') loadEconomy();
  if (name === 'roblox') loadRobloxSessions();
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    document.getElementById('ws-indicator').className = 'connected';
    document.getElementById('ws-text').textContent = 'Đã kết nối';
    reconnectDelay = 1000;
    loadDashboard();
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    handleWSEvent(msg);
  };
  ws.onclose = () => {
    document.getElementById('ws-indicator').className = '';
    document.getElementById('ws-text').textContent = 'Mất kết nối';
    setTimeout(connectWS, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  };
}

function handleWSEvent(msg) {
  const eventMap = {
    nation_created: () => { notify('🌍 Quốc gia mới: '+msg.data.name); loadDashboard(); if(document.getElementById('page-nations').classList.contains('active')) loadNations(); },
    member_joined: () => { notify(`👤 ${msg.data.user} đã gia nhập ${msg.data.nation}`); },
    war_declared: () => { notify(`⚔️ CHIẾN TRANH: ${msg.data.attacker} vs ${msg.data.defender}`, 'red'); loadDashboard(); },
    peace_declared: () => { notify(`🕊️ Hòa bình: ${msg.data.nations.join(' & ')}`); loadDashboard(); },
    nation_updated: () => { if(document.getElementById('page-nations').classList.contains('active')) loadNations(); }
  };
  if (eventMap[msg.event]) eventMap[msg.event]();
}

function notify(text, type='blue') {
  const el = document.createElement('div');
  el.className = 'notification';
  el.style.borderColor = type === 'red' ? 'rgba(239,68,68,.5)' : 'rgba(59,130,246,.5)';
  el.textContent = text;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function api(path, opts={}) {
  const r = await fetch(API+path, {headers:{'Content-Type':'application/json'},...opts});
  return r.json();
}

async function loadDashboard() {
  const data = await api('/api/stats');
  document.getElementById('stat-nations').textContent = data.nations ?? '—';
  document.getElementById('stat-users').textContent = data.users ?? '—';
  document.getElementById('stat-wars').textContent = data.wars ?? '—';
  document.getElementById('stat-alliances').textContent = data.alliances ?? '—';
  document.getElementById('stat-soldiers').textContent = data.soldiers ?? '—';
  document.getElementById('stat-missions').textContent = data.missions ?? '—';

  const lb = document.getElementById('leaderboard-list');
  const nations = await api('/api/nations?limit=10');
  if (nations.length === 0) { lb.innerHTML = '<div style="color:var(--muted)">Chưa có quốc gia nào.</div>'; return; }
  lb.innerHTML = nations.slice(0,10).map((n,i) => `
    <div class="leaderboard-row">
      <div class="rank-num ${i===0?'gold':i===1?'silver':i===2?'bronze':''}">${i+1}</div>
      <div><div style="font-weight:600">${n.flag_emoji} ${n.name}</div><div style="font-size:.75rem;color:var(--muted)">[${n.tag}] · ${(n.population||0).toLocaleString()} dân</div></div>
      <div class="badge badge-blue">GDP: $${((n.gdp||0)/1e9).toFixed(1)}B</div>
    </div>`).join('');

  const wl = document.getElementById('wars-list');
  const wars = await api('/api/wars?status=Đang diễn ra');
  if (!wars.length) { wl.innerHTML = '<div style="color:var(--muted)">Không có chiến tranh nào.</div>'; return; }
  wl.innerHTML = wars.map(w => `
    <div class="war-item">
      <div class="flex"><span style="font-weight:600">⚔️ ${w.attacker_name}</span><span style="color:var(--muted)">vs</span><span style="font-weight:600">${w.defender_name}</span></div>
      <div style="font-size:.75rem;color:var(--muted);margin-top:4px">${w.reason || 'Không có lý do'}</div>
      <div style="font-size:.75rem;margin-top:6px">💀 ${w.attacker_casualties} vs ${w.defender_casualties}</div>
    </div>`).join('');
}

async function loadNations() {
  const nations = await api('/api/nations');
  allNations = nations;
  renderNations(nations);
}

function renderNations(nations) {
  const grid = document.getElementById('nations-grid');
  if (!nations.length) { grid.innerHTML = '<div style="color:var(--muted)">Chưa có quốc gia nào.</div>'; return; }
  grid.innerHTML = nations.map(n => `
    <div class="nation-card" onclick="showNationDetail(${n.id})">
      <div class="accent-bar" style="background:${n.color||'#3b82f6'}"></div>
      <div class="flag">${n.flag_emoji}</div>
      <h4>${n.name}</h4>
      <div class="tag">[${n.tag}] · ${n.ideology||'—'}</div>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
        <span class="badge badge-blue">${(n.population||0).toLocaleString()} dân</span>
        <span class="badge badge-green">${n.stability||0}% ổn định</span>
      </div>
    </div>`).join('');
}

function filterNations() {
  const q = document.getElementById('nation-search').value.toLowerCase();
  renderNations(allNations.filter(n => n.name.toLowerCase().includes(q) || n.tag.toLowerCase().includes(q)));
}

async function showNationDetail(id) {
  const n = await api('/api/nations/'+id);
  document.getElementById('detail-content').innerHTML = `
    <div style="text-align:center;margin-bottom:20px">
      <div style="font-size:3rem">${n.flag_emoji}</div>
      <h2 style="margin-top:8px">${n.name} <span style="color:var(--muted);font-size:.9rem">[${n.tag}]</span></h2>
      <div class="badge badge-blue" style="margin-top:4px">${n.ideology||'—'}</div>
    </div>
    <div class="grid-2" style="gap:12px">
      <div class="stat-row"><span>Dân số</span><span class="stat-val">${(n.population||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>GDP</span><span class="stat-val">$${((n.gdp||0)/1e9).toFixed(2)}B</span></div>
      <div class="stat-row"><span>Ổn định</span><span class="stat-val">${n.stability}%</span></div>
      <div class="stat-row"><span>Thể chế</span><span class="stat-val">${n.gov_system||'—'}</span></div>
      <div class="stat-row"><span>Quân lực</span><span class="stat-val">${(n.total_military||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>Sức mạnh QĐ</span><span class="stat-val">${n.military_rank||'—'}</span></div>
    </div>
    <p style="margin-top:16px;color:var(--muted);font-size:.875rem">${n.description||'Chưa có mô tả.'}</p>`;
  document.getElementById('detail-modal').classList.add('open');
}

async function loadMap() {
  const nations = await api('/api/nations');
  const territories = await api('/api/territories');
  const svg = document.getElementById('map-svg');
  // Clear previous nation elements
  svg.querySelectorAll('.map-nation,.map-label').forEach(e => e.remove());
  svg.querySelector('text')?.remove();

  const colors = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#06b6d4','#84cc16','#f97316'];
  const positions = territories.length ? territories : nations.map((n,i) => ({
    nation_name: n.name, nation_tag: n.tag,
    map_x: 80 + (i % 7) * 100, map_y: 80 + Math.floor(i/7) * 120,
    size: 60, name: n.capital || 'Thủ Đô', flag_emoji: n.flag_emoji, nation_id: n.id,
    color: n.color || colors[i % colors.length]
  }));

  positions.forEach((t, i) => {
    const g = document.createElementNS('http://www.w3.org/2000/svg','g');
    g.className = 'map-nation';
    const r = Math.sqrt((t.size||60)) * 3;
    const circle = document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('cx', t.map_x); circle.setAttribute('cy', t.map_y);
    circle.setAttribute('r', r); circle.setAttribute('fill', t.color || colors[i%colors.length]);
    circle.setAttribute('opacity','0.8');
    const text = document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x', t.map_x); text.setAttribute('y', t.map_y+5);
    text.setAttribute('text-anchor','middle'); text.setAttribute('fill','#fff');
    text.setAttribute('font-size','12'); text.textContent = t.flag_emoji || '🏳️';
    const label = document.createElementNS('http://www.w3.org/2000/svg','text');
    label.className = 'map-label';
    label.setAttribute('x', t.map_x); label.setAttribute('y', t.map_y + r + 14);
    label.setAttribute('text-anchor','middle'); label.setAttribute('fill','rgba(255,255,255,0.8)');
    label.setAttribute('font-size','10'); label.textContent = t.nation_tag || t.name;
    g.appendChild(circle); g.appendChild(text); g.appendChild(label);
    g.addEventListener('mousemove', (e) => {
      const tt = document.getElementById('map-tooltip');
      tt.style.display = 'block';
      tt.style.left = (e.offsetX+12)+'px'; tt.style.top = (e.offsetY+12)+'px';
      tt.innerHTML = `<strong>${t.nation_name||t.name}</strong><br><span style="color:var(--muted)">${t.name}</span>`;
    });
    g.addEventListener('mouseleave', () => { document.getElementById('map-tooltip').style.display='none'; });
    svg.appendChild(g);
  });

  const tl = document.getElementById('territories-list');
  if (territories.length) {
    tl.innerHTML = `<div class="grid-3">${territories.map(t=>`
      <div style="padding:10px;border-radius:8px;border:1px solid var(--border)">
        <div style="font-weight:600">${t.name}</div>
        <div style="font-size:.8rem;color:var(--muted)">${t.nation_tag} · ${t.resource}</div>
        <div style="font-size:.75rem;margin-top:4px">${(t.population||0).toLocaleString()} dân</div>
      </div>`).join('')}</div>`;
  } else {
    tl.innerHTML = '<div style="color:var(--muted)">Chưa có lãnh thổ nào được khai báo.</div>';
  }
}

async function loadMilitary() {
  const data = await api('/api/military');
  const grid = document.getElementById('military-grid');
  if (!data.length) { grid.innerHTML = '<div style="color:var(--muted)">Chưa có dữ liệu quân đội.</div>'; return; }
  grid.innerHTML = data.map(m => `
    <div class="card">
      <h3>${m.flag_emoji} ${m.nation_name} <span class="badge badge-${m.rank_color}" style="margin-left:8px">${m.military_rank}</span></h3>
      <div class="stat-row"><span>🗡️ Lục quân</span><span class="stat-val">${(m.army_size||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>⚓ Hải quân</span><span class="stat-val">${(m.navy_size||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>✈️ Không quân</span><span class="stat-val">${(m.airforce_size||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>☢️ Vũ khí hạt nhân</span><span class="stat-val">${m.nuclear_warheads||0}</span></div>
      <div class="stat-row"><span>💰 Ngân sách</span><span class="stat-val">$${((m.defense_budget||0)/1e6).toFixed(1)}M</span></div>
    </div>`).join('');
}

async function loadDiplomacy() {
  const alliances = await api('/api/alliances');
  const al = document.getElementById('alliances-list');
  al.innerHTML = alliances.length ? alliances.map(a=>`
    <div class="alliance-item">
      <div style="font-weight:600">${a.name}</div>
      <div style="font-size:.75rem;color:var(--muted);margin-top:4px">${a.member_count||0} thành viên · ${a.founded_at?.split('T')[0]}</div>
    </div>`).join('') : '<div style="color:var(--muted)">Chưa có liên minh nào.</div>';

  const wars = await api('/api/wars');
  const wl = document.getElementById('diplomacy-list');
  wl.innerHTML = wars.length ? wars.map(w=>`
    <div class="war-item">
      <div class="flex"><span style="font-weight:600">${w.attacker_name}</span><span style="color:var(--red);font-size:.8rem">⚔️</span><span style="font-weight:600">${w.defender_name}</span></div>
      <div class="flex" style="margin-top:6px">
        <span class="badge badge-${w.status==='Đang diễn ra'?'red':'green'}">${w.status}</span>
        <span style="font-size:.75rem;color:var(--muted)">${w.started_at?.split('T')[0]}</span>
      </div>
    </div>`).join('') : '<div style="color:var(--muted)">Không có chiến tranh nào.</div>';
}

async function loadEconomy() {
  const data = await api('/api/economy');
  const grid = document.getElementById('economy-grid');
  if (!data.length) { grid.innerHTML = '<div style="color:var(--muted)">Chưa có dữ liệu kinh tế.</div>'; return; }
  grid.innerHTML = data.map(e => `
    <div class="card">
      <h3>${e.flag_emoji} ${e.nation_name}</h3>
      <div class="stat-row"><span>💰 Ngân sách</span><span class="stat-val">$${((e.balance||0)/1e6).toFixed(2)}M</span></div>
      <div class="stat-row"><span>📈 Thu nhập/giờ</span><span class="stat-val" style="color:var(--green)">+${(e.income_per_hour||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>📉 Chi phí/giờ</span><span class="stat-val" style="color:var(--red)">-${(e.expenses_per_hour||0).toLocaleString()}</span></div>
      <div class="stat-row"><span>💹 Lạm phát</span><span class="stat-val">${e.inflation||0}%</span></div>
      <div class="stat-row"><span>👷 Thất nghiệp</span><span class="stat-val">${e.unemployment||0}%</span></div>
    </div>`).join('');
}

async function loadRobloxSessions() {
  const data = await api('/api/roblox/sessions');
  const el = document.getElementById('roblox-sessions');
  el.innerHTML = data.length ? data.map(s=>`
    <div style="padding:10px;border-radius:8px;border:1px solid var(--border);margin-bottom:8px">
      <div style="font-weight:600">${s.username}</div>
      <div style="font-size:.75rem;color:var(--muted)">${s.updated_at?.split('T')[0]}</div>
    </div>`).join('') : '<div style="color:var(--muted)">Không có phiên Roblox nào.</div>';
}

async function lookupPlayer() {
  const id = document.getElementById('lookup-discord-id').value.trim();
  if (!id) return;
  const data = await api('/api/roblox/player/'+id);
  const el = document.getElementById('player-lookup-result');
  if (data.error) { el.innerHTML = `<div style="color:var(--red)">${data.error}</div>`; return; }
  el.innerHTML = `
    <div class="card" style="margin-top:8px">
      <div class="stat-row"><span>Người dùng</span><span>${data.username}</span></div>
      <div class="stat-row"><span>Quốc gia</span><span>${data.nation||'—'}</span></div>
      <div class="stat-row"><span>Quân hàm</span><span>${data.rank||'—'}</span></div>
      <div class="stat-row"><span>Số dư</span><span>${(data.balance||0).toLocaleString()} VND</span></div>
    </div>`;
}

function openCreateNation() {
  document.getElementById('create-modal').classList.add('open');
}

function closeModal() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
}

async function submitCreateNation() {
  const body = {
    name: document.getElementById('cn-name').value.trim(),
    tag: document.getElementById('cn-tag').value.trim().toUpperCase(),
    flag_emoji: document.getElementById('cn-flag').value.trim(),
    color: document.getElementById('cn-color').value,
    ideology: document.getElementById('cn-ideology').value,
    description: document.getElementById('cn-desc').value.trim(),
    api_token: document.getElementById('cn-token').value.trim()
  };
  if (!body.name || !body.tag || !body.api_token) { alert('Vui lòng điền đầy đủ thông tin bắt buộc.'); return; }
  const res = await api('/api/nations', {method:'POST', body:JSON.stringify(body)});
  if (res.error) { alert('Lỗi: '+res.error); return; }
  closeModal();
  loadNations();
  notify('🌍 Quốc gia đã được tạo thành công!');
}

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) closeModal();
});

connectWS();
loadDashboard();
</script>
</body>
</html>"""
    (TEMPLATES_DIR / "index.html").write_text(html, encoding="utf-8")
    log.info("Static files generated.")

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    generate_static_files()
    if DISCORD_TOKEN and DISCORD_TOKEN != "YOUR_DISCORD_TOKEN_HERE":
        asyncio.create_task(start_bot())
    else:
        log.warning("DISCORD_TOKEN not set — bot disabled. Set env var DISCORD_TOKEN to enable.")
    yield

app = FastAPI(title="Nation Roleplay Platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Root HTML ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    async with aiofiles.open(TEMPLATES_DIR / "index.html", encoding="utf-8") as f:
        return await f.read()

# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(ws)

# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    conn = get_db()
    try:
        return {
            "nations": conn.execute("SELECT COUNT(*) FROM nations WHERE is_active=1").fetchone()[0],
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "wars": conn.execute("SELECT COUNT(*) FROM wars WHERE status='Đang diễn ra'").fetchone()[0],
            "alliances": conn.execute("SELECT COUNT(*) FROM alliances WHERE is_active=1").fetchone()[0],
            "soldiers": conn.execute("SELECT COUNT(*) FROM soldiers").fetchone()[0],
            "missions": conn.execute("SELECT COUNT(*) FROM missions WHERE status='Đang thực hiện'").fetchone()[0],
        }
    finally:
        conn.close()

# ── Nations ───────────────────────────────────────────────────────────────────
@app.get("/api/nations")
async def get_nations(limit: int = 100):
    rows = db_fetchall("""
        SELECT n.*, u.username as leader_name
        FROM nations n LEFT JOIN users u ON u.id=n.leader_id
        WHERE n.is_active=1 ORDER BY n.gdp DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in rows]

@app.get("/api/nations/{nation_id}")
async def get_nation(nation_id: int):
    n = db_fetchone("SELECT * FROM nations WHERE id=?", (nation_id,))
    if not n:
        raise HTTPException(404, "Không tìm thấy quốc gia")
    gov = db_fetchone("SELECT * FROM governments WHERE nation_id=?", (nation_id,))
    mil = db_fetchone("SELECT * FROM military WHERE nation_id=?", (nation_id,))
    data = dict(n)
    if gov:
        data["gov_system"] = gov["system"]
        data["tax_rate"] = gov["tax_rate"]
    if mil:
        data["total_military"] = (mil["army_size"] or 0) + (mil["navy_size"] or 0) + (mil["airforce_size"] or 0)
        data["military_rank"] = mil["military_rank"]
    return data

@app.post("/api/nations")
async def create_nation(body: NationCreate):
    user = verify_api_token(body.api_token)
    if not user:
        return JSONResponse({"error": "Token không hợp lệ."}, status_code=401)
    existing_nation = get_user_nation(user["id"])
    if existing_nation:
        return JSONResponse({"error": f"Bạn đã thuộc quốc gia {existing_nation['name']}."}, status_code=400)
    tag = body.tag.upper()[:4]
    if db_fetchone("SELECT id FROM nations WHERE tag=?", (tag,)):
        return JSONResponse({"error": f"Ký hiệu {tag} đã tồn tại."}, status_code=400)
    if db_fetchone("SELECT id FROM nations WHERE name=?", (body.name,)):
        return JSONResponse({"error": f"Tên {body.name} đã tồn tại."}, status_code=400)

    nation_id = db_execute(
        "INSERT INTO nations (name, tag, flag_emoji, color, ideology, description, leader_id) VALUES (?,?,?,?,?,?,?)",
        (body.name, tag, body.flag_emoji, body.color, body.ideology, body.description, user["id"])
    )
    db_execute("INSERT INTO governments (nation_id) VALUES (?)", (nation_id,))
    db_execute("INSERT INTO military (nation_id) VALUES (?)", (nation_id,))
    db_execute("INSERT INTO economy (nation_id) VALUES (?)", (nation_id,))
    db_execute("INSERT INTO nation_members (nation_id, user_id, role, rank) VALUES (?,?,?,?)",
               (nation_id, user["id"], "Quốc trưởng", 10))

    asyncio.create_task(hub.broadcast("nation_created", {"name": body.name, "tag": tag}))
    return {"id": nation_id, "name": body.name, "tag": tag}

# ── Military ──────────────────────────────────────────────────────────────────
@app.get("/api/military")
async def get_military():
    rows = db_fetchall("""
        SELECT m.*, n.name as nation_name, n.flag_emoji, n.tag as nation_tag
        FROM military m JOIN nations n ON n.id=m.nation_id
        WHERE n.is_active=1 ORDER BY (m.army_size+m.navy_size+m.airforce_size) DESC
    """)
    result = []
    for r in rows:
        d = dict(r)
        total = (d["army_size"] or 0) + (d["navy_size"] or 0) + (d["airforce_size"] or 0)
        rank = military_rank_from_size(total)
        d["military_rank"] = rank
        d["rank_color"] = "red" if total > 200000 else "yellow" if total > 50000 else "blue"
        result.append(d)
    return result

@app.put("/api/military/{nation_tag}")
async def update_military(nation_tag: str, body: MilitaryUpdate):
    user = verify_api_token(body.api_token)
    if not user:
        raise HTTPException(401, "Token không hợp lệ")
    nation = db_fetchone("SELECT * FROM nations WHERE tag=? AND leader_id=?", (nation_tag.upper(), user["id"]))
    if not nation:
        raise HTTPException(403, "Không có quyền hoặc không tìm thấy quốc gia")
    updates = {}
    if body.army_size is not None: updates["army_size"] = body.army_size
    if body.navy_size is not None: updates["navy_size"] = body.navy_size
    if body.airforce_size is not None: updates["airforce_size"] = body.airforce_size
    if body.defense_budget is not None: updates["defense_budget"] = body.defense_budget
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db_execute(f"UPDATE military SET {set_clause}, updated_at=datetime('now') WHERE nation_id=?",
                   tuple(updates.values()) + (nation["id"],))
        # recalc rank
        mil = db_fetchone("SELECT * FROM military WHERE nation_id=?", (nation["id"],))
        total = (mil["army_size"] or 0) + (mil["navy_size"] or 0) + (mil["airforce_size"] or 0)
        rank = military_rank_from_size(total)
        db_execute("UPDATE military SET military_rank=? WHERE nation_id=?", (rank, nation["id"]))
    return {"ok": True}

# ── Wars ──────────────────────────────────────────────────────────────────────
@app.get("/api/wars")
async def get_wars(status: str = None):
    sql = """
        SELECT w.*, a.name as attacker_name, a.flag_emoji as attacker_flag,
               d.name as defender_name, d.flag_emoji as defender_flag
        FROM wars w
        JOIN nations a ON a.id=w.attacker_id
        JOIN nations d ON d.id=w.defender_id
    """
    params = ()
    if status:
        sql += " WHERE w.status=?"
        params = (status,)
    sql += " ORDER BY w.started_at DESC LIMIT 50"
    return [dict(r) for r in db_fetchall(sql, params)]

@app.post("/api/wars")
async def declare_war(body: WarDeclare):
    user = verify_api_token(body.api_token)
    if not user:
        raise HTTPException(401, "Token không hợp lệ")
    attacker = db_fetchone("SELECT * FROM nations WHERE tag=? AND leader_id=?", (body.attacker_tag.upper(), user["id"]))
    if not attacker:
        raise HTTPException(403, "Không có quyền hoặc không tìm thấy quốc gia")
    defender = db_fetchone("SELECT * FROM nations WHERE tag=? AND is_active=1", (body.defender_tag.upper(),))
    if not defender:
        raise HTTPException(404, "Không tìm thấy quốc gia bị tấn công")
    war_id = db_execute("INSERT INTO wars (attacker_id, defender_id, reason) VALUES (?,?,?)",
                        (attacker["id"], defender["id"], body.reason))
    asyncio.create_task(hub.broadcast("war_declared", {
        "attacker": attacker["name"], "defender": defender["name"], "reason": body.reason
    }))
    return {"war_id": war_id}

# ── Alliances ─────────────────────────────────────────────────────────────────
@app.get("/api/alliances")
async def get_alliances():
    rows = db_fetchall("""
        SELECT a.*, COUNT(am.id) as member_count
        FROM alliances a LEFT JOIN alliance_members am ON am.alliance_id=a.id
        WHERE a.is_active=1 GROUP BY a.id ORDER BY member_count DESC
    """)
    return [dict(r) for r in rows]

# ── Economy ───────────────────────────────────────────────────────────────────
@app.get("/api/economy")
async def get_economy():
    rows = db_fetchall("""
        SELECT e.*, n.name as nation_name, n.flag_emoji, n.tag
        FROM economy e JOIN nations n ON n.id=e.nation_id
        WHERE n.is_active=1 ORDER BY e.balance DESC
    """)
    return [dict(r) for r in rows]

# ── Territories ───────────────────────────────────────────────────────────────
@app.get("/api/territories")
async def get_territories():
    rows = db_fetchall("""
        SELECT t.*, n.name as nation_name, n.flag_emoji, n.color, n.tag as nation_tag
        FROM territories t JOIN nations n ON n.id=t.nation_id
        WHERE n.is_active=1 ORDER BY t.is_capital DESC
    """)
    return [dict(r) for r in rows]

# ── Roblox API ────────────────────────────────────────────────────────────────
@app.post("/api/roblox/sync")
async def roblox_sync(body: RobloxSync):
    if body.roblox_api_key != ROBLOX_API_KEY:
        raise HTTPException(401, "Roblox API key không hợp lệ")
    user = db_fetchone("SELECT * FROM users WHERE discord_id=?", (body.discord_id,))
    if not user:
        raise HTTPException(404, "Người dùng không tồn tại. Hãy dùng .dangky trong Discord trước.")

    data = body.data
    # Update kills/deaths if soldier exists
    if "kills" in data or "deaths" in data:
        soldier = db_fetchone("SELECT * FROM soldiers WHERE user_id=?", (user["id"],))
        if soldier:
            kills = data.get("kills", 0)
            deaths = data.get("deaths", 0)
            db_execute("UPDATE soldiers SET kills=kills+?, deaths=deaths+? WHERE id=?",
                       (kills, deaths, soldier["id"]))

    # Store session data
    db_execute("""
        INSERT INTO roblox_sessions (user_id, roblox_place_id, roblox_job_id, data, updated_at)
        VALUES (?,?,?,?,datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET data=?, roblox_place_id=?, roblox_job_id=?, updated_at=datetime('now')
    """, (user["id"], data.get("place_id",""), data.get("job_id",""), json.dumps(data),
          json.dumps(data), data.get("place_id",""), data.get("job_id","")))

    # Reward currency for kills
    if data.get("kills", 0) > 0:
        reward = data["kills"] * 50
        db_execute("UPDATE wallets SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
                   (reward, reward, user["id"]))

    asyncio.create_task(hub.broadcast("roblox_sync", {"discord_id": body.discord_id, "data": data}))
    nation = get_user_nation(user["id"])
    soldier = db_fetchone("SELECT * FROM soldiers WHERE user_id=?", (user["id"],))
    wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    return {
        "ok": True,
        "username": user["username"],
        "nation": nation["name"] if nation else None,
        "nation_tag": nation["tag"] if nation else None,
        "rank": soldier["rank"] if soldier else None,
        "balance": wallet["balance"] if wallet else 0,
    }

@app.get("/api/roblox/player/{discord_id}")
async def get_roblox_player(discord_id: str):
    user = db_fetchone("SELECT * FROM users WHERE discord_id=?", (discord_id,))
    if not user:
        return JSONResponse({"error": "Không tìm thấy người dùng. Hãy dùng .dangky trong Discord."}, status_code=404)
    nation = get_user_nation(user["id"])
    soldier = db_fetchone("SELECT * FROM soldiers WHERE user_id=?", (user["id"],))
    wallet = db_fetchone("SELECT * FROM wallets WHERE user_id=?", (user["id"],))
    return {
        "discord_id": discord_id,
        "username": user["username"],
        "nation": nation["name"] if nation else None,
        "nation_tag": nation["tag"] if nation else None,
        "rank": soldier["rank"] if soldier else None,
        "branch": soldier["branch"] if soldier else None,
        "kills": soldier["kills"] if soldier else 0,
        "deaths": soldier["deaths"] if soldier else 0,
        "missions_completed": soldier["missions_completed"] if soldier else 0,
        "balance": wallet["balance"] if wallet else 0,
        "api_token": user["api_token"],
    }

@app.get("/api/roblox/sessions")
async def get_roblox_sessions():
    rows = db_fetchall("""
        SELECT rs.*, u.username FROM roblox_sessions rs
        JOIN users u ON u.id=rs.user_id
        ORDER BY rs.updated_at DESC LIMIT 20
    """)
    return [dict(r) for r in rows]

@app.get("/api/roblox/world")
async def get_roblox_world():
    """Full world state for Roblox game to poll"""
    nations = db_fetchall("SELECT * FROM nations WHERE is_active=1")
    territories = db_fetchall("""
        SELECT t.*, n.name as nation_name, n.tag, n.flag_emoji, n.color
        FROM territories t JOIN nations n ON n.id=t.nation_id WHERE n.is_active=1
    """)
    wars = db_fetchall("""
        SELECT w.*, a.tag as attacker_tag, d.tag as defender_tag
        FROM wars w JOIN nations a ON a.id=w.attacker_id JOIN nations d ON d.id=w.defender_id
        WHERE w.status='Đang diễn ra'
    """)
    return {
        "nations": [dict(n) for n in nations],
        "territories": [dict(t) for t in territories],
        "active_wars": [dict(w) for w in wars],
        "timestamp": time.time()
    }

# ── Income tick (background) ──────────────────────────────────────────────────
async def income_tick():
    """Every 5 minutes, credit national income to economy balances."""
    while True:
        await asyncio.sleep(300)
        try:
            economies = db_fetchall("SELECT * FROM economy")
            for eco in economies:
                net = (eco["income_per_hour"] - eco["expenses_per_hour"]) / 12
                db_execute("UPDATE economy SET balance=balance+?, last_collected=datetime('now') WHERE id=?",
                           (net, eco["id"]))
        except Exception as e:
            log.error(f"Income tick error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# BOT STARTUP HELPER
# ─────────────────────────────────────────────────────────────────────────────
async def start_bot():
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        log.error(f"Discord bot error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    log.info(f"Starting Nation Roleplay Platform on port {WEB_PORT}")
    log.info(f"Roblox API Key: {ROBLOX_API_KEY}")
    log.info("Set DISCORD_TOKEN env var to enable the Discord bot.")
    uvicorn.run("main:app", host="0.0.0.0", port=WEB_PORT, reload=False, log_level="warning")
