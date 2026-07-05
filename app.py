import sys
from typing import Any
import importlib.util
import pkgutil

# Patch pkgutil.get_loader and find_loader for Python 3.14+ compatibility
if not hasattr(pkgutil, "get_loader"):
    def _get_loader(name):
        try:
            spec = importlib.util.find_spec(name)
            return spec.loader if spec else None
        except Exception:
            return None
    setattr(pkgutil, "get_loader", _get_loader)

if not hasattr(pkgutil, "find_loader"):
    def _find_loader(name, path=None):
        try:
            spec = importlib.util.find_spec(name, path)
            return spec.loader if spec else None
        except Exception:
            return None
    setattr(pkgutil, "find_loader", _find_loader)

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import psycopg2
import sqlite3
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Image as RLImage, Table, TableStyle, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import io
import logging
import os
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import json
import time
import urllib.request

app = Flask(__name__, static_folder='static')
CORS(app)

# Configure file upload directory
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins='*')

# Database connection adapter for SQLite / PostgreSQL
class DBConnection:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.use_sqlite = not self.db_url
        self.conn: Any = None

    def __enter__(self):
        if self.use_sqlite:
            self.conn = sqlite3.connect('recipes.db')
        else:
            self.conn = psycopg2.connect(self.db_url, sslmode='require')
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def execute(self, query, params=None):
        if self.use_sqlite:
            query = query.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            query = query.replace('%s', '?')
        if params is not None:
            return self.cursor.execute(query, params)
        else:
            return self.cursor.execute(query)

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    @property
    def rowcount(self):
        return self.cursor.rowcount

def init_db():
    with DBConnection() as db:
        # Create table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL,
                remarks TEXT,
                image TEXT
            )
        ''')
        # Insert sample data (skip if already exists)
        db.execute("SELECT COUNT(*) FROM recipes")
        row = db.fetchone()
        count = row[0] if row else 0
        if count == 0:
            db.execute('''
                INSERT INTO recipes (name, type, ingredients, instructions, remarks, image)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('Test Main Meal', 'main_meal', 'Ingredient1,Ingredient2', "Step 1\nStep 2", 'Sample remark', 'https://via.placeholder.com/150'))
            db.execute('''
                INSERT INTO recipes (name, type, ingredients, instructions, remarks, image)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('Test Baking', 'baking', 'Flour,Sugar', "Mix\nBake", 'Baking note', 'https://via.placeholder.com/150'))
            db.execute('''
                INSERT INTO recipes (name, type, ingredients, instructions, remarks, image)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('Test Desert', 'desert', 'Cream,Fruit', "Chill\nServe", 'Sweet note', 'https://via.placeholder.com/150'))

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/main_meals')
def main_meals():
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes WHERE type = 'main_meal'")
        recipes = [{'id': r[0], 'name': r[1], 'type': r[2], 'ingredients': r[3].split(','), 'instructions': r[4], 'remarks': r[5], 'image': r[6]} for r in db.fetchall()]
        app.logger.debug(f"Main meals fetched: {recipes}")
    return render_template('main_meals.html', recipes=recipes)

@app.route('/baking')
def baking():
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes WHERE type = 'baking'")
        recipes = [{'id': r[0], 'name': r[1], 'type': r[2], 'ingredients': r[3].split(','), 'instructions': r[4], 'remarks': r[5], 'image': r[6]} for r in db.fetchall()]
        app.logger.debug(f"Baking recipes fetched: {recipes}")
    return render_template('baking.html', recipes=recipes)

@app.route('/desert')
def desert():
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes WHERE type = 'desert'")
        recipes = [{'id': r[0], 'name': r[1], 'type': r[2], 'ingredients': r[3].split(','), 'instructions': r[4], 'remarks': r[5], 'image': r[6]} for r in db.fetchall()]
        app.logger.debug(f"Desert recipes fetched: {recipes}")
    return render_template('desert.html', recipes=recipes)

@app.route('/add_recipe')
def add_recipe_page():
    return render_template('add_recipe.html')

@app.route('/manage')
def manage_recipes():
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes ORDER BY id DESC")
        recipes = [{'id': r[0], 'name': r[1], 'type': r[2], 'ingredients': r[3].split(','), 'instructions': r[4], 'remarks': r[5], 'image': r[6]} for r in db.fetchall()]
    return render_template('manage.html', recipes=recipes)

@app.route('/edit_recipe/<int:id>')
def edit_recipe(id):
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes WHERE id = %s", (id,))
        recipe = db.fetchone()
        if recipe:
            recipe_data = {
                'id': recipe[0],
                'name': recipe[1],
                'type': recipe[2],
                'ingredients': recipe[3].split(','),
                'instructions': recipe[4],
                'remarks': recipe[5] or '',
                'image': recipe[6] or ''
            }
            app.logger.debug(f"Editing recipe: {recipe_data}")
            return render_template('edit_recipe.html', recipe=recipe_data)
        return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404

@app.route('/edit_recipe/<int:id>', methods=['POST'])
def update_recipe(id):
    try:
        name = request.form['name']
        type = request.form['type']
        ingredients_list = json.loads(request.form['ingredients'])
        ingredients = ','.join(ingredients_list)
        instructions = request.form['instructions']
        remarks = request.form.get('remarks', '')
        image_link = request.form.get('imageLink', '')

        # Handle image file upload or link fallback
        image = image_link or 'https://via.placeholder.com/150'
        if 'imageFile' in request.files:
            file = request.files['imageFile']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image = f"/static/uploads/{filename}"

        # If no new file or link is provided, preserve existing image
        if not image_link and ('imageFile' not in request.files or not request.files['imageFile'].filename):
            with DBConnection() as db:
                db.execute("SELECT image FROM recipes WHERE id = %s", (id,))
                res = db.fetchone()
                if res and res[0]:
                    image = res[0]

        with DBConnection() as db:
            db.execute('''
                UPDATE recipes
                SET name = %s, type = %s, ingredients = %s, instructions = %s, remarks = %s, image = %s
                WHERE id = %s
            ''', (name, type, ingredients, instructions, remarks, image, id))
            if db.rowcount > 0:
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404
    except Exception as e:
        app.logger.error(f"Error updating recipe: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/add_recipe', methods=['POST'])
def add_recipe():
    try:
        name = request.form['name']
        type = request.form['type']
        ingredients_list = json.loads(request.form['ingredients'])
        ingredients = ','.join(ingredients_list)
        instructions = request.form['instructions']
        remarks = request.form.get('remarks', '')
        image_link = request.form.get('imageLink', '')

        image = image_link or 'https://via.placeholder.com/150'
        if 'imageFile' in request.files:
            file = request.files['imageFile']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image = f"/static/uploads/{filename}"

        with DBConnection() as db:
            db.execute('''
                INSERT INTO recipes (name, type, ingredients, instructions, remarks, image)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (name, type, ingredients, instructions, remarks, image))
        app.logger.debug(f"Added recipe: {name}")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        app.logger.error(f"Error adding recipe: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete_recipe/<int:id>', methods=['DELETE'])
def delete_recipe(id):
    try:
        with DBConnection() as db:
            db.execute('DELETE FROM recipes WHERE id = %s', (id,))
            if db.rowcount > 0:
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404
    except Exception as e:
        app.logger.error(f"Error deleting recipe: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_recipe_image_flowable(image_src, max_width=200, max_height=150):
    try:
        if not image_src:
            return None
        if image_src.startswith('http://') or image_src.startswith('https://'):
            req = urllib.request.Request(image_src, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = io.BytesIO(response.read())
                return RLImage(img_data, width=max_width, height=max_height)
        else:
            local_path = image_src.lstrip('/')
            if os.path.exists(local_path):
                return RLImage(local_path, width=max_width, height=max_height)
    except Exception as e:
        logger.error(f"Error loading image for PDF: {str(e)}")
    return None

@app.route('/download_recipe/<int:id>/<format>')
def download_recipe(id, format):
    with DBConnection() as db:
        db.execute("SELECT * FROM recipes WHERE id = %s", (id,))
        recipe = db.fetchone()
        if not recipe:
            return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404
        recipe_data = {
            'name': recipe[1],
            'type': recipe[2],
            'ingredients': recipe[3].split(','),
            'instructions': recipe[4].split('\n'),
            'remarks': recipe[5],
            'image': recipe[6]
        }
    if format == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements: list = []
        
        # Embed image if available
        if recipe_data['image']:
            img_flowable = get_recipe_image_flowable(recipe_data['image'])
            if img_flowable:
                elements.append(img_flowable)
                elements.append(Spacer(1, 12))

        elements.append(Paragraph(recipe_data['name'], styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Type: {recipe_data['type'].replace('_', ' ').title()}", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Ingredients:", styles['Heading2']))
        ing_items: list = [ListItem(Paragraph(ing.strip(), styles['Normal'])) for ing in recipe_data['ingredients']]
        ingredients_list = ListFlowable(ing_items, bulletType='1')
        elements.append(ingredients_list)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Instructions:", styles['Heading2']))
        ins_items: list = [ListItem(Paragraph(ins.strip(), styles['Normal'])) for ins in recipe_data['instructions'] if ins.strip()]
        instructions_list = ListFlowable(ins_items, bulletType='1')
        elements.append(instructions_list)
        elements.append(Spacer(1, 12))
        if recipe_data['remarks']:
            elements.append(Paragraph("Remarks:", styles['Heading2']))
            elements.append(Paragraph(recipe_data['remarks'], styles['Normal']))
        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"{recipe_data['name']}.pdf", mimetype='application/pdf')
    return jsonify({'status': 'error', 'message': 'Invalid format'}), 400
# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5100))
    logger.debug(f"Running on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)