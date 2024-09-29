import discord
import bot
import guess
import poker
import top_messagers
import log
import very_real_ip_grabber
import profanity
import who_said_it_most
import wordbomb
import plinko
import rankings
import reddit_deletions
import message_chart
import woke_detector
import minecraft

log_handler = bot.LogHandler()
bot.logger.addHandler(log_handler)
bot.client.run(bot.token, log_handler=log_handler)
