from __future__ import annotations

import asyncio
import hmac
import time
from typing import Any

import discord
from aiohttp import web
from redbot.core import commands


def _provider_item(data: dict[str, Any]):
    provider = str(data.get("provider") or "custom").lower().strip()
    external_id = str(data.get("external_id") or data.get("id") or f"{provider}:{int(time.time() * 1000)}")
    item = data.get("item") if isinstance(data.get("item"), dict) else data
    title = item.get("title") or item.get("name") or item.get("status")
    author = item.get("author") or item.get("username") or item.get("channel") or item.get("broadcaster_user_name")
    url = item.get("url") or item.get("link")
    description = item.get("description") or item.get("text") or item.get("content")
    normalized = {
        "provider": provider,
        "external_id": external_id,
        "title": str(title)[:256] if title is not None else None,
        "author": str(author)[:256] if author is not None else None,
        "url": str(url) if url else None,
        "description": str(description)[:4096] if description is not None else None,
        "thumbnail": item.get("thumbnail") or item.get("thumbnail_url") or item.get("image"),
        "payload": data,
    }
    return provider, external_id, normalized["author"], normalized["title"], normalized["url"], normalized


async def _ensure_guild_config(sentinel):
    sentinel.config.register_guild(providers={}, routes={}, social_webhook_secret="")
    global_providers = await sentinel.config.providers()
    global_routes = await sentinel.config.routes()
    for guild in sentinel.bot.guilds:
        cfg = sentinel.config.guild(guild)
        current_routes = await cfg.routes()
        current_providers = await cfg.providers()
        if not current_providers and global_providers:
            await cfg.providers.set(global_providers)
        if not current_routes and global_routes:
            migrated = {}
            for provider, value in (global_routes or {}).items():
                entries = value if isinstance(value, list) else [value]
                for entry in entries:
                    if isinstance(entry, dict):
                        if int(entry.get("guild_id", guild.id)) != guild.id:
                            continue
                        channel_id = entry.get("channel_id")
                    else:
                        channel_id = entry
                    if channel_id:
                        migrated[str(provider).lower()] = str(channel_id)
                        break
            if migrated:
                await cfg.routes.set(migrated)


async def api_get_config(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    self.config.register_guild(providers={}, routes={}, social_webhook_secret="")
    cfg = self.config.guild(guild)
    return web.json_response({"providers": await cfg.providers(), "routes": await cfg.routes()})


async def api_put_config(self, request):
    gid = int(request.match_info["guild_id"])
    guild = self.bot.get_guild(gid)
    if guild is None:
        raise web.HTTPNotFound(text="Guild not found.")
    await self._auth(request, gid)
    data = await self._json(request)
    self.config.register_guild(providers={}, routes={}, social_webhook_secret="")
    cfg = self.config.guild(guild)
    if "providers" in data:
        await cfg.providers.set(data["providers"] if isinstance(data["providers"], dict) else {})
    if "routes" in data:
        clean = {str(k).lower(): str(v) for k, v in (data.get("routes") or {}).items() if v}
        await cfg.routes.set(clean)
    if "social_webhook_secret" in data:
        await cfg.social_webhook_secret.set(str(data["social_webhook_secret"] or ""))
    return web.json_response({"ok": True, "providers": await cfg.providers(), "routes": await cfg.routes()})


async def api_social_webhook(self, request):
    data = await self._json(request)
    guild_id = data.get("guild_id")
    token = request.headers.get("X-Sentinel-Webhook", "")
    static_token = await self.config.api_token()
    static_ok = bool(static_token and token and hmac.compare_digest(token, static_token))
    if not static_ok:
        # OAuth dashboard calls must always name exactly one target guild.
        if not guild_id:
            raise web.HTTPBadRequest(text="guild_id is required for authenticated dashboard social events.")
        await self._auth(request, int(guild_id))

    provider, external_id, author, title, url, normalized = _provider_item(data)
    item = {
        "provider": provider,
        "external_id": external_id,
        "author": author,
        "title": title,
        "url": url,
        "payload": normalized,
        "created_at": int(time.time()),
    }
    await asyncio.to_thread(self._insert_social_item, item)

    targets = []
    self.config.register_guild(providers={}, routes={}, social_webhook_secret="")
    for guild in self.bot.guilds:
        if guild_id and int(guild.id) != int(guild_id):
            continue
        cfg = self.config.guild(guild)
        routes = await cfg.routes()
        channel_id = routes.get(provider) or routes.get("custom")
        if not channel_id:
            continue
        channel = guild.get_channel(int(channel_id))
        if isinstance(channel, discord.TextChannel):
            targets.append((guild, channel))

    kwargs = {
        "title": title or f"{provider.upper()} update",
        "description": normalized.get("description") or (author if author else "New social signal"),
        "timestamp": discord.utils.utcnow(),
    }
    if url:
        kwargs["url"] = url
    embed = discord.Embed(**kwargs)
    if normalized.get("thumbnail"):
        try:
            embed.set_thumbnail(url=str(normalized["thumbnail"]))
        except Exception:
            pass
    embed.set_footer(text=f"Red Sentinel • {provider.upper()}")

    delivered = 0
    for guild, channel in targets:
        try:
            await channel.send(embed=embed)
            await self._log_event(guild, f"social.{provider}", channel=channel, payload={
                "external_id": external_id,
                "title": title,
                "author": author,
                "url": url,
            })
            delivered += 1
        except discord.HTTPException:
            continue
    return web.json_response({"ok": True, "provider": provider, "delivered": delivered})


class SentinelEnhancements(commands.Cog):
    """Extra Discord event coverage and maintenance for Red Sentinel."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        sentinel = self.bot.get_cog("RedSentinel")
        if sentinel:
            await _ensure_guild_config(sentinel)

    async def _sentinel(self):
        return self.bot.get_cog("RedSentinel")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        sentinel = await self._sentinel()
        if sentinel and channel.guild:
            await sentinel._log_event(channel.guild, "channel.create", target=channel, payload={"name": channel.name, "type": str(channel.type)})

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        sentinel = await self._sentinel()
        if sentinel and channel.guild:
            await sentinel._log_event(channel.guild, "channel.delete", target=channel, payload={"name": channel.name, "type": str(channel.type)})

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        sentinel = await self._sentinel()
        if sentinel and after.guild and (before.name != after.name or getattr(before, "topic", None) != getattr(after, "topic", None)):
            await sentinel._log_event(after.guild, "channel.update", target=after, payload={"before": before.name, "after": after.name})

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        sentinel = await self._sentinel()
        if sentinel:
            await sentinel._log_event(role.guild, "role.create", target=role, payload={"name": role.name})

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        sentinel = await self._sentinel()
        if sentinel:
            await sentinel._log_event(role.guild, "role.delete", target=role, payload={"name": role.name})

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        sentinel = await self._sentinel()
        if sentinel and (before.name != after.name or before.permissions.value != after.permissions.value):
            await sentinel._log_event(after.guild, "role.update", target=after, payload={"before": before.name, "after": after.name})

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        sentinel = await self._sentinel()
        if not sentinel or not member.guild:
            return
        before_id = getattr(before.channel, "id", None)
        after_id = getattr(after.channel, "id", None)
        if before_id == after_id:
            return
        await sentinel._log_event(member.guild, "voice.update", actor=member, target=member, payload={
            "before_channel_id": before_id,
            "after_channel_id": after_id,
            "before_channel": getattr(before.channel, "name", None),
            "after_channel": getattr(after.channel, "name", None),
        })

    @commands.group(name="sentinel")
    @commands.admin_or_permissions(manage_guild=True)
    async def sentinel(self, ctx):
        """Red Sentinel control commands."""
        if ctx.invoked_subcommand is None:
            cog = await self._sentinel()
            if cog:
                await ctx.send(f"Red Sentinel API: {await cog.config.host()}:{await cog.config.port()}")

    @sentinel.command(name="status")
    async def sentinel_status(self, ctx):
        cog = await self._sentinel()
        if not cog:
            return await ctx.send("Red Sentinel is not loaded.")
        await ctx.send(f"Red Sentinel online • API {await cog.config.host()}:{await cog.config.port()} • events stored locally.")


def patch_red_sentinel(RedSentinel):
    """Patch API methods before the cog starts its aiohttp server."""
    RedSentinel.api_get_config = api_get_config
    RedSentinel.api_put_config = api_put_config
    RedSentinel.api_social_webhook = api_social_webhook
