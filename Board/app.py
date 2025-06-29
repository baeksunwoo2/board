import bcrypt # 비밀번호 암호화를 위해 함수 호출
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from db_config import get_db_connection # DB 연결

app = Flask(__name__)
app.secret_key = 'PPACK_GONG_PAT_HOMEWORK'  # 세션 통신 간 암호화를 위한 시크릿 키

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# 1. 게시판 메인 페이지
@app.route('/')
def index():
    # 검색 관련 파라미터 받기, URL에서 검색어(q)와 검색 타입(type)을 가져옴
    search_query = request.args.get('q', '')
    search_type = request.args.get('type', 'title_content') # 기본값: 제목+내용

    conn = get_db_connection()
    cursor = conn.cursor()

    # SQL 기본 쿼리
    sql = "SELECT id, title, username, created_at, views FROM posts "
    params = []

    # 검색어가 있는 경우, WHERE 절 추가, SQL injection 방지를 위해 동적 처리
    if search_query:
        if search_type == 'title_content':
            sql += "WHERE title LIKE %s OR content LIKE %s "
            params.extend([f"%{search_query}%", f"%{search_query}%"])  # 리스트에 여러 개의 항목(title용, content용)을 한 번에 추가
        elif search_type == 'title':
            sql += "WHERE title LIKE %s "
            params.append(f"%{search_query}%")
        elif search_type == 'content':
            sql += "WHERE content LIKE %s "
            params.append(f"%{search_query}%")
        elif search_type == 'username':
            sql += "WHERE username LIKE %s "
            params.append(f"%{search_query}%")

    sql += "ORDER BY created_at DESC"
    
    cursor.execute(sql, tuple(params)) # SQL 명령어로 해석하지 않고 데이터로만 처리
    posts = cursor.fetchall()
    conn.close()

    # 템플릿에 검색어와 검색 타입도 전달
    return render_template('index.html', posts=posts, search_query=search_query, search_type=search_type)

# 2. 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = hash_password(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('이미 존재하는 사용자 이름입니다.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

# 3. 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"{user['username']}님, 환영합니다!", 'success')
            return redirect(url_for('index'))
        else:
            flash('사용자 이름 또는 비밀번호가 올바르지 않습니다.', 'danger')

    return render_template('login.html')

# 4. 로그아웃
@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('index'))

# 5. 글쓰기
@app.route('/write', methods=['GET', 'POST'])
def write():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']
        username = session['username']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posts (title, content, user_id, username) VALUES (%s, %s, %s, %s)",
                       (title, content, user_id, username))
        conn.commit()
        conn.close()
        flash('게시글이 성공적으로 작성되었습니다.', 'success')
        return redirect(url_for('index'))

    return render_template('write.html')

# 6. 게시글 상세 보기
@app.route('/post/<int:post_id>')
def view(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 조회수 증가
    cursor.execute("UPDATE posts SET views = views + 1 WHERE id = %s", (post_id,))
    conn.commit()

    # 게시글 가져오기
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    conn.close()
    
    if post is None:
        flash('존재하지 않는 게시글입니다.', 'danger')
        return redirect(url_for('index'))

    return render_template('view.html', post=post)

# 7. 게시글 수정
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if post['user_id'] != session['user_id']:
        flash('수정 권한이 없습니다.', 'danger')
        conn.close()
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute("UPDATE posts SET title = %s, content = %s WHERE id = %s", (title, content, post_id))
        conn.commit()
        conn.close()
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('view', post_id=post_id))
    
    conn.close()
    return render_template('edit.html', post=post)

# 8. 게시글 삭제
@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if post and post['user_id'] == session['user_id']:
        cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        conn.commit()
        flash('게시글이 삭제되었습니다.', 'success')
    else:
        flash('삭제 권한이 없거나 존재하지 않는 게시글입니다.', 'danger')
    
    conn.close()
    return redirect(url_for('index'))

# 9. 회원정보
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('login'))
    return render_template('profile.html')

# 10. 회원탈퇴
@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ON DELETE CASCADE 속성으로 인해 posts 테이블의 관련 레코드는 자동 삭제됨
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    flash('회원탈퇴가 완료되었습니다.', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)