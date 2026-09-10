from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup

# Keep dashboard sessions across cog/bot reloads. The main cog historically kept
# sessions only in memory, which forced OAuth again after a reload.
_original_init = RedSentinel.__init__
_original_auth = RedSentinel._auth
_original_oauth_callback = RedSentinel.oauth_callback


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
    return await _original_auth(self, request, guild_id)


async def _persistent_oauth_callback(self, request):
    response = await _original_oauth_callback(self, request)
    stored = await self.config.web_sessions()
    if not isinstance(stored, dict):
        stored = {}
    now = __import__("time").time()
    stored = {k: v for k, v in stored.items() if v.get("expires_at", 0) > now}
    stored.update(self.sessions)
    await self.config.web_sessions.set(stored)
    return response


RedSentinel.__init__ = _persistent_init
RedSentinel._auth = _persistent_auth
RedSentinel.oauth_callback = _persistent_oauth_callback


async def setup(bot):
    await bot.add_cog(RedSentinel(bot))
    await bot.add_cog(SentinelOAuthSetup(bot))
