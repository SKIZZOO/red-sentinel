from __future__ import annotations

from aiohttp import web


def _avatar(obj):
    try:
        return str(obj.display_avatar.url) if obj and obj.display_avatar else None
    except Exception:
        return None


async def api_events_rich(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._auth(request, gid)
    try:
        limit = max(1, min(int(request.query.get("limit", 100)), 500))
    except (TypeError, ValueError):
        limit = 100
    event_type = request.query.get("type") or None
    rows = await self._query_events(gid, limit, event_type)
    cache = {}

    async def resolve(uid):
        if not uid:
            return None
        uid = int(uid)
        if uid in cache:
            return cache[uid]
        obj = guild.get_member(uid) or self.bot.get_user(uid)
        if obj is None:
            try:
                obj = await self.bot.fetch_user(uid)
            except Exception:
                obj = None
        cache[uid] = obj
        return obj

    for row in rows:
        actor = await resolve(row.get("actor_id"))
        target = await resolve(row.get("target_id"))
        row["id"] = str(row.get("id"))
        row["guild_id"] = str(row.get("guild_id"))
        row["actor_id"] = str(row["actor_id"]) if row.get("actor_id") is not None else None
        row["target_id"] = str(row["target_id"]) if row.get("target_id") is not None else None
        row["channel_id"] = str(row["channel_id"]) if row.get("channel_id") is not None else None
        row["actor_avatar"] = _avatar(actor)
        row["target_avatar"] = _avatar(target)
        row["actor_display_name"] = getattr(actor, "display_name", None) or row.get("actor_name") or "System"
        row["target_display_name"] = getattr(target, "display_name", None) or row.get("target_name")
        payload = row.get("payload") or {}
        mid = payload.get("message_id")
        row["message_url"] = (f"https://discord.com/channels/{row['guild_id']}/{row['channel_id']}/{mid}"
                               if row.get("channel_id") and mid else None)
    return web.json_response(rows)


def patch_logs_api(RedSentinel):
    RedSentinel.api_events = api_events_rich
