from discord.ext import commands
import requests
import re
import mwparserfromhell as mwp


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

        # try:
        await ctx.send(results[0])  # TODO send as an embed.
        await ctx.send(pic_url)
        # except IndexError:
        #     await ctx.message.add_reaction('\U00002753')


def setup(bot):
    bot.add_cog(ACNH(bot))
