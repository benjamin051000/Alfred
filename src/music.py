import discord
from discord.ext import commands
import youtube_dl
from collections import deque
from enum import Enum
import asyncio

class MusicActivity(commands.Cog): # TODO rich presence
    class Status(Enum):
        PLAYING = 1
        PAUSED = 2
        STOPPED = 3

    def __init__(self, bot):
        self.bot = bot
        self.activity = discord.Activity()
        # self.bot.change_presence(activity=self.activity)

    async def change_activity(self, status, ytdl_info=None):
        if status == MusicActivity.Status.PLAYING:
            self.playing(ytdl_info)
        elif status == MusicActivity.Status.PAUSED:
            pass
        elif status == MusicActivity.Status.STOPPED:
            self.activity = discord.Activity() # remove activity from pane

        await self.bot.change_presence(activity=self.activity)
        print('updated bot presence.')

    def playing(self, info_dict):
        #print(info_dict)
        self.activity.type = discord.ActivityType.listening
        self.activity.name = info_dict['title']

    def paused(self, info_dict):
        pass




############################################
class MusicCog(commands.Cog):

    ytdl_opts = { #move to higher scope?
    'quiet' : True,
    #'logger' : 'the logger'
    'format' : 'bestaudio/best',
    'outtmpl' : '..\\music_cache\\%(title)s.%(ext)s',
    }

    def __init__(self, bot):
        self.bot = bot
        self.vc = None
        self.audio_streamer = None
        self.default_volume = 0.5
        self.queue = deque([])
        self.songinfo = {}
        self.now_playing_pane = MusicActivity(bot)

    @commands.command()
    async def join(self, ctx):
        await self.joinChannel(ctx)

    async def joinChannel(self, ctx):
        '''Join the invoking player's voice channel.'''
        try:
            self.vc = await ctx.message.author.voice.channel.connect()
        except:
            print("Player already connected.")

    @commands.command()
    async def leave(self, ctx):
        '''Leave the voice channel.'''
        if self.vc is not None:
            await self.vc.disconnect()


    @commands.command()
    async def queue(self, ctx): # TODO implement in discord in human-readable way, embed
        '''Displays the queue.'''
        await ctx.send(str(self.queue))
        #print(self.queue)

    @commands.command()
    async def play(self, ctx, url):
        '''Play a song via url.'''
        await ctx.message.add_reaction("\U000023F3") #hourglass not done
        await self.joinChannel(ctx)
        # TODO check if the song is already downloaded (maybe), faster caching? May fix download bug
        path, info = await MusicCog.download(url)
        self.songinfo[path] = info
        self.queue.append(path)
        print('Enqueued {}'.format(path))
        # Begin playing if we aren't already.
        if not self.vc.is_playing():
            self.playNext(ctx)

        await ctx.message.add_reaction("\U00002705") #white heavy check mark (green background in discord)
        await ctx.message.remove_reaction("\U000023F3", ctx.me) #remove hourglass not done


    def playNext(self, ctx): # TODO: Add optional path for downloaded stuff?
        '''Streams the next enqueued path in self.queue.'''
        if not self.queue:
            asyncio.run_coroutine_threadsafe(self.now_playing_pane.change_activity(MusicActivity.Status.STOPPED, None), self.bot.loop) #update the activity
            print('The audio queue is empty.')
            return

        path = self.queue.popleft()
        self.audio_streamer = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path), volume = self.default_volume)
        self.vc.play(self.audio_streamer, after = lambda e : self.playNext(ctx))
        asyncio.run_coroutine_threadsafe(self.now_playing_pane.change_activity(MusicActivity.Status.PLAYING, self.songinfo[path]), self.bot.loop) #update the activity
        print('playing', path)


    @staticmethod
    async def download(url): # TODO BUG can't use \ / in file name
        #'''Downloads the video using ytdl. Returns file path as a string.'''
        # ytdl_opts = { #move to higher scope?
        # 'quiet' : True,
        # #'logger' : 'the logger'
        # 'format' : 'bestaudio/best',
        # 'outtmpl' : '..\\music_cache\\%(title)s.%(ext)s',
        # }
        with youtube_dl.YoutubeDL(MusicCog.ytdl_opts) as ydl:
            info_dict = ydl.extract_info(url) # TODO BUG if streaming a song, and the same song is requested, error. may be m4a issue?
            print('Downloaded ', info_dict['title'] + ' successfully.')
            return ("..\\music_cache\\" + info_dict['title'] + '.' + info_dict['ext'], info_dict)

    @commands.command()
    async def pause(self, ctx):
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
                self.audio_streamer.volume = float(input) / 100
                await ctx.message.add_reaction("\U00002705") #white heavy check mark
            except:
                print('Volume must be a float.')
                return await ctx.message.add_reaction("\U00002753") #question mark
        else:
            await ctx.send('Volume set to ' + str(int(self.audio_streamer.volume * 100)) + '%.')#broken when below 100%


def setup(bot):
    bot.add_cog(MusicCog(bot))
    bot.add_cog(MusicActivity(bot))
