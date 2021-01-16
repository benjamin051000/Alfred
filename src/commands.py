"""
A file containing several classes relating to various
miscellaneous commands Alfred features.
"""
import random
from io import BytesIO

import discord
import praw
import qrcode
import requests
from discord.ext import commands

import configloader as cfload
from logger import Logger as log

cfload.read('..\\config.ini')  # TODO maybe move this to the setup function?
log.info(cfload.configSectionMap("Owner Credentials")['owner_id'], "is the owner. Only this user can use /shutdown.")


class Commands(commands.Cog):
    """Various commands"""
    prune_cutoff = 25

    def __init__(self, bot):
        self.bot = bot
        # Set up reddit client
        self.reddit_credentials = cfload.configSectionMap("Reddit API")
        self.reddit = praw.Reddit(client_id=self.reddit_credentials['client_id'],
                                  client_secret=self.reddit_credentials['client_secret'],
                                  user_agent=self.reddit_credentials['user_agent'],
                                  username=self.reddit_credentials['username'],
                                  password=self.reddit_credentials['password'])

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

    @commands.command(aliases=['reddit'])
    async def meme(self, ctx: commands.Context, subreddit='memes'):
        """Gets a random meme from Reddit and posts it.
        Specify a subreddit to get a post from (actually works with any sub). Default is r/dankmemes."""

        await ctx.message.add_reaction('⌛')
        sub = self.reddit.subreddit(subreddit)

        # Restrict NSFW subs
        if sub.over18:
            await ctx.message.add_reaction('🔞')
            return

        # Get posts and choose a random one.
        n = 100  # This could be replaced with a generator, but this is easier and almost never repeats.
        posts = [p for p in sub.hot(limit=n)]
        post = random.choice(posts)

        # Create the embed
        embed = discord.Embed(
            title=post.title,
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
        if post.selftext != '':  # If the post is a text post
            description = post.selftext[:1021] + '...' if len(post.selftext) > 1024 else post.selftext
            embed.add_field(name=str(post.score) + ' points', value=description)

        else:  # If the post is a link post
            embed.add_field(name='Score:', value=post.score, inline=True)
            embed.add_field(name='Comments:', value=str(len(post.comments)), inline=True)

        embed.set_footer(
            text='r/' + str(post.subreddit),
            icon_url='https://styles.redditmedia.com/t5_6/styles/communityIcon_a8uzjit9bwr21.png'
        )

        await ctx.send(embed=embed)

        # Change the reaction
        await ctx.message.remove_reaction('⌛', ctx.me)
        await ctx.message.add_reaction('✅')

    @commands.command()
    async def qr(self, ctx, *link: str):
        """ Generates a QR code from a provided link. Useful
        for quickly sending/picking up information on a non-discord
        device, such as a smartphone. """
        link = ' '.join(link)
        # Create the QR code
        qr = qrcode.QRCode(border=2)  # Shrinks the border a little
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image()
        # Save the qr image in a file.
        file = BytesIO()
        img.save(file, 'JPEG')
        file.seek(0)

        url = link if 'http' in link else 'http://' + link
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
                    minefield[x][y] = f'\\U0000003{str(minefield[x][y])}\\U0000FE0F\\U000020E3'.encode().decode(
                        'unicode-escape')

        # Create string to send
        text_field = 'Minesweeper:\n'
        spoiler = lambda s: '||' + s + '||'

        for x in range(width):
            for y in range(height):
                text_field += spoiler(minefield[x][y]) if not debug == '1' else minefield[x][y]
                text_field += ' '
            text_field += '\n'

        await ctx.send(text_field)

    @commands.command(aliases=['rd'])
    async def rolldice(self, ctx, ndm):
        """ Roll n m-sided die. Format is "/rolldice 2d5" (which will roll 2 d5). If ndm is specified as 'dnd' (or 'd&d')
        (e.g. "/rolldice dnd"), a standard D&D 7-dice set will be rolled, along with a 1d10 for a percentile roll."""

        output = '__Dice roll:__\n'

        if ndm.lower() == 'dnd' or ndm.lower() == 'd&d':
            for d in (4, 6, 8, 10, 10, 12, 20):
                output += f'd{d}: {random.randint(1, int(d))}\n'
        else:

            try:
                n, d = ndm.lower().split('d')
                n = int(n)
                d = int(d)
                if n <= 0 or d <= 0:
                    raise ValueError

                for i in range(1, int(n) + 1):
                    output += f'd{d}: {random.randint(1, int(d))}\n'
            except ValueError:
                await ctx.message.add_reaction("❌")
                return

        await ctx.send(output)

    @commands.command()
    async def pick(self, ctx):
        """ Choose a random member. """
        # Get users and choose a random user
        if ctx.message.mentions:
            user_choices = ctx.message.mentions
        else:
            user_choices = ctx.author.voice.channel.members

        num_users = len(user_choices) - 1
        choice = random.randint(0, num_users)

        # If a bot is chosen, remove it from the list and choose again
        while user_choices[choice].bot:
            user_choices.remove(user_choices[choice])
            num_users = len(user_choices) - 1
            choice = random.randint(0, num_users)

        await ctx.send(f"I randomly chose {user_choices[choice].display_name}.", delete_after=30)


class Dictionary(commands.Cog):
    """ A simple dictionary API. """
    dict_url = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json/'
    thes_url = ''

    def __init__(self, bot, dict_key, thes_key):
        self.bot = bot
        self.dict_key = dict_key  # Dictionary key
        self.thes_key = thes_key  # Thesaurus key

    @commands.command(aliases=['define', 'definition', 'def'])
    async def dictionary(self, ctx, *word):
        """ Gets the definition of a word. """
        formatted_word = ' '.join(word)
        url_word = '%20'.join(word)

        r = requests.get(Dictionary.dict_url + f'{url_word}?key={self.dict_key}')
        resp = r.json()
        try:
            definition = resp[0]['shortdef'][0]
            url = f"https://www.merriam-webster.com/dictionary/{url_word}"
        except Exception:
            word = f'"{formatted_word}" not found.'
            others = ', '.join(resp)
            definition = f'Did you mean:\n{others}'
            url = ''

        embed: discord.Embed = discord.Embed(title=f"{formatted_word.lower()}",
                                             colour=discord.Colour(0xe7d066),
                                             url=url,
                                             description=f"{definition}"
                                             )
        embed.set_footer(text="Merriam-Webster's Collegiate Dictionary")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Commands(bot))

    # Get keys from config file
    cfload.read('../config.ini')
    keys = cfload.configSectionMap('Merriam Webster API')
    bot.add_cog(Dictionary(bot, keys['dictionary_key'], keys['thesaurus_key']))
