from __future__ import annotations
from datetime import timedelta
import discord
from aiohttp import web

async def resolve_guild(self,gid):
    g=self.bot.get_guild(int(gid))
    if g:return g
    try:return await self.bot.fetch_guild(int(gid),with_counts=True)
    except Exception as exc:raise web.HTTPNotFound(text=f"Guild not found: {gid} ({exc})")

async def api_events(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._auth(request,gid)
    return web.json_response(await self._query_events(gid,int(request.query.get("limit",100)),request.query.get("type")))

async def api_announce(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request)
    channel=g.get_channel(int(d.get("channel_id",0)))
    if not isinstance(channel,discord.TextChannel):raise web.HTTPBadRequest(text="Invalid text channel.")
    content=str(d.get("content") or "")[:2000];ed=d.get("embed") if isinstance(d.get("embed"),dict) else None;embed=None
    if ed:
        try:color=int(str(ed.get("color",0x7C5CFC)).replace("#",""),16)
        except Exception:color=0x7C5CFC
        embed=discord.Embed(title=str(ed.get("title") or "")[:256] or discord.Embed.Empty,description=str(ed.get("description") or "")[:4096] or discord.Embed.Empty,color=color)
        if ed.get("image"):embed.set_image(url=str(ed["image"]))
    try:m=await channel.send(content=content or None,embed=embed)
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied sending: {exc}")
    await self._log_event(g,"admin.announce",channel=channel,payload={"message_id":m.id,"content":content,"embed":ed});return web.json_response({"ok":True,"message_id":m.id})

async def moderation(self,request,action):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request);uid=int(d.get("user_id",0))
    if not uid:raise web.HTTPBadRequest(text="user_id is required.")
    member=g.get_member(uid)
    if not member:
        try:member=await g.fetch_member(uid)
        except discord.NotFound:raise web.HTTPNotFound(text="Member not found.")
    reason=str(d.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action=="ban":await g.ban(member,reason=reason)
        elif action=="kick":await g.kick(member,reason=reason)
        elif action=="timeout":await member.timeout(discord.utils.utcnow()+timedelta(minutes=max(1,min(int(d.get("minutes",60)),40320))),reason=reason)
        else:raise web.HTTPBadRequest(text="Unknown moderation action.")
    except web.HTTPException:raise
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied action: {exc}")
    await self._log_event(g,f"admin.{action}",target=member,payload={"reason":reason,"minutes":d.get("minutes")});return web.json_response({"ok":True})
async def api_ban(self,request):return await moderation(self,request,"ban")
async def api_kick(self,request):return await moderation(self,request,"kick")
async def api_timeout(self,request):return await moderation(self,request,"timeout")

async def api_delete(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request);c=g.get_channel(int(d.get("channel_id",0)))
    if not isinstance(c,discord.TextChannel):raise web.HTTPBadRequest(text="Invalid text channel.")
    try:m=await c.fetch_message(int(d.get("message_id",0)));await m.delete()
    except discord.NotFound:raise web.HTTPNotFound(text="Message not found.")
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied delete: {exc}")
    await self._log_event(g,"admin.delete",channel=c,payload={"message_id":m.id});return web.json_response({"ok":True})

def patch_server_api(RedSentinel):
    RedSentinel._resolve_guild=resolve_guild;RedSentinel.api_events=api_events;RedSentinel.api_announce=api_announce;RedSentinel.api_ban=api_ban;RedSentinel.api_kick=api_kick;RedSentinel.api_timeout=api_timeout;RedSentinel.api_delete=api_delete
