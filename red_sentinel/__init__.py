from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup

# Dashboard hardening: persist OAuth sessions, normalize Discord snowflake IDs,
# authorize users by their actual Discord permissions, and keep all dashboard routes active.
_original_init = RedSentinel.__init__
_original_oauth_callback = RedSentinel.oauth_callback
_original_api_get_config = RedSentinel.api_get_config
_original_api_put_config = RedSentinel.api_put_config


def _persistent_init(self, bot):
    _original_init(self, bot)
    self.config.register_global(web_sessions={})


async def _auth_fixed(self, request, guild_id=None):
    import hmac
    import time
    from aiohttp import web

    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    static_token = await self.config.api_token()

    if token and token not in self.sessions:
        stored = await self.config.web_sessions()
        if isinstance(stored, dict):
            session = stored.get(token)
            if session and session.get("expires_at", 0) > time.time():
                self.sessions[token] = session

    session = self.sessions.get(token)
    if session and session.get("expires_at", 0) > time.time():
        normalized = dict(session)
        try:
            normalized["guild_ids"] = [int(x) for x in session.get("guild_ids", [])]
        except (TypeError, ValueError):
            normalized["guild_ids"] = []
        self.sessions[token] = normalized

        if guild_id is not None:
            gid = int(guild_id)
            if gid not in normalized["guild_ids"]:
                # OAuth guild lists can be stale or incomplete. The bot itself is
                # the source of truth for the server, and Discord permissions are
                # checked before granting dashboard access.
                guild = self.bot.get_guild(gid)
                if guild is None:
                    raise web.HTTPNotFound(text="Guild not found.")
                member = guild.get_member(int(normalized.get("user_id", 0)))
                if member is None:
                    try:
                        member = await guild.fetch_member(int(normalized.get("user_id", 0)))
                    except Exception:
                        member = None
                if not member or not (
                    member.guild_permissions.administrator
                    or member.guild_permissions.manage_guild
                ):
                    raise web.HTTPForbidden(text="Administrator or Manage Server permission required.")

        return normalized

    if static_token and token and hmac.compare_digest(token, static_token):
        return {"user_id": 0, "guild_ids": [int(guild_id)] if guild_id is not None else []}

    raise web.HTTPUnauthorized(text="Authentication required.")


async def _persistent_oauth_callback(self, request):
    response = await _original_oauth_callback(self, request)
    stored = await self.config.web_sessions()
    if not isinstance(stored, dict):
        stored = {}
    now = __import__("time").time()
    stored = {k: v for k, v in stored.items() if v.get("expires_at", 0) > now}
    for session in self.sessions.values():
        try:
            session["guild_ids"] = [int(x) for x in session.get("guild_ids", [])]
        except (TypeError, ValueError):
            session["guild_ids"] = []
    stored.update(self.sessions)
    await self.config.web_sessions.set(stored)
    return response


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
    session = await self._auth(request)
    allowed = set(session.get("guild_ids", []))
    result = []
    for guild in self.bot.guilds:
        if allowed and guild.id not in allowed:
            continue
        result.append({
            "id": guild.id,
            "name": guild.name,
            "icon": str(guild.icon.url) if guild.icon else None,
            "member_count": await _guild_count(self, guild),
        })
    return __import__("aiohttp").web.json_response(result)


async def _api_guild(self, request):
    gid = int(request.match_info["guild_id"])
    await self._auth(request, gid)
    guild = self.bot.get_guild(gid)
    if not guild:
        raise __import__("aiohttp").web.HTTPNotFound(text="Guild not found.")
    return __import__("aiohttp").web.json_response({
        "id": guild.id,
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
        "member_count": await _guild_count(self, guild),
        "channels": [{"id": c.id, "name": c.name, "type": str(c.type)} for c in guild.channels],
        "roles": [{"id": r.id, "name": r.name, "position": r.position} for r in guild.roles if not r.is_default()],
    })


async def _api_get_config(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise __import__("aiohttp").web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    return __import__("aiohttp").web.json_response({
        "providers": await self.config.providers(),
        "routes": await self.config.routes(),
    })


async def _api_put_config(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise __import__("aiohttp").web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    session = await self._auth(request, gid)
    if session.get("user_id", 0):
        member = guild.get_member(int(session["user_id"]))
        if member is None:
            try:
                member = await guild.fetch_member(int(session["user_id"]))
            except Exception:
                member = None
        if not member or not (member.guild_permissions.administrator or member.guild_permissions.manage_guild):
            raise __import__("aiohttp").web.HTTPForbidden(text="Administrator or Manage Server permission required.")
    data = await self._json(request)
    if "providers" in data:
        await self.config.providers.set(data["providers"])
    if "routes" in data:
        await self.config.routes.set(data["routes"])
    return __import__("aiohttp").web.json_response({"ok": True})


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
