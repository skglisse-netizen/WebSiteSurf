import requests

url = 'http://127.0.0.1:8000/admin/dashboard'
cookies = {'access_token': 'fake'}
data = {
    'hero_title': 'T',
    'hero_subtitle': 'S',
    'hero_button_text': 'B',
    'contact_button_text': 'C',
    'hero_image_url': 'U',
    'school_name': 'N',
    'contact_address': 'A',
    'contact_phone': 'P',
    'contact_email': 'E'
}
r = requests.post(url, data=data)
print(f'Status: {r.status_code}')
print(r.text)
