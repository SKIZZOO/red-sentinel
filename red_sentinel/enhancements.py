from __future__ import annotations
import asyncio, hmac, time
from datetime import timedelta
from typing import Any
import discord
from aiohttp import web
from redbot.core import commands

def _provider_item(data: dict[str, Any]):
    provider=str(data.get("provider") or "custom").lower().strip(); external_id=str(data.get("external_id") or data.get("id") or f"{provider}:{int(time.time()*1000)}")
    item=data.get("item") if isinstance(data.get("item"),dict) else data
    title=item.get("title") or item.get("name") or item.get("status"); author=item.get("author") or item.get("username") or item.get("channel") or item.get("broadcaster_user_name"); url=item.get("url") or item.get("link"); description=item.get("description") or item.get("text") or item.get("content")
    normalized={"provider":provider,"external_id":external_id,"title":str(title)[:256] if title is not None else None,"author":str(author)[:256] if author is not None else None,"url":str(url) if url else None,"description":str(description)[:4096] if description is not None else None,"thumbnail":item.get("thumbnail") or item.get("thumbnail_url") or item.get("image"),"payload":data}
    return provider,external_id,normalized["author"],normalized["title"],normalized["url"],normalized

async def _resolve_guild(self,gid:int):
    guild=self.bot.get_guild(int(gid))
    if guild is not None:return guild
    try:return await self.bot.fetch_guild(int(gid),with_counts=True)
    except Exception as exc:raise web.HTTPNotFound(text=f"Guild not found: {gid} ({exc})")

async def _ensure_guild_config(sentinel):
    sentinel.config.register_guild(providers={},routes={},social_webhook_secret="")
    global_providers=await sentinel.config.providers(); global_routes=await sentinel.config.routes()
    for guild in sentinel.bot.guilds:
        cfg=sentinel.config.guild(guild); current_routes=await cfg.routes(); current_providers=await cfg.providers()
        if not current_providers and global_providers:await cfg.providers.set(global_providers)
        if not current_routes and global_routes:
            migrated={}
            for provider,value in (global_routes or {}).items():
                entries=value if isinstance(value,list) else [value]
                for entry in entries:
                    if isinstance(entry,dict):
                        if int(entry.get("guild_id",guild.id))!=guild.id:continue
                        channel_id=entry.get("channel_id")
                    else:channel_id=entry
                    if channel_id:migrated[str(provider).lower()]=str(channel_id);break
            if migrated:await cfg.routes.set(migrated)

async def api_get_config(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._auth(request,gid);self.config.register_guild(providers={},routes={},social_webhook_secret="");cfg=self.config.guild(guild)
    return web.json_response({"providers":await cfg.providers(),"routes":await cfg.routes()})
async def api_put_config(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._auth(request,gid);data=await self._json(request);self.config.register_guild(providers={},routes={},social_webhook_secret="");cfg=self.config.guild(guild)
    if "providers" in data:await cfg.providers.set(data["providers"] if isinstance(data["providers"],dict) else {})
    if "routes" in data:await cfg.routes.set({str(k).lower():str(v) for k,v in (data.get("routes") or {}).items() if v})
    if "social_webhook_secret" in data:await cfg.social_webhook_secret.set(str(data["social_webhook_secret"] or ""))
    return web.json_response({"ok":True,"providers":await cfg.providers(),"routes":await cfg.routes()})

async def api_social_webhook(self,request):
    data=await self._json(request);guild_id=data.get("guild_id");token=request.headers.get("X-Sentinel-Webhook","");static_token=await self.config.api_token();static_ok=bool(static_token and token and hmac.compare_digest(token,static_token))
    if not static_ok:
        if not guild_id:raise web.HTTPBadRequest(text="guild_id is required for authenticated dashboard social events.")
        await self._auth(request,int(guild_id))
    provider,external_id,author,title,url,normalized=_provider_item(data);await asyncio.to_thread(self._insert_social_item,{"provider":provider,"external_id":external_id,"author":author,"title":title,"url":url,"payload":normalized,"created_at":int(time.time())})
    targets=[];self.config.register_guild(providers={},routes={},social_webhook_secret="")
    for guild in self.bot.guilds:
        if guild_id and int(guild.id)!=int(guild_id):continue
        routes=await self.config.guild(guild).routes();channel_id=routes.get(provider) or routes.get("custom")
        if channel_id:
            channel=guild.get_channel(int(channel_id))
            if isinstance(channel,discord.TextChannel):targets.append((guild,channel))
    embed=discord.Embed(title=title or f"{provider.upper()} update",description=normalized.get("description") or author or "New social signal",timestamp=discord.utils.utcnow())
    if url:embed.url=url
    if normalized.get("thumbnail"):
        try:embed.set_thumbnail(url=str(normalized["thumbnail"]))
        except Exception:pass
    embed.set_footer(text=f"Red Sentinel • {provider.upper()}");delivered=0
    for guild,channel in targets:
        try:await channel.send(embed=embed);await self._log_event(guild,f"social.{provider}",channel=channel,payload={"external_id":external_id,"title":title,"author":author,"url":url});delivered+=1
        except discord.HTTPException:continue
    return web.json_response({"ok":True,"provider":provider,"delivered":delivered})

async def _get_members(guild,limit=200):
    members=list(getattr(guild,"members",[]) or [])
    if not members:
        try:members=[m async for m in guild.fetch_members(limit=1000)]
        except Exception:members=[]
    members.sort(key=lambda m:(m.bot,(m.display_name or m.name).lower()));return members[:max(1,min(int(limit),500))]
async def api_members(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._auth(request,gid);query=str(request.query.get("q","")).strip().lower();limit=max(1,min(int(request.query.get("limit",200)),500));members=await _get_members(guild,500)
    if query:members=[m for m in members if query in str(m.id) or query in m.name.lower() or query in m.display_name.lower()]
    result=[{"id":int(m.id),"name":m.name,"display_name":m.display_name,"avatar":str(m.display_avatar.url) if m.display_avatar else None,"bot":bool(m.bot),"joined_at":m.joined_at.isoformat() if m.joined_at else None,"roles":[{"id":int(r.id),"name":r.name,"position":r.position} for r in m.roles if not r.is_default()],"role_ids":[int(r.id) for r in m.roles if not r.is_default()],"timeout_until":m.timed_out_until.isoformat() if m.timed_out_until else None} for m in members[:limit]]
    return web.json_response({"members":result,"total":guild.member_count or len(getattr(guild,"members",[]) or []),"cached":len(getattr(guild,"members",[]) or [])})
async def api_member_action(self,request):
    gid=int(request.match_info["guild_id"]);action=request.match_info["action"];guild=await _resolve_guild(self,gid);await self._require_admin(request,guild);data=await self._json(request);member_id=int(data.get("user_id",0))
    if not member_id:raise web.HTTPBadRequest(text="user_id is required.")
    member=guild.get_member(member_id)
    if not member:
        try:member=await guild.fetch_member(member_id)
        except discord.NotFound:raise web.HTTPNotFound(text="Member not found.")
    reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512];me=guild.me
    try:
        if action=="nickname":await member.edit(nick=(str(data.get("nickname")).strip()[:32] or None) if data.get("nickname") is not None else None,reason=reason)
        elif action in ("role_add","role_remove"):
            role=guild.get_role(int(data.get("role_id",0)))
            if role is None or role.is_default():raise web.HTTPBadRequest(text="Role not found.")
            if me and role>=me.top_role:raise web.HTTPForbidden(text="Bot cannot manage this role.")
            await (member.add_roles(role,reason=reason) if action=="role_add" else member.remove_roles(role,reason=reason))
        elif action=="timeout_clear":await member.timeout(None,reason=reason)
        elif action=="timeout":await member.timeout(discord.utils.utcnow()+timedelta(minutes=max(1,min(int(data.get("minutes",60)),40320))),reason=reason)
        elif action=="kick":await guild.kick(member,reason=reason)
        elif action=="ban":await guild.ban(member,reason=reason)
        else:raise web.HTTPBadRequest(text="Unknown member action.")
    except web.HTTPException:raise
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied the action: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected the action: {exc}")
    await self._log_event(guild,f"admin.member.{action}",target=member,payload={"reason":reason,**{k:v for k,v in data.items() if k in ("role_id","nickname","minutes")}});return web.json_response({"ok":True,"action":action,"user_id":member_id})

# Full server control APIs
async def api_channels(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._auth(request,gid)
    return web.json_response({"channels":[{"id":int(c.id),"name":c.name,"type":str(c.type),"position":getattr(c,"position",0),"category_id":getattr(c.category,"id",None),"topic":getattr(c,"topic",None),"nsfw":getattr(c,"nsfw",False)} for c in guild.channels]})
async def api_channel_action(self,request):
    gid=int(request.match_info["guild_id"]);action=request.match_info["action"];guild=await _resolve_guild(self,gid);await self._require_admin(request,guild);data=await self._json(request);reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action=="create":
            name=str(data.get("name") or "new-channel").strip()[:100];kind=str(data.get("type") or "text").lower();category=guild.get_channel(int(data["category_id"])) if data.get("category_id") else None
            if kind=="category":ch=await guild.create_category(name,reason=reason)
            elif kind=="voice":ch=await guild.create_voice_channel(name,category=category,reason=reason)
            else:ch=await guild.create_text_channel(name,category=category,topic=str(data.get("topic") or "")[:1024] or None,reason=reason)
        else:
            ch=guild.get_channel(int(data.get("channel_id",0)))
            if ch is None:raise web.HTTPNotFound(text="Channel not found.")
            if action=="rename":await ch.edit(name=str(data.get("name") or ch.name)[:100],reason=reason)
            elif action=="delete":await ch.delete(reason=reason)
            else:raise web.HTTPBadRequest(text="Unknown channel action.")
    except web.HTTPException:raise
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied the action: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected the action: {exc}")
    await self._log_event(guild,f"admin.channel.{action}",target=ch,payload={"name":ch.name if ch else None});return web.json_response({"ok":True,"action":action,"channel_id":int(ch.id) if ch else None})
async def api_roles(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._auth(request,gid)
    return web.json_response({"roles":[{"id":int(r.id),"name":r.name,"position":r.position,"color":r.color.value,"hoist":r.hoist,"mentionable":r.mentionable,"managed":r.managed,"permissions":r.permissions.value} for r in guild.roles]})
async def api_role_action(self,request):
    gid=int(request.match_info["guild_id"]);action=request.match_info["action"];guild=await _resolve_guild(self,gid);await self._require_admin(request,guild);data=await self._json(request);reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action=="create":role=await guild.create_role(name=str(data.get("name") or "New Role")[:100],permissions=discord.Permissions(int(data.get("permissions",0))),hoist=bool(data.get("hoist",False)),mentionable=bool(data.get("mentionable",False)),reason=reason)
        else:
            role=guild.get_role(int(data.get("role_id",0)))
            if role is None or role.is_default():raise web.HTTPBadRequest(text="Role not found.")
            if guild.me and role>=guild.me.top_role:raise web.HTTPForbidden(text="Bot cannot manage this role.")
            if action=="rename":await role.edit(name=str(data.get("name") or role.name)[:100],reason=reason)
            elif action=="delete":await role.delete(reason=reason)
            elif action=="permissions":await role.edit(permissions=discord.Permissions(int(data.get("permissions",role.permissions.value))),reason=reason)
            else:raise web.HTTPBadRequest(text="Unknown role action.")
    except web.HTTPException:raise
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied the action: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected the action: {exc}")
    await self._log_event(guild,f"admin.role.{action}",target=role,payload={"name":role.name if role else None});return web.json_response({"ok":True,"action":action,"role_id":int(role.id) if role else None})
async def api_guild_control(self,request):
    gid=int(request.match_info["guild_id"]);action=request.match_info["action"];guild=await _resolve_guild(self,gid);await self._require_admin(request,guild);data=await self._json(request);reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    if action!="edit":raise web.HTTPBadRequest(text="Unknown guild action.")
    kwargs={}
    if "name" in data:kwargs["name"]=str(data["name"])[:100]
    if "description" in data:kwargs["description"]=str(data["description"])[:1000] or None
    try:await guild.edit(reason=reason,**kwargs)
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied the action: {exc}")
    await self._log_event(guild,"admin.guild.edit",payload={k:v for k,v in data.items() if k in ("name","description")});return web.json_response({"ok":True})
async def api_audit(self,request):
    gid=int(request.match_info["guild_id"]);guild=await _resolve_guild(self,gid);await self._require_admin(request,guild)
    try:entries=[{"id":int(e.id),"action":str(e.action),"user":{"id":int(e.user.id),"name":str(e.user)},"target":str(e.target) if e.target else None,"reason":e.reason,"created_at":e.created_at.timestamp()} async for e in guild.audit_logs(limit=min(int(request.query.get("limit",100)),200))]
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Audit log access denied: {exc}")
    return web.json_response(entries)

class SentinelEnhancements(commands.Cog):
    def __init__(self,bot):self.bot=bot
    async def cog_load(self):
        sentinel=self.bot.get_cog("RedSentinel")
        if sentinel:await _ensure_guild_config(sentinel)
    async def _sentinel(self):return self.bot.get_cog("RedSentinel")
    @commands.Cog.listener()
    async def on_guild_channel_create(self,channel):
        s=await self._sentinel()
        if s and channel.guild:await s._log_event(channel.guild,"channel.create",target=channel,payload={"name":channel.name,"type":str(channel.type)})
    @commands.Cog.listener()
    async def on_guild_channel_delete(self,channel):
        s=await self._sentinel()
        if s and channel.guild:await s._log_event(channel.guild,"channel.delete",target=channel,payload={"name":channel.name,"type":str(channel.type)})
    @commands.Cog.listener()
    async def on_guild_channel_update(self,before,after):
        s=await self._sentinel()
        if s and after.guild and before.name!=after.name:await s._log_event(after.guild,"channel.update",target=after,payload={"before":before.name,"after":after.name})
    @commands.Cog.listener()
    async def on_guild_role_create(self,role):
        s=await self._sentinel()
        if s:await s._log_event(role.guild,"role.create",target=role,payload={"name":role.name})
    @commands.Cog.listener()
    async def on_guild_role_delete(self,role):
        s=await self._sentinel()
        if s:await s._log_event(role.guild,"role.delete",target=role,payload={"name":role.name})
    @commands.Cog.listener()
    async def on_guild_role_update(self,before,after):
        s=await self._sentinel()
        if s and (before.name!=after.name or before.permissions.value!=after.permissions.value):await s._log_event(after.guild,"role.update",target=after,payload={"before":before.name,"after":after.name})
    @commands.Cog.listener()
    async def on_voice_state_update(self,member,before,after):
        s=await self._sentinel()
        if not s or not member.guild:return
        b,a=getattr(before.channel,"id",None),getattr(after.channel,"id",None)
        if b==a:return
        await s._log_event(member.guild,"voice.update",actor=member,target=member,payload={"before_channel_id":b,"after_channel_id":a,"before_channel":getattr(before.channel,"name",None),"after_channel":getattr(after.channel,"name",None)})
    @commands.group(name="sentinel")
    @commands.admin_or_permissions(manage_guild=True)
    async def sentinel(self,ctx):
        if ctx.invoked_subcommand is None:
            c=await self._sentinel()
            if c:await ctx.send(f"Red Sentinel API: {await c.config.host()}:{await c.config.port()}")
    @sentinel.command(name="status")
    async def sentinel_status(self,ctx):
        c=await self._sentinel()
        if not c:return await ctx.send("Red Sentinel is not loaded.")
        await ctx.send(f"Red Sentinel online • API {await c.config.host()}:{await c.config.port()} • events stored locally.")

def patch_red_sentinel(RedSentinel):
    RedSentinel.api_get_config=api_get_config;RedSentinel.api_put_config=api_put_config;RedSentinel.api_social_webhook=api_social_webhook;RedSentinel.api_members=api_members;RedSentinel.api_member_action=api_member_action
    RedSentinel.api_channels=api_channels;RedSentinel.api_channel_action=api_channel_action;RedSentinel.api_roles=api_roles;RedSentinel.api_role_action=api_role_action;RedSentinel.api_guild_control=api_guild_control;RedSentinel.api_audit=api_audit
