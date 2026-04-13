import urllib.request

try:
    print('GET /')
    urllib.request.urlopen('http://127.0.0.1:8000/')
except Exception as e:
    print(f'Error /: {e}')

try:
    # Simulate a post
    import urllib.parse
    data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin'}).encode()
    req = urllib.request.Request('http://127.0.0.1:8000/admin/login', data=data)
    res = urllib.request.urlopen(req)
    cookies = res.headers.get('Set-Cookie')
    if cookies:
        req = urllib.request.Request('http://127.0.0.1:8000/admin/dashboard', headers={'Cookie': cookies})
        try:
            res = urllib.request.urlopen(req)
        except Exception as e:
            print(f'GET /admin/dashboard: {e}')
except Exception as e:
    print(f'Login Error: {e}')
