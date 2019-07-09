import discord
from discord.ext import commands
import datetime
import configloader as cfload
import praw, random
import subprocess
from logger import Logger as log

cfload.read('..\\config.ini')
log.info(cfload.configSectionMap("Owner Credentials")['owner_id'], "is the owner. Only this user can use /shutdown.")

class Commands(commands.Cog):
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'Pong! ({round(self.bot.latency, 2)} ms)')

    @commands.command(aliases = ['clean', 'purge', 'clear'])
    async def prune(self, ctx, n = 1):
        '''Deletes a number n of messages.'''
        n = abs(n)
        if n > Commands.prune_cutoff:
            await ctx.channel.send("You can only delete up to 25 messages at a time.")
            return
        log.debug(f"Purging {n + 1} message(s)...") #accounts for command invoke
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
            await ctx.message.add_reaction('\U0000274C') #Cross mark
            await ctx.send("You can't shut me down.", delete_after=15)


    @commands.command()
    async def meme(self, ctx, subreddit='dankmemes'): #TODO fix gif playback
        """Gets a random meme from reddit and posts it.
        Specify a subreddit to get a post from (actually works with any sub). Default is r/dankmemes."""
        #Load the reddit login and bot credentials from config.ini
        credentials = cfload.configSectionMap("Reddit API")

        await ctx.message.add_reaction("\U0000231B")  # hourglass done (not actually done)

        r = praw.Reddit(client_id=credentials['client_id'],
                           client_secret=credentials['client_secret'],
                           user_agent=credentials['user_agent'],
                           username=credentials['username'],
                           password=credentials['password'])
        try:
            sub = r.subreddit(subreddit)
            if sub.over18:
                return await ctx.message.add_reaction("\U0001F6AB") #Prohibited
            posts = sub.hot(limit=100)
            rand = random.randint(0, 100)
            for i, post in enumerate(posts):
                if i == rand:
                    #Create the embed
                    embed = discord.Embed(
                        title=post.title, #TODO add subreddit link somewhere, maybe use add fields
                        url='http://www.reddit.com' + post.permalink,
                        # description=post.name,
                        colour=discord.Colour(0xe7d066)
                    )
                    embed.set_image(url=post.url)
                    embed.set_author(
                        name= 'u/' + str(post.author),
                        url='http://www.reddit.com/user/' + str(post.author),
                        icon_url=post.author.icon_img
                    )
                    if post.selftext is not '': #If the post is a text post
                        description = (post.selftext[:1021] + '...') if len(post.selftext) > 1024 else post.selftext
                        embed.add_field(
                            name=str(post.score) + ' points',
                            value=description
                        )
                    else: #If the post is a link post
                        embed.add_field(
                            name='Score:',
                            value=post.score,
                            inline=True
                        )
                        embed.add_field(
                            name='Comments:',
                            value=len(post.comments),
                            inline=True
                        )
                    embed.set_footer(
                        text='r/' + str(post.subreddit),
                        icon_url='https://styles.redditmedia.com/t5_6/styles/communityIcon_a8uzjit9bwr21.png'
                    )

                    await ctx.send(embed=embed)

        except Exception as e:
            await ctx.message.add_reaction("\U0000274C") #Cross mark
            log.error('Exception in /meme:', e)
        finally:
            await ctx.message.remove_reaction('\U0000231B', ctx.me)

# embed = discord.Embed(title="Post Title", colour=discord.Colour(0xe7d066), url="https://reddit.com", description="Post Description", timestamp=datetime.datetime.utcfromtimestamp(1561002414))
#
# embed.set_image(url="https://i.redd.it/eflnf3szq6531.png")
# embed.set_author(name="author name", url="https://discordapp.com", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
# embed.set_footer(text="Reddit", icon_url="https://styles.redditmedia.com/t5_6/styles/communityIcon_a8uzjit9bwr21.png")


def setup(bot):
    bot.add_cog(Commands(bot))
