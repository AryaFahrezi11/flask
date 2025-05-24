from flask import Flask, render_template, request, redirect, jsonify, flash, session, g
import pymysql
import os

app = Flask(__name__)
app.secret_key = 'Nic Furniture'

# Konfigurasi database
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}


# Fungsi koneksi database
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.template_filter('rupiah')
def format_rupiah(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


@app.route('/')
def home():
    cur = get_db().cursor()
    query = '''
    SELECT product.*, category.name_category 
    FROM product INNER JOIN category
    ON product.category = category.id_category
    '''
    cur.execute(query)
    product = cur.fetchall()
    return render_template('home.html', produk=product)

@app.route('/home-admin')
def home_admin():
    cur = get_db().cursor()
    query = '''
    SELECT product.*, category.name_category 
    FROM product INNER JOIN category
    ON product.category = category.id_category
    '''
    cur.execute(query)
    product = cur.fetchall()
    return render_template('home.html', produk=product, admin=session.get('admin'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Semua field harus diisi!', 'error')
            return redirect('/login')
        if username == 'admin' and password == '123':
            session['admin'] = True
            return redirect('/home-admin')
        else:
            flash('Username atau Password salah', 'error')
            return redirect('/login')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/cekkoneksi')
def cek_data():  
    cur = get_db().cursor()
    cur.execute('SELECT 1')
    return jsonify({'message': 'berhasil'})

@app.route('/product')
def homepage():
    cur = get_db().cursor()
    query = '''
    SELECT product.*, category.name_category 
    FROM product INNER JOIN category
    ON product.category = category.id_category
    '''
    cur.execute(query)
    product = cur.fetchall()
    return render_template('product.html', produk=product)

@app.route('/card-product')
def card_product():
    cur = get_db().cursor()
    query = 'SELECT * FROM product'
    cur.execute(query)
    product = cur.fetchall()
    return render_template('/layouts/component/card.html', produk=product)

@app.route('/add-product')
def add_product():
    db = get_db()
    cur = db.cursor()
    
    # Ambil data kategori untuk dropdown
    cur.execute('SELECT * FROM category')
    kategori = cur.fetchall()

    # Ambil semua produk
    cur.execute('''
        SELECT product.*, category.name_category 
        FROM product 
        INNER JOIN category ON product.category = category.id_category
    ''')
    produk = cur.fetchall()

    return render_template('add-product.html', kategori=kategori, produk=produk)



@app.route('/save-product', methods=['POST'])
def save_product():
    name_product = request.form['name_product']
    image_url = request.form['image_url']
    price = request.form['price']
    category = request.form['category']
    in_stok = request.form['in_stok']
    deskripsi = request.form['deskripsi']

    # Validasi: kategori tidak boleh kosong atau nol
    if not category or category == "0":
        flash("Kategori tidak boleh kosong", "error")
        return redirect('/add-product')

    db = get_db()
    cur = db.cursor()
    query = '''
    INSERT INTO product (name_product, image_url, price, category, in_stok, deskripsi)
    VALUES (%s, %s, %s, %s, %s, %s)
    '''
    cur.execute(query, (name_product, image_url, price, category, in_stok, deskripsi))
    db.commit()

    flash("Produk berhasil ditambahkan", "success")
    return redirect('/add-product')



@app.route('/edit-product/<int:id>')
def edit_product(id):
    cur = get_db().cursor()
    query = 'SELECT * FROM product WHERE id = %s'
    cur.execute(query, [id])
    product = cur.fetchone() 
    sql = 'SELECT * FROM category'
    cur.execute(sql)
    category = cur.fetchall()
    return render_template('edit-product.html', produk=product, kategori=category)

@app.route('/update-product/<int:id>', methods=['POST'])
def update_product(id):
    name_product = request.form['name_product']
    image_URL = request.form['image_url']
    price = request.form['price']
    category = request.form['category']
    in_stok = request.form['in_stok']
    deskripsi = request.form['deskripsi']
    cur = get_db().cursor()
    query = '''UPDATE product SET 
        name_product = %s, 
        image_url = %s, 
        price = %s, 
        category = %s, 
        in_stok = %s, 
        deskripsi = %s 
        WHERE id = %s'''
    cur.execute(query, (name_product, image_URL, price, category, in_stok, deskripsi, id))
    get_db().commit()
    flash('Produk berhasil diupdate', 'success')
    return redirect('/add-product')

@app.route('/delete-product/<int:id>')
def delete_product(id):
    try:
        cur = get_db().cursor()
        query = 'DELETE FROM product WHERE id = %s'
        cur.execute(query, [id])
        get_db().commit()
        flash('Produk berhasil dihapus', 'success')
    except Exception as e:
        flash(f'Produk gagal dihapus {str(e)}', 'error')
    return redirect('/add-product')    

@app.route('/about')
def aboutpage():
    return render_template('about.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 8
    if not query:
        return render_template('search_produk.html', products=[], query=query, total_pages=0, current_page=1)
    cur = get_db().cursor()
    search_value = f"%{query}%"
    offset = (page - 1) * per_page
    cur.execute("""
        SELECT product.id, product.name_product, product.image_url, product.price
        FROM product
        WHERE product.name_product LIKE %s
        LIMIT %s OFFSET %s
    """, (search_value, per_page, offset))
    products = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM product WHERE product.name_product LIKE %s", (search_value,))
    total_products = cur.fetchone()['COUNT(*)']
    total_pages = -(-total_products // per_page)
    return render_template('search_produk.html', products=products, query=query, total_pages=total_pages, current_page=page)

@app.route('/detail-produk/<int:id>')
def detail_produk(id):
    cur = get_db().cursor()
    query_detail = 'SELECT * FROM product WHERE id = %s'
    cur.execute(query_detail, [id])
    product_detail = cur.fetchone()
    query_produk = '''
    SELECT product.*, category.name_category 
    FROM product INNER JOIN category
    ON product.category = category.id_category
    '''
    cur.execute(query_produk)
    produk = cur.fetchall()
    return render_template('detail-product.html', detail=product_detail, produk=produk)

@app.route('/contact', methods=['POST', 'GET'])
def contact():
    if request.method == 'POST':
        nama = request.form['name']
        email = request.form['email']
        pesan = request.form['pesan']
        cur = get_db().cursor()
        query = 'INSERT INTO messages (nama, email, pesan) VALUES (%s, %s, %s)'
        cur.execute(query, (nama, email, pesan))
        get_db().commit()
    return render_template('contact.html')

@app.route('/admin/messages')
def admin_messages():
    cur = get_db().cursor()
    query = 'SELECT * FROM messages ORDER BY waktu_kirim DESC'
    cur.execute(query)
    messages = cur.fetchall()
    return render_template('admin-messages.html', messages=messages)

def handler(environ, start_response):
    return app(environ, start_response)