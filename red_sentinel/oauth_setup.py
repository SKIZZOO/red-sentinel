from __future__ import annotations

import asyncio
from redbot.core import Config, commands
from redbot.core.bot import Red


class SentinelOAuthSetup(commands.Cog):
    """Private Discord-DM setup helper for Red Sentinel OAuth."""

    def __init__(self, bot: Red):
        self.bot = bot
        # Temporary setup storage. The important config is the RedSentinel cog's
        # config; this helper syncs into it so the API cog can actually read OAuth.
        self.config = Config.get_conf(self, identifier=947281164, force_registration=True)
        self.config.register_global(
            public_base_url="",
            netlify_origin="",
            oauth_client_id="",
            oauth_client_secret="",
            oauth_redirect_uri="",
        )

    def _target_config(self):
        main = self.bot.get_cog("RedSentinel")
        if main is None:
            return None
        return main.config

    async def _sync_to_main(self):
        target = self._target_config()
        if target is None:
            return False
        values = {
            "public_base_url": await self.config.public_base_url(),
            "netlify_origin": await self.config.netlify_origin(),
            "oauth_client_id": await self.config.oauth_client_id(),
            "oauth_client_secret": await self.config.oauth_client_secret(),
            "oauth_redirect_uri": await self.config.oauth_redirect_uri(),
        }
        if not all(values.values()):
            return False
        for key, value in values.items():
            await getattr(target, key).set(value)
        return True

    @commands.command(name="sentineloauth")
    @commands.is_owner()
    async def sentineloauth(self, ctx):
        """Configure Red Sentinel OAuth through a private DM."""
        # If setup was completed previously, repair/sync it into RedSentinel's
        # actual Config instead of making the owner type the secret again.
        if ctx.guild is None and await self._sync_to_main():
            await ctx.send("✅ OAuth settings synchronized to Red Sentinel. Dă `4reload red_sentinel`, apoi testează Login with Discord.")
            return

        if ctx.guild is not None:
            try:
                await ctx.author.send(
                    "🔐 Red Sentinel OAuth setup\n"
                    "Run `4sentineloauth` here in this DM. I will ask for your Client ID and Client Secret privately."
                )
            except Exception:
                await ctx.send("Nu pot să-ți trimit DM. Activează mesajele private și încearcă din nou.", delete_after=10)
            return

        await ctx.send("Trimite acum Discord Client ID.")
        try:
            msg = await self.bot.wait_for(
                "message",
                timeout=180,
                check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id,
            )
            client_id = msg.content.strip()
            try:
                await msg.delete()
            except Exception:
                pass
        except asyncio.TimeoutError:
            await ctx.send("Setup expirat. Rulează din nou `4sentineloauth`.")
            return

        if not client_id.isdigit():
            await ctx.send("Client ID invalid. Rulează din nou `4sentineloauth`.")
            return

        await self.config.oauth_client_id.set(client_id)
        await self.config.oauth_redirect_uri.set("https://red-sentinel.netlify.app/oauth/discord/callback")
        await self.config.netlify_origin.set("https://red-sentinel.netlify.app")
        await self.config.public_base_url.set("https://red-sentinel.netlify.app")
        await ctx.send("Client ID salvat. Trimite acum Client Secret.")

        try:
            msg = await self.bot.wait_for(
                "message",
                timeout=180,
                check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id,
            )
            client_secret = msg.content.strip()
            await self.config.oauth_client_secret.set(client_secret)
            try:
                await msg.delete()
            except Exception:
                pass
        except asyncio.TimeoutError:
            await ctx.send("Setup expirat înainte de Client Secret. Rulează din nou `4sentineloauth`.")
            return

        await self._sync_to_main()
        await ctx.send(
            "✅ Discord OAuth configurat și sincronizat în Red Sentinel. "
            "Dacă mesajul cu secretul nu s-a șters automat, șterge-l manual din DM. "
            "Apoi dă `4reload red_sentinel` și apasă Login with Discord."
        )


async def setup(bot: Red):
    await bot.add_cog(SentinelOAuthSetup(bot))
