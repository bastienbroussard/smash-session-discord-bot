from pymongo import MongoClient
from bson.objectid import ObjectId
from math import modf
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

from user import User
from exceptions import *


class Session:
    ##################
    #  CONSTRUCTORS  #
    ##################
    def __init__(self, data: dict, index: int):
        """
        Instantiate a Session object.

        :param data: The session data retrieved from the database.
        :param index: The index of the session in the list of the next sessions.
        """
        self._index = index
        self._id = ObjectId(str(data['_id']))
        self._date_start = data['date_start']
        self._date_end = data['date_end']
        self._places = data['places']
        self._address = data['address']
        self._comment = data['comment']
        self._host = User(data['host'])
        self._participants = [User(user) for user in data['participants']]

    @classmethod
    def from_index(cls, db: MongoClient, n: int):
        """
        Returns the nth next session.

        :param db: The MongoDB database instance.
        :param n: The index of the nth session to look for.
        :return: A Session instance.
        """
        now = datetime.now()

        try:
            return cls(db['session']
                       .find({'date_start': {'$gt': now}})
                       .sort([('date_start', 1), ('_id', 1)])
                       .skip(n - 1).limit(1)[0], n)
        except IndexError:
            if n == 1:
                raise NoSessionAvailableError()
            else:
                raise IndexError(
                    "Il n'y a pas de session correspondante...\n"
                    "Tu peux voir la liste des sessions à venir avec `/list` !"
                )
        except ValueError:
            raise ValueError("L'argument `n` ne peut pas être négatif !")

    @classmethod
    def from_id(cls, db: MongoClient, session_id: ObjectId):
        """
        Return a session found by its database id.

        :param db: The MongoDB database instance.
        :param session_id: The database id of the session to look for.
        :return: A Session instance.
        """
        future_sessions = Session.get_future_sessions(db)
        for future_session in future_sessions:
            if future_session.id == session_id:
                return future_session

    #############
    #  METHODS  #
    #############
    def is_host(self, user: User) -> bool:
        """
        Check if the user is the host of the session.

        :param user: The user to look for.
        :return: True if the user is the host of the session, False otherwise.
        """
        return self._host.id == user.id

    def is_participant(self, user: User) -> bool:
        """
        Check if the user participates to the session.

        :param user: The user to look for.
        :return: True if the user participates to the session, False otherwise.
        """
        return user.id in [participant.id for participant in self._participants]

    def add_participant(self, user: User):
        """
        Add the given user to the participants of the session.

        :param user: The user to be added.
        """
        # Check if user is not already a member of the session
        if self.is_host(user):
            raise UserIsAlreadyHostError()
        if self.is_participant(user):
            raise UserIsAlreadyParticipantError()

        # Check if there are available places
        if self.nb_participants >= self._places:
            raise SessionIsFullError()

        # Add participant
        self._participants.append(user)

    def remove_participant(self, user: User):
        """
        Remove the given user from the participants of the session.

        :param user: The user to be removed.
        """
        # Check if user is not the host
        if self.is_host(user):
            raise UserIsHostError()

        # Check if user is a member of the session
        if not self.is_participant(user):
            raise UserIsNotParticipantError()

        # Remove participant
        self._participants = [participant for participant in self._participants if participant.id != user.id]

    def get_participants_details(self) -> str:
        """
        Returns a string representation of all the participants of the session.

        :return: The string representation of the participants.
        """
        if self.nb_participants > 0:
            return '\n'.join([user.details for user in self._participants])
        else:
            return 'Aucun participant.'

    ##################
    #  PROPERTIES    #
    ##################
    @property
    def index(self) -> int:
        """
        Getter for index.

        :return: The index attribute.
        """
        return self._index

    @property
    def id(self) -> ObjectId:
        """
        Getter for id.

        :return: The id attribute.
        """
        return self._id

    @property
    def places(self) -> int:
        """
        Getter for places.

        :return: The places attribute.
        """
        return self._places

    @places.setter
    def places(self, value: int):
        """
        Setter for places.

        :param value: The new places attribute.
        """
        self._places = value

    @property
    def address(self) -> str:
        """
        Returns the address of the session if available, or custom message otherwise.

        :return: The address of the session or a custom message.
        """
        if self._address is not None:
            return self._address
        else:
            return "Demande ultérieurement en message privé !"

    @address.setter
    def address(self, value: str):
        """
        Setter for address.

        :param value: The new address attribute.
        """
        self._address = value

    @property
    def comment(self) -> str:
        """
        Getter for comment.

        :return: The comment attribute.
        """
        return self._comment

    @comment.setter
    def comment(self, value: str):
        """
        Setter for comment.

        :param value: The new comment attribute.
        """
        self._comment = value

    @property
    def host(self) -> User:
        """
        Getter for host.

        :return: The host attribute.
        """
        return self._host

    @property
    def participants(self) -> list[User]:
        """
        Getter for participants.

        :return: The participants attribute.
        """
        return self._participants

    @property
    def title(self) -> str:
        """
        Returns the title of the session as its index followed by its date and time.

        :return: The title of the session.
        """
        return (f"#{self._index}   {self._date_start.strftime('%A %d %B: %H:%M').title()} → "
                f"{self._date_end.strftime('%H:%M')}")

    @property
    def nb_participants(self) -> int:
        """
        Count the number of participants of the session.

        :return: The number of participants of the session.
        """
        return len(self._participants)

    ####################
    #  STATIC METHODS  #
    ####################
    @staticmethod
    def get_future_sessions(db: MongoClient) -> list:
        """
        Get a list of all the future sessions, sorted chronologically.

        :param db: The MongoDB database instance.
        :return: A list of Session instances containing all the future sessions.
        """
        now = datetime.now()
        return [
            Session(session, n + 1)
            for n, session in
            enumerate(db['session'].find({'date_start': {'$gt': now}}).sort([('date_start', 1), ('_id', 1)]))
        ]

    @staticmethod
    def get_dates(day: int, start_hour: float, end_hour: float) -> (datetime, datetime):
        """
        From a start hour and an end hour, returns datetime instances for the start and end of the session.

        :param day:
        :param start_hour: The start hour of the session.
        :param end_hour: The end hour of the session.
        :return: A tuple (datetime, datetime) representing respectively the start and end dates of the session.
        """
        # UX: Some people use "24" for midnight instead of "0"
        if start_hour == '24':
            start_hour = '0'
        if end_hour == '24':
            end_hour = '0'

        # Create dates in datetime format
        date_now = [int(x) for x in datetime.now().strftime('%Y %m %d').split(' ')]
        date_start = datetime(year=date_now[0], month=date_now[1], day=day,
                              hour=int(start_hour), minute=int(modf(start_hour)[0] / 100 * 6000))
        date_end = datetime(year=date_now[0], month=date_now[1], day=day,
                            hour=int(end_hour), minute=int(modf(end_hour)[0] / 100 * 6000))

        # Add one month if the day has already passed
        if date_now[2] > day:
            date_start += relativedelta(months=+1)
            date_end += relativedelta(months=+1)

        # If end hour is inferior to start hour, it means that the session lasts until the next day
        if end_hour < start_hour:
            date_end += relativedelta(hours=+24)

        return date_start, date_end

    @staticmethod
    def get_index_from_title(title: str) -> int:
        return int(re.search(r'#(\d*) ', title).group(1))
