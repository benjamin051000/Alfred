import discord
from discord.ext import commands
import datetime
import configloader as cfload
import praw, random

cfload.read("..\\config.ini")
print(cfload.configSectionMap("Owner Credentials")['owner_id'], "is the owner. Only he can use /shutdown.")

class Commands(commands.Cog):
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong! ({} ms)".format(round(self.bot.latency, 2)))

    @commands.command(aliases = ["clean", "purge"])
    async def prune(self, ctx, n = 1):
        '''Deletes n messages.'''
        n = abs(n)
        if n > Commands.prune_cutoff:
            await ctx.channel.send("You can only delete up to 25 messages at a time.")
            return
        print(f"Purging {n + 1} message(s)...") #accounts for command invoke
        await ctx.message.remove_reaction("\U000023F3", ctx.me) #hourglass not done
        await ctx.channel.purge(limit=n + 1)
        title = f'{ctx.message.author} deleted {n} message'
        title += 's!' if n > 1 else '!'
        embed = discord.Embed(title=title, colour=discord.Colour(0xe7d066))
        await ctx.send(embed=embed)

    @commands.command(aliases=['sd'])
    async def shutdown(self, ctx):
        '''Shuts down the bot.'''
        if ctx.author.id == int(cfload.configSectionMap("Owner Credentials")["owner_id"]):
            await ctx.message.add_reaction("\U0001F50C") #power plug emoji
            await self.bot.logout()
        else:
            await ctx.send("You can't shut me down.")

    @commands.command()
    async def meme(self, ctx):
        """Gets a random meme from reddit and posts it."""
        r = praw.Reddit(client_id='2iDsXiLTxBul9w',
                           client_secret='ZeoMYdHyHYMkEOXYDN7T7WRZyDs',
                           user_agent='Alfred',
                           username='benjamin051000',
                           password='Myst3exile.') #TODO HIDE THIS! (config.ini)
        sub = r.subreddit('bonehurtingjuice')
        posts = sub.hot(limit=100)
        rand = random.randint(0, 100)
        for i, post in enumerate(posts):
            if i == rand:
                await ctx.send(post.url)


def setup(bot):
    bot.add_cog(Commands(bot))
