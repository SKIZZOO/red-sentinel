from __future__ import annotations

import discord
from aiohttp import web


async def _guild(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}. The bot must be online in this server.")
    return guild


def _json_channel(c):
    return {"id": str(c.id), "name": c.name, "type": str(c.type), "position": getattr(c, "position", 0), "category_id": str(getattr(getattr(c, "category", None), "id", "")) if getattr(c, "category", None) else None, "nsfw": bool(getattr(c, "nsfw", False)), "slowmode": int(getattr(c, "slowmode_delay", 0) or 0)}


async def api_channels(self, request):
    guild = await _guild(self, request)
    await self._require_admin(request, guild)
    return web.json_response({"channels": [_json_channel(c) for c in sorted(guild.channels, key=lambda x: (getattr(x, "position", 0), x.id))]})


async def api_channel_action(self, request):
    guild = await _guild(self, request)
    await self._require_admin(request, guild)
    action = request.match_info["action"]
    data = await self._json(request)
    reason = str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action == "create":
            name = str(data.get("name") or "new-channel").strip()[:100]
            kind = str(data.get("type") or "text").lower()
            category = guild.get_channel(int(data.get("category_id", 0))) if data.get("category_id") else None
            if kind == "category": channel = await guild.create_category(name=name, reason=reason)
            elif kind == "voice": channel = await guild.create_voice_channel(name=name, category=category if isinstance(category, discord.CategoryChannel) else None, reason=reason)
            else: channel = await guild.create_text_channel(name=name, category=category if isinstance(category, discord.CategoryChannel) else None, reason=reason)
        else:
            channel = guild.get_channel(int(data.get("channel_id", 0)))
            if channel is None: raise web.HTTPNotFound(text="Channel not found.")
            if action == "rename": await channel.edit(name=str(data.get("name") or channel.name)[:100], reason=reason)
            elif action == "delete": await channel.delete(reason=reason)
            elif action == "slowmode":
                seconds=max(0,min(int(data.get("seconds",0)),21600)); await channel.edit(slowmode_delay=seconds, reason=reason)
            elif action == "lock":
                me=guild.me
                if not me: raise web.HTTPForbidden(text="Bot member is unavailable.")
                overwrite=channel.overwrites_for(me)
                overwrite.send_messages=False
                await channel.set_permissions(me, overwrite=overwrite, reason=reason)
            elif action == "unlock":
                me=guild.me
                if not me: raise web.HTTPForbidden(text="Bot member is unavailable.")
                overwrite=channel.overwrites_for(me)
                overwrite.send_messages=None
                await channel.set_permissions(me, overwrite=overwrite, reason=reason)
            else: raise web.HTTPBadRequest(text="Unknown channel action.")
        await self._log_event(guild, f"admin.channel.{action}", target=channel, payload={"name": getattr(channel,"name",None), "reason": reason})
        return web.json_response({"ok": True, "channel": _json_channel(channel)})
    except web.HTTPException: raise
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied action: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected action: {exc}")


async def api_roles(self, request):
    guild = await _guild(self, request)
    await self._require_admin(request, guild)
    return web.json_response({"roles": [{"id": str(r.id), "name": r.name, "position": r.position, "color": r.color.value, "mentionable": r.mentionable, "hoist": r.hoist, "managed": r.managed} for r in sorted(guild.roles, key=lambda x: x.position, reverse=True)]})


async def api_role_action(self, request):
    guild = await _guild(self, request)
    await self._require_admin(request, guild)
    action=request.match_info["action"]; data=await self._json(request); reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512]; me=guild.me
    try:
        if action == "create":
            role=await guild.create_role(name=str(data.get("name") or "New Role")[:100], color=discord.Color(int(str(data.get("color","0")).replace("#",""),16) if str(data.get("color","0")).strip() else 0), hoist=bool(data.get("hoist",False)), mentionable=bool(data.get("mentionable",False)), reason=reason)
        else:
            role=guild.get_role(int(data.get("role_id",0)))
            if role is None: raise web.HTTPNotFound(text="Role not found.")
            if role.is_default() or role.managed: raise web.HTTPForbidden(text="This role cannot be managed from the dashboard.")
            if me and role >= me.top_role: raise web.HTTPForbidden(text="Bot cannot manage this role because it is at/above the bot's highest role.")
            if action == "rename": role=await role.edit(name=str(data.get("name") or role.name)[:100], reason=reason)
            elif action == "edit":
                kwargs={"name":str(data.get("name") or role.name)[:100],"hoist":bool(data.get("hoist",role.hoist)),"mentionable":bool(data.get("mentionable",role.mentionable)),"reason":reason}
                if data.get("color") is not None: kwargs["color"]=discord.Color(int(str(data["color"]).replace("#",""),16))
                role=await role.edit(**kwargs)
            elif action == "delete": await role.delete(reason=reason)
            else: raise web.HTTPBadRequest(text="Unknown role action.")
        await self._log_event(guild, f"admin.role.{action}", target=role, payload={"name": getattr(role,"name",None),"reason":reason})
        return web.json_response({"ok": True, "role": {"id": str(role.id), "name": role.name, "position": role.position} if role else None})
    except web.HTTPException: raise
    except (ValueError, TypeError) as exc: raise web.HTTPBadRequest(text=f"Invalid role data: {exc}")
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied action: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected action: {exc}")


async def api_audit(self, request):
    guild=await _guild(self,request); await self._require_admin(request,guild); limit=max(1,min(int(request.query.get("limit",100)),200)); items=[]
    try:
        async for entry in guild.audit_logs(limit=limit):
            items.append({"id":str(entry.id),"action":str(entry.action),"user_id":str(entry.user.id) if entry.user else None,"user":str(entry.user) if entry.user else None,"target_id":str(getattr(entry.target,"id","")) if getattr(entry.target,"id",None) else None,"target":str(entry.target) if entry.target else None,"reason":entry.reason,"created_at":entry.created_at.isoformat()})
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Audit log access denied: {exc}")
    return web.json_response({"entries":entries})


async def api_guild_control(self, request):
    guild=await _guild(self,request); await self._require_admin(request,guild); action=request.match_info["action"]; data=await self._json(request); reason=str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    try:
        if action == "rename": await guild.edit(name=str(data.get("name") or guild.name)[:100],reason=reason)
        elif action == "description": await guild.edit(description=str(data.get("description") or "")[:120],reason=reason)
        elif action == "verification": await guild.edit(verification_level=getattr(discord.VerificationLevel,str(data.get("level") or "none")),reason=reason)
        else: raise web.HTTPBadRequest(text="Unknown server control action.")
        await self._log_event(guild,f"admin.guild.{action}",target=guild,payload={"reason":reason,"action":action})
        return web.json_response({"ok":True,"id":str(guild.id),"name":guild.name,"description":getattr(guild,"description",None)})
    except web.HTTPException: raise
    except discord.Forbidden as exc: raise web.HTTPForbidden(text=f"Discord denied the action: {exc}")
    except discord.HTTPException as exc: raise web.HTTPBadRequest(text=f"Discord rejected the action: {exc}")


def patch_server_control(RedSentinel):
    RedSentinel.api_channels=api_channels
    RedSentinel.api_channel_action=api_channel_action
    RedSentinel.api_roles=api_roles
    RedSentinel.api_role_action=api_role_action
    RedSentinel.api_audit=api_audit
    RedSentinel.api_guild_control=api_guild_control
