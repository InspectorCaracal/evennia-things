# Discord <-> Evennia

A (relatively) easy-to-use chat integration between a Discord channel and an Evennia channel.

**This is Evennia 1.0 or higher, ONLY. It DOES NOT WORK with Evennia v0.9.5***

This implementation uses `beanstalkd` to relay the messages - so while this setup is designed to all be run from the same folder, you can easily have your discord bot on a separate machine entirely from evennia. 

**Note:** If you are running your Evennia game on a Windows server, you will need to implement a different job queue.

### Installation

#### Initial Setup

1. Install [beanstalkd](https://beanstalkd.github.io/download.html) on your Evennia server.
2. Put this folder somewhere in your evennia game folder, e.g. `mygame/discord_relay/`
3. Copy `settings_default.py` to `settings.py` - it's excluded by .gitignore so you don't have to worry about accidentally saving your Discord app token to a public repository.
4. Edit `settings.py` as needed.

#### Evennia
If you don't know how to do any of these steps, you probably should be a little more familiar with Evennia before setting it up. Head over to [the Evennia discord](https://discord.gg/AJJpcRUhtF) if you need help!

1. From within your evennia virtual environment, `pip install discord greenstalk`
2. Add the `CmdDiscord2Chan` command to your AccountCmdSet.
3. Reload the server - `help discord2chan` for information on how to use!

#### Discord

1. Make sure you have [your bot application](https://discord.com/developers/applications) set up with all the necessary permissions.
2. Add your bot to any server(s) you want it to sending to.
3. Get the IDs of the Discord channels you'll be sending to - you need it to add the Evennia bot. If you click into a channel normally in a web browser, it should be the long number at the end: `https://discord.com/channels/<server ID>/<channel ID>`
4. Start up `discordbot.py` - it's a looping script, so you'll want to run it in the background. You can set it up as a service, or you can use something like `tmux`, or whatever your "run this in the background" solution of choice happens to be.

### Use

Once you have it running, you can add new bots with `discord2chan` from inside Evennia to relay any channel messages to any other channel. As long as your Discord app has access to the Discord channels you want to use, it'll manage everything itself.

### TO-DO

- Figure out a nice way to label and display which discord server+channel a bot is relaying to.
