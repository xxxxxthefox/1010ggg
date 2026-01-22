import requests, base64, json, os, bcrypt, bleach
from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta

app = Flask(__name__)

# --- إعدادات نظام المنتدى ---
GITHUB_TOKEN = "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"
GITHUB_REPO = "xxxxxthefox/POP"
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

FILES = {"users": "db_users.json", "posts": "db_posts.json", "ips": "db_ips.json", "chats": "db_chats.json"}

app.config['JWT_SECRET_KEY'] = 'fox_forum_secret_key'
jwt = JWTManager(app)

# دوال الربط السحابي
def cloud_get(path):
    res = requests.get(f"{API_BASE}/{path}", headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if res.status_code == 200:
        j = res.json()
        return json.loads(base64.b64decode(j['content'])), j['sha']
    return {}, None

def cloud_put(path, data, sha=None, msg="تحديث قاعدة بيانات المنتدى"):
    content = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    payload = {"message": msg, "content": content}
    if sha: payload["sha"] = sha
    return requests.put(f"{API_BASE}/{path}", json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})

def upload_photo(username, file_storage):
    filename = f"{username}_profile.png"
    path = f"uploads/profiles/{filename}"
    content = base64.b64encode(file_storage.read()).decode()
    check = requests.get(f"{API_BASE}/{path}", headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = check.json()['sha'] if check.status_code == 200 else None
    payload = {"message": f"رفع صورة عضوية: {username}", "content": content}
    if sha: payload["sha"] = sha
    requests.put(f"{API_BASE}/{path}", json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/auth', methods=['POST'])
def auth():
    is_reg = request.form.get('register') == 'true'
    user = request.form.get('username', '').lower().strip()
    pw = request.form.get('password', '')
    users, sha = cloud_get(FILES["users"])

    if is_reg:
        if user in users: return jsonify(msg="اسم العضو مستخدم مسبقاً"), 400
        photo = request.files.get('pic')
        pic_url = upload_photo(user, photo) if photo else ""
        users[user] = {
            "password": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
            "nickname": request.form.get('nickname') or user,
            "bio": request.form.get('bio') or "عضو جديد في المنتدى",
            "pic": pic_url,
            "verified": (user == 'xxxxxthefox') # حسابك الموثق
        }
        cloud_put(FILES["users"], users, sha, msg=f"تسجيل عضو جديد: {user}")
        return jsonify(msg="تم تسجيل عضويتك بنجاح")
    else:
        if user in users and bcrypt.checkpw(pw.encode(), users[user]['password'].encode()):
            token = create_access_token(identity=user)
            return jsonify(token=token, user_data=users[user], username=user)
        return jsonify(msg="خطأ في اسم العضو أو كلمة المرور"), 401

@app.route('/api/feed')
def get_feed():
    posts, _ = cloud_get(FILES["posts"])
    return jsonify(list(posts.values())[::-1])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
