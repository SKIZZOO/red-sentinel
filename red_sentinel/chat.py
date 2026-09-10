from __future__ import annotations
import discord
from aiohttp import web

async def api_channel_messages(self, request):
    gid = int(request.match_info["guild_id"])
    cid = int(request.match_info["channel_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._auth(request, gid)
    channel = guild.get_channel(cid)
    if not isinstance(channel, discord.TextChannel):
        raise web.HTTPBadRequest(text="Invalid text channel.")
    try:
        limit = max(1, min(int(request.query.get("limit", 80)), 100))
        messages = [m async for m in channel.history(limit=limit, oldest_first=False)]
    except discord.Forbidden as exc:
        raise web.HTTPForbidden(text=f"Discord denied reading channel history: {exc}")
    except discord.HTTPException as exc:
        raise web.HTTPBadRequest(text=f"Discord rejected channel history: {exc}")
    result = []
    for m in reversed(messages):
        result.append({
            "id": str(m.id),
            "author_id": str(m.author.id),
            "author": str(m.author),
            "display_name": getattr(m.author, "display_name", str(m.author)),
            "avatar": str(m.author.display_avatar.url) if getattr(m.author, "display_avatar", None) else None,
            "content": m.content or "",
            "created_at": m.created_at.timestamp(),
            "edited_at": m.edited_at.timestamp() if m.edited_at else None,
            "attachments": [{"url": a.url, "name": a.filename, "content_type": a.content_type} for a in m.attachments],
            "embeds": [{"title": e.title, "description": e.description, "url": e.url, "image": e.image.url if e.image else None} for e in m.embeds],
            "reply_to": str(m.reference.message_id) if m.reference and m.reference.message_id else None,
            "pinned": bool(m.pinned),
        })
    return web.json_response(result)

def patch_chat_api(RedSentinel):
    RedSentinel.api_channel_messages = api_channel_messages
