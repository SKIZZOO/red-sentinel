from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup
from .enhancements import SentinelEnhancements, patch_red_sentinel
from .server_patch import patch_server_api
from .server_control import patch_server_control
from .action_fixes import patch_action_fixes

_original_init=RedSentinel.__init__;_original_oauth_callback=RedSentinel.oauth_callback

def _persistent_init(self,bot):
    _original_init(self,bot);self.config.register_global(web_sessions={})
async def _load_session(self,token):
    if not token:return None
    import time
    s=self.sessions.get(token)
    if s and s.get("expires_at",0)>time.time():return s
    stored=await self.config.web_sessions()
    if isinstance(stored,dict):
        s=stored.get(token)
        if s and s.get("expires_at",0)>time.time():self.sessions[token]=s;return s
    return None
async def _is_dashboard_owner(self,user_id):
    try:return int(user_id) in {int(x) for x in getattr(self.bot,"owner_ids",set())}
    except Exception:return False
async def _member_can_manage(self,guild,user_id):
    if not user_id:return False
    if await _is_dashboard_owner(self,user_id):return True
    member=guild.get_member(int(user_id))
    if member is None:
        try:member=await guild.fetch_member(int(user_id))
        except Exception:return False
    p=member.guild_permissions;return bool(p.administrator or p.manage_guild)
async def _auth_fixed(self,request,guild_id=None):
    import hmac
    from aiohttp import web
    token=request.headers.get("Authorization","").removeprefix("Bearer ").strip();static_token=await self.config.api_token()
    if static_token and token:
        try:
            if hmac.compare_digest(token,static_token):return {"user_id":0,"guild_ids":[]}
        except Exception:pass
    s=await _load_session(self,token)
    if not s:raise web.HTTPUnauthorized(text="Authentication required.")
    n=dict(s);n["user_id"]=int(n.get("user_id",0))
    try:n["guild_ids"]=[int(x) for x in n.get("guild_ids",[])]
    except Exception:n["guild_ids"]=[]
    self.sessions[token]=n
    if guild_id is not None:
        gid=int(guild_id);guild=self.bot.get_guild(gid)
        if guild is None:raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
        if not await _member_can_manage(self,guild,n["user_id"]):raise web.HTTPForbidden(text="Administrator or Manage Server permission required.")
    return n
async def _require_admin_fixed(self,request,guild):
    from aiohttp import web
    session=await self._auth(request,guild.id)
    uid=int(session.get("user_id",0))
    if uid==0 or await _is_dashboard_owner(self,uid):return
    member=guild.get_member(uid)
    if member is None:
        try:member=await guild.fetch_member(uid)
        except Exception:member=None
    if not member or not (member.guild_permissions.administrator or member.guild_permissions.manage_guild):
        raise web.HTTPForbidden(text="Administrator or Manage Server permission required for dashboard actions.")
async def _persist_sessions(self):
    import time
    stored=await self.config.web_sessions()
    if not isinstance(stored,dict):stored={}
    now=time.time();stored={k:v for k,v in stored.items() if isinstance(v,dict) and v.get("expires_at",0)>now};stored.update(self.sessions);await self.config.web_sessions.set(stored)
async def _persistent_oauth_callback(self,request):
    try:return await _original_oauth_callback(self,request)
    except Exception:await _persist_sessions(self);raise
async def _guild_count(guild):
    c=getattr(guild,"member_count",None)
    if c is not None:return c
    return len(getattr(guild,"members",[]) or []) or None
async def _api_guilds(self,request):
    from aiohttp import web
    s=await self._auth(request);uid=int(s.get("user_id",0));result=[]
    owner=await _is_dashboard_owner(self,uid)
    for g in self.bot.guilds:
        if not owner and not await _member_can_manage(self,g,uid):continue
        result.append({"id":str(g.id),"name":g.name,"icon":str(g.icon.url) if g.icon else None,"member_count":await _guild_count(g)})
    result.sort(key=lambda x:x["name"].lower());return web.json_response(result)
async def _api_guild(self,request):
    from aiohttp import web
    gid=int(request.match_info["guild_id"]);await self._auth(request,gid);g=self.bot.get_guild(gid)
    if g is None:raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    return web.json_response({"id":str(g.id),"name":g.name,"icon":str(g.icon.url) if getattr(g,"icon",None) else None,"member_count":await _guild_count(g),"channels":[{"id":str(c.id),"name":c.name,"type":str(c.type)} for c in getattr(g,"channels",[])],"roles":[{"id":str(r.id),"name":r.name,"position":r.position} for r in getattr(g,"roles",[]) if not r.is_default()]})
async def _start_web_fixed(self):
    from aiohttp import web
    app=web.Application(client_max_size=8*1024*1024)
    app.add_routes([
        web.get("/api/health",self.api_health),web.get("/api/guilds",self.api_guilds),web.get("/api/guilds/{guild_id}/events",self.api_events),web.get("/api/guilds/{guild_id}/members",self.api_members),web.post("/api/guilds/{guild_id}/members/{action}",self.api_member_action),
        web.get("/api/guilds/{guild_id}/channels",self.api_channels),web.post("/api/guilds/{guild_id}/channels/{action}",self.api_channel_action),web.get("/api/guilds/{guild_id}/roles",self.api_roles),web.post("/api/guilds/{guild_id}/roles/{action}",self.api_role_action),web.get("/api/guilds/{guild_id}/audit",self.api_audit),web.post("/api/guilds/{guild_id}/control/{action}",self.api_guild_control),
        web.get("/api/guilds/{guild_id}/config",self.api_get_config),web.put("/api/guilds/{guild_id}/config",self.api_put_config),web.get("/api/guilds/{guild_id}",self.api_guild),web.post("/api/guilds/{guild_id}/announce",self.api_announce),web.post("/api/guilds/{guild_id}/moderation/ban",self.api_ban),web.post("/api/guilds/{guild_id}/moderation/kick",self.api_kick),web.post("/api/guilds/{guild_id}/moderation/timeout",self.api_timeout),web.post("/api/guilds/{guild_id}/moderation/delete",self.api_delete),web.post("/api/webhooks/social",self.api_social_webhook),web.get("/oauth/discord/start",self.oauth_start),web.get("/oauth/discord/callback",self.oauth_callback),web.get("/api/me",self.api_me)
    ])
    app.middlewares.append(self.cors_middleware);self.runner=web.AppRunner(app);await self.runner.setup();host=await self.config.host();port=await self.config.port();self.site=web.TCPSite(self.runner,host,port);await self.site.start();__import__("logging").getLogger("red_sentinel").info("Red Sentinel API listening on %s:%s",host,port)
RedSentinel.__init__=_persistent_init;RedSentinel._auth=_auth_fixed;RedSentinel._require_admin=_require_admin_fixed;RedSentinel.oauth_callback=_persistent_oauth_callback;RedSentinel.api_guilds=_api_guilds;RedSentinel.api_guild=_api_guild;RedSentinel._start_web=_start_web_fixed;patch_red_sentinel(RedSentinel);patch_server_api(RedSentinel);patch_server_control(RedSentinel);patch_action_fixes(RedSentinel)
async def setup(bot):
    await bot.add_cog(RedSentinel(bot));await bot.add_cog(SentinelOAuthSetup(bot));await bot.add_cog(SentinelEnhancements(bot))
