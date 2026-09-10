from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup

# Dashboard hardening: persist OAuth sessions and resolve server access from
# the actual bot guild list plus the user's Discord OAuth guild membership.
_original_init = RedSentinel.__init__
_original_oauth_callback = RedSentinel.oauth_callback


def _persistent_init(self, bot):
    _original_init(self, bot)
    self.config.register_global(web_sessions={})


async def _load_session(self, token):
    if not token:
        return None
    import time
    session = self.sessions.get(token)
    if session and session.get("expires_at", 0) > time.time():
        return session
    stored = await self.config.web_sessions()
    if isinstance(stored, dict):
        session = stored.get(token)
        if session and session.get("expires_at", 0) > time.time():
            self.sessions[token] = session
            return session
    return None


async def _member_can_manage(self, guild, user_id):
    if not user_id:
        return False
    member = guild.get_member(int(user_id))
    if member is None:
        try:
            member = await guild.fetch_member(int(user_id))
        except Exception:
            return False
    perms = member.guild_permissions
    return bool(perms.administrator or perms.manage_guild)


async def _auth_fixed(self, request, guild_id=None):
    import hmac
    from aiohttp import web

    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    static_token = await self.config.api_token()

    if static_token and token:
        try:
            if hmac.compare_digest(token, static_token):
                return {"user_id": 0, "guild_ids": [int(guild_id)] if guild_id is not None else []}
        except Exception:
            pass

    session = await _load_session(self, token)
    if not session:
        raise web.HTTPUnauthorized(text="Authentication required.")

    normalized = dict(session)
    normalized["user_id"] = int(normalized.get("user_id", 0))
    try:
        normalized["guild_ids"] = [int(x) for x in normalized.get("guild_ids", [])]
    except (TypeError, ValueError):
        normalized["guild_ids"] = []
    self.sessions[token] = normalized

    if guild_id is not None:
        gid = int(guild_id)
        guild = self.bot.get_guild(gid)
        if guild is None:
            raise web.HTTPNotFound(text="Guild not found.")

        # The OAuth /users/@me/guilds response is authoritative for the user's
        # Discord server membership at login. Use it first. This also avoids
        # failures when the bot cannot fetch a member because of Discord's
        # privileged member intent/cache limitations.
        if gid not in normalized["guild_ids"]:
            if not await _member_can_manage(self, guild, normalized["user_id"]):
                raise web.HTTPForbidden(text="Administrator or Manage Server permission required.")

    return normalized


async def _persist_sessions(self):
    import time
    stored = await self.config.web_sessions()
    if not isinstance(stored, dict):
        stored = {}
    now = time.time()
    stored = {k: v for k, v in stored.items() if isinstance(v, dict) and v.get("expires_at", 0) > now}
    for session in self.sessions.values():
        try:
            session["guild_ids"] = [int(x) for x in session.get("guild_ids", [])]
        except (TypeError, ValueError):
            session["guild_ids"] = []
    stored.update(self.sessions)
    await self.config.web_sessions.set(stored)


async def _persistent_oauth_callback(self, request):
    # The original callback finishes with HTTP 302, which is raised as an
    # aiohttp HTTPException. Persist the session even when that redirect is raised.
    try:
        return await _original_oauth_callback(self, request)
    except Exception:
        await _persist_sessions(self)
        raise


async def _guild_count(self, guild):
    count = getattr(guild, "member_count", None)
    if count is not None:
        return count
    try:
        fetched = await self.bot.fetch_guild(guild.id, with_counts=True)
        count = getattr(fetched, "approximate_member_count", None)
        if count is not None:
            return count
    except Exception:
        pass
    cached = len(getattr(guild, "members", ()) or ())
    return cached if cached else None


async def _api_guilds(self, request):
    from aiohttp import web

    session = await self._auth(request)
    user_id = int(session.get("user_id", 0))
    oauth_guild_ids = set()
    try:
        oauth_guild_ids = {int(x) for x in session.get("guild_ids", [])}
    except Exception:
        oauth_guild_ids = set()

    result = []
    for guild in self.bot.guilds:
        # Prefer the OAuth guild list because it is returned directly by Discord
        # for the logged-in user. If the session list is unavailable, fall back
        # to checking the live member permissions.
        if user_id and oauth_guild_ids:
            if int(guild.id) not in oauth_guild_ids:
                continue
        elif user_id and not await _member_can_manage(self, guild, user_id):
            continue

        result.append({
            "id": int(guild.id),
            "name": guild.name,
            "icon": str(guild.icon.url) if guild.icon else None,
            "member_count": await _guild_count(self, guild),
        })

    result.sort(key=lambda x: x["name"].lower())
    return web.json_response(result)


async def _api_guild(self, request):
    from aiohttp import web
    gid = int(request.match_info["guild_id"])
    await self._auth(request, gid)
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    return web.json_response({
        "id": int(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
        "member_count": await _guild_count(self, guild),
        "channels": [{"id": int(c.id), "name": c.name, "type": str(c.type)} for c in guild.channels],
        "roles": [{"id": int(r.id), "name": r.name, "position": r.position} for r in guild.roles if not r.is_default()],
    })


async def _api_get_config(self, request):
    from aiohttp import web
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    return web.json_response({"providers": await self.config.providers(), "routes": await self.config.routes()})


async def _api_put_config(self, request):
    from aiohttp import web
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    data = await self._json(request)
    if "providers" in data:
        await self.config.providers.set(data["providers"])
    if "routes" in data:
        await self.config.routes.set(data["routes"])
    return web.json_response({"ok": True})


async def _start_web_fixed(self):
    from aiohttp import web
    app = web.Application(client_max_size=8 * 1024 * 1024)
    app.add_routes([
        web.get("/api/health", self.api_health),
        web.get("/api/guilds", self.api_guilds),
        web.get("/api/guilds/{guild_id}/events", self.api_events),
        web.get("/api/guilds/{guild_id}/config", self.api_get_config),
        web.put("/api/guilds/{guild_id}/config", self.api_put_config),
        web.get("/api/guilds/{guild_id}", self.api_guild),
        web.post("/api/guilds/{guild_id}/announce", self.api_announce),
        web.post("/api/guilds/{guild_id}/moderation/ban", self.api_ban),
        web.post("/api/guilds/{guild_id}/moderation/kick", self.api_kick),
        web.post("/api/guilds/{guild_id}/moderation/timeout", self.api_timeout),
        web.post("/api/guilds/{guild_id}/moderation/delete", self.api_delete),
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
    __import__("logging").getLogger("red_sentinel").info("Red Sentinel API listening on %s:%s", host, port)


RedSentinel.__init__ = _persistent_init
RedSentinel._auth = _auth_fixed
RedSentinel.oauth_callback = _persistent_oauth_callback
RedSentinel.api_guilds = _api_guilds
RedSentinel.api_guild = _api_guild
RedSentinel.api_get_config = _api_get_config
RedSentinel.api_put_config = _api_put_config
RedSentinel._start_web = _start_web_fixed


async def setup(bot):
    await bot.add_cog(RedSentinel(bot))
    await bot.add_cog(SentinelOAuthSetup(bot))
