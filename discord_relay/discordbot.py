import discord
from discord.ext import tasks
import json
import greenstalk

#from django.conf import settings
from settings import DISCORD_TOKEN

_TOKEN = DISCORD_TOKEN

greenclient = greenstalk.Client(('127.0.0.1', 11300),watch=['EvToDiscord','DiscordToEv'])


class EvenniaRelay(discord.Client):
    async def on_ready(self):
        print(f'Logged in to Discord as {self.user} (ID: {self.user.id})')
        print('------')
        # start the task to run in the background
        self.relay.start()

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        send_msg = { "txt": message.content, "user": message.author.display_name }
        greenclient.use('DiscordToEv')
        greenclient.put(json.dumps(send_msg))

    @tasks.loop(seconds=5.0)
    async def relay(self):
        greenclient.use('EvToDiscord')

        try:
            job = greenclient.peek_ready()
            greenclient.reserve(job.id)
        except greenstalk.NotFoundError:
            # no messages to pass on
            return
        channel_id, message = json.loads(job.body)
        greenclient.delete(job)
        channel = self.get_channel(int(channel_id))
        await channel.send(message)

    @relay.before_loop
    async def before_relay(self):
        print('waiting...')
        await self.wait_until_ready()

discordclient = EvenniaRelay(intents=discord.Intents.default())
discordclient.run(_TOKEN)
