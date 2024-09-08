import os

for folder in os.listdir():
    for root, subdirs, files in os.walk(folder):
        for file in files:
            path = os.path.join(root, file)
            if not path.endswith('.wav'): continue
            wav = path
            mp3 = path[:-3] + 'mp3'
            print(wav, mp3)
            os.system(f'ffmpeg -n -i "{wav}" "{mp3}"')