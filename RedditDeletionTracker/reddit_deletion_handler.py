import msgpack
import asyncio
import json
import asyncpraw as praw
import time
import asyncio
import re
from sqlalchemy.dialects import postgresql
import json
import traceback
import sqlalchemy

sql_engine = sqlalchemy.create_engine(
    sqlalchemy.URL.create(
        'postgresql+psycopg2',
        username='postgres',
        host='127.0.0.1',
        port=5432,
        database='glisterbot2'
    ),
    enable_from_linting=False
)
sql_conn = sql_engine.connect()
sql_metadata = sqlalchemy.MetaData()
reddit_posts_table = sqlalchemy.Table(
    'MonitoredRedditPosts',
    sql_metadata,
    sqlalchemy.Column('ID', sqlalchemy.String, primary_key=True),
    sqlalchemy.Column('SUBREDDIT', sqlalchemy.String)
)
sql_metadata.create_all(sql_engine)

CONFIG_PATH = '../appsettings.json'
PORT = json.loads(open(CONFIG_PATH).read())['RedditDeletionListenerPort']

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
        sql_conn.execute(postgresql.insert(reddit_posts_table).values(
            ID = post_id,
            SUBREDDIT = self.subreddit.fullname
        ).on_conflict_do_nothing(index_elements=['ID']))
        sql_conn.commit()
    
    def remove_post_from_db(self, post_id : str):
        sql_conn.execute(
            sqlalchemy.delete(reddit_posts_table).where(reddit_posts_table.c.ID == post_id)
        )
        sql_conn.commit()
    
    def load_posts_from_db(self):
        self.posts[5] = list(row.ID for row in sql_conn.execute(
            sqlalchemy.select(reddit_posts_table).where(reddit_posts_table.c.SUBREDDIT == self.subreddit.fullname)
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
            print(f'Added to queue: {post.id}')
        print("THIS IS NOT SUPPOSED TO HAPPEN WHAT")

    async def try_record_posts(self):
        try:
            await self.record_posts()
        except Exception as e:
            print(f'Error: {e}')
            traceback.print_exc()

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
                    #print(f'Yielding {post.id}')
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

    config = json.loads(open(CONFIG_PATH).read())['reddit']
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
    sub_rules = [rule.short_name async for rule in subreddit.rules]

    _reader, writer = await asyncio.open_connection('127.0.0.1', PORT)

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

        image_url = None
        if rule and rule not in NO_IMAGES_FOR_THESE_RULES_BECAUSE_THEY_MIGHT_BE_REALLY_BAD:
            if post.thumbnail != 'self' and post.thumbnail != 'default':
                image_url = post.thumbnail
            elif post.is_reddit_media_domain and post.domain == 'i.redd.it':
                image_url = post.url

        try:

            msg_data = {
                'title': 'r/geometrydash Post Removed',
                'desc': desc,
                'timestamp': int(timestamp),
                'post_url': 'https://www.reddit.com' + post.permalink,
            }
            if image_url is not None:
                msg_data['image_url'] = image_url
            packed = msgpack.packb(msg_data)
            writer.write(len(packed).to_bytes(4, 'big') + packed)
            await writer.drain()
            tracker.remove_post_from_db(post.id)

        except:
            print(f'Failed to send to reddit removal {post.permalink}')

async def lazy_workaround():
    last_fail = 0
    fail_count = 0
    while True:
        try:
            await run_deletion_tracker()
        except Exception as e:
            print(f'Error: {e}')
            traceback.print_exc()
            now = time.time()
            fail_delta = last_fail - now
            last_fail = now
            if fail_delta > 5 * MINUTE: fail_count = 0
            wait = 10 * fail_count
            fail_count += 1
            print(f'Attempting to restart deletion tracker in {wait} seconds.')
            await asyncio.sleep(wait)

asyncio.run(lazy_workaround())