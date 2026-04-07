import os
import json
import sqlite3
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from maarifx import MaarifX
from maarifx.exceptions import MaarifXError, RateLimitError

load_dotenv()

app = Flask(__name__)

MAARIFX_API_KEY = os.getenv("MAARIFX_API_KEY")
MAARIFX_BASE_URL = os.getenv("MAARIFX_BASE_URL", "https://api2.ogretimsayfam.com")

if not MAARIFX_API_KEY:
    raise RuntimeError("MAARIFX_API_KEY is not set. Check your .env file.")

client = MaarifX(api_key=MAARIFX_API_KEY, base_url=MAARIFX_BASE_URL)

DB_PATH = Path(__file__).parent / "distributor.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT,
            email TEXT,
            maarifx_token TEXT,
            maarifx_external_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def authenticate_user(username, password):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    conn.close()
    return dict(user) if user else None


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    username = data.get("username")
    password = data.get("password")
    display_name = data.get("display_name", username)
    email = data.get("email")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Username already exists"}), 409

    try:
        sub_user = client.register_user(
            external_id=username,
            display_name=display_name,
            email=email,
        )
    except MaarifXError as e:
        conn.close()
        return jsonify({"error": f"MaarifX error: {e.message}"}), e.status_code or 500

    conn.execute(
        """INSERT INTO users (username, password, display_name, email, maarifx_token, maarifx_external_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (username, password, display_name, email, sub_user.token, username),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Registration successful",
        "username": username,
        "daily_limit": sub_user.daily_limit,
    }), 201


@app.route("/solve", methods=["POST"])
def solve():
    username = request.headers.get("X-Username")
    password = request.headers.get("X-Password")

    if not username or not password:
        return jsonify({"error": "X-Username and X-Password headers required"}), 401

    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.get("maarifx_token"):
        return jsonify({"error": "MaarifX token not found for this user"}), 500

    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400

    image_file = request.files["image"]
    text = request.form.get("text", "")
    draw_on_image = request.form.get("draw_on_image", "false").lower() == "true"
    stream = request.form.get("stream", "true").lower() != "false"

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        if stream:
            def generate():
                try:
                    for event in client.solve_stream(
                        tmp_path,
                        text=text,
                        draw_on_image=draw_on_image,
                        sub_user_token=user["maarifx_token"],
                    ):
                        if event.type == "token":
                            yield f"event: token\ndata: {json.dumps({'token': event.token})}\n\n"
                        elif event.type == "thinking":
                            yield f"event: thinking\ndata: {json.dumps({'token': event.token})}\n\n"
                        elif event.type == "thinking_done":
                            yield f"event: thinking_done\ndata: {{}}\n\n"
                        elif event.type == "status":
                            yield f"event: status\ndata: {json.dumps({'message': event.message})}\n\n"
                        elif event.type == "complete":
                            complete_data = {"requestId": event.request_id}
                            if event.usage:
                                complete_data["usage"] = {
                                    "input_tokens": event.usage.input_tokens,
                                    "output_tokens": event.usage.output_tokens,
                                }
                            if event.view_url:
                                complete_data["view_url"] = event.view_url
                            if event.text:
                                complete_data["text"] = event.text
                            yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"
                        elif event.type == "error":
                            yield f"event: error\ndata: {json.dumps({'message': event.message})}\n\n"
                except MaarifXError as e:
                    yield f"event: error\ndata: {json.dumps({'message': e.message})}\n\n"
                finally:
                    os.unlink(tmp_path)

            return Response(generate(), mimetype="text/event-stream")
        else:
            try:
                result = client.solve(
                    tmp_path,
                    text=text,
                    draw_on_image=draw_on_image,
                    sub_user_token=user["maarifx_token"],
                )

                response = {
                    "requestId": result.request_id,
                    "status": result.status,
                    "usage": {
                        "input_tokens": result.usage.input_tokens,
                        "output_tokens": result.usage.output_tokens,
                    },
                }

                if result.view_url:
                    response["view_url"] = result.view_url
                if result.text:
                    response["text"] = result.text

                return jsonify(response)

            except RateLimitError as e:
                return jsonify({"error": f"Rate limit exceeded: {e.message}"}), 429
            except MaarifXError as e:
                return jsonify({"error": f"MaarifX error: {e.message}"}), e.status_code or 500
            finally:
                os.unlink(tmp_path)

    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/users", methods=["GET"])
def list_users():
    conn = get_db()
    users = conn.execute(
        "SELECT id, username, display_name, email, created_at FROM users"
    ).fetchall()
    conn.close()

    return jsonify({
        "users": [dict(u) for u in users],
        "total": len(users),
    })


@app.route("/usage", methods=["GET"])
def usage():
    try:
        stats = client.get_usage()
        return jsonify({
            "today": {
                "requests": stats.today.requests,
                "input_tokens": stats.today.input_tokens,
                "output_tokens": stats.today.output_tokens,
                "cost_usd": stats.today.cost_usd,
            },
            "this_month": {
                "requests": stats.this_month.requests,
                "input_tokens": stats.this_month.input_tokens,
                "output_tokens": stats.this_month.output_tokens,
                "cost_usd": stats.this_month.cost_usd,
            },
            "limits": stats.limits,
        })
    except MaarifXError as e:
        return jsonify({"error": e.message}), e.status_code or 500


if __name__ == "__main__":
    print("=" * 50)
    print("MaarifX Distributor Backend Example")
    print("=" * 50)
    print(f"API Key: {MAARIFX_API_KEY[:16]}...")
    print(f"Base URL: {MAARIFX_BASE_URL}")
    print(f"Database: {DB_PATH}")
    print()
    print("Endpoints:")
    print("  POST /register  - Register new student")
    print("  POST /solve     - Solve a question")
    print("  GET  /users     - List users")
    print("  GET  /usage     - Usage statistics")
    print("=" * 50)

    app.run(debug=True, port=5000)
