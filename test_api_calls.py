import requests, json, time
url = 'http://127.0.0.1:3000/api/chat'
cases = [
  {'message':'transportation details at nnrg','sessionId':'test-transport'},
  {'message':'who is the hod of ds','sessionId':'test-hod-ds'},
  {'message':'who is hod ai&ml','sessionId':'test-hod-ai'},
]
for c in cases:
    try:
        r = requests.post(url, json=c, timeout=10)
        print('---')
        print(c['message'])
        print(r.status_code)
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print('error', e)
    time.sleep(0.5)
