import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
from collections import deque
import asyncio
import functools

class MusicActivity: #TODO this wont work anymore :( we have to get rid of it. Rip
    class status(discord.Enum):
        PLAYING = 1
        PAUSED = 2
        STOPPED = 3

    def __init__(self, bot):
        self.bot = bot
        self.activity = discord.Activity()

    async def change_act(self, status, source=None):
        if status == MusicActivity.status.PLAYING:
            self.playing(source)
        elif status == MusicActivity.status.PAUSED:
            pass
        elif status == MusicActivity.status.STOPPED:
            self.activity = discord.Activity() # reset activity

        await self.bot.change_presence(activity=self.activity)
        print('Updated bot presence.')

    def playing(self, source):
        self.activity.type = discord.ActivityType.listening
        self.activity.name = source.data['title']
        # self.activity.details = "test details section" #doesnt work


class YTDLSource: #TODO subclass to PCMVolumeTransformer? like that noob in the help server said to

    ytdl_opts = {
        "default_search": "auto",
        "noplaylist": True,
        'quiet': True,
        # 'logger' : 'the logger'
        'format': 'bestaudio/best',
        'outtmpl': '../music_cache/%(extractor)s-%(id)s-%(title)s.%(ext)s',  # %(title)s.%(ext)s',
    }

    def __init__(self, query):
        self.query = ' '.join(query)
        self.data = {} #Necessary?

        with YoutubeDL(YTDLSource.ytdl_opts) as ydl:
            try:
                self.data = ydl.extract_info(self.query)  # BUG if streaming a song, and the same song is requested, error. Also HTTP Errors.
            except Exception as e:
                print('YTDLException:', e)

            if "entries" in self.data:  # if we get a playlist, grab the first video
                self.data = self.data["entries"][0]
            self.path = ydl.prepare_filename(self.data)


class MusicPlayer:
    """Controls voice clients. Each guild gets its own queue and voice client."""

    default_volume = 0.5

    def __init__(self, bot, guild_id):
        self.guild_id = guild_id
        self.bot = bot
        self.queue = deque()
        self.vc = None
        self.audio_streamer = None
        #Necessary to preserve volue across songs. TODO Should reset after some time
        self.volume = MusicPlayer.default_volume
        self.activity = MusicActivity(self.bot)
        self.current_source = None


    def music_loop(self, ctx):
        """Streams the next YTDLSource."""
        if not self.queue:
            self.bot.loop.create_task(self.activity.change_act(MusicActivity.status.STOPPED, None))
            Music.cleanup_player(self.guild_id) #maybe after a time limit?
            return
        self.current_source = self.queue.popleft() #TODO consider using a list, which also has pop()
        # This could be abbrev'd by subclassing YTDLSource to PCMAudiostreamer, see streamer.py example.
        self.audio_streamer = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.current_source.path), volume=self.volume)
        self.vc.play(self.audio_streamer, after=lambda e : self.music_loop(ctx))
        # print('Now playing', self.current_source.data['title'])

        self.bot.loop.create_task(self.activity.change_act(MusicActivity.status.PLAYING, self.current_source))





class Music(commands.Cog):
    """Music-related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}


    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(self.bot, ctx.guild.id)
            self.players[ctx.guild.id] = player

        return player

    @classmethod
    def cleanup_player(cls, guild_id):
        pass
        # try:
        #     del self.players[guild_id] #ERROR
        # except Exception as e:
        #     print(e)

    @commands.command()
    async def join(self, ctx):
        await self.joinChannel(ctx)


    async def joinChannel(self, ctx, player):
        '''Join the invoking player's voice channel.'''
        player = player or self.get_player(ctx) #is this a thing

        try:
            player.vc = await ctx.message.author.voice.channel.connect()
        except Exception as e:
            print("Player already connected.", e)


    @commands.command()
    async def leave(self, ctx): #TODO add a task that does this automatically so he doesn't hang out forever in the chat
        '''Leave the voice channel.'''
        player = self.get_player(ctx)

        if player.vc is not None:
            await player.vc.disconnect()


    @commands.command()
    async def queue(self, ctx): # TODO add links to queues, make embed helpful
        '''Displays the song queue.'''
        player = self.get_player(ctx)

        embed = discord.Embed(title='Song Queue', colour=discord.Colour(0xe7d066)) #Yellow
        if len(player.queue) == 0:
            await ctx.send("Nothing is enqueued. Play a song with /play", delete_after=10)
            return
        else:
            for p in player.queue:
                embed.add_field(name=p.data['title'], value=None)

        await ctx.send(embed=embed)


    @commands.command()
    async def play(self, ctx, *query):
        '''Play a song.'''
        await self.playsong(ctx, *query)


    @commands.command()
    async def playnow(self, ctx, *query):
        await self.playsong(ctx, next=True, *query)


    async def playsong(self, ctx, next=False, *query):
        player = self.get_player(ctx)

        await ctx.message.add_reaction("\U0000231B")  # hourglass done

        await self.joinChannel(ctx, player)

        if next:
            player.queue.appendleft(YTDLSource(query))
            # Logger.info('Enqueued', player.queue[-1].data['title'])
        else:
            player.queue.append(YTDLSource(query))
            # Logger.info('Enqueued', player.queue[-1].data['title'])

        if not player.vc.is_playing() and not player.vc.is_paused():
            player.music_loop(ctx)

        await ctx.message.remove_reaction("\U0000231B", ctx.me)  # hourglass done
        await ctx.message.add_reaction("\U00002705")  # white heavy check mark (green in discord)
    # @commands.command()
    # async def search(self, ctx, *, search : str):
    #
    #     ydl = YoutubeDL(MusicCog.ytdl_opts)
    #     func = functools.partial(ydl.extract_info, search, download = False)
    #     info = await self.bot.loop.run_in_executor(None, func)
    #     if "entries" in info:
    #         info = info["entries"][0]
    #     # for i in info:
    #     #     print(i, ':', info[i])
    #     await ctx.send(info['webpage_url'])

    @commands.command()
    async def pause(self, ctx): #TODO if paused, /play will skip the song we are paused in. Add an if clause in play command.
        player = self.get_player(ctx)
        player.vc.pause()
        await ctx.message.add_reaction("\U000023F8") #pause button

    @commands.command(aliases = ["res"])
    async def resume(self, ctx):
        player = self.get_player(ctx)
        player.vc.resume()
        await ctx.message.add_reaction("\U000025B6") #play button

    @commands.command()
    async def skip(self, ctx):
        player = self.get_player(ctx)
        player.vc.stop()
        await ctx.message.add_reaction("\U000023ED") # next track button

    @commands.command(aliases = ["vol"])
    async def volume(self, ctx, input = None):
        player = self.get_player(ctx)
        if input is not None:
            try:
                vol = max(min(100, float(input)), 0)
            except:
                print('Volume must be a float.')
                return await ctx.message.add_reaction("\U00002753") #question mark

            player.volume = vol / 100
            player.audio_streamer.volume = player.volume
            await ctx.message.add_reaction("\U00002705")  # white heavy check mark
        else:
            await ctx.send('Volume set to ' + str(int(player.audio_streamer.volume * 100)) + '%.', delete_after=10)

def setup(bot):
    bot.add_cog(Music(bot))