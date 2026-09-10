from __future__ import annotations
from datetime import timedelta
import discord
from aiohttp import web

async def api_members_fixed(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._auth(request, gid)
    query = str(request.query.get("q", "")).strip().lower()
    limit = max(1, min(int(request.query.get("limit", 200)), 500))
    members = list(getattr(guild, "members", []) or [])
    if len(members) < min(limit, guild.member_count or limit):
        try:
            members = [m async for m in guild.fetch_members(limit=1000)]
        except Exception:
            pass
    members.sort(key=lambda m: (m.bot, (m.display_name or m.name).lower()))
    if query:
        members = [m for m in members if query in str(m.id) or query in m.name.lower() or query in m.display_name.lower()]
    result = []
    for m in members[:limit]:
        result.append({
            "id": str(m.id),
            "name": m.name,
            "display_name": m.display_name,
            "avatar": str(m.display_avatar.url) if m.display_avatar else None,
            "bot": bool(m.bot),
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            "roles": [{"id": str(r.id), "name": r.name, "position": r.position} for r in m.roles if not r.is_default()],
            "role_ids": [str(r.id) for r in m.roles if not r.is_default()],
            "timeout_until": m.timed_out_until.isoformat() if m.timed_out_until else None,
        })
    return web.json_response({"members": result, "total": guild.member_count or len(members), "cached": len(getattr(guild, "members", []) or [])})

async def api_member_action_fixed(self, request):
    gid = int(request.match_info["guild_id"])
    action = request.match_info["action"]
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild)
    data = await self._json(request)
    try:
        member_id = int(str(data.get("user_id") or "0"))
    except (ValueError, TypeError):
        raise web.HTTPBadRequest(text="Invalid user ID.")
    if not member_id:
        raise web.HTTPBadRequest(text="user_id is required.")
    member = guild.get_member(member_id)
    if member is None:
        try:
            member = await guild.fetch_member(member_id)
        except discord.NotFound:
            raise web.HTTPNotFound(text=f"Member not found: {member_id}")
        except discord.HTTPException as exc:
            raise web.HTTPBadRequest(text=f"Discord member lookup failed: {exc}")
    reason = str(data.get("reason") or "Red Sentinel dashboard action")[:512]
    me = guild.me
    try:
        if action == "nickname":
            nickname = None if data.get("nickname") is None else (str(data.get("nickname")).strip()[:32] or None)
            await member.edit(nick=nickname, reason=reason)
        elif action in ("role_add", "role_remove"):
            role_id = int(str(data.get("role_id") or "0"))
            role = guild.get_role(role_id)
            if role is None or role.is_default():
                raise web.HTTPBadRequest(text="Role not found.")
            if me and role >= me.top_role:
                raise web.HTTPForbidden(text="Bot cannot manage this role.")
            if action == "role_add":
                await member.add_roles(role, reason=reason)
            else:
                await member.remove_roles(role, reason=reason)
        elif action == "timeout_clear":
            await member.timeout(None, reason=reason)
        elif action == "timeout":
            minutes = max(1, min(int(data.get("minutes", 60)), 40320))
            await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        elif action == "kick":
            await guild.kick(member, reason=reason)
        elif action == "ban":
            await guild.ban(member, reason=reason)
        else:
            raise web.HTTPBadRequest(text="Unknown member action.")
    except web.HTTPException:
        raise
    except discord.Forbidden as exc:
        raise web.HTTPForbidden(text=f"Discord denied {action}: {exc}")
    except discord.HTTPException as exc:
        raise web.HTTPBadRequest(text=f"Discord rejected {action}: {exc}")
    return web.json_response({"ok": True, "action": action, "user_id": str(member_id)})

def patch_action_fixes(RedSentinel):
    RedSentinel.api_members = api_members_fixed
    RedSentinel.api_member_action = api_member_action_fixed
