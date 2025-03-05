from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, sqlite3
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'tools.db'
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute('CREATE TABLE IF NOT EXISTS tools (id INTEGER PRIMARY KEY, title TEXT, link TEXT, image TEXT, click_count INTEGER DEFAULT 0)')
        conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)')
        cur = conn.execute("SELECT * FROM users WHERE username = ?", ("clownman",))
        if not cur.fetchone():
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("clownman", "clownman"))
    conn.close()

init_db()

@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db_connection()
    if search:
        tools = conn.execute("SELECT * FROM tools WHERE title LIKE ? ORDER BY click_count DESC", ('%'+search+'%',)).fetchall()
    else:
        tools = conn.execute("SELECT * FROM tools ORDER BY click_count DESC").fetchall()
    conn.close()
    return render_template('index.html', tools=tools, search=search)

@app.route('/add', methods=['GET', 'POST'])
def add_tool():
    if request.method == 'POST':
        title = request.form['title']
        link = request.form['link']
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                img = Image.open(filepath)
                if img.size != (100, 100):
                    os.remove(filepath)
                    flash("图片尺寸必须为100×100px")
                    return redirect(request.url)
            except Exception:
                flash("为节约服务器资源，请提供100*100像素图片")
                return redirect(request.url)
            conn = get_db_connection()
            conn.execute("INSERT INTO tools (title, link, image) VALUES (?, ?, ?)", (title, link, filename))
            conn.commit()
            conn.close()
            flash("工具添加成功")
            return redirect(url_for('index'))
    return render_template('add_tool.html')

@app.route('/tool/<int:tool_id>')
def tool_redirect(tool_id):
    conn = get_db_connection()
    tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    if tool:
        conn.execute("UPDATE tools SET click_count = click_count + 1 WHERE id = ?", (tool_id,))
        conn.commit()
        conn.close()
        return redirect(tool['link'])
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user'] = username
            return redirect(url_for('admin'))
        else:
            flash("登录失败")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    tools = conn.execute("SELECT * FROM tools").fetchall()
    conn.close()
    return render_template('admin.html', tools=tools)

@app.route('/admin/delete/<int:tool_id>', methods=['POST'])
def delete_tool(tool_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/api/add_tool', methods=['POST'])
def api_add_tool():
    title = request.form['title']
    link = request.form['link']
    file = request.files.get('image')
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            img = Image.open(filepath)
            if img.size != (100, 100):
                os.remove(filepath)
                return {"success": False, "message": "图片尺寸必须为100×100px"}
        except Exception:
            return {"success": False, "message": "为节约服务器资源，请提供100*100像素图片"}
        conn = get_db_connection()
        cur = conn.execute("INSERT INTO tools (title, link, image) VALUES (?, ?, ?)", (title, link, filename))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "tool": {"id": new_id, "title": title, "link": link, "image": filename}}
    return {"success": False, "message": "文件上传错误"}

@app.route('/admin/edit/<int:tool_id>', methods=['GET', 'POST'])
def edit_tool(tool_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        title = request.form['title']
        link = request.form['link']
        conn.execute("UPDATE tools SET title = ?, link = ? WHERE id = ?", (title, link, tool_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    conn.close()
    return render_template('edit_tool.html', tool=tool)

if __name__ == '__main__':
    app.run(debug=True)
