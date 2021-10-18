from discord.ext.commands import Bot


class CustomEmojis:
    switch_emoji = None
    screen_emoji = None
    adapter_emoji = None

    def __init__(self, bot: Bot):
        CustomEmojis.switch_emoji = [emoji for emoji in bot.emojis if emoji.name == 'switch'][0]
        CustomEmojis.screen_emoji = [emoji for emoji in bot.emojis if emoji.name == 'screen'][0]
        CustomEmojis.adapter_emoji = [emoji for emoji in bot.emojis if emoji.name == 'gc'][0]
        print(bot.emojis)
