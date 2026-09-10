from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup

# Keep dashboard sessions across cog/bot reloads. The main cog historically kept
# sessions only in memory, which forced OAuth again after a reload.
_original_init = RedSentinel.__init__
_original_auth = RedSentinel._auth
_original_oauth_callback = RedSentinel.oauth_callback
_original_api_guilds = RedSentinel.api_guilds
_original_api_guild = RedSentinel.api_guild


def _persistent_init(self, bot):
    _original_init(self, bot)
    self.config.register_global(web_sessions={})


async def _persistent_auth(self, request, guild_id=None):
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token and token not in self.sessions:
        stored = await self.config.web_sessions()
        session = stored.get(token) if isinstance(stored, dict) else None
        if session and session.get("expires_at", 0) > __import__("time").time():
            self.sessions[token] = session

    # Discord OAuth returns guild IDs as strings, while discord.py uses ints.
    # Normalize them before the original authorization check so guild endpoints
    # do not incorrectly return 403.
    session = self.sessions.get(token)
    if session:
        session = dict(session)
        try:
            session["guild_ids"] = [int(x) for x in session.get("guild_ids", [])]
        except (TypeError, ValueError):
            session["guild_ids"] = []
        self.sessions[token] = session

    return await _original_auth(self, request, guild_id)


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
    """Return a reliable member count even when the gateway cache has no count."""
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


async def _api_guilds_with_count(self, request):
    session = await self._auth(request)
    allowed = set(session["guild_ids"])
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


async def _api_guild_with_count(self, request):
    gid = int(request.match_info["guild_id"])
    await self._auth(request, gid)
    guild = self.bot.get_guild(gid)
    if not guild:
        raise __import__("aiohttp").web.HTTPNotFound(text="Guild not found.")
    count = await _guild_count(self, guild)
    return __import__("aiohttp").web.json_response({
        "id": guild.id,
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
        "member_count": count,
        "channels": [{"id": c.id, "name": c.name, "type": str(c.type)} for c in guild.channels],
        "roles": [{"id": r.id, "name": r.name, "position": r.position} for r in guild.roles if not r.is_default()],
    })


RedSentinel.__init__ = _persistent_init
RedSentinel._auth = _persistent_auth
RedSentinel.oauth_callback = _persistent_oauth_callback
RedSentinel.api_guilds = _api_guilds_with_count
RedSentinel.api_guild = _api_guild_with_count


async def setup(bot):
    await bot.add_cog(RedSentinel(bot))
    await bot.add_cog(SentinelOAuthSetup(bot))
