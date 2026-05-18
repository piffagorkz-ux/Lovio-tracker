"""
🖤 Couple Tracker Web Server
Flask сервер + Telegram webhook
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Читаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "dummy_token_for_web_server")

DATA_FILE = "couple_data.json"

# ── ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ──────────────────────────────────────────

def load_data():
    """Загружает данные из JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    """Сохраняет данные в JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ck(id1, id2):
    """Создаёт уникальный ключ для пары"""
    return f"{min(int(id1), int(id2))}_{max(int(id1), int(id2))}"

# ── WEB INTERFACE ──────────────────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🖤 Couple Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #764ba2;
            margin-bottom: 10px;
            text-align: center;
            font-size: 2.5em;
        }
        
        .subtitle {
            color: #888;
            text-align: center;
            margin-bottom: 30px;
            font-size: 0.95em;
        }
        
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        input, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 1em;
            font-family: inherit;
            transition: border-color 0.3s;
        }
        
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        
        .info-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .info-section h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .info-section p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 8px;
        }
        
        .divider {
            height: 1px;
            background: #ddd;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖤 Couple Tracker</h1>
        <p class="subtitle">Приложение для пар, которые хотят укреплять отношения</p>
        
        <div id="message" class="message"></div>
        
        <div class="info-section">
            <h3>📱 Как начать?</h3>
            <p><strong>1.</strong> Откройте телеграм и найдите бота</p>
            <p><strong>2.</strong> Нажмите /start</p>
            <p><strong>3.</strong> Привяжите партнёра через меню</p>
            <p><strong>4.</strong> Начните использовать функции!</p>
        </div>
        
        <div class="divider"></div>
        
        <h3 style="color: #667eea; margin-bottom: 20px;">📊 Статистика</h3>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number" id="total-users">0</div>
                <div class="stat-label">Всего пользователей</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="total-couples">0</div>
                <div class="stat-label">Пар зарегистрировано</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="total-diaries">0</div>
                <div class="stat-label">Записей в дневнике</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="total-goals">0</div>
                <div class="stat-label">Целей создано</div>
            </div>
        </div>
        
        <div class="divider"></div>
        
        <h3 style="color: #667eea; margin-bottom: 20px;">💬 Контакт</h3>
        
        <div class="info-section">
            <p>Есть вопрос или проблема? Напишите нам:</p>
            <p style="margin-top: 10px; color: #667eea; font-weight: bold;">@your_support_bot</p>
        </div>
        
        <div class="divider"></div>
        
        <div class="info-section">
            <h3>✨ Функции:</h3>
            <p>✅ 📅 Важные даты и годовщины</p>
            <p>✅ 🎯 Совместные цели</p>
            <p>✅ 🎪 Челленджи для пары</p>
            <p>✅ 📝 Совместный дневник</p>
            <p>✅ 🌳 Виртуальное дерево любви</p>
            <p>✅ 🎁 Вишлист желаний</p>
            <p>✅ 💪 Отслеживание привычек</p>
            <p>✅ 📊 Аналитика отношений</p>
        </div>
    </div>
    
    <script>
        // Загружаем статистику
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                document.getElementById('total-users').textContent = data.users;
                document.getElementById('total-couples').textContent = data.couples;
                document.getElementById('total-diaries').textContent = data.diaries;
                document.getElementById('total-goals').textContent = data.goals;
            })
            .catch(e => console.error('Ошибка загрузки статистики:', e));
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Главная страница веб-интерфейса"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    """API для получения статистики"""
    data = load_data()
    
    users = len([k for k in data.keys() if k != 'couples'])
    couples = len(data.get('couples', {}))
    
    diaries = 0
    goals = 0
    for couple_data in data.get('couples', {}).values():
        diaries += len(couple_data.get('diary', []))
        goals += len(couple_data.get('goals', []))
    
    return jsonify({
        'users': users,
        'couples': couples,
        'diaries': diaries,
        'goals': goals
    })

@app.route('/api/health')
def health():
    """Проверка здоровья сервера"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

# ── ERROR HANDLERS ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ── ЗАПУСК ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
