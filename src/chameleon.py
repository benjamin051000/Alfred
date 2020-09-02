import asyncio
import enum
import json
import pickle
import random

import discord
from discord.ext import commands

import configloader as cfload


class GameState(enum.Enum):
    init = 0
    lobby = 1
    startgame = 2
    ingame = 3
    voting = 4
    roundover = 5
    cleanup = 6


class Chameleon(commands.Cog):
    """ A discord remake of The Chameleon (card game). """

    MAX_PLAYERS = 8

    def __init__(self, bot, command_prefix):
        self.bot = bot
        #self.command_prefix = command_prefix  # TODO is this ever used?
        self.game_state: GameState = GameState.init
        self.lobby = []  # Holds the names of the people in the lobby.
        self.category = None  # Points to discord.categoryChannel created (NOT in-game category card).
        self.round_winner = None  # Used in voting stage
        self.the_chameleon = None
        self.points = {}  # key: name, val: points
        self.who_got_points = '-'  # Used in points embed to explain who got points.

        self.custom_cards = {}  # Holds custom-made cards. (key:category, val:words)
        self.use_custom_cards = False  # Whether or not to use the custom cards.

        self.guild: discord.Guild = None  # Holds guild ref for color role creation.
        self.color_roles = []  # Holds references to roles created for assignment and deletion.

    @commands.Cog.listener('on_reaction_add')
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        """ Main handler for reaction-based interactions with the game. """
        if user == reaction.message.author:  # which is the bot, or spectators
            return

        if self.game_state == GameState.lobby:
            if reaction.emoji == '➕':
                channel = reaction.message.channel
                if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                    await channel.send(f"Sorry, {user}, the game is full.", delete_after=3)
                else:
                    self.lobby.append(user)
                    await channel.send(f'{user} is in!', delete_after=3)
                    await self.update_lobby_embed(reaction.message)

            elif reaction.emoji == '▶' and user in self.lobby:
                # Set up the game
                self.game_state = GameState.startgame

                guild = reaction.message.channel.guild
                self.category = await self.init_game_channels(guild)

                gametc = self.category.text_channels[0]
                await gametc.send('Welcome to __**The Chameleon**__ (an adaptation of the \'whodunit\' party game)! '
                                  '\n*You have been moved to this private room to play. '
                                  'NOTE: This game is still in development. Expect bugs and unexpected behavior!*')

                await asyncio.sleep(2)
                await gametc.send('__**Rules**__', embed=Chameleon.get_rule_embed())
                await asyncio.sleep(1)

                sent_msg: discord.Message = await gametc.send('Once everyone is ready, press ▶ to start the game!')
                await sent_msg.add_reaction('▶')

        elif self.game_state == GameState.startgame and user in self.lobby:
            if reaction.emoji == '▶':
                self.game_state = GameState.ingame
                await self.game_loop()

        elif self.game_state == GameState.roundover and user in self.lobby:
            if reaction.emoji == '🛑':
                self.game_state = GameState.cleanup

                channel = reaction.message.channel
                await channel.send('Thanks for playing!')
                await asyncio.sleep(3)
                await channel.send('Deleting the text channels in 1 second.')
                await asyncio.sleep(1)
                self.lobby.clear()
                self.game_state = GameState.init
                await self.destroy_game_channels()
            elif reaction.emoji == '📝':
                channel = reaction.message.channel
                self.toggle_custom_cards()
                await channel.send('Custom cards enabled for next round.' if self.use_custom_cards
                                   else 'Custom cards disabled for next round.')

    @commands.Cog.listener('on_reaction_remove')
    async def on_reaction_remove(self, reaction: discord.Reaction, user):
        """ Handler for removing a reaction. """
        if user == reaction.message.author:  # which is the bot
            return

        if self.game_state == GameState.lobby:
            if reaction.emoji == '➕':
                # If this reaction is removed, remove user from the lobby.
                channel = reaction.message.channel
                try:
                    self.lobby.remove(user)
                    await channel.send(f'{user} left the lobby.', delete_after=3)
                    await self.update_lobby_embed(reaction.message)
                except ValueError:  # TODO does this need to have an exception clause?
                    pass

        elif self.game_state == GameState.roundover:
            if reaction.emoji == '📝':
                channel = reaction.message.channel
                self.toggle_custom_cards()
                await channel.send('Custom cards enabled for next round.' if self.use_custom_cards
                                   else 'Custom cards disabled for next round.')

    @commands.group(invoke_without_command=True)
    async def chameleon(self, ctx):
        """ Generate a lobby for players to join. """
        if self.game_state != GameState.init:
            await ctx.send("A game is already in play. Use a subcommand.")
        else:
            self.game_state = GameState.lobby
            embed = discord.Embed(title="The Chameleon", colour=discord.Colour(0xe7d066),
                                  description="Click the ➕ button below this message to join/leave the lobby."
                                              "Press ▶ to start the game with the players in the lobby.")

            embed.add_field(name="__Players in lobby__", value='-', inline=True)
            embed.set_footer(text='NOTE: This game is still in development. Expect bugs and unexpected behavior!')

            sent_msg = await ctx.send(embed=embed)
            await sent_msg.add_reaction('➕')
            await sent_msg.add_reaction('▶')

            # Save the guild reference for role creation.
            self.guild = ctx.guild

    async def update_lobby_embed(self, message: discord.Message):
        new_embed: discord.Embed = message.embeds[0]

        # Add player names. If a player has a custom nickname, display that and their username in parentheses.
        names = [f'{e.display_name} ({e.name})' if e.display_name != e.name else e.display_name for e in self.lobby]
        names = names or '-'

        new_embed.set_field_at(
            0,
            name=f"__Players in lobby__({len(self.lobby)}/{Chameleon.MAX_PLAYERS})",
            value='\n'.join(names), inline=True
        )
        await message.edit(embed=new_embed)

    @staticmethod
    def get_rule_embed():
        with open('chameleon_assets/rules_message.pickle', 'rb') as f:
            return pickle.load(f)

    @chameleon.command()
    async def join(self, ctx):
        """ Join the lobby for the chameleon game. """
        if self.game_state == GameState.lobby:
            if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                await ctx.send(f"Sorry, {ctx.author}, the game is full.")
            else:
                self.lobby.append(ctx.author)
                await ctx.send(f'Added {ctx.author} to the lobby.')
                # TODO update embed or deprecate this command

    @chameleon.command()
    async def leave(self, ctx):
        """ Leave the lobby. """
        if self.game_state == GameState.lobby:
            try:
                self.lobby.remove(ctx.author)
                # TODO update embed here or deprecate this command
            except ValueError:
                pass

    @chameleon.command()
    async def start(self, ctx):
        """ Starts the game with the players in the lobby. """
        await ctx.send(f"Starting game...")
        self.game_state = GameState.startgame

    async def init_game_channels(self, guild: discord.Guild) -> discord.CategoryChannel:
        """ Create the game CategoryChannel and move players into it. Return the CategoryChannel."""
        category = await guild.create_category('The Chameleon')
        await guild.create_text_channel('chameleon-game', category=category)
        gamevc = await guild.create_voice_channel('The Chameleon', category=category)

        for player in self.lobby:
            # player is a User. Get it as a member.
            member: discord.Member = guild.get_member(player.id)
            try:
                await member.move_to(gamevc)
            except discord.errors.HTTPException:
                # This means the user was not connected to voice. No worries, just continue.
                pass

        return category

    async def destroy_game_channels(self):
        """ Destroys the category created, as well as all channels within it. """
        try:
            for channel in self.category.text_channels + self.category.voice_channels:
                await channel.delete()
            await self.category.delete()
        except discord.errors.NotFound:
            pass  # The channel was deleted before

    @chameleon.command()
    async def forcequit(self, ctx):
        """ Stops the game at any point. """
        self.game_state = GameState.cleanup
        await ctx.send('Stopping the game in 1 second.', delete_after=1)
        await asyncio.sleep(1)
        self.lobby.clear()
        self.points.clear()
        self.game_state = GameState.init
        await self.destroy_game_channels()
        await self.__remove_color_roles()

    async def game_loop(self):
        """ The main game loop. """
        game_round = 0
        self.points = {k: 0 for k in self.lobby}
        tc = self.category.text_channels[0]

        while self.game_state == GameState.ingame:
            game_round += 1
            self.round_winner = None

            await asyncio.sleep(2)
            category, words = await self.new_category_card(tc)

            first_half = '\n'.join(words[:len(words)//2])
            second_half = '\n'.join(words[len(words)//2:])

            embed = discord.Embed(title=category, colour=discord.Colour(0xe7d066), description=f'*Round {game_round}*')
            embed.add_field(name='-', value=first_half, inline=True)
            embed.add_field(name='-', value=second_half, inline=True)
            await tc.send(f'__**Round {game_round}**__\nThe card is:', embed=embed)

            await asyncio.sleep(2)

            ########################################################
            # Choosing the Chameleon
            ########################################################
            word = random.choice(words)
            await tc.send('Check your Private Messages for the secret word.')

            random.shuffle(self.lobby)
            self.the_chameleon = self.lobby[0]

            for user in self.lobby:
                if user == self.the_chameleon:
                    await user.send('**You are the chameleon!** Try to blend in so you are not suspected, '
                                    'and determine the secret word.')
                else:
                    await user.send(f'You are not the chameleon. The secret word is **{word}**.')

            await asyncio.sleep(10)

            # Shuffle player order again to ensure no one knows who the chameleon is.
            random.shuffle(self.lobby)

            names = [e.display_name for e in self.lobby]
            colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪']
            # Used for role creation.
            c_codes = [0xde2e43, 0xffac32, 0xfdcb58, 0x79b15a, 0x55acef, 0xaa8fd6, 0xc0694e, 0x32373d, 0xe6e7e9]

            color_codes = {k: v for k, v in zip(colors, c_codes)}

            keys = random.shuffle(color_codes.keys())  # Vary colors (aesthetic purposes only)

            f_names = [f'{c} {n}' for c, n in zip(keys, names)]

            # Assign corresponding color roles to players.
            await self.create_color_roles(color_codes)

            # Assign color roles to each player.
            await self.__assign_color_roles()

            embed = discord.Embed(title='Player Order', colour=discord.Colour(0xe7d066), description='\n'.join(f_names))
            poll_msg = await tc.send('In the following order, describe the secret word with one descriptor word.', embed=embed)

            await asyncio.sleep(45)
            await tc.send('Once everyone has said their word, debate who you think the Chameleon is.')
            await asyncio.sleep(15)

            ########################################################
            # Voting stage
            ########################################################
            await tc.send('Vote on who the Chameleon is. If the Chameleon is voted out, try to guess what the word is.\n'
                          '*Voting ends immediately after everyone has cast their vote.*')

            self.game_state = GameState.voting
            for i in range(len(f_names)):
                await poll_msg.add_reaction(colors[i])

            await self.bot.wait_for('reaction_add', check=self.tally)

            ########################################################
            # Declare chameleon, calculate points
            ########################################################
            chameleon_guess = False

            self.who_got_points = f'The secret  word was: **{word}**!\n'

            if self.round_winner == self.the_chameleon:
                # Chameleon was found
                desc = f'You discovered the chameleon to be **{self.round_winner}**! ' \
                       f'Now, {self.round_winner} gets a chance to guess the right word.'
                embed = discord.Embed(title='You did it!', description=desc, colour=discord.Colour(0x00cc00))
                await tc.send(embed=embed)
                chameleon_guess = True

            elif self.round_winner is None:
                # Tie game
                desc = f'There was a tie, and the chameleon was not found. The chameleon was **{self.the_chameleon}**!'
                embed = discord.Embed(title='Tie!', description=desc, colour=discord.Colour(0xababab))
                await tc.send(embed=embed)

                chameleon_guess = True

            else:
                # Chameleon got away
                desc = f'{self.round_winner} is not the chameleon. The chameleon was **{self.the_chameleon}!**'
                embed = discord.Embed(title='The chameleon got away!', description=desc, colour=discord.Colour(0xff0000))
                await tc.send(embed=embed)

                # Update points. The chameleon gets 2 points.
                self.points[self.the_chameleon] += 2
                self.who_got_points += 'For eluding the party, chameleon gets 2 points!'

            # Score chameleon's guess
            if chameleon_guess:
                msg = await tc.send('If the chameleon guessed correctly, press ✅. If not, press ❌.')
                await msg.add_reaction('✅')
                await msg.add_reaction('❌')

                await self.bot.wait_for('reaction_add', check=self.check_guess)

            ########################################################
            # Display word, points, Round over
            ########################################################
            embed = discord.Embed(title=f"Round {game_round} Leaderboard",
                                  colour=discord.Colour(0xe7d066), description=self.who_got_points)

            # Player names. If a player has a custom nickname, display that and their username in parentheses.
            sorted_lobby = sorted(self.lobby, key=lambda e: self.points[e], reverse=True)
            p_names = [
                f'{e.display_name} ({e.name}): {self.points[e]}' if e.display_name != e.name
                else f'{e.display_name}: {self.points[e]}'
                for e in sorted_lobby
            ] or '-'

            embed.add_field(name="Current Standings", value='\n'.join(p_names))

            await tc.send(embed=embed)

            round_over_msg = await tc.send('Once the round is over, click 🔁 to play another round, or 🛑 to finish the game.'
                                           ' If you play another round, click 📝 to enable/disable custom deck.')
            self.game_state = GameState.roundover
            for r in '🔁🛑📝':
                await round_over_msg.add_reaction(r)

            # Current state of use_custom_cards
            cc = 'enabled' if self.use_custom_cards else 'disabled'
            await tc.send(f'Custom cards are {cc} for next round.')

            await self.bot.wait_for('reaction_add', check=lambda reaction, _: str(reaction.emoji) == '🔁')

            # If we get here, go back and do it again!
            self.game_state = GameState.ingame

    def tally(self, reaction: discord.Reaction, user: discord.User) -> bool:  # TODO make sure no one votes twice
        """ Sets self.round_winner to a winner if there is an undisputed winner.
         In the case of a tie, no one is set as the winner.
         Return whether or not everyone has voted (to continue in the game loop). """
        if user == reaction.message.author:
            return False  # Sometimes the bot types reactions that will affect the game, oops

        if reaction.emoji == '⏭':  # For debugging only
            return True

        message: discord.Message = reaction.message
        all_reacts = message.reactions
        totals = [r.count for r in all_reacts]  # Maps directly to self.lobby
        if sum(totals) - len(self.lobby) < len(self.lobby):  # Subtract the reactions the bot added
            return False

        m = totals.index(max(totals))

        # Look for a tie. m is leftmost max.
        for i in range(m+1, len(totals)):
            if totals[i] == max(totals):
                return True  # Do not assign a winner this round.

        self.round_winner = self.lobby[m]
        return True

    def check_guess(self, reaction: discord.Reaction, _user: discord.User) -> bool:
        tc = reaction.message
        if reaction.message != tc or _user not in self.lobby:
            return False

        if reaction.emoji == '✅':
            # The chameleon guessed correctly. Give the chameleon one point.
            self.points[self.round_winner] += 1
            self.who_got_points += 'The chameleon gets 1 point for guessing correctly!'
            return True
        elif reaction.emoji == '❌':
            # The chameleon guessed wrong. Everyone except him/her gets 2 points.
            for k in self.points.keys():
                if k != self.the_chameleon:
                    self.points[k] += 2
                self.who_got_points += 'Because the chameleon guessed wrong, everyone else gets 2 points!'
            return True

    async def new_category_card(self, channel):
        if self.use_custom_cards:
            if len(self.custom_cards) > 0:
                return random.choice(list(self.custom_cards.items()))  # Returns a tuple of (key, val)
            else:
                await channel.send('No custom cards! Using normal deck instead. '
                                   'To add a custom card, use the `chameleon custom` command.')

        with open('chameleon_assets/category_cards.json', 'r') as f:
            cards: dict = json.load(f)
        return random.choice(list(cards.items()))

    @chameleon.command()
    async def custom(self, ctx, *data: str):
        """ Create a custom card. The first word is the category,
        the following words are words in the category. Usage:
        '/chameleon custom foods apple banana pineapple orange'

        *data, which is a tuple of strings, is separated into a dict, which
        follows convention of the other cards."""
        self.custom_cards.update({data[0]: data[1:]})
        await ctx.send(f'\'{data[0]}\' card added to custom cards.')

    def toggle_custom_cards(self):
        """ Invoked via reaction event handler. """
        self.use_custom_cards = not self.use_custom_cards

    async def create_color_roles(self, color_codes):
        """ Generate the color roles outlined by the given color codes. """
        for color, c_code in color_codes.items():
            self.color_roles.append(await self.guild.create_role(
                name=f'Chameleon-{color}',
                reason='Used in Chameleon game.',
                colour=c_code
            ))

    async def __remove_color_roles(self):
        """ Deletes the color roles from the guild. Used during cleanup. """
        for role in self.color_roles:
            await role.delete()

    async def __assign_color_roles(self):
        """ Assigns self.color_roles to self.players """


def setup(bot):
    prefix = cfload.configSectionMap('Commands')['command_prefix']
    bot.add_cog(Chameleon(bot, prefix))
