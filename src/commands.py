import discord
from discord.ext import commands
import datetime


class CommandsCog(commands.Cog):
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong! ({} ms)".format(round(self.bot.latency, 2)))

    @commands.command(aliases = ["clean", "purge"])
    async def prune(self, ctx, n = 1):
        """Deletes a number n of messages."""
        n = abs(n)
        if n > CommandsCog.prune_cutoff:
            await ctx.channel.send("You can only delete up to 25 messages at a time.")
            return
        print(f"Purging {n + 1} message(s)...") #accounts for command invoke
        await ctx.message.remove_reaction("\U000023F3", ctx.me) #hourglass not done
        await ctx.channel.purge(limit = n + 1)
        embed = discord.Embed(title = f'{ctx.message.author} purged {n} messages!', colour = discord.Colour(0xe7d066))
        embed.set_footer(text = f"Messages purged at {datetime.datetime.now()}") # TODO round off seconds!
        await ctx.send(embed = embed)

    @commands.command()
    async def shutdown(self, ctx):
        """Shuts down the bot."""
        if ctx.author.id == 176384928672514050: # TODO put ID in config file
            await ctx.message.add_reaction("\U0001F50C") #power plug emoji
            await self.bot.logout()
        else:
            await ctx.send("You can't shut me down.")

def setup(bot):
    bot.add_cog(CommandsCog(bot))
