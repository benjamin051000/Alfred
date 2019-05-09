import discord
from discord.ext import commands
import datetime
import configloader as cfload

cfload.read("..\\config.ini")
print(cfload.configSectionMap("Owner Credentials"), "is the owner. Only he can use /shutdown.")

class CommandsCog(commands.Cog):
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong! ({} ms)".format(round(self.bot.latency, 2)))

    @commands.command(aliases = ["clean", "purge"])
    async def prune(self, ctx, n = 1):
        '''Deletes a number n of messages.'''
        n = abs(n)
        if n > CommandsCog.prune_cutoff:
            await ctx.channel.send("You can only delete up to 25 messages at a time.")
            return
        print(f"Purging {n + 1} message(s)...") #accounts for command invoke
        await ctx.message.remove_reaction("\U000023F3", ctx.me) #hourglass not done
        await ctx.channel.purge(limit=n + 1)
        title = f'{ctx.message.author} deleted {n} message'
        title += 's!' if n > 1 else '!'
        embed = discord.Embed(title=title, colour=discord.Colour(0xe7d066))
        await ctx.send(embed=embed)

    @commands.command()
    async def shutdown(self, ctx):
        '''Shuts down the bot.'''
        if ctx.author.id == int(cfload.configSectionMap("Owner Credentials")["owner_id"]):
            await ctx.message.add_reaction("\U0001F50C") #power plug emoji
            await self.bot.logout()
        else:
            await ctx.send("You can't shut me down.")

def setup(bot):
    bot.add_cog(CommandsCog(bot))
