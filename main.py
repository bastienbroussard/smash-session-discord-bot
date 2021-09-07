import datetime
from dateutil.relativedelta import relativedelta
import locale
from urllib.parse import quote_plus
from math import modf
import os
from dotenv import load_dotenv

import discord
from pymongo import MongoClient
from bson.objectid import ObjectId

# Sensitive information are stored in .env file not present in the repository
load_dotenv()
USER = quote_plus(os.environ('SMASH_SESSION_DB_USER'))
PASS = quote_plus(os.environ('SMASH_SESSION_DB_PASS'))
SERVER = os.environ('SMASH_SESSION_DB_SERVER')
DATABASE = os.environ('SMASH_SESSION_DB_DATABASE')
BOT_TOKEN = os.environ('SMASH_SESSION_BOT_TOKEN')


class DiscordClient(discord.Client):
    def __init__(self, db, **options):
        super().__init__(**options)
        locale.setlocale(locale.LC_TIME, 'fr_FR')
        self.db = db
        self.previous_message = None
        self.previous_session = None
        self.switch_emoji = None
        self.screen_emoji = None
        self.commands = {
            'help': self.show_help,
            'create': self.create_session,
            'update': self.update_session,
            'list': self.list_sessions,
            'show': self.show_session,
            'next': self.next_session,
            'join': self.join_session,
            'leave': self.leave_session,
            'delete': self.delete_session
        }

    async def on_ready(self):
        self.switch_emoji = [str(emoji) for emoji in self.emojis if emoji.name == 'switch'][0]
        self.screen_emoji = [str(emoji) for emoji in self.emojis if emoji.name == 'screen'][0]
        print('connected')

    async def on_message(self, message):
        if message.content.startswith('!ses ') or message.content.startswith('!session ') or message.content == '!ses':
            # Delete user message
            await message.delete()

            # Delete bot previous message
            if self.previous_message is not None:
                await self.previous_message.delete()

            # Reset previous session
            self.previous_session = None

            # Get command and args
            args = message.content.split(' ')

            # No command is provided
            if len(args) == 1:
                self.previous_message = await self.show_help(message, [])

            # A valid command is provided
            elif args[1] in self.commands:
                try:
                    self.previous_message = await self.commands[args[1]](message, args[2:])
                except (IndexError, ValueError, TypeError):
                    self.previous_message = await message.channel.send(
                        'Certaines informations sont incorrectes...\n'
                        f'Tape `!ses help {args[1]}` pour en savoir plus.'
                    )

            # An invalid command is provided
            else:
                self.previous_message = await message.channel.send(
                    'Je ne connais pas cette commande... Tape `!ses help` pour voir ce que je sais faire !'
                )

    async def on_reaction_add(self, reaction, reaction_author):
        if not reaction_author.bot and len(reaction.message.reactions) > 0 and reaction.message.reactions[0].me:
            # Delete bot previous message
            if self.previous_message is not None:
                await self.previous_message.delete()

            # If user is host
            session = self.previous_session
            if reaction_author.id == session['host']['id']:
                self.db['session'].update_one({
                    '_id': ObjectId(str(session['_id']))
                }, {
                    '$set': {
                        'host': {
                            'id': session['host']['id'],
                            'consoles': session['host']['consoles'] + int(reaction.emoji.name == 'switch'),
                            'screens': session['host']['screens'] + int(reaction.emoji.name == 'screen')
                        }
                    }
                })
                self.previous_message = await self.show_session(reaction.message, [str(session['_id'])])

            # If user is a participant
            elif reaction_author.id in [user['id'] for user in session['participants']]:
                participants = session['participants']
                for i, participant in enumerate(participants):
                    if participant['id'] == reaction_author.id:
                        participants[i]['consoles'] += int(reaction.emoji.name == 'switch')
                        participants[i]['screens'] += int(reaction.emoji.name == 'screen')

                self.db['session'].update_one({
                    '_id': ObjectId(str(session['_id']))
                }, {
                    '$set': {'participants': participants}
                })
                self.previous_message = await self.show_session(reaction.message, [str(session['_id'])])

            # If user is a new member of the session
            else:
                reaction.message.author = reaction_author
                self.previous_message = await self.join_session(reaction.message, [
                    str(session['_id']), int(reaction.emoji.name == 'switch'), int(reaction.emoji.name == 'screen')
                ])

    async def show_help(self, message, args):
        # If no command is provided, list all commands
        if len(args) == 0:
            help_str = 'Voici ce que je sais faire :\n'
            for command in self.commands:
                command_help = self.db['help'].find_one({'command': command})
                help_str += f'{command_help["usage"]}: {command_help["desc"]}\n'
            return await message.channel.send(help_str)

        # If a command is provided and if it exists, show detailed help of this command
        if args[0] in self.commands:
            command_help = self.db['help'].find_one({'command': args[0]})
            return await message.channel.send(
                f'**__Utilisation :__**\n{command_help["usage"]}\n\n'
                f'**__Description :__**\n{command_help["desc"]}\n\n'
                f'**__Arguments :__**\n{command_help["args"]}\n\n'
                f'**__Exemple :__**\n{command_help["example"]}'
            )

        # Else, show error
        return await message.channel.send(
            f'Je ne peux pas afficher l\'aide détaillée de `{args[0]}` car je ne connais pas cette commande...'
        )

    async def create_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['create'])

        # If less than 3 arguments are provided, show error
        if len(args) < 3:
            command_help = self.db['help'].find_one({'command': 'create'})
            return await message.channel.send(
                f'Il me manque des informations !\nUtilisation: {command_help["usage"]}\n'
                'Tape `!ses help create` pour en savoir plus.'
            )

        # Dates
        day_start = int(args[0])
        hour_start = float(args[1])
        hour_end = float(args[2])
        date_now = [int(x) for x in datetime.datetime.now().strftime('%Y %m %d').split(' ')]
        date_start = datetime.datetime(year=date_now[0], month=date_now[1], day=day_start,
                                       hour=int(hour_start), minute=int(modf(hour_start)[0] / 100 * 6000))
        date_end = datetime.datetime(year=date_now[0], month=date_now[1], day=day_start,
                                     hour=int(hour_end), minute=int(modf(hour_end)[0] / 100 * 6000))
        if date_now[2] > day_start:
            date_start += relativedelta(months=+1)
            date_end += relativedelta(months=+1)
        if hour_end < hour_start:
            date_end += relativedelta(hours=+24)

        # Places
        places = int(args[3]) if len(args) > 3 else None
        if places is not None:
            if places < 0:
                raise ValueError()

        # Insert in database
        inserted_id = str(self.db['session'].insert_one({
            'host': {
                'id': message.author.id,
                'consoles': 0,
                'screens': 0
            },
            'date_start': date_start,
            'date_end': date_end,
            'places': places,
            'participants': []
        }).inserted_id)

        # Show created session
        return await self.show_session(message, [inserted_id])

    async def update_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['update'])

        # If less than 4 arguments are provided, show error
        if len(args) < 4:
            command_help = self.db['help'].find_one({'command': 'update'})
            return await message.channel.send(
                f'Il me manque des informations !\nUtilisation: {command_help["usage"]}\n'
                'Tape `!ses help update` pour en savoir plus.'
            )

        # Check if user is the host of the session
        session = self._get_nth_session(int(args[0]))
        if message.author.id != session['host']['id']:
            return await message.channel.send('Tu n\'es pas l\'hôte de la session, tu ne peux pas la modifier !')

        # Dates
        day_start = int(args[1])
        hour_start = float(args[2])
        hour_end = float(args[3])
        date_now = [int(x) for x in datetime.datetime.now().strftime('%Y %m %d').split(' ')]
        date_start = datetime.datetime(year=date_now[0], month=date_now[1], day=day_start,
                                       hour=int(hour_start), minute=int(modf(hour_start)[0] / 100 * 6000))
        date_end = datetime.datetime(year=date_now[0], month=date_now[1], day=day_start,
                                     hour=int(hour_end), minute=int(modf(hour_end)[0] / 100 * 6000))
        if date_now[2] > day_start:
            date_start += relativedelta(months=+1)
            date_end += relativedelta(months=+1)
        if hour_end < hour_start:
            date_end += relativedelta(hours=+24)

        # Places
        places = int(args[4]) if len(args) > 4 else None
        if places is not None:
            if places < 0:
                raise ValueError()

        # Update session
        self.db['session'].update_one({
            '_id': ObjectId(str(session['_id']))
        }, {
            '$set': {
                'date_start': date_start,
                'date_end': date_end,
                'places': places
            }
        })

        # Show updated session
        return await self.show_session(message, [str(session['_id'])])

    async def list_sessions(self, message, args):
        # Check if there is no session
        now = datetime.datetime.now()
        sessions = list(self.db['session'].find({'date_start': {'$gt': now}}).sort([('date_start', 1), ('_id', 1)]))
        if len(sessions) == 0:
            return await message.channel.send(
                'Il n\'y a aucune session de prévue pour le moment...\n'
                'Crées-en une avec la commande `create` si tu veux !'
            )

        # Create embed
        embed = discord.Embed(title='Sessions à venir')
        for session in sessions:
            embed.add_field(name=session['date_start'].strftime('%A %d %B: %H:%M').title() + ' → ' +
                                 session['date_end'].strftime('%H:%M'),
                            value=f'Hôte: {self._get_user_str(session["host"])}\n'
                                  f'Participants: {len(session["participants"])}' +
                                  (f' / {session["places"]}' if session["places"] is not None else ''),
                            inline=False)
        return await message.channel.send(embed=embed)

    async def show_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['show'])

        # Find session by id
        if len(args[0]) == 24:
            session = self.db['session'].find_one({'_id': ObjectId(args[0])})
        # Find nth next session
        else:
            session = self._get_nth_session(int(args[0]))

        # Participants
        participants = ''
        for participant in session['participants']:
            participants += self._get_user_str(participant) + '\n'

        # Create embed
        embed = discord.Embed(title=session['date_start'].strftime('%A %d %B: %H:%M').title() + ' → ' +
                                    session['date_end'].strftime('%H:%M'))
        embed.add_field(name='Hôte', value=self._get_user_str(session["host"]))
        embed.add_field(name=f'Participants ({len(session["participants"])}' +
                             (f' / {session["places"]}' if session["places"] is not None else '') + ')',
                        value=participants if participants != '' else '\b')

        # Send embed
        bot_message = await message.channel.send(embed=embed)

        # Assign session to catch emojis
        self.previous_session = session

        # Add equipment reactions to embed
        await bot_message.add_reaction(self.switch_emoji)
        await bot_message.add_reaction(self.screen_emoji)
        return bot_message

    async def next_session(self, message, args):
        # Show next session
        return await self.show_session(message, ['1'])

    async def join_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['join'])

        # Equipment
        consoles = int(args[1]) if len(args) > 1 else 0
        screens = int(args[2]) if len(args) > 2 else 0

        # Check if consoles or screens are negative
        if consoles < 0 or screens < 0:
            raise ValueError

        # Find session by id
        if len(args[0]) == 24:
            session = self.db['session'].find_one({'_id': ObjectId(args[0])})
        # Find nth next session
        else:
            session = self._get_nth_session(int(args[0]))

        # Check if user is already a member of the session
        if message.author.id == session['host']['id']:
            return await message.channel.send('Euh... Tu es déjà l\'hôte de cette session...')
        if message.author.id in [user['id'] for user in session['participants']]:
            return await message.channel.send('Tu participes déjà à cette session !')

        # Check if there are available places
        if session['places'] != None:
            if len(session['participants']) >= session['places']:
                return await message.channel.send('Il n\'y a plus de place dans cette session...')

        # Join session
        self.db['session'].update_one({
            '_id': ObjectId(str(session['_id']))
        }, {
            '$set': {
                'participants': session['participants'] + [{
                    'id': message.author.id,
                    'consoles': consoles,
                    'screens': screens
                }]
            }
        })

        # Show updated session
        return await self.show_session(message, [str(session['_id'])])

    async def leave_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['leave'])

        # Check if user is not the host
        session = self._get_nth_session(int(args[0]))
        if message.author.id == session['host']['id']:
            return await message.channel.send(
                'Tu es l\'hôte de la session ! Utilise la commande `delete` si tu veux supprimer la session.'
            )

        # Check if user is not a member of the session
        if message.author.id not in [user['id'] for user in session['participants']]:
            return await message.channel.send('Euh... Tu ne participes pas à cette session...')

        # Leave session
        self.db['session'].update_one({
            '_id': ObjectId(str(session['_id']))
        }, {
            '$set': {
                'participants': [user for user in session['participants'] if user['id'] != message.author.id]
            }
        })
        return await self.show_session(message, [str(session['_id'])])

    async def delete_session(self, message, args):
        # If no argument is provided, show detailed help
        if len(args) == 0:
            return await self.show_help(message, ['delete'])

        # Check if user is the host of the session
        session = self._get_nth_session(int(args[0]))
        if message.author.id != session['host']['id']:
            return await message.channel.send('Tu n\'es pas l\'hôte de la session, tu ne peux pas la supprimer !')

        # Delete session
        self.db['session'].delete_one({'_id': ObjectId(str(session['_id']))})

        # Success message
        return await message.channel.send('La session a bien été supprimée !')

    def _get_nth_session(self, n):
        now = datetime.datetime.now()
        return self.db['session'] \
            .find({'date_start': {'$gt': now}}) \
            .sort([('date_start', 1), ('_id', 1)]) \
            .skip(n - 1).limit(1)[0]

    def _get_user_str(self, user):
        print(self.users)
        user_str = f'@{user["username"]} #{user["discriminator"]} '
        for _ in range(user['consoles']):
            user_str += f'{self.switch_emoji} '
        for _ in range(user['screens']):
            user_str += f'{self.screen_emoji} '
        return user_str


if __name__ == '__main__':
    db_client = MongoClient(f'mongodb+srv://{USER}:{PASS}@{SERVER}/{DATABASE}?retryWrites=true&w=majority')[DATABASE]
    discord_client = DiscordClient(db_client)
    discord_client.run(BOT_TOKEN)
