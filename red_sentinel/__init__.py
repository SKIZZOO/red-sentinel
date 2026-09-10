from .red_sentinel import RedSentinel

async def setup(bot):
    await bot.add_cog(RedSentinel(bot))
