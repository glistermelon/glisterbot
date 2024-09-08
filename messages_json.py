from log import sql, sql_conn, msg_table, reactions_table, mentions_table, role_mentions_table
import json as jsonmod

data = {}

def get_reactions(msg):
    json = []
    for row in sql_conn.execute(sql.select(reactions_table).where(reactions_table.c.MESSAGE_ID == msg.DISCORD_ID)):
        json.append({ 'r': row.REACTION, 'c': row.COUNT })
    return json if len(json) > 0 else None

def get_mentions(msg):
    json = []
    for row in sql_conn.execute(sql.select(mentions_table).where(mentions_table.c.MESSAGE_ID == msg.DISCORD_ID)):
        json.append(row.MENTIONED_USER)
    return json if len(json) > 0 else None

def get_role_mentions(msg):
    json = []
    for row in sql_conn.execute(sql.select(role_mentions_table).where(role_mentions_table.c.MESSAGE_ID == msg.DISCORD_ID)):
        json.append(row.MENTIONED_ROLE)
    return json if len(json) > 0 else None

i = 0

for row in sql_conn.execute(sql.select(msg_table)):

    if row.CHANNEL not in data: data[row.CHANNEL] = []
    json = {
        'id': row.DISCORD_ID,
        'm': row.CONTENT,
        't': row.TIMESTAMP,
        'a': row.AUTHOR,
        'u': row.JUMP_URL,
        'e': row.MENTIONS_EVERYONE
    }
    m = get_reactions(row)
    if m: json['rs'] = m
    m = get_mentions(row)
    if m: json['ms'] = m
    m = get_role_mentions(row)
    if m: json['rm'] = m
    data[row.CHANNEL].append(json)

    i += 1
    if i % 1000 == 0: print(i, end='\r')

with open('messages.json', 'w') as f:
    f.write(jsonmod.dumps(data, separators=(',',':')))