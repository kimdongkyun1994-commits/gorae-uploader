"""Gorae Shorts Uploader — complete upload script (YouTube Data API v3, scope youtube.upload).

Uploads one of the channel owner's own Shorts to his own channel and schedules it.
Credentials come from environment variables only (never stored in code):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Usage:
  python3 upload.py video.mp4 --title "..." --description "..." --tags "a,b" \
      --privacy public --publish-at 2026-11-13T09:00:00+09:00 [--thumbnail cover.png]
Only the Python standard library is used.
"""
import argparse, json, os, sys, urllib.parse, urllib.request

TOKEN_URL = 'https://oauth2.googleapis.com/token'
UPLOAD_URL = 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status'
THUMB_URL = 'https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={}&uploadType=media'


def access_token():
    data = urllib.parse.urlencode({
        'client_id': os.environ['YT_CLIENT_ID'], 'client_secret': os.environ['YT_CLIENT_SECRET'],
        'refresh_token': os.environ['YT_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    return json.load(urllib.request.urlopen(TOKEN_URL, data))['access_token']


def upload(path, title, description, tags, privacy, publish_at, category='27'):
    tok = access_token()
    status = {'privacyStatus': privacy, 'selfDeclaredMadeForKids': False}
    if publish_at:  # scheduled publishing requires privacyStatus=private until publishAt
        status = {'privacyStatus': 'private', 'publishAt': publish_at, 'selfDeclaredMadeForKids': False}
    meta = {'snippet': {'title': title[:100], 'description': description[:5000], 'tags': tags, 'categoryId': category},
            'status': status}
    size = os.path.getsize(path)
    req = urllib.request.Request(UPLOAD_URL, data=json.dumps(meta).encode(), method='POST', headers={
        'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    session = urllib.request.urlopen(req).headers['Location']  # resumable session URI
    with open(path, 'rb') as f:
        put = urllib.request.Request(session, data=f.read(), method='PUT', headers={
            'Authorization': 'Bearer ' + tok, 'Content-Type': 'video/mp4', 'Content-Length': str(size)})
        video = json.load(urllib.request.urlopen(put))
    return tok, video


def set_thumbnail(tok, video_id, image):
    with open(image, 'rb') as f:
        req = urllib.request.Request(THUMB_URL.format(video_id), data=f.read(), method='POST', headers={
            'Authorization': 'Bearer ' + tok, 'Content-Type': 'image/png' if image.endswith('.png') else 'image/jpeg'})
    return json.load(urllib.request.urlopen(req))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video'); ap.add_argument('--title', required=True); ap.add_argument('--description', default='')
    ap.add_argument('--tags', default=''); ap.add_argument('--privacy', default='public', choices=['public', 'unlisted', 'private'])
    ap.add_argument('--publish-at'); ap.add_argument('--thumbnail')
    a = ap.parse_args()
    tok, v = upload(a.video, a.title, a.description, [t.strip() for t in a.tags.split(',') if t.strip()], a.privacy, a.publish_at)
    print(json.dumps({'id': v['id'], 'channelId': v['snippet']['channelId'], 'status': v['status']}, ensure_ascii=False))
    if a.thumbnail:
        try:
            set_thumbnail(tok, v['id'], a.thumbnail)
        except Exception as e:  # thumbnails need a phone-verified channel
            print('thumbnail skipped:', str(e)[:200], file=sys.stderr)
