from flask import Flask, jsonify, redirect, request, session, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
import os, secrets, requests, jwt, re
from dotenv import load_dotenv
load_dotenv()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
PORT = int(os.getenv("BACKEND_PORT", "4000"))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret")
DB_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", f"http://localhost:{PORT}/auth/google/callback")
ADMIN_EMAILS = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.secret_key = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

CORS(app, supports_credentials=True, resources={r"/*": {"origins": [FRONTEND_ORIGIN]}})

engine = create_engine(DB_URI, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    google_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    picture = Column(String)
    role = Column(String, default="editor")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    content = Column(Text, nullable=False)
    image_path = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category")
    author = relationship("User")

Base.metadata.create_all(bind=engine)

def slugify(text):
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_-]+', '-', text)
    return text or secrets.token_hex(4)

def create_jwt(payload: dict, minutes: int = 60*24):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes)
    to_encode = {"iat": int(now.timestamp()), "exp": int(exp.timestamp()), **payload}
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

def auth_required(roles=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Unauthorized"}), 401
            token = auth.split(" ", 1)[1]
            try:
                claims = decode_jwt(token)
            except Exception as e:
                return jsonify({"error": "Invalid token", "detail": str(e)}), 401
            if roles and claims.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403
            request.user = claims
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"
GOOGLE_SCOPE = "openid email profile"

@app.get("/auth/google")
def auth_google():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return jsonify({"error": "Missing GOOGLE_CLIENT_ID/SECRET"}), 500
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    session["oauth_nonce"] = nonce
    from urllib.parse import urlencode
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": state,
        "nonce": nonce,
        "prompt": "consent"
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")

@app.get("/auth/google/callback")
def auth_google_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state or state != session.get("oauth_state"):
        return jsonify({"error": "Invalid state or code"}), 400

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    token_resp = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
    if token_resp.status_code != 200:
        return jsonify({"error": "token_exchange_failed", "detail": token_resp.text}), 400
    tokens = token_resp.json()
    id_token = tokens.get("id_token")
    if not id_token:
        return jsonify({"error": "missing_id_token"}), 400

    info_resp = requests.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token}, timeout=10)
    if info_resp.status_code != 200:
        return jsonify({"error": "id_token_invalid", "detail": info_resp.text}), 400
    info = info_resp.json()

    sub = info.get("sub")
    email = info.get("email")
    name = info.get("name") or info.get("email")
    picture = info.get("picture")

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(google_id=sub).one_or_none()
        if not user:
            role = "admin" if email and email.lower() in ADMIN_EMAILS else "editor"
            user = User(google_id=sub, email=email, name=name, picture=picture, role=role)
            db.add(user)
            db.commit()
        else:
            user.email = email or user.email
            user.name = name or user.name
            user.picture = picture or user.picture
            db.commit()
        token = create_jwt({
            "sub": user.google_id,
            "uid": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "role": user.role
        })
    finally:
        db.close()

    return redirect(f"{FRONTEND_ORIGIN}/auth/callback?token={token}")

@app.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"authenticated": False}), 200
    token = auth.split(" ", 1)[1]
    try:
        claims = decode_jwt(token)
        return jsonify({"authenticated": True, "user": claims})
    except Exception as e:
        return jsonify({"authenticated": False, "error": str(e)}), 200

@app.post("/api/upload")
@auth_required(roles=["admin", "editor"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    filename = secure_filename(f.filename)
    base, ext = os.path.splitext(filename)
    unique = f"{base}_{secrets.token_hex(4)}{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
    f.save(path)
    return jsonify({"path": f"/uploads/{unique}"})

@app.get("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.get("/api/categories")
def list_categories():
    db = SessionLocal()
    try:
        rows = db.execute("SELECT id, name, slug, created_at FROM categories ORDER BY created_at DESC").fetchall()
        return jsonify([{"id": r[0], "name": r[1], "slug": r[2]} for r in rows])
    finally:
        db.close()

@app.post("/api/categories")
@auth_required(roles=["admin", "editor"])
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    slug = data.get("slug") or slugify(name)
    if not name:
        return jsonify({"error": "Name required"}), 400
    db = SessionLocal()
    try:
        existing = db.execute("SELECT 1 FROM categories WHERE name=:n OR slug=:s", {"n": name, "s": slug}).first()
        if existing:
            return jsonify({"error": "Category exists"}), 400
        db.execute("INSERT INTO categories (name, slug, created_at) VALUES (:n, :s, :t)",
                   {"n": name, "s": slug, "t": datetime.now(timezone.utc)})
        db.commit()
        new = db.execute("SELECT id, name, slug FROM categories WHERE slug=:s", {"s": slug}).first()
        return jsonify({"id": new[0], "name": new[1], "slug": new[2]})
    finally:
        db.close()

@app.get("/api/posts")
def list_posts():
    db = SessionLocal()
    try:
        posts = db.query(Post).order_by(Post.created_at.desc()).all()
        out = []
        for p in posts:
            out.append({
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "content": p.content,
                "image_path": p.image_path,
                "category": {"id": p.category.id, "name": p.category.name, "slug": p.category.slug} if p.category else None,
                "author": {"id": p.author.id, "name": p.author.name, "email": p.author.email} if p.author else None,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            })
        return jsonify(out)
    finally:
        db.close()

@app.get("/api/posts/<string:slug>")
def get_post(slug):
    db = SessionLocal()
    try:
        p = db.query(Post).filter_by(slug=slug).one_or_none()
        if not p:
            return jsonify({"error": "Not found"}), 404
        return jsonify({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "content": p.content,
            "image_path": p.image_path,
            "category_id": p.category_id,
            "author_id": p.author_id,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })
    finally:
        db.close()

@app.get("/api/post_by_id/<int:pid>")
def get_post_by_id(pid):
    db = SessionLocal()
    try:
        p = db.query(Post).get(pid)
        if not p:
            return jsonify({"error": "Not found"}), 404
        return jsonify({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "content": p.content,
            "image_path": p.image_path,
            "category_id": p.category_id,
            "author_id": p.author_id,
        })
    finally:
        db.close()

@app.post("/api/posts")
@auth_required(roles=["admin", "editor"])
def create_post():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    image_path = data.get("image_path")
    category_id = data.get("category_id")
    if not title or not content:
        return jsonify({"error": "Title and content required"}), 400
    slug = data.get("slug") or slugify(title)
    db = SessionLocal()
    try:
        if db.query(Post).filter_by(slug=slug).first():
            slug = f"{slug}-{secrets.token_hex(2)}"
        p = Post(title=title, slug=slug, content=content, image_path=image_path,
                 category_id=category_id, author_id=request.user.get("uid"))
        db.add(p)
        db.commit()
        return jsonify({"id": p.id, "slug": p.slug})
    finally:
        db.close()

@app.put("/api/posts/<int:pid>")
@auth_required(roles=["admin", "editor"])
def update_post(pid):
    data = request.get_json() or {}
    db = SessionLocal()
    try:
        p = db.query(Post).get(pid)
        if not p:
            return jsonify({"error": "Not found"}), 404
        if request.user.get("role") != "admin" and request.user.get("uid") != p.author_id:
            return jsonify({"error": "Forbidden"}), 403
        for field in ["title", "content", "image_path", "category_id"]:
            if field in data:
                setattr(p, field, data[field])
        if "slug" in data and data["slug"]:
            p.slug = data["slug"]
        p.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

@app.delete("/api/posts/<int:pid>")
@auth_required(roles=["admin"])
def delete_post(pid):
    db = SessionLocal()
    try:
        p = db.query(Post).get(pid)
        if not p:
            return jsonify({"error": "Not found"}), 404
        db.delete(p)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
