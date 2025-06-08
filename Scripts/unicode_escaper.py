def esc(s):
    escaped = ''
    for c in s:
        c = hex(ord(c))[2:]
        c = '0' * (8 - len(c)) + c
        c = '\\U' + c
        escaped += c
    return escaped

while True:
    s = esc(input(': '))
    print(s)