import requests, re

s = requests.Session()
r = s.get('http://127.0.0.1:8000/admin/login/')
csrftoken = s.cookies.get('csrftoken', '')

login_data = {
    'username': 'stratos',
    'password': 'Stratos@2026',
    'csrfmiddlewaretoken': csrftoken,
    'next': '/admin/'
}
s.post('http://127.0.0.1:8000/admin/login/', data=login_data)

r3 = s.get('http://127.0.0.1:8000/admin/users/user/')
with open('debug_out.html', 'w', encoding='utf-8') as f:
    f.write(r3.text)

if 'Traceback' in r3.text:
    match = re.search(r'(?s)<textarea id="traceback_area".*?>(.*?)</textarea>', r3.text)
    if match:
        tb = match.group(1).replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        print(tb)
    else:
        print('No textarea found')
else:
    match2 = re.search(r'(?s)<pre class="exception_value">(.*?)</pre>', r3.text)
    if match2:
        print('Exception:', match2.group(1))
