from __future__ import annotations
import discord
from aiohttp import web

async def _chat_channel(self, request):
    gid=int(request.match_info["guild_id"]);cid=int(request.match_info["channel_id"]);guild=self.bot.get_guild(gid)
    if guild is None: raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._auth(request,gid)
    channel=guild.get_channel(cid)
    if channel is None:
        try: channel=await self.bot.fetch_channel(cid)
        except (discord.NotFound,discord.Forbidden): channel=None
        except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord channel lookup failed: {exc}")
    if not isinstance(channel,(discord.TextChannel,discord.Thread)):
        raise web.HTTPBadRequest(text="Invalid text channel.")
    if getattr(channel,'guild',None) and channel.guild.id != guild.id:
        raise web.HTTPForbidden(text="Channel does not belong to this server.")
    return guild,channel

def _member_profile(m):
    return {"id":str(m.id),"name":m.name,"display_name":m.display_name,"global_name":getattr(m,"global_name",None),"avatar":str(m.display_avatar.url) if m.display_avatar else None,"bot":bool(m.bot),"joined_at":m.joined_at.isoformat() if m.joined_at else None,"created_at":m.created_at.isoformat() if m.created_at else None,"roles":[{"id":str(r.id),"name":r.name,"position":r.position,"color":str(r.color) if r.color.value else None} for r in m.roles if not r.is_default()],"role_ids":[str(r.id) for r in m.roles if not r.is_default()],"timeout_until":m.timed_out_until.isoformat() if m.timed_out_until else None,"top_role":{"id":str(m.top_role.id),"name":m.top_role.name,"position":m.top_role.position} if m.top_role else None}

async def api_channel_messages(self,request):
    guild,channel=await _chat_channel(self,request)
    try:
        limit=max(1,min(int(request.query.get("limit",80)),100));before=request.query.get("before");kw={"limit":limit,"oldest_first":False}
        if before: kw["before"]=discord.Object(id=int(before))
        messages=[m async for m in channel.history(**kw)]
    except (ValueError,TypeError): raise web.HTTPBadRequest(text="Invalid before message ID.")
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied reading channel history: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected channel history: {exc}")
    result=[]
    for m in reversed(messages):
        author=m.author;member=guild.get_member(author.id);roles=[{"id":str(r.id),"name":r.name,"position":r.position,"color":str(r.color) if r.color.value else None} for r in member.roles if not r.is_default()] if member else [];embeds=[]
        for e in m.embeds: embeds.append({"title":e.title,"description":e.description,"url":e.url,"image":e.image.url if e.image else None,"thumbnail":e.thumbnail.url if e.thumbnail else None,"video":e.video.url if e.video else None})
        result.append({"id":str(m.id),"author_id":str(author.id),"author":str(author),"display_name":getattr(author,"display_name",str(author)),"global_name":getattr(author,"global_name",None),"avatar":str(author.display_avatar.url) if getattr(author,"display_avatar",None) else None,"bot":bool(getattr(author,"bot",False)),"roles":roles,"top_role":roles[-1] if roles else None,"content":m.content or "","created_at":m.created_at.timestamp(),"edited_at":m.edited_at.timestamp() if m.edited_at else None,"attachments":[{"url":a.url,"name":a.filename,"content_type":a.content_type,"width":a.width,"height":a.height} for a in m.attachments],"embeds":embeds,"reply_to":str(m.reference.message_id) if m.reference and m.reference.message_id else None,"pinned":bool(m.pinned)})
    return web.json_response(result)

async def api_chat_profile(self,request):
    gid=int(request.match_info["guild_id"]);uid=int(request.match_info["user_id"]);guild=self.bot.get_guild(gid)
    if guild is None: raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._auth(request,gid);member=guild.get_member(uid)
    if member is None:
        try: member=await guild.fetch_member(uid)
        except discord.NotFound: raise web.HTTPNotFound(text="Member not found.")
        except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord member lookup failed: {exc}")
    return web.json_response(_member_profile(member))

async def api_send_chat_message(self,request):
    guild,channel=await _chat_channel(self,request);await self._require_admin(request,guild);data=await self._json(request);content=str(data.get("content") or "").strip()
    if not content: raise web.HTTPBadRequest(text="Message content is required.")
    if len(content)>2000: raise web.HTTPBadRequest(text="Message is limited to 2000 characters.")
    try: msg=await channel.send(content)
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied sending: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected message: {exc}")
    await self._log_event(guild,"admin.chat_send",channel=channel,payload={"message_id":str(msg.id),"content":content});return web.json_response({"ok":True,"message_id":str(msg.id)})

async def api_delete_chat_message(self,request):
    guild,channel=await _chat_channel(self,request);await self._require_admin(request,guild);mid=int(request.match_info["message_id"])
    try: msg=await channel.fetch_message(mid);await msg.delete()
    except discord.NotFound: raise web.HTTPNotFound(text="Message not found.")
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied deleting message: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected deleting message: {exc}")
    await self._log_event(guild,"admin.chat_delete",channel=channel,payload={"message_id":str(mid)});return web.json_response({"ok":True})

def patch_chat_api(RedSentinel):
    RedSentinel.api_channel_messages=api_channel_messages;RedSentinel.api_chat_profile=api_chat_profile;RedSentinel.api_send_chat_message=api_send_chat_message;RedSentinel.api_delete_chat_message=api_delete_chat_message
