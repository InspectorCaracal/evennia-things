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


class DiscordBotRunner(DefaultScript):
	"""
	Initializes the bot its attached to and checks the incoming message
	queue for the bot.
	"""

	def at_script_creation(self):
		"""
		Called once, when script is created.
		"""
		self.key = "botstarter"
		self.desc = "bot start/relay"
		self.persistent = True
		self.db.started = False
		self.interval = 1

	def at_start(self):
		"""
		Kick bot into gear.
		"""
		if not self.ndb.started:
			self.account.start()
			self.ndb.started = True

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
		self.account.execute_cmd(**get_msg)
		greenclient.delete(job)

	def at_server_reload(self):
		self.ndb.started = True


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
		script_key = str(self.key)
		self.scripts.add(DiscordBotRunner, key=script_key)
		self.is_bot = True

	def start(self):
		# fake connection status
		self.is_connected = True

	def initialize(self, ev_channel, dc_botname, dc_chan_id, **kwargs):
		channel = search.channel_search(ev_channel)
		if not channel:
			raise RuntimeError(f"Evennia Channel '{ev_channel}' not found.")
		channel = channel[0]
		channel.connect(self)
#		self.username = dc_botname
		self.db.ev_channel = channel
		self.db.dc_channel = dc_chan_id

	def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
		"""
		Overloading because this bot doesn't need to directly receive messages.
		"""
		return

	def channel_msg(self, message, channel, senders=None, **kwargs):
		"""
		Evennia channel -> Discord bot
		"""
		if self in senders:
			# don't loop our own messages
			return

		if not self.ndb.dc_channel:
			self.ndb.dc_channel = self.db.dc_channel

		prefix, message = message.split(':',maxsplit=1)
		names = list_to_string(sender.name for sender in senders) if senders else None
		text = FORMAT_TO_DISCORD.format(user=names, message=message) if names else message
		# send text to greenstalk
		greenclient.use('EvToDiscord')
		send_msg = json.dumps([self.ndb.dc_channel, text])
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

		if not self.ndb.ev_channel and self.db.ev_channel:
				# cache channel lookup
			self.ndb.ev_channel = self.db.ev_channel

		if self.ndb.ev_channel:
			self.ndb.ev_channel.msg(text, senders=self)
