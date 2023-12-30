from calendar import c
import nextcord
from nextcord.ext import commands
import os
import tinydb
from league import League, Trade, ReturnCodes, ALL_CHARACHTERS
import logging

logging.basicConfig(level=logging.INFO)

#set logging level of nextcord
logging.getLogger('nextcord').setLevel(logging.ERROR)

TESTING_GUILD_ID = 1190771563625201724  # Replace with your guild ID

# member intent
intents = nextcord.Intents.default()
intents.members = True

bot = commands.Bot(intents=intents)

league = League("data/league.json", "data/trades.json")


async def get_name(user_id: int):
    guild = bot.get_guild(TESTING_GUILD_ID)
    # get username of owner from user id
    try:
        name = (await bot.fetch_user(user_id)).name
    except nextcord.errors.NotFound:
        logging.warn(f'User {user_id} not found!')
        return "Unknown Owner"


    # get nickname of owner from user id
    member = guild.get_member(user_id)
    if member.nick:
        logging.info(f'Using nickname {member.nick} for {name}')
        name = member.nick

    return name

@bot.event
async def on_ready():
    logging.info(f'We have logged in as {bot.user}')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')
    logging.info(f'Guild ID: {TESTING_GUILD_ID}')

########## TEAM COMMANDS ##########

@bot.slash_command(guild_ids=[TESTING_GUILD_ID], name="team", description="Manage your team")
async def team_cmd(interaction: nextcord.Interaction):
    pass

@team_cmd.subcommand(description="View your team")
async def view(interaction: nextcord.Interaction, team: str = nextcord.SlashOption("team", required=False, description="The name of the team you want to view")):
    if team:
        team = league.teams_db.get(tinydb.Query().user_id == int(team))
    else:
        team = league.get_team(interaction.user.id)

    if team:
        msg = f'## {team["team_name"]}'
        if len(team["players"]) == 0:
            msg += "\nNo Players Yet!"
        else:
            msg += "\nPlayers:\n"
            for player in team["players"]:
                msg += f'- {player.title()}\n'

        await interaction.response.send_message(msg, ephemeral=True)
    else:
        await interaction.response.send_message("You don't have a team!", ephemeral=True)

@view.on_autocomplete("team")
async def view_autocomplete(interaction: nextcord.Interaction, team: str):
    choices = league.get_teams(True)
    await interaction.response.send_autocomplete(choices)

@team_cmd.subcommand(description="Create a new team")
async def create(interaction: nextcord.Interaction, team_name: str = nextcord.SlashOption(required=True, description="The name of your team")):
    
    # check if user already has a team
    if league.get_team(interaction.user.id):
        await interaction.response.send_message("You already have a team!", ephemeral=True)
        return

    # create team
    league.create_team(interaction.user.id, team_name)

    await interaction.response.send_message(f'{await get_name(interaction.user.id)} created a team called {team_name}!')
    logging.info(f'{await get_name(interaction.user.id)} created a team called {team_name}')

@team_cmd.subcommand(description="Delete your team")
async def delete(interaction: nextcord.Interaction):
    if league.delete_team(interaction.user.id) == ReturnCodes.SUCCESS:
        await interaction.response.send_message(f'{await get_name(interaction.user.id)} deleted their team!')

        logging.info(f'{await get_name(interaction.user.id)} deleted their team')
    else:
        await interaction.response.send_message("You don't have a team!", ephemeral=True)

@team_cmd.subcommand(description="Add a player to your team")
async def add(interaction: nextcord.Interaction, player: str = nextcord.SlashOption(required=True, description="The name of the player you want to add")):
    team = league.get_team(interaction.user.id)
    player = player.upper()

    if team:
        if player in team["players"]:
            await interaction.response.send_message("Player is already on your team!", ephemeral=True)
            return

        if player not in league.free_agents:
            if player in ALL_CHARACHTERS:
                await interaction.response.send_message("Player is not a free agent!", ephemeral=True)
                return
            else:
                await interaction.response.send_message("Player does not exist!", ephemeral=True)
                return

        league.add_player(interaction.user.id, player)
        await interaction.response.send_message(f'{await get_name(interaction.user.id)} added {player.title()} to their team!')

        logging.info(f'{await get_name(interaction.user.id)} added {player.title()} to their team')
    else:
        await interaction.response.send_message("You don't have a team!", ephemeral=True)

@add.on_autocomplete("player")
async def add_autocomplete(interaction: nextcord.Interaction, player: str):
    choices = league.free_agents
    choices = [c.title() for c in choices if c.upper().startswith(player.upper())]

    await interaction.response.send_autocomplete(choices[:25])

@team_cmd.subcommand(description="Drop a player from your team")
async def drop(interaction: nextcord.Interaction, player: str = nextcord.SlashOption("player", required=True, description="The name of the player you want to remove")):
    team = league.get_team(interaction.user.id)
    player = player.upper()

    if team:
        if player not in team["players"]:
            await interaction.response.send_message("Player is not on your team!", ephemeral=True)
            return

        league.remove_player(interaction.user.id, player)
        await interaction.response.send_message(f'{await get_name(interaction.user.id)} dropped {player.title()} from their team!')

        logging.info(f'{await get_name(interaction.user.id)} dropped {player.title()} from their team')
    else:
        await interaction.response.send_message("You don't have a team!", ephemeral=True)

@drop.on_autocomplete("player")
async def drop_autocomplete(interaction: nextcord.Interaction, drop: str):
    choices = league.get_team(interaction.user.id)["players"]
    choices = [c.title() for c in choices if c.upper().startswith(drop.upper())]

    await interaction.response.send_autocomplete(choices)

########## LEAGUE COMMANDS ##########

@bot.slash_command(guild_ids=[TESTING_GUILD_ID], description="View league information", name="league")
async def league_cmd(interaction: nextcord.Interaction):
    pass

@league_cmd.subcommand(description="View all free agents")
async def free_agents(interaction: nextcord.Interaction):
    free_agents = league.get_free_agents()

    msg = "## Free Agents\n"
    if len(free_agents) == 0:
        msg += "No free agents yet!"
    else:
        for player in free_agents:
            msg += f'- {player.title()}\n'

    await interaction.response.send_message(msg, ephemeral=True)

@league_cmd.subcommand(description="View all teams")
async def teams(interaction: nextcord.Interaction):
    teams = league.get_teams()

    msg = "## Teams\n"
    if len(teams) == 0:
        msg += "No teams yet!"
    else:
        for team in teams:
            msg += f'- {team["team_name"]} - (Owner: {await get_name(team["user_id"])})\n'

    await interaction.response.send_message(msg, ephemeral=True)

@league_cmd.subcommand(description="View all trades")
async def trades(interaction: nextcord.Interaction):
    trades = league.get_trades()

    msg = "## Pending Trades\n"
    if len(trades) == 0:
        msg += "No trades yet!"
    else:
        for trade in trades:
            user1_team = league.get_team(trade.user1_id)
            user2_team = league.get_team(trade.user2_id)

            msg += f'- {user1_team["team_name"]} wants to trade {trade.user1_trade.title()} for {user2_team["team_name"]}\'s {trade.user2_trade.title()}\n'

            # add indented link to message
            msg += f'  - [View Trade](https://discord.com/channels/{TESTING_GUILD_ID}/{interaction.channel_id}/{trade.message_id})\n'
    await interaction.response.send_message(msg, ephemeral=True)

########## TRADE COMMANDS ##########
    
async def check_trades():
    # check if any trades have expired
    trades = league.get_trades()
    for trade in trades:
        if trade.validate_trade(league) != ReturnCodes.SUCCESS:
            league.cancel_trade(trade)

            # update trade embed
            msg = await bot.get_channel(trade.channel_id).fetch_message(trade.message_id)
            embed = await trade_embed(trade)
            embed.color = nextcord.Color.red()
            await msg.edit(embed=embed)

            logging.info(f'Trade {trade.message_id} expired')


async def trade_embed(trade: Trade):
    user1_team = league.get_team(trade.user1_id)
    user2_team = league.get_team(trade.user2_id)

    embed=nextcord.Embed(title="Trade Proposal", description="A trade proposal has been created!", color=nextcord.Color.blue())
    embed.add_field(name=trade.user1_trade.title(), value=f'{user1_team["team_name"]} - {await get_name(user1_team["user_id"])}', inline=True)
    embed.add_field(name="for", value="", inline=True)
    embed.add_field(name=trade.user2_trade.title(), value=f'{user2_team["team_name"]} - {await get_name(user2_team["user_id"])}', inline=True)
    embed.set_footer(text="Right click or long press this message then click Apps -> Accept/Deny Trade")

    return embed

@bot.slash_command(guild_ids=[TESTING_GUILD_ID], description="Manage trades", name="trade")
async def trade_cmd(interaction: nextcord.Interaction):
    pass

@trade_cmd.subcommand(description="Create a trade")
async def create(interaction: nextcord.Interaction, user2: str = nextcord.SlashOption("other_team", required=True, description="The team you want to trade with"), user1_trade: str = nextcord.SlashOption(required=True, description="The player you want to trade", name="your_player"), user2_trade: str = nextcord.SlashOption(required=True, description="The player you want to trade for", name="for_player")):
    user2 = int(user2)
    user1_team = league.get_team(interaction.user.id)
    user2_team = league.get_team(user2)

    user1_trade = user1_trade.upper()
    user2_trade = user2_trade.upper()

    if interaction.user.id == user2:
        await interaction.response.send_message("You can't trade with yourself!", ephemeral=True)
        return

    if user1_team and user2_team:
        if user1_trade not in user1_team["players"]:
            await interaction.response.send_message("You don't have that player!", ephemeral=True)
            return

        if user2_trade not in user2_team["players"]:
            await interaction.response.send_message("They don't have that player!", ephemeral=True)
            return

        trade = league.create_trade(interaction.user.id, user2, user1_trade, user2_trade)
        if trade == ReturnCodes.INVALID_TRADE:
            await interaction.response.send_message("Invalid trade!", ephemeral=True)
            return

        # create ping for other user
        user2_ping = f'<@{user2}> you have a new trade proposal!'

        # send embed
        embed = await trade_embed(trade)
        msg = await interaction.response.send_message(user2_ping, embed=embed)
        full_msg: nextcord.Message = await msg.fetch()

        # update trade with message id
        league.assign_trade_message(trade, full_msg.id)

        logging.info(f'{await get_name(interaction.user.id)} created a trade with {await get_name(user2)}')
    else:
        await interaction.response.send_message("You don't have a team!", ephemeral=True)

@create.on_autocomplete("user2")
async def create_autocomplete(interaction: nextcord.Interaction, other_team: str):
    choices = league.get_teams()
    choices_new = {}
    for c in choices:
        if c["user_id"] == interaction.user.id:
            continue
        if c["team_name"].upper().startswith(other_team.upper()):
            choices_new[c["team_name"]] = str(c["user_id"])

    await interaction.response.send_autocomplete(choices_new)

@create.on_autocomplete("user1_trade")
async def create_autocomplete(interaction: nextcord.Interaction, your_player: str):
    choices = league.get_team(interaction.user.id)["players"]
    choices = [c.title() for c in choices if c.upper().startswith(your_player.upper())]

    await interaction.response.send_autocomplete(choices)

@create.on_autocomplete("user2_trade")
async def create_autocomplete(interaction: nextcord.Interaction, for_player: str):
    try:
        choices = league.get_team(int(interaction.data["options"][0]["options"][0]["value"]))["players"]
    except ValueError:
        return
    
    choices = [c.title() for c in choices if c.upper().startswith(for_player.upper())]

    await interaction.response.send_autocomplete(choices)

# handle trade accept/deny
@bot.message_command(name="Accept Trade")
async def accept_trade_cmd(interaction: nextcord.Interaction, message: nextcord.Message):
    trade = league.get_trade(message.id)

    if trade and trade.validate_trade(league) == ReturnCodes.SUCCESS:
        if interaction.user.id == trade.user2_id:
            league.process_trade(trade)

            await interaction.response.send_message(f'<@{trade.user1_id}>, <@{trade.user2_id}> accepted the trade!')

            # change color of embed
            embed = await trade_embed(trade)
            embed.color = nextcord.Color.green()
            await message.edit(embed=embed)

            logging.info(f'Trade {trade.message_id} accepted')
        else:
            await interaction.response.send_message("You can't accept this trade!", ephemeral=True)
    else:
        await interaction.response.send_message("This trade is no longer valid!", ephemeral=True)

@bot.message_command(name="Deny Trade")
async def deny_trade_cmd(interaction: nextcord.Interaction, message: nextcord.Message):
    trade = league.get_trade(message.id)

    if trade and trade.validate_trade(league) == ReturnCodes.SUCCESS:
        if interaction.user.id == trade.user2_id:
            league.cancel_trade(trade)
            await interaction.response.send_message(f'<@{trade.user1_id}>, <@{trade.user2_id}> denied the trade!')

            # change color of embed
            embed = await trade_embed(trade)
            embed.color = nextcord.Color.red()
            await message.edit(embed=embed)

            logging.info(f'Trade {trade.message_id} denied')
        else:
            await interaction.response.send_message("You can't deny this trade!", ephemeral=True)
    else:
        await interaction.response.send_message("This trade is no longer valid!", ephemeral=True)

@bot.message_command(name="Cancel Trade")
async def cancel_trade_cmd(interaction: nextcord.Interaction, message: nextcord.Message):
    trade = league.get_trade(message.id)

    if trade and trade.validate_trade(league) == ReturnCodes.SUCCESS:
        if interaction.user.id == trade.user1_id:
            league.cancel_trade(trade)
            await interaction.response.send_message(f'<@{trade.user2_id}>, <@{trade.user1_id}> cancelled the trade!')

            # change color of embed
            embed = await trade_embed(trade)
            embed.color = nextcord.Color.red()
            await message.edit(embed=embed)

            logging.info(f'Trade {trade.message_id} cancelled')
        else:
            await interaction.response.send_message("You can't cancel this trade!", ephemeral=True)
    else:
        await interaction.response.send_message("This trade is no longer valid!", ephemeral=True)

bot.run(os.getenv("BOT_TOKEN"))