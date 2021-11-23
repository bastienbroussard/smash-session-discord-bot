class NoSessionAvailableError(Exception):
    def __str__(self) -> str:
        return (
            "Il n'y a aucune session de prévue pour le moment...\n"
            "Crées-en une avec la commande `/create` si tu veux !"
        )


class UserIsAlreadyHostError(Exception):
    def __str__(self) -> str:
        return "Euh... Tu essayes de rejoindre ta propre session ? :sweat_smile:"


class UserIsAlreadyParticipantError(Exception):
    def __str__(self) -> str:
        return "Tu participes déjà à cette session !"


class SessionIsFullError(Exception):
    def __str__(self) -> str:
        return "Il n'y a plus de place dans cette session..."


class UserIsHostError(Exception):
    def __str__(self) -> str:
        return (
            "Tu es l'hôte de la session ! "
            "Utilise la commande `/delete` si tu veux supprimer ta session... :pensive:"
        )


class UserIsNotHostError(Exception):
    def __str__(self) -> str:
        return "Tu ne peux modifier ou supprimer une session que si tu en es l'hôte..."


class UserIsNotParticipantError(Exception):
    def __str__(self) -> str:
        return "Euh... Tu ne participes pas à cette session... :sweat_smile:"


class TooManyEquipmentError(Exception):
    def __str__(self) -> str:
        return "Euh t'abuses pas un peu sur les équipements là ? :thinking:"
