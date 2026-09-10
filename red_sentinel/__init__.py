from .red_sentinel import RedSentinel
from .oauth_setup import SentinelOAuthSetup

async def setup(bot):
    await bot.add_cog(RedSentinel(bot))
    await bot.add_cog(SentinelOAuthSetup(bot))
