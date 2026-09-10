from __future__ import annotations

import asyncio
import re
import secrets
import time
from urllib.parse import urlparse

import discord
from aiohttp import web

PLATFORMS = {"twitch": "Twitch", "youtube": "YouTube", "kick": "Kick"}


def _platform(url: str, selected: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "twitch.tv" in host: return "twitch"
    if "youtube.com" in host or "youtu.be" in host: return "youtube"
    if "kick.com" in host: return "kick"
    return selected if selected in PLATFORMS else "twitch"


def _name(url: str, supplied: str) -> str:
    if supplied.strip(): return supplied.strip()[:100]
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[-1][:100] if parts else "Streamer"


def _live_from_html(platform: str, text: str) -> bool | None:
    low = text.lower()
    # Prefer explicit structured live flags. Do not alert on ambiguous pages.
    patterns = {
        "twitch": [r'"islive"\s*:\s*true', r'"islivebroadcast"\s*:\s*true'],
        "youtube": [r'"islivebroadcast"\s*:\s*true', r'"islivenow"\s*:\s*true'],
        "kick": [r'"islive"\s*:\s*true', r'"livestream"\s*:\s*\{'],
    }
    if any(re.search(p, low) for p in patterns.get(platform, [])): return True
    # Explicit false is useful for structured pages; otherwise unknown.
    if platform == "twitch" and re.search(r'"islive"\s*:\s*false', low): return False
    if platform == "youtube" and re.search(r'"islivebroadcast"\s*:\s*false', low): return False
    if platform == "kick" and re.search(r'"islive"\s*:\s*false', low): return False
    return None


async def _check_source(self, source: dict) -> tuple[bool | None, dict]:
    url = str(source.get("url", ""))
    platform = source.get("platform", "twitch")
    if not url or not self.session: return None, {}
    try:
        async with self.session.get(url, headers={"User-Agent": "RedSentinel/1.0 (+Discord livestream monitor)"}, allow_redirects=True) as r:
            if r.status >= 400: return None, {}
            text = await r.text(errors="ignore")
            live = _live_from_html(platform, text)
            meta = {"status": r.status}
            title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', text, re.I)
            if title_match: meta["title"] = title_match.group(1)[:200]
            image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', text, re.I)
            if image_match: meta["image"] = image_match.group(1)[:1000]
            return live, meta
    except Exception:
        return None, {}


async def _send_live_alert(self, guild, source, meta):
    channel = guild.get_channel(int(source.get("channel_id", 0)))
    if not isinstance(channel, discord.TextChannel): return False
    settings = await self.config.stream_settings()
    gs = settings.get(str(guild.id), {}) if isinstance(settings, dict) else {}
    title = str(source.get("title") or gs.get("title") or "🔴 {name} is LIVE!")
    message = str(gs.get("message") or "{name} just went live on {platform}. Come hang out!")
    name = str(source.get("name") or "Streamer")
    platform = PLATFORMS.get(source.get("platform"), source.get("platform", "live"))
    title = title.replace("{name}", name).replace("{platform}", platform)
    message = message.replace("{name}", name).replace("{platform}", platform)
    color_raw = str(gs.get("color") or "9146FF").replace("#", "")
    try: color = int(color_raw, 16)
    except ValueError: color = 0x9146FF
    embed = discord.Embed(title=title[:256], description=message[:4096], url=str(source.get("url")), color=max(0, min(color, 0xFFFFFF)))
    if meta.get("image") or source.get("image"): embed.set_image(url=str(meta.get("image") or source.get("image")))
    embed.set_footer(text=f"Red Sentinel • {platform} live alert")
    mention = bool(source.get("mention_everyone", False))
    content = "@everyone" if mention else None
    await channel.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=mention))
    await self._log_event(guild, "social.livestream", channel=channel, payload={"provider": source.get("platform"), "source_id": source.get("id"), "name": name, "url": source.get("url")})
    return True


async def stream_loop(self):
    await asyncio.sleep(5)
    while True:
        try:
            sources = await self.config.stream_sources()
            if not isinstance(sources, dict): sources = {}
            changed = False
            for gid, items in list(sources.items()):
                guild = self.bot.get_guild(int(gid))
                if not guild: continue
                for source in list(items or []):
                    if not source.get("enabled", True): continue
                    live, meta = await _check_source(self, source)
                    if live is None: continue
                    was_live = bool(source.get("live", False))
                    source["last_checked"] = int(time.time())
                    source["live"] = live
                    source["status"] = "live" if live else "offline"
                    if live and not was_live:
                        try: await _send_live_alert(self, guild, source, meta)
                        except Exception: pass
                    changed = True
                sources[gid] = items
            if changed: await self.config.stream_sources.set(sources)
        except asyncio.CancelledError: raise
        except Exception: pass
        await asyncio.sleep(max(30, min(int(await self.config.social_poll_seconds()), 600)))


async def api_streams(self, request):
    gid = int(request.match_info["guild_id"]); guild = self.bot.get_guild(gid)
    if not guild: raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild)
    data = await self.config.stream_sources(); items = data.get(str(gid), []) if isinstance(data, dict) else []
    return web.json_response({"sources": items, "settings": (await self.config.stream_settings()).get(str(gid), {})})


async def api_streams_save(self, request):
    gid = int(request.match_info["guild_id"]); guild = self.bot.get_guild(gid)
    if not guild: raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild); data = await request.json()
    sources = await self.config.stream_sources(); all_sources = dict(sources) if isinstance(sources, dict) else {}
    current = list(all_sources.get(str(gid), [])); action = str(data.get("action", ""))
    if action == "add":
        url = str(data.get("url", "")).strip(); name = str(data.get("name", "")).strip(); platform = _platform(url, str(data.get("platform", "twitch")))
        if not url.startswith(("https://", "http://")): raise web.HTTPBadRequest(text="A valid livestream URL is required.")
        try: channel = guild.get_channel(int(str(data.get("channel_id") or "0")))
        except Exception: channel = None
        if not isinstance(channel, discord.TextChannel): raise web.HTTPBadRequest(text="Invalid Discord text channel.")
        source = {"id": secrets.token_hex(8), "platform": platform, "name": _name(url, name), "url": url, "channel_id": str(channel.id), "title": str(data.get("title", ""))[:256], "image": str(data.get("image", ""))[:1000], "mention_everyone": bool(data.get("mention_everyone", False)), "enabled": True, "live": False, "status": "offline", "last_checked": 0}
        current.append(source)
    elif action == "delete": current = [x for x in current if str(x.get("id")) != str(data.get("id"))]
    elif action == "toggle":
        for x in current:
            if str(x.get("id")) == str(data.get("id")): x["enabled"] = not bool(x.get("enabled", True))
    else: raise web.HTTPBadRequest(text="Unknown livestream action.")
    all_sources[str(gid)] = current; await self.config.stream_sources.set(all_sources); return web.json_response({"ok": True, "sources": current})


async def api_stream_settings(self, request):
    gid = int(request.match_info["guild_id"]); guild = self.bot.get_guild(gid)
    if not guild: raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild); data = await request.json(); settings = await self.config.stream_settings(); all_settings = dict(settings) if isinstance(settings, dict) else {}
    all_settings[str(gid)] = {"title": str(data.get("title") or "🔴 {name} is LIVE!")[:256], "message": str(data.get("message") or "{name} just went live on {platform}. Come hang out!")[:4096], "color": str(data.get("color") or "9146FF").replace("#", "")[:6], "dedupe": bool(data.get("dedupe", True))}
    await self.config.stream_settings.set(all_settings); return web.json_response({"ok": True, "settings": all_settings[str(gid)]})


def patch_streams(RedSentinel):
    original_load = RedSentinel.cog_load; original_unload = RedSentinel.cog_unload
    async def load(self):
        original_load_result = await original_load(self)
        self.stream_task = asyncio.create_task(stream_loop(self), name="red-sentinel-stream-monitor")
        return original_load_result
    async def unload(self):
        task = getattr(self, "stream_task", None)
        if task: task.cancel()
        return await original_unload(self)
    RedSentinel.cog_load = load; RedSentinel.cog_unload = unload
    RedSentinel.api_streams = api_streams; RedSentinel.api_streams_save = api_streams_save; RedSentinel.api_stream_settings = api_stream_settings
