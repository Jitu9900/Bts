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

def http_get(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception:
        return None

def get_youtube_id(url):
    m = re.search(r'(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([^"&?/\s]{11})', url, re.I)
    return m.group(1) if m else False

def extract_size(m):
    for k in ('contentLength', 'clen', 'size'):
        if m.get(k):
            return int(m[k])
    url = m.get('url', '')
    mt = re.search(r'[&?]clen=(\d+)', url)
    return int(mt.group(1)) if mt else 0

def fetch_video_info(video_id):
    yt_url = f"https://youtu.be/{video_id}"
    api_url = DOWNLOAD_API + urllib.parse.quote(yt_url)
    res = http_get(api_url, 40)
    if not res:
        return None
    try:
        d = json.loads(res)
        if d.get('status') == 'success' and d.get('data', {}).get('medias'):
            return d['data']
    except Exception:
        pass
    return None

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

    if action == 'formats':
        video_id = str(q.get('v', '')).strip()
        if not video_id:
            return respond({'success': 0, 'error': 'missing'})
        vid = get_youtube_id(video_id) or video_id
        data = fetch_video_info(vid)
        if not data:
            return respond({'success': 0, 'error': 'unavailable'})

        formats = []
        for m in data['medias']:
            if m.get('type') != 'video' or not m.get('url') or not m.get('height'):
                continue
            formats.append({
                'fid': str(m.get('formatId', '')),
                'h': int(m['height']),
                'e': m.get('ext', 'mp4'),
                'a': bool(m.get('audioQuality')),
                'br': int(m.get('bitrate', 0)),
                'fps': int(m.get('fps', 0)),
                's': extract_size(m)
            })
        formats.sort(key=lambda x: (-x['h'], 0 if x['a'] else 1, -x['br']))
        return respond({'success': 1, 'title': data.get('title', ''), 'formats': formats})

    if action == 'stream':
        video_id = str(q.get('v', '')).strip()
        quality = int(q.get('h', 720))
        if not video_id:
            return respond({'success': 0, 'error': 'missing'})
        vid = get_youtube_id(video_id) or video_id
        data = fetch_video_info(vid)
        if not data:
            return respond({'success': 0, 'error': 'unavailable'})

        videos, audios, muxed = [], [], []
        for m in data['medias']:
            if not m.get('url'):
                continue
            t = m.get('type', '')
            has_audio = bool(m.get('audioQuality'))
            h = int(m.get('height', 0))
            if t == 'video':
                item = {
                    'h': h,
                    'e': m.get('ext', 'mp4'),
                    'url': m['url'],
                    'mime': m.get('mimeType', 'video/mp4'),
                    'br': int(m.get('bitrate', 0))
                }
                if has_audio:
                    muxed.append(item)
                else:
                    videos.append(item)
            elif t == 'audio':
                audios.append({
                    'br': int(m.get('bitrate', 0)),
                    'e': m.get('ext', 'm4a'),
                    'url': m['url'],
                    'mime': m.get('mimeType', 'audio/mp4')
                })

        audios.sort(key=lambda x: -x['br'])
        best_audio = audios[0] if audios else None
        videos.sort(key=lambda x: x['h'])
        muxed.sort(key=lambda x: x['h'])

        quality_list = []
        for m in muxed:
            quality_list.append({'h': m['h'], 'vUrl': m['url'], 'vMime': m['mime'], 'aUrl': None, 'aMime': None, 'muxed': True})
        for v in videos:
            quality_list.append({
                'h': v['h'], 'vUrl': v['url'], 'vMime': v['mime'],
                'aUrl': best_audio['url'] if best_audio else None,
                'aMime': best_audio['mime'] if best_audio else None,
                'muxed': False
            })

        by_h = {}
        for qq in quality_list:
            if qq['h'] not in by_h:
                by_h[qq['h']] = qq
            elif qq['muxed'] and not by_h[qq['h']]['muxed']:
                by_h[qq['h']] = qq

        final_list = [by_h[k] for k in sorted(by_h.keys())]
        if not final_list:
            return respond({'success': 0, 'error': 'no_streams'})

        chosen = final_list[0]
        for f in final_list:
            if f['h'] <= quality:
                chosen = f
        if final_list[-1]['h'] < quality:
            chosen = final_list[-1]

        return respond({'success': 1, 'title': data.get('title', ''), 'chosen': chosen, 'formats': final_list})

    if action == 'dl_video':
        video_id = str(q.get('v', '')).strip()
        fid = str(q.get('f', '')).strip()
        if not video_id or not fid:
            return Response("Bad Request", status=400)
        vid = get_youtube_id(video_id) or video_id
        data = fetch_video_info(vid)
        if not data:
            return Response("Bad Gateway", status=502)
        target = next((m for m in data['medias'] if str(m.get('formatId', '')) == fid), None)
        if not target or not target.get('url'):
            return Response("Not Found", status=404)

        title = re.sub(r'[^\w\s\-\.]+', '_', data.get('title', 'video')).strip() or 'video'
        quality = target.get('quality') or f"{target.get('height', '')}p"
        ext = target.get('ext', 'mp4')
        filename = f"{title} - {quality}.{ext}"

        req = urllib.request.Request(target['url'], headers={'User-Agent': 'Mozilla/5.0'})
        upstream = urllib.request.urlopen(req, timeout=30)

        def generate():
            while True:
                chunk = upstream.read(131072)
                if not chunk:
                    break
                yield chunk

        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Cache-Control': 'no-store'
        }
        size = extract_size(target)
        if size > 0:
            headers['Content-Length'] = str(size)
        return Response(generate(), headers=headers)

    if action == 'dl_pdf':
        file_name = str(q.get('f', '')).strip()
        if not file_name or not re.match(r'^[a-zA-Z0-9]+\.pdf$', file_name, re.I):
            return Response("Bad Request", status=400)
        url = f"https://{ALLOWED_PDF_HOST}/public/storage/pdf/{file_name}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        upstream = urllib.request.urlopen(req, timeout=30)

        def generate():
            while True:
                chunk = upstream.read(131072)
                if not chunk:
                    break
                yield chunk

        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Cache-Control': 'no-store'
        }
        return Response(generate(), headers=headers)

    return respond({'success': 0, 'error': 'unknown'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
