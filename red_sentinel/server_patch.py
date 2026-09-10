from __future__ import annotations
from datetime import timedelta
import discord
from aiohttp import web

async def resolve_guild(self,gid):
    g=self.bot.get_guild(int(gid))
    if g:return g
    raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")

async def api_events(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._auth(request,gid)
    return web.json_response(await self._query_events(gid,int(request.query.get("limit",100)),request.query.get("type")))

async def api_announce(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request)
    try: channel=g.get_channel(int(str(d.get("channel_id") or "0")))
    except (ValueError,TypeError): channel=None
    if not isinstance(channel,discord.TextChannel):raise web.HTTPBadRequest(text="Invalid text channel.")
    content=str(d.get("content") or "").strip()[:2000]
    ed=d.get("embed") if isinstance(d.get("embed"),dict) else None
    embed=None
    if ed:
        title=str(ed.get("title") or "").strip()[:256]
        description=str(ed.get("description") or "").strip()[:4096]
        image=str(ed.get("image") or "").strip()[:2048]
        # A color by itself is not a valid Discord embed. Only create one when it has visible content.
        if title or description or image:
            try:
                raw=ed.get("color",0x7C5CFC);color=int(str(raw).replace("#",""),16) if not isinstance(raw,int) else raw
                kw={"color":max(0,min(color,0xFFFFFF))}
                if title:kw["title"]=title
                if description:kw["description"]=description
                embed=discord.Embed(**kw)
                if image:embed.set_image(url=image)
            except (ValueError,TypeError):raise web.HTTPBadRequest(text="Invalid embed data.")
    if not content and embed is None:raise web.HTTPBadRequest(text="Message content or embed title, description, or image is required.")
    try:
        m=await channel.send(content=content or None,embed=embed)
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied sending: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected the announcement: {exc}")
    await self._log_event(g,"admin.announce",channel=channel,payload={"message_id":str(m.id),"content":content,"embed":ed});return web.json_response({"ok":True,"message_id":str(m.id)})

async def moderation(request_self,request,action):
    self=request_self;gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request)
    try:uid=int(str(d.get("user_id") or "0"))
    except (ValueError,TypeError):raise web.HTTPBadRequest(text="Invalid user ID.")
    if not uid:raise web.HTTPBadRequest(text="user_id is required.")
    member=g.get_member(uid)
    if not member:
        try:member=await g.fetch_member(uid)
        except discord.NotFound:raise web.HTTPNotFound(text=f"Member not found: {uid}")
        except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord member lookup failed: {exc}")
    reason=str(d.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action=="ban":await g.ban(member,reason=reason)
        elif action=="kick":await g.kick(member,reason=reason)
        elif action=="timeout":await member.timeout(discord.utils.utcnow()+timedelta(minutes=max(1,min(int(d.get("minutes",60)),40320))),reason=reason)
        else:raise web.HTTPBadRequest(text="Unknown moderation action.")
    except web.HTTPException:raise
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied {action}: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected {action}: {exc}")
    await self._log_event(g,f"admin.{action}",target=member,payload={"reason":reason,"minutes":d.get("minutes")});return web.json_response({"ok":True})
async def api_ban(self,request):return await moderation(self,request,"ban")
async def api_kick(self,request):return await moderation(self,request,"kick")
async def api_timeout(self,request):return await moderation(self,request,"timeout")

async def api_delete(self,request):
    gid=int(request.match_info["guild_id"]);g=await resolve_guild(self,gid);await self._require_admin(request,g);d=await self._json(request)
    c=g.get_channel(int(str(d.get("channel_id") or "0")))
    if not isinstance(c,discord.TextChannel):raise web.HTTPBadRequest(text="Invalid text channel.")
    try:m=await c.fetch_message(int(str(d.get("message_id") or "0")));await m.delete()
    except discord.NotFound:raise web.HTTPNotFound(text="Message not found.")
    except discord.Forbidden as exc:raise web.HTTPForbidden(text=f"Discord denied delete: {exc}")
    except discord.HTTPException as exc:raise web.HTTPBadRequest(text=f"Discord rejected delete: {exc}")
    await self._log_event(g,"admin.delete",channel=c,payload={"message_id":str(m.id)});return web.json_response({"ok":True})

def patch_server_api(RedSentinel):
    RedSentinel._resolve_guild=resolve_guild;RedSentinel.api_events=api_events;RedSentinel.api_announce=api_announce;RedSentinel.api_ban=api_ban;RedSentinel.api_kick=api_kick;RedSentinel.api_timeout=api_timeout;RedSentinel.api_delete=api_delete
