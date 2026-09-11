from __future__ import annotations

import asyncio
import re
import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import discord
from aiohttp import web

PLATFORMS = {"twitch": "Twitch", "youtube": "YouTube", "kick": "Kick"}


def _platform(url: str, selected: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "twitch.tv" in host:
        return "twitch"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "kick.com" in host:
        return "kick"
    return selected if selected in PLATFORMS else "twitch"


def _name(url: str, supplied: str) -> str:
    if supplied.strip():
        return supplied.strip()[:100]
    parts = [p for p in urlparse(url).path.split("/") if p]
    if parts:
        return parts[-1][:100]
    return "Streamer"


def _probe_url(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["_rs_probe"] = str(int(time.time()))
    return urlunparse(parsed._replace(query=urlencode(query)))


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def _bool_flag(text: str, names: tuple[str, ...]) -> bool | None:
    low = _compact(text)
    for name in names:
        escaped = re.escape(name)
        if re.search(rf'["\']?{escaped}["\']?\s*:\s*true\b', low):
            return True
        if re.search(rf'["\']?{escaped}["\']?\s*:\s*false\b', low):
            return False
    return None


def _live_from_html(platform: str, text: str) -> bool | None:
    """Best-effort detection using public page data, without provider credentials.

    The providers change their rendered HTML frequently, so this intentionally checks
    several known structured-data flags rather than relying on one exact payload.
    """
    low = _compact(text)

    if platform == "twitch":
        direct = _bool_flag(low, ("isLive", "is_live", "isLiveBroadcast"))
        if direct is not None:
            return direct
        if re.search(r'"stream"\s*:\s*\{[^{}]{0,1200}?"type"\s*:\s*"live"', low):
            return True
        if re.search(r'"stream"\s*:\s*null', low):
            return False
        if "twitch" in low and re.search(r'\bstream_type\b\s*[:=]\s*["\']live', low):
            return True

    if platform == "youtube":
        for name in ("isLiveBroadcast", "isLiveNow"):
            flag = _bool_flag(low, (name,))
            if flag is not None:
                return flag
        live_content = re.search(r'"livebroadcastcontent"\s*:\s*"(live|none|upcoming)"', low)
        if live_content:
            return live_content.group(1) == "live"
        if re.search(r'"badges"\s*:\s*\[[^]]{0,2000}?"live"', low):
            return True

    if platform == "kick":
        direct = _bool_flag(low, ("isLive", "is_live", "livestream_is_live"))
        if direct is not None:
            return direct
        livestream = re.search(r'"livestream"\s*:\s*(null|\{)', low)
        if livestream:
            if livestream.group(1) == "null":
                return False
            block = low[livestream.end():livestream.end() + 5000]
            nested = _bool_flag(block, ("isLive", "is_live"))
            if nested is not None:
                return nested

    # Generic fallbacks that have appeared in provider payloads.
    generic = _bool_flag(low, ("is_live", "isLive"))
    if generic is not None:
        return generic
    return None


async def _check_source(self, source: dict) -> tuple[bool | None, dict]:
    url = str(source.get("url", "")).strip()
    platform = str(source.get("platform", "twitch")).lower()
    if not url or not self.session:
        return None, {"error": "monitor session or URL unavailable"}

    try:
        probe = _probe_url(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36 RedSentinel/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        async with self.session.get(probe, headers=headers, allow_redirects=True) as r:
            text = await r.text(errors="ignore")
            if r.status >= 400:
                return None, {"status": r.status, "error": f"HTTP {r.status}", "url": str(r.url)}
            live = _live_from_html(platform, text)
            meta = {"status": r.status, "url": str(r.url), "bytes": len(text)}
            title_match = re.search(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)', text, re.I)
            if title_match:
                meta["title"] = title_match.group(1)[:200]
            image_match = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)', text, re.I)
            if image_match:
                meta["image"] = image_match.group(1)[:1000]
            if live is None:
                meta["error"] = "Provider page did not expose a recognized live/offline flag."
            return live, meta
    except Exception as exc:
        return None, {"error": f"{type(exc).__name__}: {exc}"}


async def _send_live_alert(self, guild, source, meta):
    try:
        channel = guild.get_channel(int(str(source.get("channel_id", 0))))
    except (TypeError, ValueError):
        channel = None
    if not isinstance(channel, discord.TextChannel):
        return False

    try:
        settings = await self.config.stream_settings()
    except Exception:
        settings = {}
    gs = settings.get(str(guild.id), {}) if isinstance(settings, dict) else {}
    title = str(source.get("title") or gs.get("title") or "🔴 {name} is LIVE!")
    message = str(gs.get("message") or "{name} just went live on {platform}. Come hang out!")
    name = str(source.get("name") or "Streamer")
    platform = PLATFORMS.get(source.get("platform"), source.get("platform", "live"))
    title = title.replace("{name}", name).replace("{platform}", platform)
    message = message.replace("{name}", name).replace("{platform}", platform)
    color_raw = str(gs.get("color") or "9146FF").replace("#", "")
    try:
        color = int(color_raw, 16)
    except ValueError:
        color = 0x9146FF
    embed = discord.Embed(title=title[:256], description=message[:4096], url=str(source.get("url")), color=max(0, min(color, 0xFFFFFF)))
    if meta.get("image") or source.get("image"):
        embed.set_image(url=str(meta.get("image") or source.get("image")))
    embed.set_footer(text=f"Red Sentinel • {platform} live alert")
    mention = bool(source.get("mention_everyone", False))
    content = "@everyone" if mention else None
    await channel.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=mention))
    await self._log_event(guild, "social.livestream", channel=channel, payload={"provider": source.get("platform"), "source_id": source.get("id"), "name": name, "url": source.get("url"), "status": "live"})
    return True


async def _monitor_once(self):
    sources = await self.config.stream_sources()
    if not isinstance(sources, dict):
        sources = {}
    changed = False
    for gid, items in list(sources.items()):
        try:
            guild = self.bot.get_guild(int(gid))
        except (TypeError, ValueError):
            guild = None
        if not guild:
            continue
        for source in list(items or []):
            if not source.get("enabled", True):
                continue
            live, meta = await _check_source(self, source)
            source["last_checked"] = int(time.time())
            source["last_status"] = meta.get("status")
            source["last_error"] = meta.get("error", "")
            if meta.get("title"):
                source["last_title"] = meta["title"]
            if meta.get("image"):
                source["last_image"] = meta["image"]
            if live is None:
                changed = True
                continue

            was_live = bool(source.get("live", False))
            initialized = bool(source.get("initialized", False))
            source["live"] = live
            source["status"] = "live" if live else "offline"
            source["initialized"] = True
            if not initialized:
                # If a source is added while already live, notify once immediately.
                # On restart, initialized/live are persisted so we do not duplicate.
                if live:
                    try:
                        await _send_live_alert(self, guild, source, meta)
                        source["last_alert"] = int(time.time())
                    except Exception as exc:
                        source["last_error"] = f"alert: {type(exc).__name__}: {exc}"
                changed = True
            elif live and not was_live:
                try:
                    await _send_live_alert(self, guild, source, meta)
                    source["last_alert"] = int(time.time())
                    source["last_error"] = ""
                except Exception as exc:
                    source["last_error"] = f"alert: {type(exc).__name__}: {exc}"
                changed = True
            else:
                changed = True
        sources[gid] = items
    if changed:
        await self.config.stream_sources.set(sources)


async def stream_loop(self):
    await asyncio.sleep(5)
    while True:
        try:
            await _monitor_once(self)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            try:
                import logging
                logging.getLogger("red_sentinel").exception("livestream monitor iteration failed: %s", exc)
            except Exception:
                pass
        try:
            delay = int(await self.config.social_poll_seconds())
        except Exception:
            delay = 60
        await asyncio.sleep(max(30, min(delay, 300)))


async def api_streams(self, request):
    try:
        gid = int(request.match_info["guild_id"])
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid guild id.")
    guild = self.bot.get_guild(gid)
    if not guild:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild)
    try:
        self.config.register_global(stream_sources={}, stream_settings={})
    except Exception:
        pass
    try:
        data = await self.config.stream_sources()
    except Exception:
        data = {}
    try:
        settings = await self.config.stream_settings()
    except Exception:
        settings = {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(settings, dict):
        settings = {}
    return web.json_response({"sources": data.get(str(gid), []) or [], "settings": settings.get(str(gid), {}) or {}})


async def api_streams_save(self, request):
    try:
        gid = int(request.match_info["guild_id"])
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid guild id.")
    guild = self.bot.get_guild(gid)
    if not guild:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild)
    data = await request.json()
    try:
        self.config.register_global(stream_sources={}, stream_settings={})
    except Exception:
        pass
    try:
        sources = await self.config.stream_sources()
    except Exception:
        sources = {}
    all_sources = dict(sources) if isinstance(sources, dict) else {}
    current = list(all_sources.get(str(gid), []))
    action = str(data.get("action", ""))
    if action == "add":
        url = str(data.get("url", "")).strip()
        name = str(data.get("name", "")).strip()
        platform = _platform(url, str(data.get("platform", "twitch")))
        if not url.startswith(("https://", "http://")):
            raise web.HTTPBadRequest(text="A valid livestream URL is required.")
        try:
            channel = guild.get_channel(int(str(data.get("channel_id") or "0")))
        except Exception:
            channel = None
        if not isinstance(channel, discord.TextChannel):
            raise web.HTTPBadRequest(text="Invalid Discord text channel.")
        source = {
            "id": secrets.token_hex(8),
            "platform": platform,
            "name": _name(url, name),
            "url": url,
            "channel_id": str(channel.id),
            "title": str(data.get("title", ""))[:256],
            "image": str(data.get("image", ""))[:1000],
            "mention_everyone": bool(data.get("mention_everyone", False)),
            "enabled": True,
            "live": False,
            "status": "offline",
            "initialized": False,
            "last_checked": 0,
            "last_error": "",
        }
        current.append(source)
    elif action == "delete":
        current = [x for x in current if str(x.get("id")) != str(data.get("id"))]
    elif action == "toggle":
        for x in current:
            if str(x.get("id")) == str(data.get("id")):
                x["enabled"] = not bool(x.get("enabled", True))
    elif action == "check":
        source = next((x for x in current if str(x.get("id")) == str(data.get("id"))), None)
        if not source:
            raise web.HTTPNotFound(text="Livestream source not found.")
        live, meta = await _check_source(self, source)
        source["last_checked"] = int(time.time())
        source["last_status"] = meta.get("status")
        source["last_error"] = meta.get("error", "")
        if meta.get("title"):
            source["last_title"] = meta["title"]
        if meta.get("image"):
            source["last_image"] = meta["image"]
        if live is not None:
            source["live"] = live
            source["status"] = "live" if live else "offline"
            source["initialized"] = True
    else:
        raise web.HTTPBadRequest(text="Unknown livestream action.")
    all_sources[str(gid)] = current
    await self.config.stream_sources.set(all_sources)
    return web.json_response({"ok": True, "sources": current})


async def api_stream_settings(self, request):
    try:
        gid = int(request.match_info["guild_id"])
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid guild id.")
    guild = self.bot.get_guild(gid)
    if not guild:
        raise web.HTTPNotFound(text=f"Guild not available to the running bot: {gid}")
    await self._require_admin(request, guild)
    data = await request.json()
    try:
        self.config.register_global(stream_sources={}, stream_settings={})
    except Exception:
        pass
    try:
        settings = await self.config.stream_settings()
    except Exception:
        settings = {}
    all_settings = dict(settings) if isinstance(settings, dict) else {}
    all_settings[str(gid)] = {
        "title": str(data.get("title") or "🔴 {name} is LIVE!")[:256],
        "message": str(data.get("message") or "{name} just went live on {platform}. Come hang out!")[:4096],
        "color": str(data.get("color") or "9146FF").replace("#", "")[:6],
        "dedupe": bool(data.get("dedupe", True)),
    }
    await self.config.stream_settings.set(all_settings)
    return web.json_response({"ok": True, "settings": all_settings[str(gid)]})


def patch_streams(RedSentinel):
    original_load = RedSentinel.cog_load
    original_unload = RedSentinel.cog_unload

    async def load(self):
        result = await original_load(self)
        try:
            self.config.register_global(stream_sources={}, stream_settings={})
        except Exception:
            pass
        self.stream_task = asyncio.create_task(stream_loop(self), name="red-sentinel-stream-monitor")
        return result

    async def unload(self):
        task = getattr(self, "stream_task", None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return await original_unload(self)

    RedSentinel.cog_load = load
    RedSentinel.cog_unload = unload
    RedSentinel.api_streams = api_streams
    RedSentinel.api_streams_save = api_streams_save
    RedSentinel.api_stream_settings = api_stream_settings
