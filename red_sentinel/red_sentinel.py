from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp
from aiohttp import web
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("red_sentinel")

DB_VERSION = 1


class RedSentinel(commands.Cog):
    """
    Red Sentinel: a web-control-plane + event logging + automation cog for Red-DiscordBot.

    The Netlify frontend talks to this cog's API. Secrets stay on the Red host.
    """

    __version__ = "0.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=947281163, force_registration=True)
        self.config.register_global(
            host="0.0.0.0",
            port=8787,
            api_token="",
            public_base_url="",
            netlify_origin="",
            oauth_client_id="",
            oauth_client_secret="",
            oauth_redirect_uri="",
            log_retention_days=30,
            social_poll_seconds=60,
            providers={},
            routes={},
        )

        self.session: Optional[aiohttp.ClientSession] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.db_path: Optional[Path] = None
        self.db_lock = asyncio.Lock()
        self.event_buffer = deque(maxlen=250)
        self.social_task: Optional[asyncio.Task] = None
        self.oauth_states: dict[str, float] = {}
        self.sessions: dict[str, dict[str, Any]] = {}

    async def cog_load(self):
        data_dir = Path(await self.bot.get_cog_data_path(self))
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "sentinel.sqlite3"
        await asyncio.to_thread(self._init_db)
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        await self._start_web()
        self.social_task = asyncio.create_task(self._social_loop(), name="red-sentinel-social")

    async def cog_unload(self):
        if self.social_task:
            self.social_task.cancel()
            try:
                await self.social_task
            except asyncio.CancelledError:
                pass
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        if self.session:
            await self.session.close()

    # -------------------- database --------------------

    def _init_db(self):
        assert self.db_path
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    actor_id INTEGER,
                    actor_name TEXT,
                    channel_id INTEGER,
                    channel_name TEXT,
                    target_id INTEGER,
                    target_name TEXT,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS social_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    author TEXT,
                    title TEXT,
                    url TEXT,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(provider, external_id)
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_guild_time ON events(guild_id, created_at DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_social_provider_time ON social_items(provider, created_at DESC)")
            db.commit()

    async def _log_event(
        self,
        guild: discord.Guild,
        event_type: str,
        *,
        actor: Optional[discord.abc.User] = None,
        channel: Optional[discord.abc.GuildChannel] = None,
        target: Optional[discord.abc.User] = None,
        payload: Optional[dict[str, Any]] = None,
    ):
        row = (
            guild.id,
            event_type,
            getattr(actor, "id", None),
            str(actor) if actor else None,
            getattr(channel, "id", None),
            getattr(channel, "name", None),
            getattr(target, "id", None),
            str(target) if target else None,
            json.dumps(payload or {}, default=str),
            int(time.time()),
        )
        async with self.db_lock:
            await asyncio.to_thread(self._insert_event, row)
        self.event_buffer.appendleft({
            "guild_id": guild.id, "type": event_type,
            "actor": {"id": getattr(actor, "id", None), "name": str(actor) if actor else None},
            "channel": {"id": getattr(channel, "id", None), "name": getattr(channel, "name", None)},
            "target": {"id": getattr(target, "id", None), "name": str(target) if target else None},
            "payload": payload or {}, "created_at": row[-1],
        })

    def _insert_event(self, row):
        assert self.db_path
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO events
                (guild_id,type,actor_id,actor_name,channel_id,channel_name,target_id,target_name,payload,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, row)
            db.commit()

    async def _query_events(self, guild_id: int, limit=100, event_type=None):
        def run():
            assert self.db_path
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                q = "SELECT * FROM events WHERE guild_id=?"
                args = [guild_id]
                if event_type:
                    q += " AND type=?"
                    args.append(event_type)
                q += " ORDER BY created_at DESC LIMIT ?"
                args.append(min(max(limit, 1), 500))
                return [dict(x) for x in db.execute(q, args).fetchall()]
        rows = await asyncio.to_thread(run)
        for r in rows:
            r["payload"] = json.loads(r["payload"])
        return rows

    # -------------------- Discord listeners --------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        await self._log_event(
            message.guild, "message.create",
            actor=message.author, channel=message.channel,
            payload={"message_id": message.id, "content": message.content[:4000]},
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or after.author.bot:
            return
        await self._log_event(
            after.guild, "message.edit", actor=after.author, channel=after.channel,
            payload={"message_id": after.id, "before": before.content[:2000], "after": after.content[:2000]},
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        await self._log_event(
            message.guild, "message.delete", actor=message.author if message.author else None,
            channel=message.channel,
            payload={"message_id": message.id, "content": getattr(message, "content", "")[:2000]},
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._log_event(member.guild, "member.join", target=member,
                              payload={"account_created": member.created_at.isoformat()})

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._log_event(member.guild, "member.leave", target=member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            await self._log_event(after.guild, "member.nickname", target=after,
                                  payload={"before": before.nick, "after": after.nick})

    # -------------------- web server --------------------

    async def _start_web(self):
        app = web.Application(client_max_size=8 * 1024 * 1024)
        app.add_routes([
            web.get("/api/health", self.api_health),
            web.get("/api/guilds", self.api_guilds),
            web.get("/api/guilds/{guild_id}", self.api_guild),
            web.get("/api/guilds/{guild_id}/events", self.api_events),
            web.post("/api/guilds/{guild_id}/announce", self.api_announce),
            web.post("/api/guilds/{guild_id}/moderation/ban", self.api_ban),
            web.post("/api/guilds/{guild_id}/moderation/kick", self.api_kick),
            web.post("/api/guilds/{guild_id}/moderation/timeout", self.api_timeout),
            web.post("/api/guilds/{guild_id}/moderation/delete", self.api_delete),
            web.get("/api/guilds/{guild_id}/config", self.api_get_config),
            web.put("/api/guilds/{guild_id}/config", self.api_put_config),
            web.post("/api/webhooks/social", self.api_social_webhook),
            web.get("/oauth/discord/start", self.oauth_start),
            web.get("/oauth/discord/callback", self.oauth_callback),
            web.get("/api/me", self.api_me),
        ])
        app.middlewares.append(self.cors_middleware)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        host = await self.config.host()
        port = await self.config.port()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        log.info("Red Sentinel API listening on %s:%s", host, port)

    @web.middleware
    async def cors_middleware(self, request, handler):
        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            try:
                response = await handler(request)
            except web.HTTPException as exc:
                response = exc
        origin = request.headers.get("Origin", "")
        allowed = await self.config.netlify_origin()
        if allowed and origin == allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not allowed:
            response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,OPTIONS"
        response.headers["Vary"] = "Origin"
        return response

    async def _auth(self, request, guild_id: Optional[int] = None):
        # OAuth session is preferred. Static API token is intended for private/self-hosted installs.
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        static_token = await self.config.api_token()
        session = self.sessions.get(token)
        if session and session["expires_at"] > time.time():
            if guild_id and guild_id not in session["guild_ids"]:
                raise web.HTTPForbidden(text="You do not have access to this server.")
            return session
        if static_token and hmac.compare_digest(token, static_token):
            return {"user_id": 0, "guild_ids": [guild_id] if guild_id else []}
        raise web.HTTPUnauthorized(text="Authentication required.")

    async def _json(self, request):
        try:
            return await request.json()
        except Exception:
            raise web.HTTPBadRequest(text="Expected JSON.")

    async def api_health(self, request):
        return web.json_response({"ok": True, "version": self.__version__, "time": int(time.time())})

    async def api_me(self, request):
        session = await self._auth(request)
        return web.json_response({"id": session["user_id"], "guild_ids": session["guild_ids"]})

    async def api_guilds(self, request):
        session = await self._auth(request)
        guilds = []
        allowed = set(session["guild_ids"])
        for g in self.bot.guilds:
            if not allowed or g.id in allowed:
                guilds.append({"id": g.id, "name": g.name, "icon": str(g.icon.url) if g.icon else None, "member_count": g.member_count})
        return web.json_response(guilds)

    async def api_guild(self, request):
        gid = int(request.match_info["guild_id"])
        await self._auth(request, gid)
        g = self.bot.get_guild(gid)
        if not g:
            raise web.HTTPNotFound(text="Guild not found.")
        return web.json_response({
            "id": g.id, "name": g.name, "icon": str(g.icon.url) if g.icon else None,
            "member_count": g.member_count,
            "channels": [{"id": c.id, "name": c.name, "type": str(c.type)} for c in g.channels],
            "roles": [{"id": r.id, "name": r.name, "position": r.position} for r in g.roles if not r.is_default()],
        })

    async def api_events(self, request):
        gid = int(request.match_info["guild_id"])
        await self._auth(request, gid)
        limit = int(request.query.get("limit", 100))
        event_type = request.query.get("type")
        return web.json_response(await self._query_events(gid, limit, event_type))

    async def _member_from_payload(self, guild, data):
        user_id = int(data.get("user_id", 0))
        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                raise web.HTTPNotFound(text="Member not found.")
        return member

    async def _require_admin(self, request, guild):
        session = await self._auth(request, guild.id)
        # Static API token is explicitly trusted; OAuth sessions need to be server administrators.
        if session["user_id"] == 0:
            return
        member = guild.get_member(int(session["user_id"]))
        if not member or not member.guild_permissions.administrator:
            raise web.HTTPForbidden(text="Administrator permission required.")

    async def api_announce(self, request):
        gid = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(gid)
        if not guild:
            raise web.HTTPNotFound(text="Guild not found.")
        await self._require_admin(request, guild)
        data = await self._json(request)
        channel = guild.get_channel(int(data["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            raise web.HTTPBadRequest(text="Invalid text channel.")
        content = data.get("content", "")
        embed_data = data.get("embed")
        embed = None
        if embed_data:
            embed_kwargs = {"color": int(embed_data.get("color", 0x7C5CFC))}
            if embed_data.get("title"):
                embed_kwargs["title"] = str(embed_data["title"])[:256]
            if embed_data.get("description"):
                embed_kwargs["description"] = str(embed_data["description"])[:4096]
            if embed_data.get("url"):
                embed_kwargs["url"] = str(embed_data["url"])
            embed = discord.Embed(**embed_kwargs)
            if embed_data.get("footer"):
                embed.set_footer(text=str(embed_data["footer"])[:2048])
            if embed_data.get("image"):
                embed.set_image(url=str(embed_data["image"]))
            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=str(embed_data["thumbnail"]))
        msg = await channel.send(content=content or None, embed=embed)
        await self._log_event(guild, "admin.announce", actor=None, channel=channel,
                              payload={"message_id": msg.id, "content": content, "embed": embed_data})
        return web.json_response({"ok": True, "message_id": msg.id})

    async def api_ban(self, request):
        return await self._moderate(request, "ban")

    async def api_kick(self, request):
        return await self._moderate(request, "kick")

    async def api_timeout(self, request):
        return await self._moderate(request, "timeout")

    async def _moderate(self, request, action):
        gid = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(gid)
        if not guild:
            raise web.HTTPNotFound(text="Guild not found.")
        await self._require_admin(request, guild)
        data = await self._json(request)
        member = await self._member_from_payload(guild, data)
        reason = data.get("reason") or "Red Sentinel web panel"
        try:
            if action == "ban":
                await guild.ban(member, reason=reason, delete_message_seconds=min(int(data.get("delete_seconds", 0)), 604800))
            elif action == "kick":
                await guild.kick(member, reason=reason)
            else:
                seconds = max(1, min(int(data.get("seconds", 3600)), 2419200))
                await member.timeout(discord.utils.utcnow() + timedelta(seconds=seconds), reason=reason)
        except discord.Forbidden:
            raise web.HTTPForbidden(text="Discord denied this action. Check bot role/permissions.")
        await self._log_event(guild, f"moderation.{action}", target=member, payload={"reason": reason})
        return web.json_response({"ok": True, "action": action, "user_id": member.id})

    async def api_delete(self, request):
        gid = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(gid)
        if not guild:
            raise web.HTTPNotFound(text="Guild not found.")
        await self._require_admin(request, guild)
        data = await self._json(request)
        channel = guild.get_channel(int(data["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            raise web.HTTPBadRequest(text="Invalid text channel.")
        message = await channel.fetch_message(int(data["message_id"]))
        await message.delete()
        await self._log_event(guild, "moderation.delete", actor=None, channel=channel,
                              payload={"message_id": message.id})
        return web.json_response({"ok": True})

    async def api_get_config(self, request):
        gid = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(gid)
        if not guild:
            raise web.HTTPNotFound(text="Guild not found.")
        await self._require_admin(request, guild)
        routes = await self.config.routes()
        providers = await self.config.providers()
        return web.json_response({
            "routes": routes.get(str(gid), {}),
            "providers": providers,
            "social_poll_seconds": await self.config.social_poll_seconds(),
        })

    async def api_put_config(self, request):
        gid = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(gid)
        if not guild:
            raise web.HTTPNotFound(text="Guild not found.")
        await self._require_admin(request, guild)
        data = await self._json(request)
        routes = await self.config.routes()
        routes[str(gid)] = data.get("routes", routes.get(str(gid), {}))
        await self.config.routes.set(routes)
        if "social_poll_seconds" in data:
            await self.config.social_poll_seconds.set(max(15, int(data["social_poll_seconds"])))
        return web.json_response({"ok": True})

    # -------------------- OAuth --------------------

    async def oauth_start(self, request):
        client_id = await self.config.oauth_client_id()
        redirect = await self.config.oauth_redirect_uri()
        if not client_id or not redirect:
            raise web.HTTPNotImplemented(text="Discord OAuth is not configured. Use a static API token for a private install.")
        state = secrets.token_urlsafe(32)
        self.oauth_states[state] = time.time() + 600
        params = {
            "client_id": client_id, "redirect_uri": redirect,
            "response_type": "code", "scope": "identify guilds",
        }
        return web.HTTPFound("https://discord.com/oauth2/authorize?" + urlencode(params) + "&state=" + state)

    async def oauth_callback(self, request):
        code, state = request.query.get("code"), request.query.get("state")
        if not code or state not in self.oauth_states or self.oauth_states[state] < time.time():
            raise web.HTTPBadRequest(text="Invalid OAuth state.")
        self.oauth_states.pop(state, None)
        client_id = await self.config.oauth_client_id()
        secret = await self.config.oauth_client_secret()
        redirect = await self.config.oauth_redirect_uri()
        if not self.session:
            raise web.HTTPServiceUnavailable()
        async with self.session.post(
            "https://discord.com/api/oauth2/token",
            data={"client_id": client_id, "client_secret": secret, "grant_type": "authorization_code",
                  "code": code, "redirect_uri": redirect},
        ) as r:
            token_data = await r.json()
        if "access_token" not in token_data:
            raise web.HTTPUnauthorized(text="Discord OAuth token exchange failed.")
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        async with self.session.get("https://discord.com/api/users/@me", headers=headers) as r:
            user = await r.json()
        async with self.session.get("https://discord.com/api/users/@me/guilds", headers=headers) as r:
            guilds = await r.json()
        # Only guilds where the OAuth user has Administrator or Manage Guild.
        accessible = []
        for g in guilds:
            perms = int(g.get("permissions", 0))
            if (perms & 0x8) or (perms & 0x20):
                if self.bot.get_guild(int(g["id"])):
                    accessible.append(int(g["id"]))
        session_token = secrets.token_urlsafe(48)
        self.sessions[session_token] = {
            "user_id": int(user["id"]), "guild_ids": accessible,
            "expires_at": time.time() + 3600,
        }
        frontend = await self.config.netlify_origin()
        if not frontend:
            frontend = "/"
        location = frontend.rstrip("/") + "/#token=" + session_token
        raise web.HTTPFound(location)

    # -------------------- social integrations --------------------

    async def api_social_webhook(self, request):
        secret = await self.config.api_token()
        provided = request.headers.get("X-Sentinel-Webhook", "")
        if not secret or not hmac.compare_digest(provided, secret):
            raise web.HTTPUnauthorized(text="Invalid webhook secret.")
        data = await self._json(request)
        provider = data.get("provider", "custom")
        item = data.get("item", data)
        await self._dispatch_social(provider, item)
        return web.json_response({"ok": True})

    async def _dispatch_social(self, provider: str, item: dict[str, Any]):
        providers = await self.config.providers()
        routes = await self.config.routes()
        for guild_id, route in routes.items():
            target_channel = route.get(provider)
            if not target_channel:
                continue
            guild = self.bot.get_guild(int(guild_id))
            channel = guild.get_channel(int(target_channel)) if guild else None
            if not isinstance(channel, discord.TextChannel):
                continue
            title = item.get("title") or item.get("text") or f"{provider.title()} update"
            url = item.get("url")
            description = item.get("description") or item.get("text") or ""
            embed_kwargs = {"title": title[:256], "description": description[:4096], "color": 0x7C5CFC,
                            "timestamp": discord.utils.utcnow()}
            if url:
                embed_kwargs["url"] = str(url)
            embed = discord.Embed(**embed_kwargs)
            if item.get("author"):
                embed.set_author(name=str(item["author"]))
            if item.get("thumbnail"):
                embed.set_thumbnail(url=item["thumbnail"])
            if item.get("image"):
                embed.set_image(url=item["image"])
            embed.set_footer(text=f"Red Sentinel • {provider}")
            await channel.send(embed=embed)

    async def _social_loop(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                await asyncio.sleep(max(15, int(await self.config.social_poll_seconds())))
                # Provider polling is intentionally opt-in. Configure providers in the web panel
                # or call the webhook endpoint from Make/Zapier/n8n/your own workers.
                # This keeps API secrets on the Red host and avoids hard dependency on paid APIs.
                await self._cleanup_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Social loop error")

    async def _cleanup_sessions(self):
        now = time.time()
        self.sessions = {k: v for k, v in self.sessions.items() if v["expires_at"] > now}

    # -------------------- commands --------------------

    @commands.group(name="sentinel", invoke_without_command=True)
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def sentinel(self, ctx: commands.Context):
        """Red Sentinel administration."""
        await ctx.send(
            f"**Red Sentinel {self.__version__}**\n"
            f"API: `{await self.config.host()}:{await self.config.port()}`\n"
            "Use `[p]sentinel token`, `[p]sentinel status`, or the web dashboard."
        )

    @sentinel.command(name="token")
    @commands.is_owner()
    async def sentinel_token(self, ctx: commands.Context):
        """Generate a private API token for the dashboard."""
        token = secrets.token_urlsafe(40)
        await self.config.api_token.set(token)
        await ctx.author.send(f"Your Red Sentinel API token is:\n`{token}`\n\nDo not share it publicly.")
        await ctx.send("API token generated and sent to your DMs.", delete_after=8)

    @sentinel.command(name="status")
    @commands.admin_or_permissions(manage_guild=True)
    async def sentinel_status(self, ctx: commands.Context):
        """Show dashboard status."""
        await ctx.send(
            f"**Red Sentinel** `{self.__version__}`\n"
            f"Web API: `{await self.config.host()}:{await self.config.port()}`\n"
            f"Public URL: `{await self.config.public_base_url() or 'not configured'}`"
        )


async def _safe_close(cog: RedSentinel):
    if cog.session:
        await cog.session.close()
