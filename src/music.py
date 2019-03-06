import discord
from discord.ext import commands
import youtube_dl
from os import listdir
import asyncio  #for song_queue


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = None
        self.audio_streamer = None
        self.default_volume = 1.0
        self.song_queue = asyncio.Queue() #maxsize = 0
        #self.playing = False

    @commands.command()
    async def join(self, ctx):
        await self.joinChannel(ctx)

    async def joinChannel(self, ctx):  #must this be its own method?
        '''Join the invoking player's voice channel.'''
        try:
            self.vc = await ctx.message.author.voice.channel.connect() #weird things happen when window is x'ed out
        except:
            print("Player already connected.")

    @commands.command()
    async def leave(self, ctx):
        '''Leave the voice channel.'''
        if self.vc is not None:
            await self.vc.disconnect()

    @commands.command()
    async def play(self, ctx, url):
        '''Plays a downloaded song via FFMPEG, downloading it via youtube_dl.'''
        #songlist = listdir('..\\music_cache')
        #print('\nSongs in music_cache: ', songlist, '\n')
        # TODO check if the song is already downloaded
        await ctx.message.add_reaction("\U000023F3") #hourglass not done
        path = await MusicCog.download(url)
        await self.joinChannel(ctx)
        if self.vc.is_playing():
            return await ctx.send('Player already in use.')
        self.audio_streamer = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path), volume = self.default_volume)
        self.vc.play(self.audio_streamer)
        await ctx.message.remove_reaction("\U000023F3", ctx.me) #hourglass not done
        await ctx.message.add_reaction("\U00002705") #white heavy check mark

    @staticmethod
    async def download(url):
        '''Downloads the video using ytdl, returns file path as a string.'''
        ytdl_opts = {
        'quiet' : True,
        #'logger' : 'the logger'
        'format' : 'bestaudio/best',
        'outtmpl' : '..\\music_cache\\%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ytdl_opts) as ydl:
            info_dict = ydl.extract_info(url)
            print('Downloaded ', info_dict['title'] + '.webm successfully.')
            return "..\\music_cache\\" + info_dict['title'] + '.webm'

    @commands.command()
    async def pause(self, ctx):
        self.vc.pause()
        await ctx.message.add_reaction("\U000023F8") #pause button

    @commands.command(aliases = ["res"])
    async def resume(self, ctx):
        self.vc.resume()
        await ctx.message.add_reaction("\U000025B6") #play button

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
            await ctx.send('Volume set at ' + str(int(self.audio_streamer.volume) * 100) + '.')


def setup(bot):
    bot.add_cog(MusicCog(bot))
    #bot.add_cog(MusicCommands(bot))
