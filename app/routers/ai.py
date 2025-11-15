from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Generator, List, Dict
import json
import ollama
from ollama import Client
from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/ai", tags=["ai"])
limiter = Limiter(key_func=get_remote_address)

# Настройки Ollama из переменных окружения
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
client = Client(host=OLLAMA_HOST)

def get_burnout_prompt_context(score: int | None) -> str:
    """Генерирует системный промпт на основе уровня выгорания пользователя"""
    if score is None:
        return "Пользователь без оценки стресса. Отвечайте в стандартном режиме."
    
    if 10 <= score <= 25:
        return "Пользователь в зеленой зоне (низкий стресс). Отвечайте профессионально и кратко."
    elif 26 <= score <= 40:
        return "Пользователь в желтой зоне (умеренный стресс). Будьте дружелюбны и поддерживающие."
    elif 41 <= score <= 55:
        return "Пользователь в оранжевой зоне (высокий стресс). Будьте максимально эмпатичны, мягки и поддерживающи. Избегайте критики, давайте только конструктивные советы."
    elif 56 <= score <= 60:
        return "КРИТИЧЕСКИЙ УРОВЕНЬ СТРЕССА! Вы — ментор по психологической поддержке. Будьте очень мягкими, заботливыми и позитивными. Только мотивирующие и поддерживающие сообщения."
    else:
        return "Пользователь без оценки стресса. Отвечайте в стандартном режиме."

def ollama_stream_generator(model: str, messages: List[Dict], burnout_score: int | None) -> Generator[str, None, None]:
    """Генератор потокового ответа от Ollama с адаптивным промптом"""
    try:
        # Добавляем системное сообщение на основе burnout score
        system_context = get_burnout_prompt_context(burnout_score)
        enhanced_messages = [{"role": "system", "content": system_context}] + messages
        
        logger.info(f"Sending request to Ollama model '{model}' with {len(enhanced_messages)} messages")
        stream = client.chat(model=model, messages=enhanced_messages, stream=True)
        
        for chunk in stream:
            content = chunk['message']['content']
            yield f"data: {json.dumps({'content': content})}\n\n"
            
    except Exception as e:
        logger.error(f"Ollama streaming error: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"

@router.post("/chat")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    chat_request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Основной эндпоинт для чата с адаптивным ИИ на основе уровня выгорания.
    Возвращает потоковый ответ в формате Server-Sent Events.
    """
    logger.info(f"User {current_user.email_corporate} is starting chat session")
    
    # Получаем или создаем сессию чата
    if chat_request.session_id:
        session = db.query(models.ChatBotSession).filter(
            models.ChatBotSession.id == chat_request.session_id,
            models.ChatBotSession.user_id == current_user.id
        ).first()
        
        if not session:
            logger.warning(f"Session {chat_request.session_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Continuing existing session {session.id}")
    
    else:
        # Создаем новую сессию с заголовком из первого сообщения
        first_message_content = chat_request.messages[0].content if chat_request.messages else "New Chat"
        session = models.ChatBotSession(
            user_id=current_user.id, 
            title=first_message_content[:50]
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created new session {session.id} for user {current_user.id}")
    
    # Сохраняем сообщение пользователя в базу
    if chat_request.messages:
        user_message_content = chat_request.messages[-1].content
        user_message = models.ChatBotMessage(
            session_id=session.id,
            role="user",
            content=user_message_content
        )
        db.add(user_message)
        db.commit()
    
    # Получаем полную историю сообщений из сессии
    db_messages = db.query(models.ChatBotMessage).filter(
        models.ChatBotMessage.session_id == session.id
    ).order_by(models.ChatBotMessage.created_at).all()
    
    # Форматируем историю для Ollama
    message_history = [
        {"role": msg.role, "content": msg.content} 
        for msg in db_messages
    ]
    
    # Возвращаем потоковый ответ
    return StreamingResponse(
        ollama_stream_generator(chat_request.model, message_history, current_user.burn_out_score),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": str(session.id)
        }
    )

@router.get("/sessions", response_model=List[schemas.ChatSessionBotInDB])
@limiter.limit("30/minute")
def get_user_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все чат-сессии текущего пользователя"""
    sessions = db.query(models.ChatBotSession).filter(
        models.ChatBotSession.user_id == current_user.id
    ).order_by(models.ChatBotSession.created_at.desc()).all()
    
    logger.info(f"User {current_user.id} requested {len(sessions)} chat sessions")
    return sessions

@router.get("/sessions/{session_id}", response_model=schemas.ChatSessionBotInDB)
@limiter.limit("30/minute")
def get_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить конкретную сессию с полной историей сообщений"""
    session = db.query(models.ChatBotSession).filter(
        models.ChatBotSession.id == session_id,
        models.ChatBotSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def delete_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Удалить сессию и все связанные сообщения"""
    session = db.query(models.ChatBotSession).filter(
        models.ChatBotSession.id == session_id,
        models.ChatBotSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    
    logger.info(f"User {current_user.id} deleted session {session_id}")
    return None

# Опциональный HTML интерфейс для тестирования
@router.get("/ui", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def chat_ui(request: Request):
    """HTML интерфейс для тестирования чата (dev mode)"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Assistant с поддержкой выгорания</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            #auth { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            #chat-container { display: none; }
            #chat { background: white; height: 500px; overflow-y: auto; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 10px; }
            .message { margin: 15px 0; padding: 10px 15px; border-radius: 8px; max-width: 80%; }
            .user { background: #e3f2fd; margin-left: auto; text-align: right; }
            .assistant { background: #f5f5f5; }
            #input-area { display: flex; gap: 10px; margin-top: 10px; }
            input, button { padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
            input { flex: 1; }
            button { background: #4CAF50; color: white; cursor: pointer; min-width: 100px; }
            button:hover { background: #45a049; }
            .login-btn { background: #2196F3; }
            .login-btn:hover { background: #0b7dda; }
            .disabled { opacity: 0.5; pointer-events: none; }
            .loading::after { content: '...'; animation: dots 1.5s infinite; }
            @keyframes dots { 0%, 20% { content: '.'; } 40% { content: '..'; } 60%, 100% { content: '...'; } }
            #user-info { position: absolute; top: 20px; right: 20px; background: white; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div id="auth">
            <h2>🔐 Вход в AI Assistant</h2>
            <input type="email" id="email" placeholder="Корпоративный email">
            <input type="password" id="password" placeholder="Пароль">
            <button class="login-btn" onclick="login()">Войти</button>
        </div>
        
        <div id="chat-container">
            <h1>💬 AI Assistant (Адаптивная поддержка)</h1>
            <div id="user-info">Уровень стресса: <span id="burnout-level"></span></div>
            <div id="chat"></div>
            <div id="input-area">
                <input type="text" id="prompt" placeholder="Введите ваш вопрос..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Отправить</button>
            </div>
        </div>

        <script>
            let token = null;
            let currentSessionId = null;
            
            async function login() {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch('/auth/token', {  // ← Убрал /auth префикс
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
                });
                
                if (response.ok) {
                    const data = await response.json();
                    token = data.access_token;
                    document.getElementById('auth').style.display = 'none';
                    document.getElementById('chat-container').style.display = 'block';
                    loadUserInfo();
                } else {
                    alert('Ошибка авторизации');
                }
            }
            
            async function loadUserInfo() {
                const response = await fetch('/users/me', {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const user = await response.json();
                const level = getBurnoutLevel(user.burn_out_score);
                document.getElementById('burnout-level').textContent = level;
            }
            
            function getBurnoutLevel(score) {
                if (!score) return '⚪ Нет данных';
                if (score <= 25) return '🟢 Низкий';
                if (score <= 40) return '🟡 Умеренный';
                if (score <= 55) return '🟠 Высокий';
                return '🔴 Критический';
            }
            
            async function sendMessage() {
                const input = document.getElementById('prompt');
                const prompt = input.value.trim();
                if (!prompt) return;
                
                addMessageToChat('user', prompt);
                input.value = '';
                input.disabled = true;
                
                const messageData = {
                    model: '""" + OLLAMA_MODEL + """',
                    messages: [{role: 'user', content: prompt}],
                    session_id: currentSessionId
                };
                
                const response = await fetch('/ai/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(messageData)
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantMessage = '';
                const assistantDiv = addMessageToChat('assistant', '');
                
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') break;
                            
                            try {
                                const parsed = JSON.parse(data);
                                if (parsed.content) {
                                    assistantMessage += parsed.content;
                                    assistantDiv.textContent = assistantMessage;
                                    document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
                                }
                            } catch (e) {}
                        }
                    }
                }
                
                // Если это первое сообщение в сессии, сохраняем ID
                if (!currentSessionId && response.headers.get('X-Session-ID')) {
                    currentSessionId = parseInt(response.headers.get('X-Session-ID'));
                }
                
                input.disabled = false;
                input.focus();
            }
            
            function addMessageToChat(role, content) {
                const chat = document.getElementById('chat');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                messageDiv.textContent = content;
                chat.appendChild(messageDiv);
                chat.scrollTop = chat.scrollHeight;
                return messageDiv;
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') sendMessage();
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)