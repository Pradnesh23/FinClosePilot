import urllib.request
import urllib.error

try:
    urllib.request.urlopen('http://127.0.0.1:8000/api/runs/7ca181ef-d6c6-4f5d-a7b7-4710f50cbbfd')
except urllib.error.HTTPError as e:
    print(e.read().decode())
