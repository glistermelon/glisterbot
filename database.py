import psycopg2
import sqlalchemy as sql
from sqlalchemy.dialects import postgresql

engine = sql.create_engine(sql.URL.create(
    'postgresql+psycopg2',
    username='postgres',
    password='password',
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

reactions_constraint = sql.UniqueConstraint('MESSAGE_ID', 'REACTION')
reactions_table = sql.Table(
    'Reactions',
    sql_metadata,
    sql.Column('MESSAGE_ID', sql.ForeignKey('Messages.DISCORD_ID'), primary_key=True),
    sql.Column('REACTION', sql.BigInteger, primary_key=True),
    sql.Column('COUNT', sql.Integer),
    reactions_constraint
)

for table in (msg_table, mentions_table, role_mentions_table, reactions_table, channel_table, streak_table):
    if engine.dialect.has_table(sql_conn, table.name):
        sql_metadata.remove(table)
    sql_metadata.create_all(engine)