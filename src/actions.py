# General imports
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os
from pymongo import MongoClient
import certifi
from datetime import datetime
from bson.objectid import ObjectId

# Discord-relative imports
from discord import Embed
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_actionrow, create_select, create_select_option, create_button

# Local-relative imports
from session import Session
from user import User
from exceptions import *
from custom_emojis import CustomEmojis
from equipment import Equipment


# Sensitive information are stored in .env file not present in the repository
load_dotenv()
USER = quote_plus(os.environ.get('SMASH_SESSION_DB_USER'))
PASS = quote_plus(os.environ.get('SMASH_SESSION_DB_PASS'))
SERVER = os.environ.get('SMASH_SESSION_DB_SERVER')
DATABASE = os.environ.get('SMASH_SESSION_DB_DATABASE')
BOT_TOKEN = os.environ.get('SMASH_SESSION_BOT_TOKEN')

# Initialize database
ca = certifi.where()
db = MongoClient(f'mongodb+srv://{USER}:{PASS}@{SERVER}/{DATABASE}?retryWrites=true&w=majority', tlsCAFile=ca)[DATABASE]


def get_session_list_message() -> (Embed, list):
    """
    Find all the future sessions and return them as a list in an embed. Create also the appropriated dropdown menu to
    show the details of a session.

    :return: A tuple (Embed, list of components) representing the bot message to be sent.
    """
    # Get all the future sessions
    future_sessions = Session.get_future_sessions(db)

    # Check if there is no session
    if len(future_sessions) == 0:
        raise NoSessionAvailableError()

    # Create embed
    embed = Embed(title="Sessions à venir")
    dropdown_options = []
    for session in future_sessions:
        embed.add_field(name=session.title,
                        value=f"Hôte: <@{session.host.id}>\n"
                              f"Participants: {session.nb_participants} / {session.places}",
                        inline=False)
        dropdown_options.append(create_select_option(f"#{session.index}   Session chez {session.host.name}",
                                                     value=str(session.index)))

    # Create dropdown
    dropdown = create_select(
        options=dropdown_options,
        placeholder="Sélectionne une session pour afficher ses détails :",
        min_values=1,
        max_values=1,
        custom_id='dropdown_select_session_callback'
    )

    # Return embed and components
    return embed, [create_actionrow(dropdown)]


def get_session_details_message(session: Session) -> (Embed, list):
    """
    From a given session, return an embed of its details. Create also the appropriated buttons to perform actions based
    on the displayed session.

    :param session: The session to be detailed.
    :return: A tuple (Embed, list of components) representing the bot message to be sent.
    """
    # Create embed
    embed = Embed(title=session.title)
    embed.add_field(name="Hôte", value=session.host.details)
    embed.add_field(name=f"Participants ({session.nb_participants} / {session.places})",
                    value=session.get_participants_details())
    embed.add_field(name="Adresse",
                    value=session.address,
                    inline=False)
    if session.comment is not None:
        embed.add_field(name="Commentaire",
                        value=session.comment,
                        inline=False)

    # Create buttons
    components = [create_actionrow(
        create_button(style=ButtonStyle.blurple, label="Je participe !", custom_id='btn_join_session_callback'),
        create_button(style=ButtonStyle.red, label="Je me désinscris...", custom_id='btn_leave_session_callback')
    ), create_actionrow(
        create_button(emoji=CustomEmojis.switch_emoji, style=ButtonStyle.grey,
                      label="J'apporte une console", custom_id='btn_bring_switch_callback'),
        create_button(emoji=CustomEmojis.screen_emoji, style=ButtonStyle.grey,
                      label="J'apporte un écran", custom_id='btn_bring_screen_callback'),
        create_button(emoji=CustomEmojis.adapter_emoji, style=ButtonStyle.grey,
                      label="J'apporte un adaptateur GC", custom_id='btn_bring_adapter_callback')
    )]

    # Return embed and components
    return embed, components


def create_session(host: User, date_start: datetime, date_end: datetime, places: int,
                   address: str, comment: str) -> Session:
    """
    Add to the database a new session hosted by the given user and with the given details.

    :param host: The User who hosts the session.
    :param date_start: The start date and time of the session.
    :param date_end: The end date and time of the session.
    :param places: The number of places available for the session.
    :param address: The address of the session.
    :param comment: An extra comment about the session.
    :return: A Session instance corresponding to the created session.
    """
    # Places
    if places < 0:
        raise ValueError("Tu ne peux pas avoir un nombre négatif de places chez toi ! :sweat_smile:")

    # Insert in database
    inserted_id = db['session'].insert_one({
        'host': {
            'id': host.id,
            'name': host.name,
            'discriminator': host.discriminator,
            'consoles': 0,
            'screens': 0,
            'adapters': 0
        },
        'date_start': date_start,
        'date_end': date_end,
        'places': places,
        'address': address,
        'comment': comment,
        'participants': []
    }).inserted_id

    # Get the session instance of the created session
    return Session.from_id(db, inserted_id)


def update_session(session: Session, places: int, address: str, comment: str):
    """
    Update the session wit the specified details.

    :param session: The session to update.
    :param places: The number of places available for the session.
    :param address: The address of the session.
    :param comment: An extra comment about the session.
    :return:
    """
    # Update session and prepare fields to update
    fields = {}
    if places is not None:
        session.places = places
        fields['places'] = places
    if address is not None:
        session.address = address
        fields['address'] = address
    if comment is not None:
        session.comment = comment
        fields['comment'] = comment

    # Update database
    db['session'].update_one({
        '_id': session.id
    }, {
        '$set': {
            'date_start': date_start,
            'date_end': date_end,
            'places': places
        }
    })


def join_session(session: Session, joining_user: User):
    """
    Add the given user to the list of participants of the given session with the specified equipment.

    :param session: The session to join.
    :param joining_user: The user who wants to join the session.
    """
    # Join session
    session.add_participant(joining_user)

    # Update database
    db['session'].update_one({
        '_id': session.id
    }, {
        '$set': {
            'participants': [user.data for user in session.participants]
        }
    })


def leave_session(session: Session, leaving_user: User):
    """
    Remove the given user from the list of participants of the given session if he participates in it.

    :param session: The session to leave.
    :param leaving_user: The user who wants to leave the session.
    """
    # Leave session
    session.remove_participant(leaving_user)

    # Update database
    db['session'].update_one({
        '_id': session.id
    }, {
        '$set': {
            'participants': [user.data for user in session.participants]
        }
    })


def bring_equipment(session: Session, user: User, equipment: Equipment):
    """
    Update the equipment brought by the given user to the given session.

    :param session: The session the user participates in.
    :param user: The user to be updated.
    :param equipment: The kind of equipment the user brings.
    """
    if session.is_host(user):
        # Update user's equipment
        session.host.add_equipment(equipment)

        # Update database
        db['session'].update_one({
            '_id': session.id
        }, {
            '$set': {
                'host': session.host.data
            }
        })

    elif session.is_participant(user):
        # Update user's equipment
        for participant in session.participants:
            if participant.id == user.id:
                participant.add_equipment(equipment)

        # Update database
        db['session'].update_one({
            '_id': session.id
        }, {
            '$set': {
                'participants': [participant.data for participant in session.participants]
            }
        })

    else:
        raise UserIsNotParticipantError()

