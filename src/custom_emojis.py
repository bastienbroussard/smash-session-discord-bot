from discord.ext.commands import Bot


class CustomEmojis:
    switch_emoji = None
    screen_emoji = None
    adapter_emoji = None

    def __init__(self, bot: Bot):
        CustomEmojis.switch_emoji = bot.get_emoji(981506666287743027)
        CustomEmojis.screen_emoji = bot.get_emoji(981507321802948628)
        CustomEmojis.adapter_emoji = bot.get_emoji(981507354359136306)
