import datetime
import glob
import os
from asyncio import TimeoutError
from collections import deque
from functools import partial

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

import configloader as cfload
from logger import Logger as log


class MusicActivity:
    """Represents a Discord Activity that allows the
    bot to change its Activity presence to the song
    it is listening to."""

    class Status(discord.Enum):
        PLAYING = 1
        PAUSED = 2
        STOPPED = 3

    def __init__(self, bot):
        self.bot = bot
        self.activity = discord.Activity()

    async def change_act(self, status, source=None):
        if status == MusicActivity.Status.PLAYING:
            self.playing(source)
        elif status == MusicActivity.Status.STOPPED:
            self.activity = discord.Activity()  # Resets activity

        await self.bot.change_presence(activity=self.activity)
        log.debug('Updated bot presence.')

    def playing(self, source):
        self.activity.type = discord.ActivityType.listening
        self.activity.name = source.data['title']
        # self.activity.details = "test details section" # Doesn't work with the current Discord API


class UserCanceledDownloadError(Exception):
    """ Custom Error for handling when a user cancels the downloading of a YTDLSource. """
    pass


class YTDLSource:  # TODO subclass to PCMVolumeTransformer? (like that noob in the help server did)

    ytdl_opts = {
        'default_search': 'auto',
        'noplaylist': True,
        'quiet': True,
        # 'logger' : 'the logger'
        'format': 'bestaudio/best',
        'restrictfilenames': True,
        'outtmpl': '../music_cache/%(extractor)s-%(title)s.%(ext)s',
    }

    """ The maximum duration a video can be before Alfred asks you to confirm you want to download a long video. """
    CUTOFF_DURATION = 7200

    def __init__(self, query, data, path):
        self.query = query
        self.data = data
        self.path = path

    @classmethod
    async def create(cls, ctx: commands.Context, query):
        """ Creates and returns a YTDLSource object, which represents audio content
         from YouTube. """
        query = ' '.join(query)

        with YoutubeDL(cls.ytdl_opts) as ydl:

            await ctx.message.add_reaction("🔍")

            search_func = partial(ydl.extract_info, url=query, download=False)
            info = await ctx.bot.loop.run_in_executor(None, search_func)

            if 'entries' in info:  # Grab the first video.
                info = info['entries'][0]

            confirmation_msg = None

            # Check the duration
            if info['duration'] > cls.CUTOFF_DURATION:
                fduration = datetime.timedelta(seconds=info['duration'])
                confirmation_msg = await ctx.send(f'This video is {fduration} long. Are you sure you want to play it?')

                for emoji in '✅❌':
                    await confirmation_msg.add_reaction(emoji)

                def check_confirmation(reaction, user):
                    if user == reaction.message.author:
                        return False
                    return reaction.message.id == confirmation_msg.id and (reaction.emoji) in '✅❌'

                try:
                    reaction, user = await ctx.bot.wait_for('reaction_add', timeout=30, check=check_confirmation)
                except TimeoutError:
                    # After 30 seconds, trigger a timeout.
                    await confirmation_msg.delete()
                    raise TimeoutError('Confirmation to download content timed out.')

                if str(reaction.emoji) == '❌':
                    await confirmation_msg.delete()
                    raise UserCanceledDownloadError('Content download canceled by user.')

            if confirmation_msg:
                await confirmation_msg.delete()

            await ctx.message.remove_reaction('🔍', ctx.me)
            await ctx.message.add_reaction('⌛')

            # Download the video
            download_func = partial(ydl.extract_info, url=info['webpage_url'])
            # Interesting observation: Songs may play out of order depending on how long it takes them to download.
            download_data = await ctx.bot.loop.run_in_executor(None, download_func)
            path = ydl.prepare_filename(download_data)

            await ctx.message.remove_reaction('🔍', ctx.me)  # TODO might throw
            await ctx.message.remove_reaction('⌛', ctx.me)
            await ctx.message.add_reaction('✅')

        return cls(query, download_data, path)


class MusicPlayer:
    """Controls voice clients. Each guild gets its own queue and voice client."""

    default_volume = 0.5

    def __init__(self, bot, guild_id):
        self.guild_id = guild_id
        self.bot = bot
        self.queue = deque()
        self.vc = None
        self.audio_streamer = None
        # 0-1. Default volume to preserve volume across songs.
        self.volume = MusicPlayer.default_volume
        self.activity = MusicActivity(self.bot)
        self.current_source = None

    def music_loop(self, ctx):
        """Streams the next YTDLSource in self.queue."""
        # If the queue is empty, destroy the player.
        if not self.queue:
            self.bot.loop.create_task(self.activity.change_act(MusicActivity.Status.STOPPED, None))
            self.bot.loop.create_task(Music.destroy_player(self.guild_id))
            return

        self.current_source = self.queue.popleft()
        # PCMVolumeTransformer allows the volume to be changed.
        self.audio_streamer = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.current_source.path), volume=self.volume)
        # Play the audio. This has a recursive call to pop the next song until the queue is empty.
        self.vc.play(self.audio_streamer, after=lambda e: self.music_loop(ctx))
        log.debug('Now playing', self.current_source.data['title'])

        self.bot.loop.create_task(self.activity.change_act(MusicActivity.Status.PLAYING, self.current_source))


class Music(commands.Cog):
    """Music-related commands."""

    # Represents guild-specific music clients.
    players = {}

    def __init__(self, bot, owner_id):
        self.bot = bot
        self.owner_id = owner_id

    def get_player(self, ctx):
        """Gets a guild's music player.
        If it doesn't exist, generates a new one."""
        try:
            player = Music.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(self.bot, ctx.guild.id)
            Music.players[ctx.guild.id] = player
            log.debug('Created new MusicPlayer for guild', str(ctx.guild.id))
        return player

    @classmethod
    async def destroy_player(cls, guild_id):
        """Destroys a guild's player. Disconnects from the channel
        and deletes the player entry in Music.players."""
        if cls.players[guild_id].vc is not None:
            await cls.players[guild_id].vc.disconnect()
        del cls.players[guild_id]
        log.debug('Destroyed', str(guild_id) + '\'s MusicPlayer.')

    @commands.command()
    async def join(self, ctx):
        await self.joinChannel(ctx)

    async def joinChannel(self, ctx, player=None):
        """Join the invoking user's voice channel."""
        player = player or self.get_player(ctx)

        try:
            player.vc = await ctx.author.voice.channel.connect()
        except discord.errors.ClientException:
            log.info('Player already connected.')

    @commands.command()
    async def leave(self, ctx):
        """Leave the voice channel, clear the queue."""
        player = self.get_player(ctx)
        await Music.destroy_player(player.guild_id)
        await self.activity.change_act(MusicActivity.Status.STOPPED, None)

    @commands.command(aliases=['q'])
    async def queue(self, ctx):  # TODO add links to queues, improve embed functionality and UI
        """Displays the song queue."""
        player = self.get_player(ctx)

        embed = discord.Embed(title='Song Queue', colour=discord.Colour(0xe7d066))  # Yellow
        if len(player.queue) == 0:
            await ctx.send('Nothing is enqueued. Play a song with /play', delete_after=10)
        else:
            for p in player.queue:
                embed.add_field(name=p.data['title'], value='_'*10, inline=False)
            await ctx.send(embed=embed)

    @commands.command()
    async def play(self, ctx, *query):
        """Play a song."""
        await self.playsong(ctx, *query)

    @commands.command()
    async def playnext(self, ctx, *query):
        """Skip the line! Play a song immediately after the currently playing song."""
        await self.playsong(ctx, *query, up_next=True)

    async def playsong(self, ctx, *query, up_next=False):
        """ Creates a YTDL source for the query, adds it to the queue, and starts the music loop. """
        player = self.get_player(ctx)

        # Make sure the user actually searched something
        if not query:
            return await ctx.message.add_reaction("❓")

        await self.joinChannel(ctx, player)

        # Add the YTDLSource to the queue, either up front or in the back
        try:
            source = await YTDLSource.create(ctx, query)
        except TimeoutError:
            # User took too long to respond to the confirmation message. By default, the track is not downloaded.
            await ctx.message.remove_reaction("\U0000231B", ctx.me)  # hourglass done
            await ctx.message.add_reaction('⏰')
            return
        except UserCanceledDownloadError:
            await ctx.message.remove_reaction("\U0000231B", ctx.me)  # hourglass done (not actually done)
            await ctx.message.add_reaction('🚫')
            return

        if up_next:
            player.queue.appendleft(source)
        else:
            player.queue.append(source)

        if not player.vc.is_playing() and not player.vc.is_paused():
            # Start the music loop.
            player.music_loop(ctx)

        await ctx.message.remove_reaction("\U0000231B", ctx.me)  # hourglass done
        await ctx.message.add_reaction("\U00002705")  # white heavy check mark (green in discord)

    @commands.command()
    async def pause(self, ctx):
        player = self.get_player(ctx)
        player.vc.pause()
        await ctx.message.add_reaction("\U000023F8")  # pause button

    @commands.command(aliases=["res"])
    async def resume(self, ctx):
        player = self.get_player(ctx)
        player.vc.resume()
        await ctx.message.add_reaction("\U000025B6")  # play button

    @commands.command()
    async def skip(self, ctx):
        player = self.get_player(ctx)
        player.vc.stop()
        await ctx.message.add_reaction("\U000023ED")  # next track button

    @commands.command(aliases=["vol"])
    async def volume(self, ctx, vol=None):
        player = self.get_player(ctx)
        if vol:
            try:
                # Limit the volume between 0 and 100.
                new_vol = max(min(100., float(vol)), 0.)  # TODO do these need to be floats?
            except ValueError:
                log.debug('Volume must be a float.')
                return await ctx.message.add_reaction('❓')

            player.volume = new_vol / 100
            player.audio_streamer.volume = player.volume
            emoji = '🔈' if player.volume == 0 else '🔊'
            await ctx.message.add_reaction(emoji)  # white heavy check mark (green in Discord)
        else:
            await ctx.send(f'Volume currently set to {int(player.audio_streamer.volume * 100)}%.', delete_after=10)

    @commands.command()
    async def clearcache(self, ctx):
        """ ADMIN COMMAND: Clear music cache. """
        if ctx.author.id == self.owner_id:
            await ctx.send('You can\'t use this command.', delete_after=5)
            return
        try:
            music_files = glob.glob('../music_cache/*')
            print('Files to be removed:', music_files)
            for file in music_files:
                os.remove(file)
            await ctx.message.add_reaction('🗑')
        except Exception as e:
            await ctx.add_reaction('⚠')
            raise e


def setup(bot):
    admin_id = cfload.configSectionMap('Owner Credentials')['owner_id']
    bot.add_cog(Music(bot, admin_id))
