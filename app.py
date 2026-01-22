import requests, base64, json, os, bcrypt, bleach
from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS  # مكتبة حل مشكلة الحظر
from datetime import datetime, timedelta

app = Flask(__name__)

# --- تفعيل CORS للسماح للواجهة بالاتصال بالسيرفر ---
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

# --- إعدادات النظام ---
GITHUB_TOKEN = "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"
GITHUB_REPO = "xxxxxthefox/POP"
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

FILES = {
    "users": "db_users.json", 
    "posts": "db_posts.json", 
    "ips": "db_ips.json", 
    "chats": "db_chats.json"
}

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fox_ultra_secret_2026')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

# --- دوال الربط مع GitHub ---

def cloud_get(path):
    try:
        res = requests.get(f"{API_BASE}/{path}", headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
        if res.status_code == 200:
            j = res.json()
            return json.loads(base64.b64decode(j['content'])), j['sha']
        return {}, None
    except: return {}, None

def cloud_put(path, data, sha=None, msg="Forum Update"):
    content = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    payload = {"message": msg, "content": content}
    if sha: payload["sha"] = sha
    return requests.put(f"{API_BASE}/{path}", json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)

def upload_to_github(username, file_bytes, filename):
    path = f"uploads/profiles/{username}_{filename}"
    content = base64.b64encode(file_bytes).decode()
    check = requests.get(f"{API_BASE}/{path}", headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = check.json()['sha'] if check.status_code == 200 else None
    payload = {"message": "Update avatar", "content": content}
    if sha: payload["sha"] = sha
    requests.put(f"{API_BASE}/{path}", json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"

# --- المسارات (Endpoints) ---

@app.route('/api/auth', methods=['POST', 'OPTIONS'])
def auth():
    # معالجة طلب تسجيل العضوية أو الدخول
    is_reg = request.form.get('register') == 'true'
    user = request.form.get('username', '').lower().strip()
    pw = request.form.get('password', '')
    
    users, sha = cloud_get(FILES["users"])

    if is_reg:
        if user in users: return jsonify(msg="اسم العضوية مستخدم"), 400
        pic = request.files.get('pic')
        pic_url = upload_to_github(user, pic.read(), pic.filename) if pic else ""
        
        users[user] = {
            "password": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
            "nickname": request.form.get('nickname') or user,
            "bio": request.form.get('bio') or "عضو في منتديات FOX",
            "pic": pic_url,
            "verified": (user == 'xxxxxthefox')
        }
        cloud_put(FILES["users"], users, sha)
        return jsonify(msg="تم تسجيل العضوية")
    else:
        if user in users and bcrypt.checkpw(pw.encode(), users[user]['password'].encode()):
            token = create_access_token(identity=user)
            return jsonify(token=token, username=user, nickname=users[user]['nickname'], pic=users[user]['pic'])
        return jsonify(msg="خطأ في البيانات"), 401

@app.route('/api/feed', methods=['GET'])
def get_feed():
    posts, _ = cloud_get(FILES["posts"])
    return jsonify(list(posts.values())[::-1])

@app.route('/api/post', methods=['POST'])
@jwt_required()
def add_post():
    user_id = get_jwt_identity()
    content = bleach.clean(request.json.get('content', ''))
    
    users, _ = cloud_get(FILES["users"])
    posts, sha = cloud_get(FILES["posts"])
    
    post_id = str(len(posts) + 1)
    posts[post_id] = {
        "user": user_id,
        "nickname": users[user_id]['nickname'],
        "pic": users[user_id]['pic'],
        "content": content,
        "date": datetime.now().isoformat()
    }
    cloud_put(FILES["posts"], posts, sha)
    return jsonify(msg="تم نشر الموضوع")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
