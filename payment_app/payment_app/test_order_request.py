import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

payload = {
    'total': 677.99,
    'subtotal': 677.99,
    'shippingAmount': 0,
    'discountAmount': 0,
    'taxAmount': 0,
    'itemCount': 1,
    'primaryLabel': 'Test product',
    'items': [
        {
            'productId': 'prod-1',
            'productName': 'Test product',
            'quantity': 1,
            'price': 677.99,
        }
    ],
    'shippingDetails': {
        'address': '123 Main St, Test City',
        'email': 'test@example.com',
        'phone': '9999999999',
        'name': 'Test User',
    },
    'paymentDetails': {
        'paymentReference': 'payref_4bd9817337982e29f26f1a60',
    },
    'paymentReference': 'payref_4bd9817337982e29f26f1a60',
    'guestToken': 'test-guest-token',
}

req = Request(
    'http://127.0.0.1:8007/api/v1/orders',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST',
)

output = {}
try:
    with urlopen(req, timeout=20) as resp:
        output['status'] = resp.status
        output['body'] = resp.read().decode('utf-8')
except HTTPError as e:
    output['status'] = e.code
    output['body'] = e.read().decode('utf-8')
except URLError as e:
    output['error'] = str(e)

with open('test_order_response.json', 'w', encoding='utf-8') as out_file:
    json.dump(output, out_file, indent=2)
