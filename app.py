import os
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from scripts.export_order import export_to_pdf, export_to_excel
from image_utils import resize_image

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['UPLOAD_FOLDER'] = 'static/images/products'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        flash(f"Database connection error: {e}", 'error')
        return None

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/factory/upload', methods=['GET', 'POST'])
def factory_upload():
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        search_query = request.args.get('search', '').strip()
        if search_query:
            products = c.execute('SELECT * FROM products WHERE product_code LIKE ?', (f'%{search_query}%',)).fetchall()
        else:
            products = c.execute('SELECT * FROM products').fetchall()
        
        inventory = {}
        orders = {}
        balances = {}
        color_groups = {}
        uploaded_product = None
        uploaded_inventory = []
        pending_orders = c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.status = "Pending"').fetchall()

        resized_images = {}
        for product in products:
            if product['product_image']:
                try:
                    resized_path = resize_image(os.path.join('static', product['product_image']))
                    resized_images[product['product_id']] = resized_path[7:] if resized_path else None
                except Exception as e:
                    flash(f"Error resizing image for product {product['product_code']}: {e}", 'error')
                    resized_images[product['product_id']] = None
            else:
                resized_images[product['product_id']] = None

            c.execute('SELECT * FROM inventory_breakdown WHERE product_id = ?', (product['product_id'],))
            inventory[product['product_id']] = [dict(row) for row in c.fetchall()]

            c.execute('SELECT * FROM orders WHERE product_id = ?', (product['product_id'],))
            raw_orders = c.fetchall()
            orders[product['product_id']] = [dict(order, product_name=product['product_name']) for order in raw_orders]

            color_groups[product['product_id']] = {}
            for inv in inventory[product['product_id']]:
                color = inv['color'] if inv['color'] is not None else 'Unknown'
                if color not in color_groups[product['product_id']]:
                    color_groups[product['product_id']][color] = []
                color_groups[product['product_id']][color].append({
                    'size': inv['size'] if inv['size'] is not None else 'Unknown',
                    'quantity': inv['quantity'] if inv['quantity'] is not None else 0
                })

            balance = {}
            for inv in inventory[product['product_id']]:
                color = inv['color'] if inv['color'] is not None else 'Unknown'
                size = inv['size'] if inv['size'] is not None else 'Unknown'
                produced_qty = inv['quantity'] if inv['quantity'] is not None else 0
                sent_qty = sum(
                    order['quantity'] for order in orders.get(product['product_id'], [])
                    if order['color'] == color and order['size'] == size
                )
                balance[(color, size)] = produced_qty - sent_qty
            balances[product['product_id']] = balance

        if request.method == 'POST' and 'product_code' in request.form:
            product_code = request.form['product_code']
            product_name = request.form['product_name']
            product_description = request.form['product_description']
            category = request.form['category']
            campaign_type = request.form['campaign_type']
            image = request.files['product_image']

            if image and not allowed_file(image.filename):
                flash('Invalid file type! Only PNG, JPG, JPEG, and GIF are allowed.', 'error')
                return redirect(url_for('factory_upload'))

            if image:
                file_extension = os.path.splitext(image.filename)[1]
                random_filename = f"{uuid.uuid4().hex}{file_extension}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
                image.save(image_path)
                db_image_path = f"images/products/{random_filename}"
            else:
                db_image_path = None

            c.execute('''INSERT INTO products (product_code, product_name, product_image, product_description, category, campaign_type, produced_quantity, released_quantity)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (product_code, product_name, db_image_path, product_description, category, campaign_type, 0, 0))
            product_id = c.lastrowid

            colors = request.form.getlist('color[]')
            sizes = request.form.getlist('size[]')
            quantities = request.form.getlist('quantity[]')

            total_produced = 0
            for color, size, qty in zip(colors, sizes, quantities):
                qty = int(qty)
                total_produced += qty
                c.execute('''INSERT INTO inventory_breakdown (product_id, color, size, quantity)
                             VALUES (?, ?, ?, ?)''', (product_id, color, size, qty))

            c.execute('UPDATE products SET produced_quantity = ? WHERE product_id = ?', (total_produced, product_id))

            c.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            uploaded_product = c.fetchone()
            c.execute('SELECT * FROM inventory_breakdown WHERE product_id = ?', (product_id,))
            uploaded_inventory = [dict(row) for row in c.fetchall()]

            if uploaded_product['product_image']:
                try:
                    resized_images[product_id] = resize_image(os.path.join('static', uploaded_product['product_image']))[7:]
                except Exception as e:
                    flash(f"Error resizing uploaded image: {e}", 'error')
                    resized_images[product_id] = None

            conn.commit()
            flash('Product uploaded successfully!', 'success')
            return render_template('factory_upload.html', products=products, inventory=inventory, orders=orders, 
                                  balances=balances, color_groups=color_groups, resized_images=resized_images, 
                                  uploaded_product=uploaded_product, uploaded_inventory=uploaded_inventory, 
                                  pending_orders=pending_orders, search_query=search_query)

        conn.close()
        return render_template('factory_upload.html', products=products, inventory=inventory, orders=orders, 
                              balances=balances, color_groups=color_groups, resized_images=resized_images, 
                              uploaded_product=uploaded_product, uploaded_inventory=uploaded_inventory, 
                              pending_orders=pending_orders, search_query=search_query)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('factory_upload'))
    except Exception as e:
        flash(f"Unexpected error: {e}", 'error')
        conn.close()
        return redirect(url_for('factory_upload'))

@app.route('/delete_inventory/<int:inventory_id>', methods=['GET'])
def delete_inventory(inventory_id):
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT product_id, quantity FROM inventory_breakdown WHERE id = ?', (inventory_id,))
        inventory = c.fetchone()
        if not inventory:
            flash('Inventory record not found!', 'error')
            return redirect(url_for('factory_upload'))

        product_id = inventory['product_id']
        quantity_to_remove = inventory['quantity']

        c.execute('DELETE FROM inventory_breakdown WHERE id = ?', (inventory_id,))

        c.execute('UPDATE products SET produced_quantity = produced_quantity - ? WHERE product_id = ?', 
                  (quantity_to_remove, product_id))

        conn.commit()
        flash('Inventory record deleted successfully!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_upload'))

@app.route('/edit_inventory/<int:inventory_id>', methods=['GET', 'POST'])
def edit_inventory(inventory_id):
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT * FROM inventory_breakdown WHERE id = ?', (inventory_id,))
        inventory = c.fetchone()
        if not inventory:
            flash('Inventory record not found!', 'error')
            return redirect(url_for('factory_upload'))

        c.execute('SELECT * FROM products WHERE product_id = ?', (inventory['product_id'],))
        product = c.fetchone()

        if request.method == 'POST':
            color = request.form['color']
            size = request.form['size']
            quantity = int(request.form['quantity'])

            old_quantity = inventory['quantity']
            quantity_diff = quantity - old_quantity

            c.execute('UPDATE inventory_breakdown SET color = ?, size = ?, quantity = ? WHERE id = ?', 
                      (color, size, quantity, inventory_id))

            c.execute('UPDATE products SET produced_quantity = produced_quantity + ? WHERE product_id = ?', 
                      (quantity_diff, inventory['product_id']))

            conn.commit()
            flash('Inventory record updated successfully!', 'success')
            return redirect(url_for('factory_upload'))

        conn.close()
        return render_template('edit_inventory.html', inventory=inventory, product=product)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('factory_upload'))

@app.route('/factory/products', methods=['GET'])
def factory_products():
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        search_query = request.args.get('search', '').strip()
        if search_query:
            products = c.execute('SELECT * FROM products WHERE product_code LIKE ?', (f'%{search_query}%',)).fetchall()
        else:
            products = c.execute('SELECT * FROM products').fetchall()
        
        inventory = {}
        orders = {}
        balances = {}
        color_groups = {}
        resized_images = {}

        for product in products:
            if product['product_image']:
                try:
                    resized_path = resize_image(os.path.join('static', product['product_image']))
                    resized_images[product['product_id']] = resized_path[7:] if resized_path else None
                except Exception as e:
                    flash(f"Error resizing image for product {product['product_code']}: {e}", 'error')
                    resized_images[product['product_id']] = None
            else:
                resized_images[product['product_id']] = None

            c.execute('SELECT * FROM inventory_breakdown WHERE product_id = ?', (product['product_id'],))
            inventory[product['product_id']] = [dict(row) for row in c.fetchall()]

            c.execute('SELECT * FROM orders WHERE product_id = ?', (product['product_id'],))
            raw_orders = c.fetchall()
            orders[product['product_id']] = [dict(order, product_name=product['product_name']) for order in raw_orders]

            color_groups[product['product_id']] = {}
            for inv in inventory[product['product_id']]:
                color = inv['color'] if inv['color'] is not None else 'Unknown'
                if color not in color_groups[product['product_id']]:
                    color_groups[product['product_id']][color] = []
                color_groups[product['product_id']][color].append({
                    'size': inv['size'] if inv['size'] is not None else 'Unknown',
                    'quantity': inv['quantity'] if inv['quantity'] is not None else 0
                })

            balance = {}
            for inv in inventory[product['product_id']]:
                color = inv['color'] if inv['color'] is not None else 'Unknown'
                size = inv['size'] if inv['size'] is not None else 'Unknown'
                produced_qty = inv['quantity'] if inv['quantity'] is not None else 0
                sent_qty = sum(
                    order['quantity'] for order in orders.get(product['product_id'], [])
                    if order['color'] == color and order['size'] == size and order['status'] != 'Cancelled'
                )
                balance[(color, size)] = produced_qty - sent_qty
            balances[product['product_id']] = balance

        conn.close()
        return render_template('factory_products.html', products=products, inventory=inventory, orders=orders, 
                              balances=balances, color_groups=color_groups, resized_images=resized_images, 
                              search_query=search_query)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('factory_products'))

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM inventory_breakdown WHERE product_id = ?', (product_id,))
        c.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
        conn.commit()
        flash('Product deleted successfully!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_products'))

@app.route('/shop', methods=['GET', 'POST'])
def shop_view():
    if 'user_id' not in session or session.get('role') != 'shop':
        flash('Please login as shop admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        search_query = request.args.get('search', '').strip()
        if search_query:
            products = c.execute('SELECT * FROM products WHERE product_code LIKE ?', (f'%{search_query}%',)).fetchall()
        else:
            products = c.execute('SELECT * FROM products').fetchall()
        
        inventory = {}
        orders = c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id').fetchall()

        for product in products:
            c.execute('SELECT * FROM inventory_breakdown WHERE product_id = ?', (product['product_id'],))
            inventory[product['product_id']] = [dict(row) for row in c.fetchall()]

        if request.method == 'POST' and request.form.get('place_order'):
            product_id = request.form['product_id']
            color = request.form['color']
            size = request.form['size']
            quantity = int(request.form['quantity'])
            order_date = request.form['order_date']
            expected_delivery_date = request.form['expected_delivery_date']
            is_urgent = 1 if request.form.get('is_urgent') else 0
            comments = request.form['comments']
            order_number = f"ORD-{uuid.uuid4().hex[:8]}"

            # Check if an active order already exists for this product, color, and size
            c.execute('SELECT * FROM orders WHERE product_id = ? AND color = ? AND size = ? AND status IN ("Pending", "Released")', 
                      (product_id, color, size))
            existing_order = c.fetchone()
            if existing_order:
                flash('An active order already exists for this product, color, and size. Please wait until the current order is completed.', 'error')
                return redirect(url_for('shop_view', tab='place-order', product_id=product_id, color=color, size=size))

            c.execute('SELECT quantity FROM inventory_breakdown WHERE product_id = ? AND color = ? AND size = ?', (product_id, color, size))
            stock = c.fetchone()
            produced_quantity = stock['quantity'] if stock else 0

            c.execute('SELECT SUM(quantity) as total_ordered FROM orders WHERE product_id = ? AND color = ? AND size = ? AND status != "Cancelled"', 
                      (product_id, color, size))
            ordered_result = c.fetchone()
            total_ordered = ordered_result['total_ordered'] if ordered_result['total_ordered'] else 0

            available_quantity = produced_quantity - total_ordered
            if available_quantity < quantity:
                flash(f"Not enough stock for {color} {size}. Available: {available_quantity}. Please place a new product order.", 'error')
                return redirect(url_for('shop_view', tab='place-order', product_id=product_id, color=color, size=size))
            
            c.execute('''INSERT INTO orders (order_number, product_id, color, size, quantity, order_date, expected_delivery_date, is_urgent, comments, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (order_number, product_id, color, size, quantity, order_date, expected_delivery_date, is_urgent, comments, 'Pending'))
            conn.commit()
            flash('Order placed successfully!', 'success')

        if request.method == 'POST' and request.form.get('place_new_order'):
            product_name = request.form['product_name']
            color = request.form['color']
            size = request.form['size']
            quantity = int(request.form['quantity'])
            order_date = request.form['order_date']
            expected_delivery_date = request.form['expected_delivery_date']
            is_urgent = 1 if request.form.get('is_urgent') else 0
            comments = request.form['comments']
            order_number = f"NEW-ORD-{uuid.uuid4().hex[:8]}"

            c.execute('''INSERT INTO orders (order_number, product_id, color, size, quantity, order_date, expected_delivery_date, is_urgent, comments, status, product_name)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (order_number, None, color, size, quantity, order_date, expected_delivery_date, is_urgent, comments, 'Pending', product_name))
            conn.commit()
            flash('New product order placed successfully!', 'success')

        conn.close()
        return render_template('shop_view.html', products=products, inventory=inventory, orders=orders, search_query=search_query)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('shop_view'))

@app.route('/order_status/<int:product_id>/<color>/<size>')
def order_status(product_id, color, size):
    if 'user_id' not in session or session.get('role') != 'shop':
        flash('Please login as shop admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
        product = c.fetchone()
        if not product:
            flash('Product not found!', 'error')
            return redirect(url_for('shop_view'))

        c.execute('SELECT * FROM orders WHERE product_id = ? AND color = ? AND size = ?', (product_id, color, size))
        orders = c.fetchall()

        conn.close()
        return render_template('order_status.html', product=product, orders=orders, color=color, size=size)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('shop_view'))

@app.route('/confirm_order/<order_number>', methods=['GET', 'POST'])
def confirm_order(order_number):
    if 'user_id' not in session or session.get('role') != 'shop':
        flash('Please login as shop admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE order_number = ?', (order_number,))
        order = c.fetchone()
        
        if request.method == 'POST':
            received_quantity = int(request.form['received_quantity'])
            received_color = request.form['received_color']
            received_size = request.form['received_size']
            received_date = request.form['received_date']
            adjustment_comments = request.form['adjustment_comments']

            c.execute('''UPDATE orders SET quantity = ?, color = ?, size = ?, received_date = ?, adjustment_comments = ?, status = ?
                         WHERE order_number = ?''',
                      (received_quantity, received_color, received_size, received_date, adjustment_comments, 'Received', order_number))
            conn.commit()
            flash('Order receipt confirmed!', 'success')
            return redirect(url_for('shop_view'))

        conn.close()
        return render_template('confirm_order.html', order=order)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('shop_view'))

@app.route('/edit_order/<order_number>', methods=['POST'])
def edit_order(order_number):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        quantity = int(request.form['quantity'])
        color = request.form['color']
        size = request.form['size']
        expected_delivery_date = request.form['expected_delivery_date']
        comments = request.form['comments']
        is_urgent = 1 if request.form.get('is_urgent') else 0

        c.execute('UPDATE orders SET quantity = ?, color = ?, size = ?, expected_delivery_date = ?, comments = ?, is_urgent = ? WHERE order_number = ?',
                  (quantity, color, size, expected_delivery_date, comments, is_urgent, order_number))
        conn.commit()
        flash('Order updated successfully!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

@app.route('/cancel_order/<order_number>', methods=['POST'])
def cancel_order(order_number):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('UPDATE orders SET status = ? WHERE order_number = ?', ('Cancelled', order_number))
        conn.commit()
        flash('Order cancelled successfully!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

@app.route('/release_order/<order_number>', methods=['POST'])
def release_order(order_number):
    if 'user_id' not in session or session.get('role') != 'factory':
        flash('Please login as factory admin!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('UPDATE orders SET status = ? WHERE order_number = ?', ('Released', order_number))
        c.execute('SELECT product_id, quantity FROM orders WHERE order_number = ?', (order_number,))
        order = c.fetchone()
        if order['product_id']:
            c.execute('UPDATE products SET released_quantity = released_quantity + ? WHERE product_id = ?', (order['quantity'], order['product_id']))
        conn.commit()
        flash('Order released to shop!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_upload'))

@app.route('/reject_order/<order_number>', methods=['POST'])
def reject_order(order_number):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('UPDATE orders SET status = ? WHERE order_number = ?', ('Rejected', order_number))
        conn.commit()
        flash('Order rejected!', 'success')
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_upload'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        if not conn:
            return redirect(url_for('index'))
        c = conn.cursor()
        
        try:
            c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = c.fetchone()
            
            if user:
                session['user_id'] = user['user_id']
                session['role'] = user['role']
                if user['role'] == 'factory':
                    return redirect(url_for('factory_upload'))
                elif user['role'] == 'shop':
                    return redirect(url_for('shop_view'))
            flash('Invalid credentials!', 'error')
        except sqlite3.Error as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        products = c.execute('SELECT product_name, produced_quantity FROM products').fetchall()
        orders = c.execute('SELECT o.order_number, o.product_id, o.quantity, o.expected_delivery_date, o.received_date, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.status != "Cancelled"').fetchall()
        
        production_labels = [p['product_name'] for p in products]
        production_values = [p['produced_quantity'] for p in products]
        
        delivery_labels = [o['product_name'] if o['product_name'] else f"Order {o['order_number']}" for o in orders]
        delivery_values = [o['quantity'] for o in orders]
        
        on_time = sum(1 for o in orders if o['received_date'] and o['received_date'] <= o['expected_delivery_date'])
        delayed = len(orders) - on_time
        delivery_status_labels = ['On Time', 'Delayed']
        delivery_status_values = [on_time, delayed]
        
        conn.close()
        return render_template('dashboard.html', production_labels=production_labels[:10], production_values=production_values[:10],
                              delivery_labels=delivery_labels[:10], delivery_values=delivery_values[:10],
                              delivery_status_labels=delivery_status_labels, delivery_status_values=delivery_status_values)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
        conn.close()
        return redirect(url_for('dashboard'))

@app.route('/factory/upload/export/pdf')
def factory_upload_export_pdf():
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        product = c.fetchone()
        if not product:
            flash('No data to export!', 'error')
            return redirect(url_for('factory_upload'))
        
        filename = "factory_upload.pdf"
        export_data = dict(product)
        export_data['order_number'] = "N/A"
        export_data['quantity'] = export_data.pop('inv_quantity', 0)
        export_to_pdf(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_upload'))

@app.route('/factory/upload/export/excel')
def factory_upload_export_excel():
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        product = c.fetchone()
        if not product:
            flash('No data to export!', 'error')
            return redirect(url_for('factory_upload'))
        
        filename = "factory_upload.xlsx"
        export_data = dict(product)
        export_data['order_number'] = "N/A"
        export_data['quantity'] = export_data.pop('inv_quantity', 0)
        export_to_excel(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_upload'))

@app.route('/factory/products/export/pdf')
def factory_products_export_pdf():
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        product = c.fetchone()
        if not product:
            flash('No data to export!', 'error')
            return redirect(url_for('factory_products'))
        
        filename = "factory_products.pdf"
        export_data = dict(product)
        export_data['order_number'] = "N/A"
        export_data['quantity'] = export_data.pop('inv_quantity', 0)
        export_to_pdf(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_products'))

@app.route('/factory/products/export/excel')
def factory_products_export_excel():
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        product = c.fetchone()
        if not product:
            flash('No data to export!', 'error')
            return redirect(url_for('factory_products'))
        
        filename = "factory_products.xlsx"
        export_data = dict(product)
        export_data['order_number'] = "N/A"
        export_data['quantity'] = export_data.pop('inv_quantity', 0)
        export_to_excel(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('factory_products'))

@app.route('/shop/export/pdf/<tab>')
def shop_export_pdf(tab):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        if tab == 'available':
            c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        elif tab == 'place-order':
            c.execute('SELECT * FROM products LIMIT 1')
        elif tab == 'follow-up':
            c.execute('SELECT o.*, p.product_name, p.product_description FROM orders o LEFT JOIN products p ON o.product_id = p.product_id LIMIT 1')
        elif tab == 'place-new-order':
            c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.product_id IS NULL LIMIT 1')
        elif tab == 'order-status':
            product_id = request.args.get('product_id')
            color = request.args.get('color')
            size = request.args.get('size')
            c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.product_id = ? AND o.color = ? AND o.size = ? LIMIT 1', 
                      (product_id, color, size))
        data = c.fetchone()
        if not data:
            flash('No data to export!', 'error')
            return redirect(url_for('shop_view'))
        
        filename = f"shop_{tab}.pdf"
        export_data = dict(data)
        export_data['order_number'] = export_data.get('order_number', 'N/A')
        export_data['quantity'] = export_data.get('inv_quantity', export_data.get('quantity', 0))
        export_to_pdf(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

@app.route('/shop/export/excel/<tab>')
def shop_export_excel(tab):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        if tab == 'available':
            c.execute('SELECT p.*, i.color, i.size, i.quantity AS inv_quantity FROM products p LEFT JOIN inventory_breakdown i ON p.product_id = i.product_id LIMIT 1')
        elif tab == 'place-order':
            c.execute('SELECT * FROM products LIMIT 1')
        elif tab == 'follow-up':
            c.execute('SELECT o.*, p.product_name, p.product_description FROM orders o LEFT JOIN products p ON o.product_id = p.product_id LIMIT 1')
        elif tab == 'place-new-order':
            c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.product_id IS NULL LIMIT 1')
        elif tab == 'order-status':
            product_id = request.args.get('product_id')
            color = request.args.get('color')
            size = request.args.get('size')
            c.execute('SELECT o.*, p.product_name FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE o.product_id = ? AND o.color = ? AND o.size = ? LIMIT 1', 
                      (product_id, color, size))
        data = c.fetchone()
        if not data:
            flash('No data to export!', 'error')
            return redirect(url_for('shop_view'))
        
        filename = f"shop_{tab}.xlsx"
        export_data = dict(data)
        export_data['order_number'] = export_data.get('order_number', 'N/A')
        export_data['quantity'] = export_data.get('inv_quantity', export_data.get('quantity', 0))
        export_to_excel(export_data, filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

@app.route('/confirm_order/<order_number>/export/pdf')
def confirm_order_export_pdf(order_number):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT o.*, p.product_name, p.product_description FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE order_number = ?', (order_number,))
        order = c.fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('shop_view'))
        
        filename = f"confirm_order_{order_number}.pdf"
        export_to_pdf(dict(order), filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

@app.route('/confirm_order/<order_number>/export/excel')
def confirm_order_export_excel(order_number):
    conn = get_db()
    if not conn:
        return redirect(url_for('index'))
    c = conn.cursor()
    
    try:
        c.execute('SELECT o.*, p.product_name, p.product_description FROM orders o LEFT JOIN products p ON o.product_id = p.product_id WHERE order_number = ?', (order_number,))
        order = c.fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('shop_view'))
        
        filename = f"confirm_order_{order_number}.xlsx"
        export_to_excel(dict(order), filename)
        return send_file(filename, as_attachment=True)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()
    return redirect(url_for('shop_view'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)