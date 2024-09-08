import psycopg2
import sqlalchemy as sql
from sqlalchemy.dialects import postgresql
import json

engine = sql.create_engine(sql.URL.create(
    'postgresql+psycopg2',
    username='postgres',
    password=json.loads(open('config.json').read())['psql_pw'],
    host='localhost',
    port=5432,
    database='glisterbot'
))

sql_conn = engine.connect()

sql_metadata = sql.MetaData()

streak_table = sql.Table(
    'Streaks',
    sql_metadata,
    sql.Column('CHANNEL', sql.BigInteger, primary_key=True),
    sql.Column('PICTIONARY_USER', sql.BigInteger),
    sql.Column('PICTIONARY', sql.Integer),
    sql.Column('MUSIC_USER', sql.BigInteger),
    sql.Column('MUSIC', sql.Integer)
)

timespan_table = sql.Table(
    'Timespans',
    sql_metadata,
    sql.Column('CHANNEL', sql.BigInteger),
    sql.Column('BEGIN', sql.BigInteger),
    sql.Column('END', sql.BigInteger)
)

msg_table = sql.Table(
    'Messages',
    sql_metadata,
    sql.Column('DISCORD_ID', sql.BigInteger, primary_key=True),
    sql.Column('CONTENT', sql.Text),
    sql.Column('TIMESTAMP', sql.BigInteger),
    sql.Column('AUTHOR', sql.BigInteger),
    sql.Column('JUMP_URL', sql.String),
    sql.Column('MENTIONS_EVERYONE', sql.Boolean),
    sql.Column('CHANNEL', sql.BigInteger)
)

channel_table = sql.Table(
    'Channels',
    sql_metadata,
    sql.Column('CHANNEL', sql.BigInteger, primary_key=True),
    sql.Column('SERVER', sql.BigInteger)
)

mentions_constraint = sql.UniqueConstraint('MESSAGE_ID', 'MENTIONED_USER')
mentions_table = sql.Table(
    'Mentions',
    sql_metadata,
    sql.Column('MESSAGE_ID', sql.ForeignKey('Messages.DISCORD_ID'), primary_key=True),
    sql.Column('MENTIONED_USER', sql.BigInteger, primary_key=True),
    mentions_constraint
)

role_mentions_constraint = sql.UniqueConstraint('MESSAGE_ID', 'MENTIONED_ROLE')
role_mentions_table = sql.Table(
    'RoleMentions',
    sql_metadata,
    sql.Column('MESSAGE_ID', sql.ForeignKey('Messages.DISCORD_ID'), primary_key=True),
    sql.Column('MENTIONED_ROLE', sql.BigInteger, primary_key=True),
    role_mentions_constraint
)

reactions_constraint = sql.UniqueConstraint('MESSAGE_ID', 'USER', 'EMOJI_ID', 'EMOJI_NAME')
reactions_table = sql.Table(
    'Reactions',
    sql_metadata,
    sql.Column('MESSAGE_ID', sql.ForeignKey('Messages.DISCORD_ID')),
    sql.Column('USER', sql.BigInteger),
    sql.Column('EMOJI_ID', sql.BigInteger, nullable=True),
    sql.Column('EMOJI_NAME', sql.String, nullable=True),
    reactions_constraint
)

profanity_constraint = sql.UniqueConstraint('WORD', 'USER')
profanity_table = sql.Table(
    'Profanity',
    sql_metadata,
    sql.Column('WORD', sql.String, primary_key=True),
    sql.Column('USER', sql.BigInteger, primary_key=True),
    sql.Column('COUNT', sql.Integer),
    profanity_constraint
)

rankings_cat_table = sql.Table(
    'RankingsCategories',
    sql_metadata,
    sql.Column('ID', sql.Integer, primary_key=True, autoincrement=True),
    sql.Column('NAME', sql.String),
    sql.Column('DISPLAY_NAME', sql.String)
)

rankings_item_table = sql.Table(
    'RankingsItems',
    sql_metadata,
    sql.Column('ID', sql.Integer, primary_key=True, autoincrement=True),
    sql.Column('CATEGORY_ID', sql.ForeignKey('RankingsCategories.ID')),
    sql.Column('NAME', sql.String),
    sql.Column('DISPLAY_NAME', sql.String)
)

rankings_score_constraint = sql.UniqueConstraint('ITEM_ID', 'SERVER')
rankings_score_table = sql.Table(
    'RankingsScores',
    sql_metadata,
    sql.Column('ID', sql.Integer, primary_key=True, autoincrement=True),
    sql.Column('ITEM_ID', sql.ForeignKey('RankingsItems.ID')),
    sql.Column('SERVER', sql.BigInteger),
    sql.Column('COUNT', sql.Integer),
    sql.Column('SCORE', sql.Double),
    rankings_score_constraint
)

rankings_constraint = sql.UniqueConstraint('USER', 'SCORE_ID')
rankings_table = sql.Table(
    'Rankings',
    sql_metadata,
    sql.Column('USER', sql.BigInteger, primary_key=True),
    sql.Column('SCORE_ID', sql.ForeignKey('RankingsScores.ID'), primary_key=True),
    sql.Column('VALUE', sql.Integer),
    rankings_constraint
)

rankings_kick_constraint = sql.UniqueConstraint('USER', 'SCORE_ID')
rankings_kick_table = sql.Table(
    'RankingsVoteKicks',
    sql_metadata,
    sql.Column('USER', sql.BigInteger, primary_key=True),
    sql.Column('SCORE_ID', sql.ForeignKey('RankingsScores.ID'), primary_key=True),
    rankings_kick_constraint
)

for table in (msg_table, mentions_table, role_mentions_table, reactions_table, channel_table, streak_table, profanity_table,
              rankings_cat_table, rankings_item_table, rankings_table, rankings_kick_table):
    if engine.dialect.has_table(sql_conn, table.name):
        sql_metadata.remove(table)
    sql_metadata.create_all(engine)
