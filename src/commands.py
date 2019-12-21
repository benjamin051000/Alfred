import discord
from discord.ext import commands
import configloader as cfload
import praw, random
from logger import Logger as log
import qrcode
from io import BytesIO

cfload.read('..\\config.ini')
log.info(cfload.configSectionMap("Owner Credentials")['owner_id'], "is the owner. Only this user can use /shutdown.")

class Commands(commands.Cog):
    """Various commands"""
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'Pong! ({round(self.bot.latency, 2)} ms)')

    @commands.command(aliases=['clean', 'purge', 'clear'])
    async def prune(self, ctx, n=1):
        """Deletes a number n of messages."""
        n = abs(n)
        if n > Commands.prune_cutoff:
            await ctx.channel.send('You can only delete up to 25 messages at a time.')
            return
        log.debug(f'Purging {n + 1} message(s)...')  # Includes the invoking command
        await ctx.message.remove_reaction("\U000023F3", ctx.me)  # Hourglass not done
        await ctx.channel.purge(limit=n + 1)

        title = f'{ctx.message.author} deleted {n} message'
        title += 's!' if n > 1 else '!'
        embed = discord.Embed(title=title, colour=discord.Colour(0xe7d066))
        await ctx.send(embed=embed)

    @commands.command(aliases=['sd'])
    async def shutdown(self, ctx):
        """Shuts down the bot."""
        if ctx.author.id == int(cfload.configSectionMap('Owner Credentials')['owner_id']):
            await ctx.message.add_reaction('\U0001F50C')  # Power plug emoji
            await self.bot.logout()
        else:
            await ctx.message.add_reaction('\U0000274C')  # Cross mark
            await ctx.send("You can't shut me down.", delete_after=15)

    @commands.command()
    async def meme(self, ctx, subreddit='dankmemes'):  #TODO fix gif playback
        """Gets a random meme from Reddit and posts it.
        Specify a subreddit to get a post from (actually works with any sub). Default is r/dankmemes."""
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
                return await ctx.message.add_reaction("\U0001F6AB")  # Prohibited
            n = 100
            posts = sub.hot(limit=n)
            rand = random.randint(0, n)
            for (i, post) in enumerate(posts):  # TODO try random.choice() for the enumeration
                if i == rand:
                    embed = discord.Embed(
                        title=post.title,  #TODO add subreddit link somewhere, maybe use add fields
                        url='http://www.reddit.com' + post.permalink,
                        # description=post.name,
                        colour=discord.Colour(0xe7d066)
                    )
                    if post.url != 'https://www.reddit.com' + post.permalink:  # It's an image post
                        embed.set_image(url=post.url)
                    embed.set_author(
                        name='u/' + str(post.author),
                        url='http://www.reddit.com/user/' + str(post.author),
                        icon_url=post.author.icon_img
                    )
                    if post.selftext is not '':  #If the post is a text post
                        description = post.selftext[:1021] + '...' if len(post.selftext) > 1024 else post.selftext
                        embed.add_field(
                            name=str(post.score) + ' points',
                            value=description
                        )
                    else:  #If the post is a link post
                        embed.add_field(
                            name='Score:',
                            value=post.score,
                            inline=True
                        )
                        embed.add_field(
                            name='Comments:',
                            value=str(len(post.comments)),
                            inline=True
                        )
                    embed.set_footer(
                        text='r/' + str(post.subreddit),
                        icon_url='https://styles.redditmedia.com/t5_6/styles/communityIcon_a8uzjit9bwr21.png'
                    )

                    await ctx.send(embed=embed)

        except Exception as e:
            await ctx.message.add_reaction("\U0000274C")  # Cross mark
            log.error('Exception in /meme:', e)
        finally:
            await ctx.message.remove_reaction('\U0000231B', ctx.me)

    @commands.command()
    async def qr(self, ctx, *link: str):
        """Generates a QR code from a provided link."""
        link = ' '.join(link)
        img = qrcode.make(link)  # TODO Run in executor # TODO shrink img size (maybe)
        file = BytesIO()
        img.save(file, 'JPEG')  # TODO Run in executor
        file.seek(0)
        url = link if 'http://' in link else 'http://' + link
        await ctx.send(url, file=discord.File(file, 'qr.jpeg'))

    @commands.command(aliases=['ms'])
    async def minesweeper(self, ctx, width: int = 5, height: int = 5, mines: int = 5, debug=None):
        """Plays minesweeper. Specify the width and height of the board, and the number of mines.
        Debug reveals all tiles. Default board is a 5x5 with 5 mines."""
        # Check for invalid input
        if width <= 0 or height <= 0 or mines <= 0:
            await ctx.send('Please enter width, height, and number of mines greater than zero.', delete_after=10)
            return

        # Max board that doesn't break is 13x13. TODO restrict this? max len is 2048 chars
        minefield = [[0 for h in range(height)] for w in range(width)]

        for i in range(mines):
            while True:  # TODO consider replacing with random.choice() for the lists
                # Find an empty space and place a mine there
                x, y = random.randint(0, width - 1), random.randint(0, height - 1)
                if minefield[x][y] != 'M':
                    minefield[x][y] = 'M'
                    break
        # Mark the other ones
        for x in range(width):
            for y in range(height):
                if minefield[x][y] != 'M':
                    total_mines = 0
                    # Check the 8 tiles around it
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            if 0 <= x + dx < width and 0 <= y + dy < height:
                                total_mines += int(minefield[x + dx][y + dy] == 'M')
                    minefield[x][y] = total_mines

        # Convert the numbers to emoji
        for x in range(width):
            for y in range(height):
                if minefield[x][y] == 'M':
                    minefield[x][y] = '\U0001F4A3'
                else:
                    # Convert the number to its proper keycap emoji variant
                    minefield[x][y] = f'\\U0000003{str(minefield[x][y])}\\U0000FE0F\\U000020E3'.encode().decode('unicode-escape')

        # Create string to send
        text_field = 'Minesweeper:\n'
        spoiler = lambda s: '||' + s + '||'

        for x in range(width):
            for y in range(height):
                text_field += spoiler(minefield[x][y]) if not debug == '1' else minefield[x][y]
                text_field += ' '
            text_field += '\n'

        await ctx.send(text_field)


def setup(bot):
    bot.add_cog(Commands(bot))
