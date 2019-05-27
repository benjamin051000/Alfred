import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
from collections import deque
from enum import Enum
import asyncio
import functools

class MusicActivity(): #TODO fix
    class Status(Enum):
        PLAYING = 1
        PAUSED = 2
        STOPPED = 3

    def __init__(self, bot):
        self.bot = bot
        self.activity = discord.Activity()

    async def change_activity(self, status, YTDLSource=None):
        if status == MusicActivity.Status.PLAYING:
            self.playing(YTDLSource)
        elif status == MusicActivity.Status.PAUSED:
            pass
        elif status == MusicActivity.Status.STOPPED:
            self.activity = discord.Activity() # reset activity

        await self.bot.change_presence(activity=self.activity)
        print('Updated bot presence.')

    def playing(self, source):
        self.activity.type = discord.ActivityType.listening
        self.activity.name = source.data['title']
        # self.activity.details = "test details section" #doesnt work



class YTDLSource(): #subclass to PCMVolumeTransformer?

    ytdl_opts = {
        "default_search": "auto",
        "noplaylist": True,
        'quiet': True,
        # 'logger' : 'the logger'
        'format': 'bestaudio/best',
        'outtmpl': '..\\music_cache\\%(extractor)s-%(id)s-%(title)s.%(ext)s',  # %(title)s.%(ext)s',
    }

    def __init__(self, query):
        self.query = ' '.join(query)
        self.data = {}
        # self.path = None #is this line necessary?

        with YoutubeDL(YTDLSource.ytdl_opts) as ydl:
            try:
                self.data = ydl.extract_info(self.query)  # BUG if streaming a song, and the same song is requested, error. Also HTTP Errors.
            except Exception as e:
                print('YTDLException:', e)

            if "entries" in self.data:  # if we get a playlist, grab the first video
                self.data = self.data["entries"][0]
            self.path = '../music_cache/' + ydl.prepare_filename(self.data)



class MusicCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.vc = None
        self.audio_streamer = None
        self.default_volume = 0.5
        self.queue = deque() # A queue with TYDLSource objects
        self.now_playing_pane = MusicActivity(bot)
        self.current_song = None

    @commands.command()
    async def join(self, ctx):
        await self.joinChannel(ctx)

    async def joinChannel(self, ctx):
        '''Join the invoking player's voice channel.'''
        # try:
        self.vc = await ctx.message.author.voice.channel.connect()
        # except Exception as e:
            # print("Player already connected.")
            # print(e)

    @commands.command()
    async def leave(self, ctx):
        '''Leave the voice channel.'''
        if self.vc is not None:
            await self.vc.disconnect()

    @commands.command()
    async def queue(self, ctx): # TODO I'm sure this is broken now, also make it look nice
        '''Displays the song queue.'''
        embed = discord.Embed(title='Song Queue', colour=discord.Colour(0xe7d066)) #Yellow
        if len(self.queue) == 0:
            await ctx.send("Nothing is enqueued. Play a song with /play", delete_after=10)
            return
        else:
            for p in self.queue:
                embed.add_field(name=p.data['title'], value=None)

        await ctx.send(embed=embed)

    @commands.command()
    async def play(self, ctx, *query):
        '''Play a song.'''
        await ctx.message.add_reaction("\U0000231B")  # hourglass done

        await self.joinChannel(ctx)

        async with ctx.typing():
            self.queue.append(YTDLSource(query))
            print('Enqueued', self.queue[-1].data['title']) #not sure if I did this correctly


        if not self.vc.is_playing() and not self.vc.is_paused():
            self.playNext(ctx)

        await ctx.message.remove_reaction("\U0000231B", ctx.me)  # hourglass done
        await ctx.message.add_reaction("\U00002705") #white heavy check mark (green in discord)



    def playNext(self, ctx): #TODO make async? Probably not. It's quick
        '''Streams the next YTDLSource.'''
        if not self.queue:
            asyncio.run_coroutine_threadsafe(self.now_playing_pane.change_activity(MusicActivity.Status.STOPPED, None), self.bot.loop) #update the activity
            print('The audio queue is empty.')
            return
        self.current_song = self.queue.popleft()
        #TODO find a way to preserve last song's volume.
        self.audio_streamer = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.current_song.path), volume=self.default_volume) #This could be abbrev'd by subclassing YTDLSource to PCMAudiostreamer, see streamer.py example.
        self.vc.play(self.audio_streamer, after = lambda e : self.playNext(ctx))

        asyncio.run_coroutine_threadsafe(self.now_playing_pane.change_activity(MusicActivity.Status.PLAYING, self.current_song), self.bot.loop)
        # print('playing', nextSong.data['title'])


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
        self.vc.pause()
        await ctx.message.add_reaction("\U000023F8") #pause button

    @commands.command(aliases = ["res"])
    async def resume(self, ctx):
        self.vc.resume()
        await ctx.message.add_reaction("\U000025B6") #play button

    @commands.command()
    async def skip(self, ctx):
        self.vc.stop()
        await ctx.message.add_reaction("\U000023ED") # next track button

    @commands.command(aliases = ["vol"])
    async def volume(self, ctx, input = None):
        if input is not None:
            try:
                vol = max(min(100, float(input)), 0)
            except:
                print('Volume must be a float.')
                return await ctx.message.add_reaction("\U00002753") #question mark

            self.audio_streamer.volume = vol / 100
            await ctx.message.add_reaction("\U00002705")  # white heavy check mark
        else:
            await ctx.send('Volume set to ' + str(int(self.audio_streamer.volume * 100)) + '%.', delete_after=10)

def setup(bot):
    bot.add_cog(MusicCog(bot))