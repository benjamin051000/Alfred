import re

import discord
import mwparserfromhell as mwp
import requests
from discord.ext import commands


# Use https://www.mediawiki.org/wiki/API:Revisions#Sample_Code to GET from https://animalcrossing.fandom.com/wiki/Fish_(New_Horizons)

class ACNH(commands.Cog):
    """ Various helper commands for Animal Crossing: New Horizons game on the Nintendo Switch. """

    fish_url = 'https://animalcrossing.fandom.com/api.php?action=query&prop=revisions&rvprop=content&rvslots=*&format=json&titles=Fish_(New_Horizons)'

    @commands.command(aliases=['fi', 'fish'])
    async def fishinfo(self, ctx, *query):
        """ Retrieves fish information for AC:NH. """

        query = ' '.join(query).lower()  # Format query  # TODO breaks for "great white shark"

        r = requests.get(ACNH.fish_url).json()  # Consider using aiohttp (although this seems to be fast enough for now)
        data = r['query']['pages']['143083']['revisions'][0]['*']

        wikitext = mwp.parse(data)
        templates = wikitext.filter_templates()
        filtered_list = list(
            filter(lambda template: template.name.matches('TableContent') or template.name.matches('roundyR'),
                   templates))

        # Remove first roundyR. The second one separates north and south hemispheres.
        roundy_r = filtered_list.pop(0)
        idx = filtered_list.index(roundy_r)

        n_hemisphere = filtered_list[:idx]  # Fish name is at element.params[1]
        s_hemisphere = filtered_list[idx + 1:]

        results = list(filter(lambda temp: temp.params[1].strip('\n []').lower() == query, n_hemisphere)) + list(
            filter(lambda temp: temp.params[1].strip('\n []').lower() == query, s_hemisphere))

        # Get the icon for the embed.
        # This uses another API call, which sucks, but I can't get the HTML URL from the above wikitext.
        # It seems unavoidable at the moment.
        try:
            icon_name = results[0].params[2].strip('\n []').replace('File:', '').strip().replace(' ', '_')
        except IndexError:
            await ctx.message.add_reaction('\U00002753')
            return

        html_url = 'https://animalcrossing.fandom.com/api.php?action=parse&page=Fish_(New_Horizons)&prop=text&format=json'
        html_r = requests.get(html_url).json()
        html_data = html_r['parse']['text']['*']

        try:
            pic_url = re.search(f'href="(?P<URL>(.*?){icon_name}(.*?))"', html_data).group('URL')
        except AttributeError:
            print('Couldn\'t find', icon_name)
            await ctx.message.add_reaction('\U00002754')  # TODO remove, or make same color as above reaction (2753)
            return

        # Create the embed
        fish_name = results[0].params[1].strip(' \n[]')
        fish_price = str(results[0].params[3].strip(' \n')) + ' bells'
        fish_shadow_size = results[0].params[5].strip(' \n')

        fish_tod = str(results[0].params[6])
        clean = re.compile('<.*?>')
        fish_tod = re.sub(clean, '', fish_tod)
        fish_location = str(results[0].params[4]).strip(' \n') + ', ' + fish_tod

        fish_north_times = results[0].params[7:19]
        fish_south_times = results[1].params[7:19]
        fish_north_months = ''
        fish_south_months = ''

        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        n_num = 0
        s_num = 0
        for n in range(len(fish_north_times)):
            if fish_north_times[n].value.strip(' \n') == '✓':
                fish_north_months += months[n] + ', '
                n_num += 1
            if fish_south_times[n].value.strip(' \n') == '✓':
                fish_south_months += months[n] + ', '
                s_num += 1

        fish_north_months = fish_north_months[:-2]
        fish_south_months = fish_south_months[:-2]

        if n_num == 12:
            fish_north_months = 'All year'

        if s_num == 12:
            fish_south_months = 'All year'

        embed = discord.Embed(title=fish_name,
                              colour=discord.Colour(0x44b9e3))  # , url="fish_url")  # TODO add url to fish page
        embed.set_thumbnail(url=pic_url)
        embed.set_footer(text="Animal Crossing: New Horizons",
                         icon_url="https://vignette.wikia.nocookie.net/animalcrossing/images/6/64/Favicon.ico/revision/latest?cb=20141121212537")  # TODO icon broken

        embed.add_field(name="Value", value=fish_price, inline=True)
        embed.add_field(name="Location, TOD", value=fish_location, inline=True)
        embed.add_field(name="Shadow size", value=fish_shadow_size, inline=False)
        embed.add_field(name="Northern Hemisphere", value=fish_north_months, inline=True)
        embed.add_field(name="Southern Hemisphere", value=fish_south_months, inline=True)
        # embed.add_field(name="Description",
        #                 value="The blue marlin (力ジキマグロ, swordfish?), known as the swordfish in Animal Forest e+, is a rare fish in the Animal Crossing series. In Animal Forest e+ it is only seen in the sea around the Private Island, where it makes occasional appearances as an arapaima-sized shadow. However, due to the current of the island, some are impossible to catch as they are too far out to reach. The fish can be found all day and has a huge size.")

        await ctx.send('This feature is currently in beta. Please be patient with glitches and errors.', embed=embed)


def setup(bot):
    bot.add_cog(ACNH(bot))
