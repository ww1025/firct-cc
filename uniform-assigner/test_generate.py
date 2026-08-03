import requests, json

files = {'excel': ('test.xlsx', open('本月礼服分配.xlsx', 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
data = {'schedule': '周一：柳洋、姚忻成、马欣雅、张博宣'}
r = requests.post('http://localhost:8765/generate', files=files, data=data)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    j = r.json()
    print(f"Conflicts: {j['conflicts_count']}, Reassigns: {j['reassignments_count']}")
    print(f"Message: {j['message']}")
else:
    print(r.text[:500])
