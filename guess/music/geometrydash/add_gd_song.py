import os
import json
import requests
import sys
import time

def add_song(newgrounds_id : str, output_dir : str = 'options'):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    song_path = f'{output_dir}/{newgrounds_id}.mp3'
    if not os.path.exists(song_path):
        print('Song file not found; downloading')
        r = requests.get('https://www.newgrounds.com/audio/download/' + newgrounds_id)
        if r.status_code == 400:
            print('Newgrounds download status code 400, attempting secondary download method')
            # god bless + credit: https://github.com/RoootTheFox/newgrounds-audio-downloader/blob/main/main.js
            r = requests.get('https://www.newgrounds.com/audio/listen/' + newgrounds_id)
            if r.status_code != 200:
                print('Newgrounds download status code', r.status_code)
                return
            data = r.content.decode()
            url = data[data.index('<![CDATA[') + 9:]
            url = url[url.index('embedController([') + 17:]
            url = url[0 : url.index('\",\"')]
            url = url[0 : url.index('?')]
            url = url[url.index('url') + 3:]
            url = url[url.index(':\"') + 2:].replace('\\/', '/')
            r = requests.get(url)
        if r.status_code != 200:
            print('Newgrounds download status code', r.status_code)
            return
        with open(song_path, 'wb') as f:
            f.write(r.content)
    else: print('Song file found; skipping download')
    
    print('Getting levels from GD servers')

    levels = []

    page = 0
    while True:
        # I know you're not supposed to use this API but RobTop's servers are so bad
        # and I'd rather be banned from GDBrowser than the GD servers
        r = requests.get(f'https://gdbrowser.com/api/search/*?page={page}&count=10&songID={newgrounds_id}&customSong=&starred=')
        if r.status_code == 500 or r.content == b'-1': break
        if r.status_code != 200:
            print('GDBrowser API status code', r.status_code)
            if (r.status_code == 429): print(r.headers)
        page += 1
        levels += [level['name'] for level in json.loads(r.content)]
        time.sleep(1)
    
    print('Adding levels:', levels)
    
    info = None
    with open('info.json') as f:
        info = json.loads(f.read())
    info['answers'][newgrounds_id] = levels
    with open('info.json', 'w') as f:
        f.write(json.dumps(info))

argc = len(sys.argv)
if argc < 2: print('No newgrounds song ID specified')
elif argc > 2: print('Too many arguments provided')
else: add_song(sys.argv[1])