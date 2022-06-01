#############
#  IMPORTS  #
#############
# General imports
import discord.user

# Local imports
from custom_emojis import CustomEmojis
from equipment import Equipment
from exceptions import TooManyEquipmentError

###############
#  CONSTANTS  #
###############
MAX_CONSOLES = 3
MAX_SCREENS = 3
MAX_ADAPTERS = 3

class User:
    ##################
    #  CONSTRUCTORS  #
    ##################
    def __init__(self, data: dict):
        """
        Instantiate a User object.

        :param data: The user data retrieved from the database.
        """
        self._id = data['id']
        self._name = data['name']
        self._discriminator = data['discriminator']
        self._consoles = data['consoles']
        self._screens = data['screens']
        self._adapters = data['adapters']

        # Check if any equipment is negative
        if self._consoles < 0 or self._screens < 0 or self._adapters < 0:
            raise ValueError("Tu ne peux pas apporter un nombre négatif d'équipement... :sweat_smile:")

        # Check if any equipment is too high
        if self._consoles > MAX_CONSOLES or self._screens > MAX_SCREENS or self._adapters > MAX_ADAPTERS:
            raise TooManyEquipmentError()

    @classmethod
    def from_author(cls, author: discord.user.User, consoles: int = 0, screens: int = 0, adapters: int = 0):
        return cls({
            'id': author.id,
            'name': author.name,
            'discriminator': author.discriminator,
            'consoles': consoles,
            'screens': screens,
            'adapters': adapters
        })

    #############
    #  METHODS  #
    #############
    def add_equipment(self, equipment: Equipment):
        """
        Add the given equipment to the equipment count of the user.

        :param equipment: The kind of equipment to be incremented.
        """
        if equipment == Equipment.Console:
            if self._consoles + 1 > MAX_CONSOLES:
                raise TooManyEquipmentError()
            self._consoles += 1
        elif equipment == Equipment.Screen:
            if self._screens + 1 > MAX_SCREENS:
                raise TooManyEquipmentError()
            self._screens += 1
        elif equipment == Equipment.Adapter:
            if self._adapters + 1 > MAX_ADAPTERS:
                raise TooManyEquipmentError()
            self._adapters += 1

    ################
    #  PROPERTIES  #
    ################
    @property
    def data(self) -> dict:
        """
        Getter for data.

        :return: The data attribute.
        """
        return {
            'id': self._id,
            'name': self._name,
            'discriminator': self._discriminator,
            'consoles': self._consoles,
            'screens': self._screens,
            'adapters': self._adapters
        }

    @property
    def id(self) -> int:
        """
        Getter for id.

        :return: The id attribute.
        """
        return self._id

    @property
    def name(self) -> str:
        """
        Getter for name.

        :return: The name attribute.
        """
        return self._name

    @property
    def discriminator(self) -> str:
        """
        Getter for discriminator.

        :return: The discriminator attribute.
        """
        return self._discriminator

    @property
    def consoles(self) -> int:
        """
        Getter for consoles.

        :return: The consoles attribute.
        """
        return self._consoles

    @property
    def screens(self) -> int:
        """
        Getter for screens.

        :return: The screens attribute.
        """
        return self._screens

    @property
    def adapters(self) -> int:
        """
        Getter for adapters.

        :return: The adapters attribute.
        """
        return self._adapters

    @property
    def details(self) -> str:
        """
        Returns the id of the user followed by the equipment he brings to the session.

        :return: A string representing the user details.
        """
        user_str = f"<@{self._id}> "
        for _ in range(self._consoles):
            user_str += f"<:switch:801390051463397386> "
        for _ in range(self._screens):
            user_str += f"<:screen:801390701958791189> "
        for _ in range(self._adapters):
            user_str += f"<:gc:885488021355495444> "
        return user_str
