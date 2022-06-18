from django.conf import settings

from evennia.accounts.bots import Bot
from evennia import DefaultScript
from evennia.utils import create, search, logger, utils
from evennia.utils.utils import class_from_module, list_to_string
from evennia.utils.ansi import strip_ansi

import greenstalk
import json

from .settings import FORMAT_TO_EVENNIA, FORMAT_TO_DISCORD, BEANSTALK_HOST, BEANSTALK_PORT

greenclient = greenstalk.Client((BEANSTALK_HOST, BEANSTALK_PORT),watch=['EvToDiscord','DiscordToEv'])


class DiscordRelayScript(DefaultScript):
	"""
	Polls the incoming Discord message queue and relays the messages to the
	relevant Evennia bot.
	"""

	def at_script_creation(self):
		"""
		Called once, when script is created.
		"""
		self.key = "DiscordRelay"
		self.desc = "Relays incoming messages from Discord"
		self.persistent = True
		self.interval = 1
		self.db.bots = {}

	def at_start(self):
		"""
		Kick bots into gear.
		"""
		if not self.ndb.bots:
			self.ndb.bots = self.db.bots

		for bot in self.ndb.bots.values():
			if bot:
				bot.start()

	def at_repeat(self):
		"""
		Called self.interval seconds to check for new messages from Discord
		"""
		greenclient.use('DiscordToEv')
		try:
			job = greenclient.peek_ready()
			greenclient.reserve(job.id)
		except greenstalk.NotFoundError:
			# no messages to pass on
			return

		get_msg = json.loads(job.body)
		greenclient.delete(job)
		dc_chan = get_msg.pop("channel",0)
		bot = self.ndb.bots.get(dc_chan)
		if bot:
			bot.execute_cmd(**get_msg)

	def at_server_reload(self):
		self.ndb.bots = self.db.bots

	def add_bot(self, bot, dc_channel):
		if dc_channel in self.ndb.bots:
			return False
		self.db.bots[dc_channel] = bot
		self.ndb.bots = self.db.bots
		return True

	def remove_bot(self, bot):
		self.db.bots = {key: value for key, value in self.ndb.bots.items() if value != bot}
		self.ndb.bots = self.db.bots


class DiscordBot(Bot):
	"""
	Implements the evennia-facing side of a Discord bot.
	"""
	def basetype_setup(self):
		"""
		This sets up the basic properties for the bot.
		"""
		self.db.encoding = "utf-8"
		lockstring = (
			"examine:perm(Admin);edit:perm(Admin);delete:perm(Admin);"
			"boot:perm(Admin);msg:false();noidletimeout:true()"
		)
		self.locks.add(lockstring)
		# set the basics of being a bot
		self.is_bot = True

	def start(self):
		# fake connection status
		self.is_connected = True
		self.ndb.ev_channel = self.db.ev_channel
		self.ndb.dc_channel = self.db.dc_channel

	def initialize(self, ev_channel, dc_botname, dc_chan_id, **kwargs):
		channel = search.channel_search(ev_channel)
		if not channel:
			raise RuntimeError(f"Evennia Channel '{ev_channel}' not found.")
		channel = channel[0]
		channel.connect(self)
#		self.username = dc_botname
		self.db.ev_channel = channel
		self.db.dc_channel = dc_chan_id
		self.start()

	def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
		"""
		Overloading because this bot doesn't need to directly receive messages.
		"""
		return

	def at_pre_channel_msg(self, message, channel, senders=None, **kwargs):
		"""
		Formats the message to be sent to Discord.
		"""
		if senders:
			logger.log_msg(f"senders: {senders}")
			sender_string = ", ".join(sender.name for sender in senders)
			message = message.lstrip()
			# catch emotes
			if message.startswith((':',';')):
				em = ''
				message = message[1:]
			else:
				em = ':'
			message = FORMAT_TO_DISCORD.format(user=sender_string, message=message, em=em)
		logger.log_msg(f"returning {message}")
		return message

	def channel_msg(self, message, channel, senders=None, **kwargs):
		"""
		Evennia channel -> Discord bot
		"""
		if self in senders:
			# don't loop our own messages
			return
		if kwargs.get("relay"):
			# don't pass on messages from other Discord relays
			return

		if not self.ndb.dc_channel:
			self.ndb.dc_channel = self.db.dc_channel

		# send text to greenstalk
		greenclient.use('EvToDiscord')
		send_msg = json.dumps([self.ndb.dc_channel, message])
		greenclient.put(send_msg)

	def execute_cmd(self, session=None, txt=None, **kwargs):
		"""
		Take incoming data and send it to connected channel. This is
		triggered by the bot_data_in Inputfunc.
		Args:
			session (Session, optional): not used
			txt (str, optional):  Command string.
		Keyword Args:
			user (str): The name of the user who sent the message.
		"""
		if user := kwargs.get('user'):
			text = FORMAT_TO_EVENNIA.format(user=user, message=txt)
		else:
			text = txt

		if not self.ndb.ev_channel:
			# cache channel lookup
			self.ndb.ev_channel = self.db.ev_channel

		if self.ndb.ev_channel:
			self.ndb.ev_channel.msg(text, senders=self, relay=True)
