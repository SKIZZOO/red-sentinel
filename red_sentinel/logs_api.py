from __future__ import annotations

import discord
from aiohttp import web


def _avatar(obj):
    try:
        return str(obj.display_avatar.url) if obj and obj.display_avatar else None
    except Exception:
        return None


def _stringify_snowflakes(value):
    """Keep Discord snowflake IDs as strings so browsers cannot round them."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key.endswith("_id") or key in {"id", "message_id", "channel_id", "guild_id", "user_id", "actor_id", "target_id"}:
                if item is not None and isinstance(item, (int, float)):
                    out[key] = str(item)
                else:
                    out[key] = _stringify_snowflakes(item)
            else:
                out[key] = _stringify_snowflakes(item)
        return out
    if isinstance(value, list):
        return [_stringify_snowflakes(x) for x in value]
    return value


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
        payload = _stringify_snowflakes(row.get("payload") or {})
        row["payload"] = payload
        mid = payload.get("message_id")
        row["message_id"] = str(mid) if mid is not None else None
        row["message_url"] = (f"https://discord.com/channels/{row['guild_id']}/{row['channel_id']}/{mid}"
                               if row.get("channel_id") and mid else None)
    return web.json_response(rows)


async def api_delete_log_message(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    await self._require_admin(request, guild)
    data = await self._json(request)
    try:
        cid = int(str(data.get("channel_id") or ""))
        mid = int(str(data.get("message_id") or ""))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="A valid channel ID and message ID are required.")

    channel = guild.get_channel(cid)
    if channel is None:
        try:
            channel = await self.bot.fetch_channel(cid)
        except discord.NotFound:
            raise web.HTTPNotFound(text="Discord channel no longer exists.")
        except discord.Forbidden:
            raise web.HTTPForbidden(text="Discord denied access to that channel.")
        except discord.HTTPException as exc:
            raise web.HTTPBadRequest(text=f"Discord channel lookup failed: {exc}")

    if getattr(channel, "guild", None) is not None and channel.guild.id != guild.id:
        raise web.HTTPForbidden(text="Channel does not belong to this server.")
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise web.HTTPBadRequest(text="That log does not point to a deletable text channel or thread.")

    try:
        message = await channel.fetch_message(mid)
    except discord.NotFound:
        raise web.HTTPNotFound(text="Message not found. It may already have been deleted from Discord.")
    except discord.Forbidden:
        raise web.HTTPForbidden(text="Discord denied access to that message. Check View Channel, Read Message History and Manage Messages.")
    except discord.HTTPException as exc:
        raise web.HTTPBadRequest(text=f"Discord rejected the message lookup: {exc}")

    try:
        await message.delete(reason="Red Sentinel dashboard — delete from Live Logs")
    except discord.NotFound:
        raise web.HTTPNotFound(text="Message was already deleted from Discord.")
    except discord.Forbidden:
        raise web.HTTPForbidden(text="Discord denied deleting the message. The bot needs Manage Messages in that channel.")
    except discord.HTTPException as exc:
        raise web.HTTPBadRequest(text=f"Discord rejected deleting the message: {exc}")

    await self._log_event(guild, "admin.delete", channel=channel, payload={"message_id": str(mid), "source": "live_logs"})
    return web.json_response({"ok": True, "message_id": str(mid)})


def patch_logs_api(RedSentinel):
    RedSentinel.api_events = api_events_rich
    RedSentinel.api_delete = api_delete_log_message
