from discord.ext.commands import Bot


class CustomEmojis:
    switch_emoji = None
    screen_emoji = None
    adapter_emoji = None

    def __init__(self, bot: Bot):
        CustomEmojis.switch_emoji = bot.get_emoji(801390051463397386)
        CustomEmojis.screen_emoji = bot.get_emoji(801390701958791189)
        CustomEmojis.adapter_emoji = bot.get_emoji(885488021355495444)
        print(bot.emojis)
