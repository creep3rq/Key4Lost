import os, sqlite3, uuid, base64, numpy as np, cv2
import insightface
from insightface.app import FaceAnalysis
from flask import Flask, request, jsonify, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==================== SQLite ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, post_type TEXT, tag TEXT,
        desc TEXT, loc TEXT, time TEXT, status TEXT DEFAULT '',
        claimed_by TEXT, img_path TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS claim_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER,
        name TEXT, sim REAL, time TEXT)""")
    count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    if count == 0:
        from datetime import datetime
        now = datetime.now().strftime("%m/%d %H:%M")
        conn.execute("INSERT INTO items (post_type,tag,desc,loc,time,status,img_path) VALUES (?,?,?,?,?,?,?)",
            ("招领","电子产品","物品类别：鼠标 材质：塑料 颜色：白色 显著特征：有点脏。使用痕迹明显。",
             "图书馆",now,"进行中",
             "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&q=80&w=400&h=300"))
        conn.execute("INSERT INTO items (post_type,tag,desc,loc,time,status,img_path) VALUES (?,?,?,?,?,?,?)",
            ("招领","卡片证件","姓名：江小智的卡 卡证类型：校园卡 补充说明：蠡湖校区图书馆捡到的",
             "地点未填写",now,"进行中",
             "https://images.unsplash.com/photo-1620052581237-5d38faee252f?auto=format&fit=crop&q=80&w=400&h=300"))
    conn.commit(); conn.close()

init_db()

# ==================== InsightFace ====================
face_app = FaceAnalysis()
face_app.prepare(ctx_id=0)
face_bank = []
dataset_dir = os.path.join(BASE_DIR, "face_dataset")
if os.path.isdir(dataset_dir):
    for fname in os.listdir(dataset_dir):
        fpath = os.path.join(dataset_dir, fname)
        img = cv2.imread(fpath)
        if img is None: continue
        faces = face_app.get(img)
        if faces:
            name = os.path.splitext(fname)[0]
            face_bank.append((name, faces[0].embedding))
            print(f"[FaceBank] {name}")

# ==================== Flask ====================
server = Flask(__name__)

@server.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@server.route("/")
def index():
    with open(os.path.join(BASE_DIR, "index.html"),"r",encoding="utf-8") as f:
        return f.read()

@server.route("/api/upload", methods=["POST"])
def upload():
    if "image" not in request.files: return jsonify({"error":"no file"}),400
    f = request.files["image"]
    ext = os.path.splitext(f.filename)[1] or ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    f.save(os.path.join(UPLOAD_DIR, fname))
    return jsonify({"path":f"/uploads/{fname}"})

@server.route("/uploads/<filename>")
def serve_upload(filename):
    return send_file(os.path.join(UPLOAD_DIR, filename))

@server.route("/api/items")
def get_items():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@server.route("/api/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True)
    if not data: return jsonify({"error":"no data"}),400
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO items (post_type,tag,desc,loc,time,status,img_path) VALUES (?,?,?,?,?,?,?)",
        (data.get("postType",""),data.get("tag",""),data.get("desc",""),
         data.get("loc",""),data.get("time",""),"进行中",data.get("img_path","")))
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"id":rid,"ok":True})

@server.route("/api/items/<int:item_id>/claim", methods=["POST"])
def claim(item_id):
    data = request.get_json(silent=True)
    if not data: return jsonify({"error":"no data"}),400
    n = data.get("name",""); s = data.get("sim",0); t = data.get("time","")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE items SET claimed_by=?, status='已认领' WHERE id=?",(n,item_id))
    conn.execute("INSERT INTO claim_log (item_id,name,sim,time) VALUES (?,?,?,?)",(item_id,n,s,t))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@server.route("/api/logs")
def get_logs():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM claim_log ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@server.route("/recognize", methods=["POST"])
def recognize():
    data = request.get_json(silent=True)
    if not data or "image" not in data: return jsonify({"error":"no image"}),400
    b64 = data["image"]
    if "," in b64: b64 = b64.split(",",1)[1]
    try: img_bytes = base64.b64decode(b64)
    except: return jsonify({"error":"base64 decode"}),400
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None: return jsonify({"error":"image decode"}),400
    faces = face_app.get(frame)
    if not faces: return jsonify({"name":"stranger","sim":0,"face_count":0})
    face = faces[0]; bn="stranger"; bs=0.0
    for name, emb in face_bank:
        sim = float(face_app.models['recognition'].compute_sim(face.embedding, emb))
        if sim > bs: bs = sim; bn = name
    if bs < 0.5: bn = "stranger"
    return jsonify({"name":bn,"sim":round(bs,4),"face_count":len(faces)})

if __name__ == "__main__":
    print("[Server] http://localhost:5000")
    server.run(host="0.0.0.0", port=5000, debug=False)
