from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, abort, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import json
from flask_migrate import Migrate

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

DATA_FOLDER = 'data'
CLIENT_PAGES_FOLDER = '/var/www/tablica/client_pages'
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(CLIENT_PAGES_FOLDER, exist_ok=True)

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal Server Error"}), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.error(f"Unhandled Exception: {e}")
    return jsonify({"error": "Internal Server Error"}), 500

class Manager(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    clients = db.relationship('Client', backref='manager', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'), nullable=False)
    data_file = db.Column(db.String(255), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Manager.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('manager_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        manager = Manager.query.filter_by(username=username).first()
        if manager and manager.check_password(password):
            login_user(manager)
            return redirect(url_for('manager_dashboard'))
        return 'Invalid username or password'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register_manager', methods=['GET', 'POST'])
@login_required
def register_manager():
    if not current_user.is_admin:
        abort(403)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = Manager.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
        else:
            new_manager = Manager(username=username)
            new_manager.set_password(password)
            db.session.add(new_manager)
            db.session.commit()
            flash('New manager registered successfully', 'success')
            return redirect(url_for('manager_dashboard'))
    return render_template('register_manager.html')

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    return render_template('manager_dashboard.html')



@app.route('/manager/clients')
@login_required
def manager_clients():
    clients = Client.query.filter_by(manager_id=current_user.id).all()
    return render_template('manager_clients.html', clients=clients)

@app.route('/manager/client/<int:client_id>')
@login_required
def client_page(client_id):
    client = Client.query.get_or_404(client_id)
    if client.manager_id != current_user.id:
        abort(403)
    return render_template_string(HTML_TEMPLATE, client_id=client_id)

@app.route('/manager/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        client_name = request.form['client_name']
        new_client = Client(name=client_name, manager_id=current_user.id, data_file=os.path.join(DATA_FOLDER, f'client_{client_name}.json'))
        db.session.add(new_client)
        db.session.commit()
        
        with open(new_client.data_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        return redirect(url_for('manager_clients'))
    return render_template('add_client.html')

@app.route('/api/save_data/<int:client_id>', methods=['POST'])
@login_required
def save_data(client_id):
    client = Client.query.get_or_404(client_id)
    if client.manager_id != current_user.id:
        abort(403)
    
    data = request.json
    with open(client.data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"message": "Data saved successfully"}), 200

@app.route('/api/load_data/<int:client_id>', methods=['GET'])
@login_required
def load_data(client_id):
    client = Client.query.get_or_404(client_id)
    if client.manager_id != current_user.id:
        abort(403)
    
    try:
        with open(client.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data), 200
    except FileNotFoundError:
        return jsonify({"message": "No saved data found"}), 404

@app.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    if client.manager_id != current_user.id:
        abort(403)
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully', 'success')
    return redirect(url_for('manager_clients'))

@app.route('/api/update_client_page/<int:client_id>', methods=['POST'])
@login_required
def update_client_page(client_id):
    client = Client.query.get_or_404(client_id)
    if client.manager_id != current_user.id:
        abort(403)
    
    request_data = request.json
    all_data = request_data['data']
    hide_columns = request_data['hideColumns']

    client_html = generate_client_html(all_data, hide_columns, client_id)

    client_page_path = os.path.join(CLIENT_PAGES_FOLDER, f'client_{client_id}.html')
    with open(client_page_path, 'w', encoding='utf-8') as f:
        f.write(client_html)

    return jsonify({"message": "Client page updated successfully", "url": f"/client_{client_id}.html"}), 200

@app.route('/api/save_client_data/<int:client_id>', methods=['POST'])
def save_client_data(client_id):
    client = Client.query.get_or_404(client_id)
    client_data = request.json
    
    with open(client.data_file, 'r+', encoding='utf-8') as f:
        all_data = json.load(f)
        for item in client_data['checkboxStates']:
            all_data['sections'][item['sectionIndex']]['rows'][item['rowIndex']]['selected'] = item['checked']
        f.seek(0)
        json.dump(all_data, f, ensure_ascii=False, indent=2)
        f.truncate()
    
    return jsonify({"message": "Client data saved successfully"}), 200

@app.route('/client_<int:client_id>.html')
def serve_client_page(client_id):
    return send_from_directory(CLIENT_PAGES_FOLDER, f'client_{client_id}.html')



def generate_client_html(all_data, hide_columns, client_id):
    client_html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Страница клиента</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.3.1/jspdf.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/dom-to-image@2.6.0/dist/dom-to-image.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                padding: 20px;
                display: flex;
                justify-content: center; /* Центрирование по горизонтали */
            }}
            .container {{
                max-width: 1400px;
                width: 100%;
                margin: 0 auto; /* Центрирование по горизонтали */
            }}
            .header {{
                text-align: left; /* Заголовок слева */
            }}
            .table-of-contents {{
                text-align: left; /* Оглавление слева */
            }}
            .section {{
                margin-bottom: 30px;
                text-align: left; /* Разделы слева */
            }}
            table {{
                width: 100%; /* Ширина таблицы 100% */
                max-width: 1400px; /* Максимальная ширина таблицы */
                padding:8px;
                border-collapse: collapse;
                margin: 0 auto; /* Центрирование таблицы */
                 /* Фиксированная ширина таблицы */
                 
            }}
            th, td {{
                border: 1px solid #ddd;
                padding:5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            th {{
                background-color: #f2f2f2;
                padding:7px;
                word-wrap: break-word; /* Перенос слов */
            }}
            tr {{
                background-color: #f2f2f2;
                padding:7px;
                word-wrap: break-word; /* Перенос слов */
            }}
            td {{
                padding:6px;
                word-wrap: break-word; /* Перенос слов */
            }}
            td:nth-child(2) {{
                max-width: 175px; /* Увеличенная ширина колонки для наименования */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            td:nth-child(3), td:nth-child(4) {{
                max-width: 70px; /* Уменьшенная ширина колонок для цены и количества */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            td:nth-child(5) {{
                max-width: 75px; /* Уменьшенная ширина колонок для цены и количества */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
             td:nth-child(6), td:nth-child(7) {{
                width: 75px; 
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            td:nth-child(10) {{
                width: 40px; /* Уменьшенная ширина колонки для выбора */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            td:nth-child(8) {{
                max-width: 135px; /* Уменьшенная ширина колонки для выбора */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
           td:nth-child(9) {{
                max-width: 135px; /* Уменьшенная ширина колонки для выбора */
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
                word-wrap: break-word; /* Перенос слов */
            }}
            .small-image {{
                width: 183px; /* Установите ширину изображения на 100% */
                height: auto;
                
            }}
            .overlay {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.7);
                z-index: 999;
                justify-content: center;
                align-items: center;
            }}
            .enlarged-image {{
                max-width: 90%;
                max-height: 90%;
                object-fit: contain;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .table-of-contents {{
              background-color: #f0f0f0;
              padding: 10px;
              border-radius: 5px;
              margin-bottom: 20px;
            }}
            .table-of-contents h2 {{
              margin-top: 0;
            }}
            .table-of-contents ul {{
              list-style-type: none;
              padding-left: 0;
            }}
            .table-of-contents li {{
              margin-bottom: 5px;
            }}
            .table-of-contents a {{
              text-decoration: none;
              color: #333;
            }}
            .table-of-contents a:hover {{
              text-decoration: underline;
            }}
            .asd{{
                width: 72px;
                height: auto;
            }}
            .large-checkbox {{
                transform: scale(2.5); /* Увеличение размера чекбокса */
                margin-left: 25px; /* Добавление отступа вокруг чекбокса */
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img class="asd" src="/static/logo.png" alt="Company Logo">
                <h2>{all_data['headerData']['designProject']}</h2>
                <p>Телефон: {all_data['headerData']['phoneNumber']}</p>
            </div>
            
            <div class="table-of-contents">
              <h2>Оглавление</h2>
              <ul>
    """

    for index, section in enumerate(all_data['sections']):
        client_html += f'<li><a href="#section-{index}">{section["name"]}</a></li>'

    client_html += """
              </ul>
            </div>
    """

    for info in all_data['additionalInfo']:
        client_html += f"<p>{info}</p>"

    for info in all_data['managerInfo']:
        client_html += f"<p>{info}</p>"

    for info in all_data['companyInfo']:
        client_html += f"<p>{info}</p>"

    for line in all_data['descriptionData']:
        client_html += f"<p>{line}</p>"

    for section_index, section in enumerate(all_data['sections']):
        client_html += f'<div class="section" id="section-{section_index}" data-section-index="{section_index}"><h3>{section["name"]}</h3>'
        client_html += '<table><tr><th>Изображение</th><th>Наименование</th><th>Цена</th><th>Количество</th><th>Стоимость</th>'
        if not hide_columns:
            client_html += '<th>Артикул</th><th>Монтаж</th><th>Характеристики</th>'
        client_html += '<th>Комментарий</th><th>Выбрано</th></tr>'

        for row_index, row in enumerate(section['rows']):
            client_html += f'<tr data-row-index="{row_index}">'
            client_html += f'<td style="width:185px;"><img src="{row["image"]}" class="small-image" onclick="expandImage(this)"></td>'
            client_html += f'<td>{row["name"]}</td><td>{row["price"]}</td><td>{row["quantity"]}</td><td class="row-total">0.00</td>'
            if not hide_columns:
                client_html += f'<td><a href="{row["articleUrl"]}" target="_blank">{row["articleText"]}</a></td>'
                client_html += f'<td><a href="{row["characteristics"]}" target="_blank">{row["characteristicsText"]}</a></td>'  # Изменено на гиперссылку
                client_html += f'<td>{row["installation"]}</td>'
            client_html += f'<td>{row["comment"]}</td>'
            client_html += f'<td><input type="checkbox" class="large-checkbox" {"checked" if row["selected"] else ""} onchange="updateTotals()"></td>'
            client_html += '</tr>'

        client_html += '<tfoot><tr><td colspan="4">Итого:</td><td id="section-total">0.00</td></tr></tfoot>'
        client_html += '</table></div>'

    client_html += '<div class="total"><h3>Общая стоимость: <span id="grand-total">0.00</span></h3></div>'
    client_html += '<button id="save-button" onclick="saveClientData()">Сохранить</button>'
    client_html += f'<button id="save-pdf-button" onclick="saveAsPdf()">Скачать PDF</button>'
    client_html += '<div class="overlay" id="overlay"><img id="enlargedImage" class="enlarged-image" src="" alt="Enlarged image"></div>'

    client_html += f"""
    <script>
     function updateTotals() {{
        let grandTotal = 0;
        document.querySelectorAll('.section').forEach(section => {{
            let sectionTotal = 0;
            section.querySelectorAll('tbody tr').forEach(row => {{
                const checkbox = row.querySelector('input[type="checkbox"]');
                if (checkbox && checkbox.checked) {{
                    const price = parseFloat(row.cells[2].textContent.replace(',', '.')) || 0;
                    const quantity = parseFloat(row.cells[3].textContent.replace(',', '.')) || 0;
                    const rowTotal = price * quantity;
                    row.cells[4].textContent = rowTotal.toFixed(2).replace('.', ',');
                    sectionTotal += rowTotal;
                }} else {{
                    row.cells[4].textContent = 'Стоимость';
                }}
            }});
            const sectionTotalElement = section.querySelector('#section-total');
            if (sectionTotalElement) {{
                sectionTotalElement.textContent = sectionTotal.toFixed(2).replace('.', ',');
            }}
            grandTotal += sectionTotal;
        }});
        const grandTotalElement = document.querySelector('#grand-total');
        if (grandTotalElement) {{
            grandTotalElement.textContent = grandTotal.toFixed(2).replace('.', ',');
        }}
    }}

    function expandImage(img) {{
        const overlay = document.getElementById('overlay');
        const enlargedImg = document.getElementById('enlargedImage');
        enlargedImg.src = img.src;
        overlay.style.display = 'flex';
    }}

    document.getElementById('overlay').addEventListener('click', function() {{
        this.style.display = 'none';
    }});

    function saveClientData() {{
        const data = {{
            checkboxStates: Array.from(document.querySelectorAll('input[type="checkbox"]')).map(checkbox => {{
                return {{
                    sectionIndex: parseInt(checkbox.closest('.section').dataset.sectionIndex),
                    rowIndex: parseInt(checkbox.closest('tr').dataset.rowIndex),
                    checked: checkbox.checked
                }};
            }})
        }};

        fetch('/api/save_client_data/{client_id}', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify(data)
        }})
        .then(response => response.json())
        .then(data => {{
            alert('Данные успешно сохранены');
        }})
        .catch((error) => {{
            console.error('Error:', error);
            alert('Произошла ошибка при сохранении данных');
        }});
    }}

    function saveAsPdf() {{

    document.getElementById('save-button').style.display = 'none';
    document.getElementById('save-pdf-button').style.display = 'none';

    const container = document.querySelector('.container');

    // Создаем изображение из контейнера с помощью html2canvas
    html2canvas(container, {{
        scale: 2,
        useCORS: true,
        logging: false,
        proxy: 'html2canvasproxy.php',
        allowTaint: true,
        removeContainer: true
    }}).then(canvas => {{
        const width = canvas.width;
        let height = canvas.height;

        // Устанавливаем минимальное значение высоты
        if (height < 3510) {{
            height = 4667; // Устанавливаем высоту в 4667, если она меньше
        }}
        else {{
            height = height + 3510; // Устанавливаем высоту в 4667, если она меньше
        }}
        

        // Высота страницы в пикселях
        const pageSize = 3507; 
        const numPages = Math.ceil(height / pageSize);

        // Создаем новый документ PDF
        const doc = new jspdf.jsPDF('p', 'mm', 'a4', true, 300);

        // Проходим по каждой странице
        for (let i = 0; i < numPages; i++) {{
            const yPos = i * pageSize; // Позиция Y для текущей страницы
            const pageHeight = Math.min(pageSize, height - yPos); // Высота текущей страницы

            // Создаем новый canvas для текущей страницы
            const pageCanvas = document.createElement('canvas');
            pageCanvas.width = width - 6; // Учитываем отступы
            pageCanvas.height = pageHeight - 6; // Учитываем отступы

            // Рисуем соответствующую часть оригинального canvas на page canvas
            const pageCtx = pageCanvas.getContext('2d');
            pageCtx.drawImage(canvas, 3, yPos + 3, width - 6, pageHeight - 6, 0, 0, pageCanvas.width, pageCanvas.height);

            // Добавляем page canvas в документ PDF
            const pageData = pageCanvas.toDataURL('image/png');
            doc.addImage(pageData, 'PNG', 0, 0, doc.internal.pageSize.width, doc.internal.pageSize.height);

            // Если это не последняя страница, добавляем новую страницу
            if (i < numPages - 1) {{
                doc.addPage(); // Добавление новой страницы
            }}
        }}

        doc.save('client_page.pdf'); // Сохранение PDF

        document.getElementById('save-button').style.display = 'inline-block';
        document.getElementById('save-pdf-button').style.display = 'inline-block';

    }});
}}

    updateTotals();
    </script>
    </div>
    </body>
    </html>
    """

    return client_html

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editable Table with Image Upload and Preview</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.3.1/jspdf.min.js"></script>
    <style>
    :root {
        --primary-color: #4567b7;
        --secondary-color: #f7f7f7;
        --font-size: 12px;
        --font-family: 'Open Sans', sans-serif;
    }

    body {
        font-family: var(--font-family);
        font-size: var(--font-size);
    }

    .frame {
        background-color: #f9f9f9;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
        page-break-after: always;
        page-break-inside: avoid;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .header .company-name {
        font-size: 18px;
        font-weight: bold;
        color: var(--primary-color);
    }

    .header .design-project {
        font-size: 14px;
        color: #666;
    }

    .header .phone-number {
        font-size: 12px;
        color: #666;
    }

    .additional-info, .manager-info, .company-info {
        margin-bottom: 20px;
    }

    .additional-info p, .manager-info p, .company-info p {
        margin: 5px 0;
    }

    .description ol, .description ul {
        margin-left: 20px;
    }

    .description li {
        margin-bottom: 5px;
    }

    .section {
        margin-bottom: 20px;
    }

    table {
        border-collapse: collapse;
        width: 100%;
        max-width: 1920px; /* Максимальная ширина таблицы */
        margin: 0 auto; /* Центрирование таблицы */
         /* Фиксированная ширина таблицы */
    }

    th, td {
        border: 1px solid #ddd;
        padding: 5px;
        text-align: left;
        word-wrap: break-word; /* Перенос слов */
    }

    th {
        background-color: var(--secondary-color);
    }

    table td:nth-child(1) {
    max-width: 155px;
    
}

table td:nth-child(2) {
    max-width: 90px;
}

table td:nth-child(3), table td:nth-child(4) {
    max-width: 45px;
    max-width: 45px;
}
table td:nth-child(4) {
    max-width: 55px;
}
table td:nth-child(5) {
    max-width: 70px;
}
table td:nth-child(6), table td:nth-child(7) {
    max-width: 70px;
}

table td:nth-child(8) {
    max-width: 40px;
    
}
table td:nth-child(9) {
    max-width: 40px;
    
}
table td:nth-child(10) {
    width: 15px;
    
}

    .small-image {
        max-width: 155px;
        height: auto;
        display: block;
        margin: 0 auto;
        aspect-ratio: 16/9;
        object-fit: cover;
        border-radius: 5px;
        cursor: pointer;
    }

    button {
        background-color: var(--primary-color);
        color: #fff;
        border: none;
        padding: 5px 10px;
        font-size: 12px;
        cursor: pointer;
        border-radius: 5px;
        margin-right: 5px;
    }

    button:hover {
        opacity: 0.8;
    }

    .total-price-container {
        margin-top: 20px;
        text-align: right;
    }

    .total-price {
        font-size: 16px;
        font-weight: bold;
    }

    .image-preview {
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .image-preview.expanded {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        max-width: 90%;
        max-height: 90%;
        z-index: 1000;
    }

    .overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.7);
        z-index: 999;
        justify-content: center;
        align-items: center;
    }

    .enlarged-image {
        max-width: 90%;
        max-height: 90%;
    
    }

    #client-page-url {
        margin-top: 10px;
        padding: 10px;
        background-color: #e0e0e0;
        border-radius: 5px;
    }

    .move-buttons {
        display: flex;
        flex-direction: column;
    }

    .move-buttons button {
        margin: 2px 0;
    }

    .table-of-contents {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }

    .table-of-contents h2 {
        margin-top: 0;
    }

    .table-of-contents ul {
        list-style-type: none;
        padding-left: 0;
    }

    .table-of-contents li {
        margin-bottom: 5px;
    }

    .table-of-contents a {
        text-decoration: none;
        color: #333;
    }

    .table-of-contents a:hover {
        text-decoration: underline;
    }

    .asd {
        width: 72px;
        height: auto;
    }
    .large-checkbox {
        transform: scale(1.5); /* Увеличение размера чекбокса */
        margin: 10px; /* Добавление отступа вокруг чекбокса */
    }
</style>
</style>
</head>
<body>
    <div class="frame">
        <div class="header">
            <img class="asd" src="/static/logo.png" alt="Company Logo" >
            <div class="design-project" contenteditable="true">Дизайн-проект</div>
            <div class="phone-number" contenteditable="true">Телефон</div>
        </div>
        <div class="additional-info">
            <p contenteditable="true">Дополнительная информация 1</p>
        </div>
        <div class="table-of-contents">
            <h2>Оглавление</h2>
            <ul id="toc-list"></ul>
        </div>
        <div id="sections"></div>
        <button onclick="addSection()">Добавить раздел</button>
        <div class="total-price-container">
            <span class="total-price">Итого: 0.00</span>
        </div>
        <button onclick="saveData()">Сохранить</button>
        <button onclick="loadSavedData()">Загрузить</button>
        <button onclick="createClientPage()">Создать страницу клиента</button>
        
        <div>
            <input type="checkbox" id="hide-columns-checkbox">
            <label for="hide-columns-checkbox">Скрыть столбцы 6-8 на странице клиента</label>
        </div>
        <div id="client-page-url"></div>
    </div>
    <div class="overlay" id="imageOverlay">
        <img id="enlargedImage" class="enlarged-image" src="" alt="Enlarged image">
    </div>

    <script>
        let sectionCounter = 0;
        const clientId = {{ client_id }};

        function updateTableOfContents() {
            const tocList = document.getElementById('toc-list');
            tocList.innerHTML = '';
            document.querySelectorAll('.section h3').forEach((heading, index) => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = `#section-${index}`;
                a.textContent = heading.textContent;
                li.appendChild(a);
                tocList.appendChild(li);
                
                heading.parentElement.id = `section-${index}`;
            });
        }

        function addSection(name = '', rows = []) {
    sectionCounter++;
    const sectionsContainer = document.getElementById('sections');
    const newSection = document.createElement('div');
    newSection.className = 'section';
    newSection.innerHTML = `
        <h3 contenteditable="true">${name || 'Раздел ' + sectionCounter}</h3>
        <table>
            <thead>
                <tr>
                    <th>Изображение</th>
                    <th>Наименование</th>
                    <th>Цена</th>
                    <th>Количество</th>
                    <th>Стоимость</th>
                    <th>Артикул</th>
                    <th>Монтаж</th>
                    <th>Характеристики</th>
                    <th>Комментарий</th>
                    <th>Выбрать</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody></tbody>
            <tfoot>
                <tr>
                    <td colspan="4">Итого:</td>
                    <td id="section-total">0.00</td>
                    <td colspan="6"></td>
                </tr>
            </tfoot>
        </table>
        <button onclick="addRow(this.parentElement)">Добавить строку</button>
        <button onclick="deleteSection(this.parentElement)">Удалить раздел</button>
        <div class="move-buttons">
            <button onclick="moveSection(this.parentElement.parentElement, 'up')">↑</button>
            <button onclick="moveSection(this.parentElement.parentElement, 'down')">↓</button>
        </div>
    `;
    sectionsContainer.appendChild(newSection);

    if (rows.length > 0) {
        rows.forEach(row => addRow(newSection, row));
    } else {
        addRow(newSection);
    }
    updateTableOfContents();
}

       function addRow(section, data = {}) {
    const tbody = section.querySelector('tbody');
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td><img src="${data.image || ''}" class="small-image" onclick="expandImage(this)"><input type="file" accept="image/*" onchange="handleImageUpload(this)" style="width: 107px; height: 25px; font-size: 12px; margin-top: 5px;margin-left: 55px;"></td>
        <td contenteditable="true">${data.name || ''}</td>
        <td contenteditable="true">${data.price || ''}</td>
        <td contenteditable="true">${data.quantity || ''}</td>
        <td>0.00</td>
        <td>
            <a href="${data.articleUrl || '#'}" target="_blank" contenteditable="true">${data.articleText || 'Артикул'}</a>
            <input type="text" placeholder="URL" value="${data.articleUrl || ''}" onchange="updateArticleLink(this)" style="width:45px;">
        </td>
        <td>
            <a href="${data.characteristics || '#'}" target="_blank" contenteditable="true">${data.characteristicsText || 'Монтаж'}</a>
            <input type="text" placeholder="URL" value="${data.characteristics || ''}" onchange="updarticleLink(this)" style="width:45px;">
        </td>
        <td contenteditable="true">${data.installation || ''}</td>
        <td contenteditable="true">${data.comment || ''}</td>
        <td><input type="checkbox" onchange="updateTotalPrice()" ${data.selected ? 'checked' : ''}></td>
        <td>
            <button onclick="deleteRow(this.parentElement.parentElement)">Удалить</button>
            <div class="move-buttons">
                <button onclick="moveRow(this.parentElement.parentElement.parentElement, 'up')">↑</button>
                <button onclick="moveRow(this.parentElement.parentElement.parentElement, 'down')">↓</button>
            </div>
        </td>
    `;
    tbody.appendChild(newRow);

    // Добавляем обработчики событий для изменения значений в третьем и четвертом столбцах
    newRow.cells[2].addEventListener('input', updateTotalPrice);
    newRow.cells[3].addEventListener('input', updateTotalPrice);

    updateTotalPrice();
}

      
        function updarticleLink(input) {
            const link = input.previousElementSibling;
            link.href = input.value;
        }
        function updateArticleLink(input) {
            const link = input.previousElementSibling;
            link.href = input.value;
        }

        function deleteSection(section) {
            section.remove();
            updateTotalPrice();
            updateTableOfContents();
        }

        function deleteRow(row) {
            row.remove();
            updateTotalPrice();
        }

        function moveSection(section, direction) {
            const container = section.parentElement;
            if (direction === 'up' && section.previousElementSibling) {
                container.insertBefore(section, section.previousElementSibling);
            } else if (direction === 'down' && section.nextElementSibling) {
                container.insertBefore(section.nextElementSibling, section);
            }
            updateTableOfContents();
        }

        function moveRow(row, direction) {
            const tbody = row.parentElement;
            if (direction === 'up' && row.previousElementSibling) {
                tbody.insertBefore(row, row.previousElementSibling);
            } else if (direction === 'down' && row.nextElementSibling) {
                tbody.insertBefore(row.nextElementSibling, row);
            }
        }

        function handleImageUpload(input) {
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = input.previousElementSibling;
            img.src = e.target.result;
        }
        reader.readAsDataURL(file);
    }
}

// Добавляем этот код для скрытия кнопки "Выберите файл"
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.style.display = 'none';
});

// Добавляем этот код для активации кнопки "Выберите файл" по нажатию на изображение
document.querySelectorAll('.small-image').forEach(img => {
    img.addEventListener('click', () => {
        const input = img.nextElementSibling;
        input.click();
    });
});

        function expandImage(img) {
            const overlay = document.getElementById('imageOverlay');
            const enlargedImg = document.getElementById('enlargedImage');
            enlargedImg.src = img.src;
            overlay.style.display = 'flex';
        }

        document.getElementById('imageOverlay').addEventListener('click', function() {
            this.style.display = 'none';
        });

        function updateTotalPrice() {
    let grandTotal = 0;
    document.querySelectorAll('.section').forEach(section => {
        let sectionTotal = 0;
        section.querySelectorAll('tbody tr').forEach(row => {
            const checkbox = row.querySelector('input[type="checkbox"]');
            if (checkbox && checkbox.checked) {
                const price = parseFloat(row.cells[2].textContent.replace(',', '.')) || 0;
                const quantity = parseFloat(row.cells[3].textContent.replace(',', '.')) || 0;
                const rowTotal = price * quantity;
                row.cells[4].textContent = rowTotal.toFixed(2).replace('.', ',');
                sectionTotal += rowTotal;
            } else {
                row.cells[4].textContent = '0.00';
            }
        });
        section.querySelector('#section-total').textContent = sectionTotal.toFixed(2).replace('.', ',');
        grandTotal += sectionTotal;
    });
    document.querySelector('.total-price').textContent = `Итого: ${grandTotal.toFixed(2).replace('.', ',')}`;
}

        function getAllData() {
            const data = {
                headerData: {
                    
                    designProject: document.querySelector('.design-project').textContent,
                    phoneNumber: document.querySelector('.phone-number').textContent
                },
                additionalInfo: Array.from(document.querySelectorAll('.additional-info p')).map(p => p.textContent),
                managerInfo: Array.from(document.querySelectorAll('.manager-info p')).map(p => p.textContent),
                companyInfo: Array.from(document.querySelectorAll('.company-info p')).map(p => p.textContent),
                descriptionData: Array.from(document.querySelectorAll('.description-line')).map(p => p.textContent),
                sections: Array.from(document.querySelectorAll('.section')).map(section => ({
                    name: section.querySelector('h3').textContent,
                    rows: Array.from(section.querySelectorAll('tbody tr')).map(row => ({
                        image: row.querySelector('img').src,
                        name: row.cells[1].textContent,
                        price: row.cells[2].textContent,
                        quantity: row.cells[3].textContent,
                        articleText: row.cells[5].querySelector('a').textContent,
                        articleUrl: row.cells[5].querySelector('a').href,
                        characteristicsText: row.cells[6].querySelector('a').textContent,
                        characteristics: row.cells[6].querySelector('a').href,
                        installation: row.cells[7].textContent,
                        comment: row.cells[8].textContent,
                        selected: row.querySelector('input[type="checkbox"]').checked
                    }))
                }))
            };
            return data;
        }

        function handleImageUpload(input) {
            const file = input.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = input.previousElementSibling;
                    img.src = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        }
        function saveData() {
            const data = getAllData();
            fetch(`/api/save_data/${clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                alert('Данные успешно сохранены');
            })
            .catch((error) => {
                console.error('Error:', error);
                alert('Произошла ошибка при сохранении данных');
            });
        }

        function loadSavedData() {
            fetch(`/api/load_data/${clientId}`)
                .then(response => response.json())
                .then(data => {
                    document.querySelector('.design-project').textContent = data.headerData.designProject;
                    document.querySelector('.phone-number').textContent = data.headerData.phoneNumber;

                    document.querySelectorAll('.additional-info p').forEach((p, index) => {
                        p.textContent = data.additionalInfo[index] || '';
                    });

                    document.querySelectorAll('.manager-info p').forEach((p, index) => {
                        p.textContent = data.managerInfo[index] || '';
                    });

                    document.querySelectorAll('.company-info p').forEach((p, index) => {
                        p.textContent = data.companyInfo[index] || '';
                    });

                    document.querySelectorAll('.description-line').forEach((p, index) => {
                        p.textContent = data.descriptionData[index] || '';
                    });

                    document.getElementById('sections').innerHTML = '';
                    data.sections.forEach(section => {
                        addSection(section.name, section.rows);
                    });

                    // Обновляем состояние чекбоксов
                    data.sections.forEach((section, sectionIndex) => {
                        section.rows.forEach((row, rowIndex) => {
                            const checkbox = document.querySelector(`#sections .section:nth-child(${sectionIndex + 1}) tbody tr:nth-child(${rowIndex + 1}) input[type="checkbox"]`);
                            if (checkbox) {
                                checkbox.checked = row.selected;
                            }
                        });
                    });

                    updateTotalPrice();
                    updateTableOfContents();
                })
                .catch((error) => {
                    console.error('Error:', error);
                    alert('Произошла ошибка при загрузке данных');
                });
        }

        function createClientPage() {
            const data = getAllData();
            const hideColumns = document.getElementById('hide-columns-checkbox').checked;
            fetch(`/api/update_client_page/${clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({data, hideColumns})
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('client-page-url').innerHTML = `<a href="${data.url}" target="_blank">Страница клиента</a>`;
                saveData(); // Сохраняем данные после обновления страницы клиента
            })
            .catch((error) => {
                console.error('Error:', error);
                alert('Произошла ошибка при создании страницы клиента');
            });
        }

       
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)


#sudo systemctl daemon-reload
#sudo systemctl restart gunicorn
#sudo systemctl restart nginx