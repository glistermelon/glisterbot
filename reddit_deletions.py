import asyncpraw as praw
import discord
import bot
import datetime
import time
import asyncio
import re
import database
from database import sql, sql_conn
from sqlalchemy.dialects import postgresql
import os
import json
import logging

webhook_urls = ['https://discord.com/api/webhooks/1282429899730190336/-4KfcLF3oYkjJLsVK1ToX9QAtHxWBQxnoZMweVtmy8E7PPpCe2XXbaVm5LICwA-U1q-Y']

max_tracking_period = 2 * 24 * 60 * 60 # 2 days

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24

class SubredditWatcher:
    
    # posts: { check interval : time since posted } all in seconds

    @classmethod
    async def create(cls, reddit, subreddit : praw.reddit.Subreddit):
        self = cls()
        self.reddit = reddit
        self.subreddit = subreddit
        await self.subreddit.load()
        self.posts = {}
        return self

    def add_post_to_db(self, post_id : str):
        sql_conn.execute(postgresql.insert(database.reddit_posts_table).values(
            ID = post_id,
            SUBREDDIT = self.subreddit.fullname
        ).on_conflict_do_nothing(index_elements=['ID']))
        sql_conn.commit()
    
    def remove_post_from_db(self, post_id : str):
        sql_conn.execute(
            sql.delete(database.reddit_posts_table).where(database.reddit_posts_table.c.ID == post_id)
        )
        sql_conn.commit()
    
    def load_posts_from_db(self):
        self.posts[5] = list(row.ID for row in sql_conn.execute(
            sql.select(database.reddit_posts_table).where(database.reddit_posts_table.c.SUBREDDIT == self.subreddit.fullname)
        ).all())
    
    async def record_posts(self):
        self.load_posts_from_db()
        existing = [post for post_list in self.posts.values() for post in post_list]
        async for post in self.subreddit.stream.submissions():
            if post.id in existing: continue
            a = [post.id]
            i = 30
            try:
                self.posts[i] += a
            except:
                self.posts[i] = a
            self.add_post_to_db(post.id)
            bot.logger.info(f'Added to queue: {post.id}')
        print("THIS IS NOT SUPPOSED TO HAPPEN WHAT")

    async def try_record_posts(self):
        try:
            await self.record_posts()
        except Exception as e:
            bot.logger.error(e, exc_info=1)

    async def check_posts(self):

        while True:

            while len(self.posts) == 0:
                await asyncio.sleep(10)

            soonest = min(self.posts.keys())
            posts = self.posts[soonest]
            del self.posts[soonest]
            self.posts = { k - soonest: v for k, v in self.posts.items() }
            
            await asyncio.sleep(soonest)

            async for post in self.reddit.info(fullnames = ['t3_' + post_id for post_id in posts]):
                #logger.info(f'Checking: {post}')
                if post.removed_by_category == 'moderator':
                    #bot.logger.info(f'Yielding {post.id}')
                    self.remove_post_from_db(post.id)
                    yield post
                else:
                    #logger.info('Adding back into queue')
                    track_time = time.time() - post.created_utc
                    #logger.info(f'Track time: {track_time}')
                    if track_time < max_tracking_period:
                        interval = None
                        if track_time < 12 * HOUR: interval = 30
                        elif track_time < DAY: interval = 60
                        else: interval = 120
                        a = [post.id]
                        try:
                            self.posts[interval] += a
                        except:
                            self.posts[interval] = a
                        #logger.info(f'Placed in interval {interval}')
                    else:
                        self.remove_post_from_db(post.id)
            #logger.info('Iteration done')

async def run_deletion_tracker():

    config = json.loads(open('config.json').read())['reddit']
    reddit = praw.Reddit(
        client_id = config['client_id'],
        client_secret = config['client_secret'],
        user_agent = config['user_agent'],
        username = config['username'],
        password = config['password']
    )
    subreddit = await reddit.subreddit('geometrydash')
    tracker = await SubredditWatcher.create(reddit, subreddit)
    recorder_task = asyncio.create_task(tracker.try_record_posts())
    recorder_task_failed = False
    def recorder_callback(t):
        nonlocal recorder_task_failed
        recorder_task_failed = True
    recorder_task.add_done_callback(recorder_callback)
    moderators = [user.name async for user in subreddit.moderator]
    moderators.remove('zbot-gd')
    NO_IMAGES_FOR_THESE_RULES_BECAUSE_THEY_MIGHT_BE_REALLY_BAD = [6]
    webhooks = [discord.Webhook.from_url(url, client=bot.client) for url in webhook_urls]
    sub_rules = [rule.short_name async for rule in subreddit.rules]

    async for post in tracker.check_posts():

        if recorder_task_failed: raise RuntimeError('Recorder task failed. Returning from tracker.')

        author = None
        rule = None
        suspect = None
        timestamp = time.time()

        desc = '**Title:** ' + post.title + '\n**Author:** u/'
        if (post.author != None):
            desc += post.author.name
            author = post.author.name
        else:
            desc += '*Unknown*'

        post_comments = await post.comments()

        mod_comments = [c for c in post_comments if hasattr(c.author, 'name') and c.author.name in moderators]
        if len(mod_comments):
            suspect = sorted(mod_comments, key = lambda c:c.created_utc)[0].author.name
            desc += '\n**Removal Suspect:** u/' + suspect

        reason_comment = None
        for comment in post.comments:
            if hasattr(comment.author, 'name') and comment.author.name == 'geometrydash-ModTeam':
                reason_comment = comment
                break
        if reason_comment is None and len(mod_comments):
            reason_comment = mod_comments[0]

        if reason_comment is not None:
        
            rule = re.search('rule [0-9]+', reason_comment.body, flags=re.IGNORECASE)
            if rule is not None:
                rule = rule.group(0)[5:]
                try:
                    rule = int(rule)
                    desc += f'\n**Rule {rule}: **' + sub_rules[rule - 1]
                except Exception as e:
                    rule = None
                    desc += f'\n*Removal Reason Unknown*'
            else: desc += f'\n*Removal Reason Unknown*'

            timestamp = comment.created_utc
        
        else: desc += f'\n*Removal Reason Unknown*'

        embed = discord.Embed(
            title = 'r/geometrydash Post Removed',
            color = 0xff0000,
            description = desc,
            timestamp = datetime.datetime.fromtimestamp(timestamp),
            url = 'https://www.reddit.com' + post.permalink
        )

        if rule and rule not in NO_IMAGES_FOR_THESE_RULES_BECAUSE_THEY_MIGHT_BE_REALLY_BAD:
            if post.thumbnail != 'self' and post.thumbnail != 'default':
                embed.set_image(url = post.thumbnail)
            elif post.is_reddit_media_domain and post.domain == 'i.redd.it':
                embed.set_image(url = post.url)

        for webhook in webhooks:
            try:
                await webhook.send(embed=embed)
            except:
                print(f'Failed to send to webhook: {webhook.url}')

async def lazy_workaround():
    last_fail = 0
    fail_count = 0
    while True:
        try:
            await run_deletion_tracker()
        except Exception as e:
            bot.logger.error(e, exc_info=1)
            now = time.time()
            fail_delta = last_fail - now
            last_fail = now
            if fail_delta > 5 * MINUTE: fail_count = 0
            wait = 10 * fail_count
            fail_count += 1
            bot.logger.info(f'Attempting to restart deletion tracker in {wait} seconds.')
            asyncio.sleep(wait)

bot.run_on_ready.append(lazy_workaround())
