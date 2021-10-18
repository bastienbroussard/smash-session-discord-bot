#############
#  IMPORTS  #
#############
# General imports
import locale
import ssl

# Discord-relative imports
from discord import Intents, Embed
from discord.ext.commands import Bot
from discord_slash import SlashCommand, SlashContext, ComponentContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow

# Local-relative imports
from session import Session
from user import User
from custom_emojis import CustomEmojis
from actions import *
from exceptions import *
from equipment import Equipment

# Bot initialization
bot = Bot(command_prefix="!", self_bot=True, help_command=None, intents=Intents.default())
slash = SlashCommand(bot, sync_commands=False)


#############
#  EVENTS   #
#############
@bot.event
async def on_ready():
    """
    Event triggered when the bot is ready.
    """
    # Set current locale
    locale.setlocale(locale.LC_TIME, 'fr_FR')

    # Initialize custom emojis
    CustomEmojis(bot)


@bot.event
async def on_slash_command_error(ctx: SlashContext, exception: Exception):
    """
    Event triggered when an error occurs during the execution of a slash command.

    :param ctx: The context.
    :param exception: The exception caught.
    """
    await ctx.send(str(exception), hidden=True)


@bot.event
async def on_component_callback_error(ctx: ComponentContext, exception: Exception):
    """
    Event triggered when an error occurs during the execution of a component callback.

    :param ctx: The context.
    :param exception: The exception caught.
    :return:
    """
    await ctx.send(str(exception), hidden=True)


@slash.slash(
    name='list',
    description="Affiche la liste des sessions à venir."
)
async def list_sessions(ctx: SlashContext):
    """
    Slash command to list and show all the future sessions.

    :param ctx: The context.
    """
    embed, components = get_session_list_message()
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='show',
    description="Affiche les détails de la n-ième prochaine session.",
    options=[
        {
            'name': 'n',
            'description': "L'indice de la session à afficher dans la liste de toutes les futures sessions.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        }
    ]
)
async def show(ctx: SlashContext, n: int):
    """
    Slash command which sends an embed of the nth next session with its components.

    :param ctx: The context.
    :param n: The index of the nth session to look for.
    """
    # Find nth next session
    session = Session.from_index(db, n)

    # Show the details of the session
    embed, components = get_session_details_message(session)
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='next',
    description="Affiche les détails de la prochaine session. Équivalent à `/show 1`."
)
async def show_next(ctx: SlashContext):
    """
    Slash command which sends an embed of the next session with its components. Equivalent to `/show 1`.

    :param ctx: The context.
    """
    # Find next session
    session = Session.from_index(db, 1)

    # Show the details of the session
    embed, components = get_session_details_message(session)
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='create',
    description="Crée une session avec les informations données.",
    options=[
        {
            'name': 'day',
            'description':
                "Le jour de ta session (mois courant si le jour n'est pas encore passé, mois suivant sinon).",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        },
        {
            'name': 'start_hour',
            'description': "L'heure de début de ta session. Un nombre à virgule est autorisé pour les minutes.",
            'type': SlashCommandOptionType.STRING,
            'required': 'true'
        },
        {
            'name': 'end_hour',
            'description': "L'heure de fin de ta session. Un nombre à virgule est autorisé pour les minutes.",
            'type': SlashCommandOptionType.STRING,
            'required': 'true'
        },
        {
            'name': 'places',
            'description': "Le nombre de participants que peut accueillir ta session, sans te compter.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        },
        {
            'name': 'address',
            'description': "L\'adresse de chez toi. Tu peux ne pas l\'indiquer.",
            'type': SlashCommandOptionType.STRING,
            'required': 'false'
        },
        {
            'name': 'comment',
            'description': "Note toute information supplémentaire que tu juges utile ici.",
            'type': SlashCommandOptionType.STRING,
            'required': 'false'
        }
    ]
)
async def create(ctx: SlashContext, day: int, start_hour: str, end_hour: str, places: int,
                 address: str = None, comment: str = None):
    """
    Slash command to create a session with the specified information.

    :param ctx: The context.
    :param day: The day of the session.
    :param start_hour: The start hour of the session.
    :param end_hour: The end hour of the session.
    :param places: The number of places available for the session.
    :param address: The address of the session.
    :param comment: An extra comment about the session.
    """
    # Get start and end dates of the session
    date_start, date_end = Session.get_dates(day, float(start_hour), float(end_hour))

    # Add the session in database and get the created session instance
    created_session = create_session(User.from_author(ctx.author), date_start, date_end, places, address, comment)

    # Show the details of the created session
    embed, components = get_session_details_message(created_session)
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='update',
    description="Modifie la n-ième prochaine session avec les informations données.",
    options=[
        {
            'name': 'n',
            'description': "L'indice de la session à modifier dans la liste de toutes les futures sessions.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        },
        {
            'name': 'places',
            'description': "Le nombre de participants que peut accueillir ta session, sans te compter.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'false'
        },
        {
            'name': 'address',
            'description': "L\'adresse de chez toi. Tu peux ne pas l\'indiquer.",
            'type': SlashCommandOptionType.STRING,
            'required': 'false'
        },
        {
            'name': 'comment',
            'description': "Note toute information supplémentaire que tu juges utile ici.",
            'type': SlashCommandOptionType.STRING,
            'required': 'false'
        }
    ]
)
async def update(ctx: SlashContext, n: int, places: int = None, address: str = None, comment: str = None):
    """
    Slash command to update the nth next session with the specified information.

    :param ctx: The context.
    :param n: The index of the nth session to update.
    :param places: The number of places available for the session.
    :param address: The address of the session.
    :param comment: An extra comment about the session.
    """
    # Find the session to update
    session = Session.from_index(db, n)

    # Check if the user is the host (only the host can update its session)
    if not session.is_host(User.from_author(ctx.author)):
        raise UserIsNotHostError()

    # Update the session in the database
    update_session(session, places, address, comment)

    # Show the details of the updated session
    embed, components = get_session_details_message(session)
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='delete',
    description="Supprime la n-ième prochaine session (si tu en es l'hôte).",
    options=[
        {
            'name': 'n',
            'description': "L'indice de la session à supprimer dans la liste de toutes les futures sessions.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        }
    ]
)
async def delete(ctx: SlashContext, n: int):
    """
    Slash command to delete the nth next session.

    :param ctx: The context.
    :param n: The index of the nth session to delete.
    """
    # Find the session to delete
    session = Session.from_index(db, n)

    # Check if the user is the host (only the host can delete its session)
    if not session.is_host(User.from_author(ctx.author)):
        raise UserIsNotHostError()

    # Delete session
    db['session'].delete_one({'_id': session.id})

    # Send a success message
    await ctx.send("Ta session a bien été supprimée !", hidden=True)


@slash.slash(
    name='join',
    description="Rejoins la n-ième prochaine session en précisant l\'équipement apporté.",
    options=[
        {
            'name': 'n',
            'description': "L'indice de la session à rejoindre dans la liste de toutes les futures sessions.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        },
        {
            'name': 'consoles',
            'description': "Le nombre de Switch que tu apportes. Vaut 0 si non précisé.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'false'
        },
        {
            'name': 'screens',
            'description': "Le nombre d\'écrans que tu apportes. Vaut 0 si non précisé.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'false'
        },
        {
            'name': 'adapters',
            'description': "Le nombre d\'adaptateurs GC que tu apportes. Vaut 0 si non précisé.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'false'
        }
    ]
)
async def join(ctx: SlashContext, n: int, consoles: int = 0, screens: int = 0, adapters: int = 0):
    """
    Slash command to join the nth next session with the specified equipment.

    :param ctx: The context.
    :param n: The index of the nth session to join.
    :param consoles: The number of consoles the user brings to the session.
    :param screens: The number of screens the user brings to the session.
    :param adapters: The number of adapters the user brings to the session.
    """
    # Find the session to join
    session = Session.from_index(db, n)

    # Join the session
    user = User.from_author(ctx.author, consoles, screens, adapters)
    join_session(session, user)

    # Show updated session
    embed, components = get_session_details_message(session)
    await ctx.send(embed=embed, components=components)


@slash.slash(
    name='leave',
    description="Quitte la n-ième prochaine session.",
    options=[
        {
            'name': 'n',
            'description': "L'indice de la session à rejoindre dans la liste de toutes les futures sessions.",
            'type': SlashCommandOptionType.INTEGER,
            'required': 'true'
        }
    ]
)
async def leave(ctx: SlashContext, n: int):
    """
    Slash command to leave the nth next session if the user participates in it.

    :param ctx: The context.
    :param n: The index of the nth session to leave.
    """
    # Find session to leave
    session = Session.from_index(db, n)

    # Leave the session
    leave_session(session, User.from_author(ctx.author))

    # Send the embed of the updated session
    embed, components = get_session_details_message(session)
    await ctx.send(embed=embed, components=components)


@slash.component_callback()
async def dropdown_select_session_callback(ctx: ComponentContext):
    """
    The callback after the used chose a session to be detailed in the dropdown.

    :param ctx: The context.
    """
    # Find selected session
    selected_session = Session.from_index(db, int(ctx.selected_options[0]))

    # Show the details of the session
    embed, components = get_session_details_message(selected_session)
    await ctx.edit_origin(embed=embed, components=components)


@slash.component_callback()
async def btn_join_session_callback(ctx: ComponentContext):
    """
    The callback after the user clicked on the button to join the displayed session.

    :param ctx: The context.
    """
    # Find the index of the session with the title of the embed origin message
    n = Session.get_index_from_title(ctx.origin_message.embeds[0].title)

    # Find the session to join
    session = Session.from_index(db, n)

    # Join the session
    join_session(session, User.from_author(ctx.author))

    # Update the embed
    embed, components = get_session_details_message(session)
    await ctx.edit_origin(embed=embed, components=components)


@slash.component_callback()
async def btn_leave_session_callback(ctx: ComponentContext):
    """
    The callback after the user clicked on the button to leave the displayed session.

    :param ctx: The context.
    """
    # Find the index of the session with the title of the embed origin message
    n = Session.get_index_from_title(ctx.origin_message.embeds[0].title)

    # Find the session to leave
    session = Session.from_index(db, n)

    # Leave the session
    leave_session(session, User.from_author(ctx.author))

    # Update the embed
    embed, components = get_session_details_message(session)
    await ctx.edit_origin(embed=embed, components=components)


@slash.component_callback()
async def btn_bring_switch_callback(ctx: ComponentContext):
    """
    The callback after the user clicked on the button to bring a console to the session.

    :param ctx: The context.
    """
    # Find the index of the session with the title of the embed origin message
    n = Session.get_index_from_title(ctx.origin_message.embeds[0].title)

    # Find the concerned session
    session = Session.from_index(db, n)

    # Update the user's equipment
    bring_equipment(session, User.from_author(ctx.author), Equipment.Console)

    # Update the embed
    embed, components = get_session_details_message(session)
    await ctx.edit_origin(embed=embed, components=components)


@slash.component_callback()
async def btn_bring_screen_callback(ctx: ComponentContext):
    """
    The callback after the user clicked on the button to bring a screen to the session.

    :param ctx: The context.
    """
    # Find the index of the session with the title of the embed origin message
    n = Session.get_index_from_title(ctx.origin_message.embeds[0].title)

    # Find the concerned session
    session = Session.from_index(db, n)

    # Update the user's equipment
    bring_equipment(session, User.from_author(ctx.author), Equipment.Screen)

    # Update the embed
    embed, components = get_session_details_message(session)
    await ctx.edit_origin(embed=embed, components=components)


@slash.component_callback()
async def btn_bring_adapter_callback(ctx: ComponentContext):
    """
    The callback after the user clicked on the button to bring an adapter to the session.

    :param ctx: The context.
    """
    # Find the index of the session with the title of the embed origin message
    n = Session.get_index_from_title(ctx.origin_message.embeds[0].title)

    # Find the concerned session
    session = Session.from_index(db, n)

    # Update the user's equipment
    bring_equipment(session, User.from_author(ctx.author), Equipment.Adapter)

    # Update the embed
    embed, components = get_session_details_message(session)
    await ctx.edit_origin(embed=embed, components=components)


if __name__ == '__main__':
    bot.run(BOT_TOKEN)
