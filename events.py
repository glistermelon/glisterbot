import bot
from types import SimpleNamespace

listeners = {}


def add_listener(event: str, callback, *args, **kwargs):
    obj = None
    if event == 'on_message':
        obj = SimpleNamespace()
        obj.callback = callback
        obj.channel = kwargs['channel'] if 'channel' in kwargs else None
    else:
        obj = callback
    if event in listeners:
        listeners[event].append(obj)
    else:
        listeners[event] = [obj]


def rm_listener(event : str, callback):
    if event not in listeners or callback is None:
        return
    listeners[event] = [listener for listener in listeners[event] if (listener != callback) and listener.callback != callback]


@bot.client.event
async def on_message(message):
    if 'on_message' not in listeners:
        return
    for listener in listeners['on_message']:
        if message.channel is None or listener.channel == message.channel:
            await listener.callback(message)