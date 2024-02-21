#!/usr/bin/python3

# =============================================================================
#                      EpicStore v1.0 www.github.com/wrrulos
#              Discord bot to keep up with free games from Epic Games
#                               Made by wRRulos
#                                  @wrrulos
# =============================================================================

# Any error report it to my discord please, thank you. 
# Programmed in Python 3.10.8
from datetime import datetime
import requests
import discord
import asyncio
import shutil
import json
import sys
import os

from discord.ext import commands, tasks

try:
    with open('settings.json', 'r') as f:
        settings = json.loads(f.read())
        token = settings['token']
        prefix = settings['prefix']

except FileNotFoundError:
    data = { 'token': '', 'prefix': 'epicstore!' }
    with open('settings.json', 'w') as f:
        json.dump(data, f, indent=4)

if token == '' or prefix == '':
    print('\n [#] Invalid configuration!')
    sys.exit()

intents = discord.Intents.all()
client = commands.Bot(command_prefix=prefix, help_command=None, intents=intents)
api = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'

if not os.path.isdir('data'):
    os.mkdir('data')

if not os.path.isdir('data/servers'):
    os.mkdir('data/servers')
    

def save_server(server_id):
    """ Save the server folder and create the data.json file """
    server_folder = f'data/servers/{server_id}'
    server_file = f'{server_folder}/data.json'

    if os.path.exists(server_folder):
        shutil.rmtree(server_folder)

    os.mkdir(server_folder)

    with open(server_file, 'w') as f:
        data = {
            'channel_id': '',
            'send_role': True,
            'role_id': '@everyone',
            'games': [],
        }
        json.dump(data, f, indent=4)


def save_data(server_id, name, id):
    """ Save the configuration """
    file = f'data/servers/{server_id}/data.json'

    with open(file, 'r') as f:
        data = json.loads(f.read())

    data[name] = id

    with open(file, 'w') as f:
        json.dump(data, f, indent=4)


def get_games():
    """ Get current games from Epic Games API """
    games = {}
    r = requests.get(api)
    r_json = r.json()
    store_games = r_json['data']['Catalog']['searchStore']['elements']  # Games

    for num, game in enumerate(store_games):
        if game['promotions'] is None:
            continue
        num = str(num)
        game_info = [game['title'], game['description']]
        if game['keyImages'][0]['type'] == 'VaultClosed':
            game_info.append(game['keyImages'][1]['url'])
        else:
            game_info.append(game['keyImages'][0]['url'])

        game_info.append(game['price']['totalPrice']['fmtPrice']['discountPrice'])

        # Verificați dacă există oferte promoționale pentru joc
        if 'promotions' in game:
            promo_offers = game['promotions'].get('promotionalOffers', [])
            upcoming_promo_offers = game['promotions'].get('upcomingPromotionalOffers', [])
            
            # Extrageți datele de început și sfârșit pentru ofertele promoționale curente, dacă există
            current_start_date = None
            current_end_date = None
            if promo_offers:
                if promo_offers[0]['promotionalOffers']:
                    current_start_date = promo_offers[0]['promotionalOffers'][0].get('startDate')
                    current_end_date = promo_offers[0]['promotionalOffers'][0].get('endDate')

            # Extrageți datele de început și sfârșit pentru ofertele promoționale viitoare, dacă există
            upcoming_start_date = None
            upcoming_end_date = None
            if upcoming_promo_offers:
                if upcoming_promo_offers[0]['promotionalOffers']:
                    upcoming_start_date = upcoming_promo_offers[0]['promotionalOffers'][0].get('startDate')
                    upcoming_end_date = upcoming_promo_offers[0]['promotionalOffers'][0].get('endDate')

            # Adăugați toate cele patru date la lista game_info
            game_info.extend([current_start_date, current_end_date, upcoming_start_date, upcoming_end_date])
        
        else:
            # Adăugați None pentru fiecare dată dacă nu există oferte promoționale
            game_info.extend([None, None, None, None])

        games[num] = game_info

    return games







async def send_announcement(server_id, games):
    """ Send a game announcement to the channel """
    try:
        with open(f'data/servers/{str(server_id)}/data.json', 'r') as f:
            data = json.loads(f.read())

        if data['channel_id'] == '':  # În cazul în care utilizatorul nu a setat un canal.
            return

        channel = client.get_channel(int(data['channel_id']))

        # Sortează jocurile după data de început a ofertelor promoționale
        sorted_games = sorted(games.values(), key=lambda x: datetime.strptime(x[4], '%Y-%m-%dT%H:%M:%S.%fZ') if x[4] is not None else datetime.max)
        
        for game_info in sorted_games:
            embed = discord.Embed(title=f'{game_info[0]}', color=0x60f923)  # Adăugați titlul jocului ca titlu al embed-ului
            embed.set_thumbnail(url=game_info[2])  # Setăm imaginea jocului ca miniatură a embed-ului
        
            # Adăugăm descrierea și prețul redus ca câmpuri în embed
            embed.add_field(name="Description", value=game_info[1], inline=False)
            #embed.add_field(name="Discount Price", value=game_info[3], inline=False)
            
            # Dacă există date de început și de sfârșit pentru oferte promoționale, le adăugăm ca câmpuri în embed
            if game_info[4] is not None and game_info[5] is not None:
                start_date = datetime.strptime(game_info[4], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d-%m-%Y')
                end_date = datetime.strptime(game_info[5], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d-%m-%Y')
                embed.add_field(name="Start Date", value=start_date, inline=False)
                embed.add_field(name="End Date", value=end_date, inline=False)
            if len(game_info) >= 8:
                # Verificăm dacă există date de început și de sfârșit pentru ofertele promoționale ale celui de-al doilea joc
                if game_info[6] is not None and game_info[7] is not None:
                    start_date = datetime.strptime(game_info[6], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d-%m-%Y')
                    end_date = datetime.strptime(game_info[7], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d-%m-%Y')
                    embed.add_field(name="Start Date", value=start_date, inline=False)
                    embed.add_field(name="End Date", value=end_date, inline=False)

        
            await channel.send(embed=embed)

        if data['send_role'] == True:  # If the option to send a role is activated
            if data['role_id'] == '@everyone' or data['role_id'] == '@here':
                message = await channel.send(data['role_id'])

            else:
                message = await channel.send(f'<{data["role_id"]}>')

        await asyncio.sleep(2)
        await message.delete()

    except AttributeError:
        pass




@client.event
async def on_ready():
    """ When the bot starts """
    check_games.start()
    change_status.start()
    print(f"\nI'm currently at {len(client.guilds)} servers!\n")
        
    for guild in client.guilds:  # Check if a server does not have the configuration file
        if not os.path.exists(f'data/servers/{str(guild.id)}/data.json'):
            save_server(str(guild.id))


@client.event
async def on_guild_join(guild):
    """ When the bot joins the server """
    save_server(str(guild.id))


@client.event
async def on_message(message):
    """ Every time a message is sent """
    mention = f'<@{client.user.id}>'

    if mention in message.content:
        await message.channel.send(f'Salut,foloseste urmatoarea comanda `{prefix}help` ca sa ma configurezi.')

    await client.process_commands(message)


@tasks.loop(minutes=1)
async def change_status():
    """ Background task that changes the state of the bot """
    await client.change_presence(activity=discord.Game(name=f"Au intrat {len(client.guilds)} in mine!", type=0))


@tasks.loop(seconds=2)
async def check_games():
    """ 
    Background task that checks current games 
    against previously obtained ones 
    """
    games = get_games()
    game_names = [games[str(num)][0] for num in range(len(games))]
    
    for guild in client.guilds:
        with open(f'data/servers/{guild.id}/data.json', 'r') as f:
            data = json.loads(f.read())

        if data['games'] != game_names:
            with open(f'data/servers/{guild.id}/data.json', 'w') as f:
                data['games'] = game_names
                json.dump(data, f, indent=4)

            await send_announcement(guild.id, games)


@client.command(name='help')
async def help_command(ctx):
    """ Command to see available commands """
    embed = discord.Embed(title='💸 Lista comenzi', color=0x014EFF, description=None)
    embed.add_field(name=f'**{prefix}help**', value='`📄 Arata acest meniu.`', inline=False)
    embed.add_field(name=f'**{prefix}channel [channel]**', value='`🧾 Seteaza canalul unde sa trimit mesaje`', inline=False)
    embed.add_field(name=f'**{prefix}role [role]**', value='`📍 Spune-mi ce rol sa deranjez, daca nu vrei pe nimeni, foloseste din nou comanda goala.`', inline=False)
    embed.add_field(name=f'**{prefix}settings**', value='`⚙ Astea-s comenzile mele prezente.`', inline=False)
    embed.set_footer(text='🔗 Modificat de Kuteal')
    await ctx.send(embed=embed)


@client.command(name='channel')
@commands.has_permissions(administrator=True)
async def set_channel(ctx, channel):
    """ Command to save the channel id """
    channel_id = channel.replace('<', '').replace('>', '').replace('#', '')
    server_id = str(ctx.guild.id)

    for i in ctx.guild.channels:  # i = channel
        if str(i.id) in channel:
            save_data(server_id, 'games', '[]')
            save_data(server_id, 'channel_id', channel_id)
            await ctx.send(f'Canalul pe care o sa-l stresez este {channel}')
            return

    await ctx.send('E gresit canalu babe!')


@set_channel.error
async def set_channel_error(ctx, error):
    """ Catch command errors. In this case, the lack of arguments """
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Trebuie sa mi dai un canal baby!')

    if isinstance(error, commands.MissingPermissions):
        await ctx.send('scuziiii, n ai permisiuni')


@client.command(name='role')
@commands.has_permissions(administrator=True)
async def set_role(ctx, role=None):
    """ Command to save the role id """
    server_id = str(ctx.guild.id)

    if role is not None:
        if role in ['@everyone', '@here']:
            save_data(server_id, 'role_id', role)
            await ctx.send(f'rolul pe care o sa-l enervez este {role}, hihi')
            return

        for i in ctx.guild.roles:  # i = role
            if str(i.id) in role:
                save_data(server_id, 'role_id', role)
                await ctx.send(f'rolul pe care o sa-l enervez este {role}, hihi')
                return

        await ctx.send('alege un rol valid baby!')

    else:
        with open(f'data/servers/{server_id}/data.json') as f:
            data = json.loads(f.read())

        if data['send_role'] == True:
            save_data(server_id, 'send_role', False)
            await ctx.send('nu mai stresez rolurile :(')

        else:
            save_data(server_id, 'send_role', True)
            await ctx.send('o sa stresez un rol :x')


@set_role.error
async def set_role_error(ctx, error):
    """ Catch command errors """
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('n-ai permisiuni baby')


@client.command(name='settings')
@commands.has_permissions(administrator=True)
async def view_settings(ctx):
    """ This command show server settings """
    server_id = str(ctx.guild.id)

    with open(f'data/servers/{server_id}/data.json') as f:
        data = json.loads(f.read())

    channel = 'None' if data['channel_id'] == '' else f'<#{data["channel_id"]}>'
    
    embed = discord.Embed(title='💸 Setari server', color=0x014EFF, description=None)
    embed.add_field(name='**Canal**', value=channel, inline=False)
    embed.add_field(name='**Mentioneaza un rol**', value=data["send_role"], inline=False)
    embed.add_field(name='**Rol**', value=data["role_id"], inline=False)
    embed.set_footer(text='🔗 Modificat de Kuteal')
    await ctx.send(embed=embed)


@view_settings.error
async def view_settings_error(ctx, error):
    """ Catch command errors """
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('N-ai permisiuni baby :x.')


client.run(token)
