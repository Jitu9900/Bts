from flask import Flask, request, jsonify, Response, send_from_directory
import json
import base64
import urllib.parse
import urllib.request
import re
import os

app = Flask(__name__, static_folder='.')

BASE_URL = "https://bridgetosuccess.learncentre.tech/public/study_api_sprint13_security_promo/"
USER_ID_DEFAULT = "12644"
DOWNLOAD_API = "https://r-gengpt-api.vercel.app/api/video/download?url="
ALLOWED_PDF_HOST = "bridgetosuccess.learncentre.tech"

def dec_query():
    raw = request.args.get('q', '')
    if not raw:
        return {}
    raw = raw.replace('-', '+').replace('_', '/')
    while len(raw) % 4 != 0:
        raw += '='
    try:
        decoded = base64.b64decode(raw).decode('utf-8')
        arr = json.loads(decoded)
        return arr if isinstance(arr, dict) else {}
    except Exception:
        return {}

def b64url(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('+', '-').replace('/', '_').rstrip('=')

def respond(data):
    json_str = json.dumps(data, ensure_ascii=False)
    resp = jsonify({'d': b64url(json_str)})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

def api_call(data):
    post_data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL,
        data=post_data,
        headers={'User-Agent': 'okhttp/5.3.2', 'Content-Type': 'application/x-www-form-urlencoded'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {'success': 0, 'error': str(e)}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api', methods=['GET', 'POST', 'OPTIONS'])
def api_router():
    if request.method == 'OPTIONS':
        resp = Response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return resp

    q = dec_query()
    action = q.get('a', '')

    if action == 'courses':
        res = api_call({'tag': 'allCourses', 'isEBook': '0', 'userId': USER_ID_DEFAULT})
        return respond(res)

    if action == 'content':
        res = api_call({
            'tag': 'getCategoryMixed',
            'courseId': str(q.get('c', '')),
            'userId': USER_ID_DEFAULT,
            'categoryId': str(q.get('k', ''))
        })
        return respond(res)

    return respond({'success': 0, 'error': 'unknown'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
