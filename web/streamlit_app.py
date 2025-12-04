import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Support Tickets", layout="wide")
st.title("Тех.поддержка")

TICKETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tickets/tickets.json')

tickets_dir = os.path.dirname(TICKETS_FILE)
if not os.path.exists(tickets_dir):
    os.makedirs(tickets_dir)

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    
    try:
        with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
            tickets = json.load(f)
            for ticket in tickets:
                if not isinstance(ticket, dict):
                    return []
                required_fields = ['id', 'name', 'text', 'category', 'status', 'timestamp']
                for field in required_fields:
                    if field not in ticket:
                        ticket[field] = ''
            return tickets
    except (json.JSONDecodeError, UnicodeDecodeError):
        with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []

def save_tickets(tickets):
    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)

if 'tickets' not in st.session_state:
    st.session_state.tickets = load_tickets()

if 'selected_ticket' not in st.session_state:
    st.session_state.selected_ticket = None

page = st.sidebar.selectbox("Выберите страницу", 
                            ["Отправить обращение", "Работа с обращениями"])

if page == "Отправить обращение":
    st.header("Отправка обращения")
    
    with st.form("ticket_form"):
        name = st.text_input("Ваше имя:", placeholder="Иван Иванов")
        email = st.text_input("Email (не обязательно):", placeholder="example@domain.com")
        text = st.text_area("Опишите проблему:", height=150, placeholder="Подробно опишите вашу проблему...")
        submitted = st.form_submit_button("Отправить")
    
    if submitted:
        if not text.strip():
            st.error("Введите текст обращения")
        elif email.strip() and "@" not in email:
            st.error("Некорректный email")
        else:
            try:
                response = requests.post("http://localhost:8000/predict", 
                                       json={"text": text}, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    new_ticket = {
                        "id": len(st.session_state.tickets) + 1,
                        "name": name.strip() or "Аноним",
                        "email": email.strip() or "",
                        "text": text.strip(),
                        "category": result['category'],
                        "confidence": result.get('confidence', 0.0),
                        "status": "Новый",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "admin_response": ""
                    }
                    
                    st.session_state.tickets.append(new_ticket)
                    save_tickets(st.session_state.tickets)
                    
                    st.success("Обращение отправлено!")
                    st.info(f"**Категория:** {result['category']}")
                    
                    if 'confidence' in result:
                        st.info(f"**Уверенность:** {result['confidence']:.1%}")
                    
                    if "спам" in result['category'].lower():
                        st.warning("Помечено как СПАМ")
                        
            except:
                st.error("API сервер не запущен")

else:
    st.header("Обращения")
    
    if not st.session_state.tickets:
        st.info("Нет обращений")
    else:
        new_count = sum(1 for t in st.session_state.tickets if t.get('status') == "Новый")
        if new_count > 0:
            st.warning(f"{new_count} новых обращений!")
        
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Статус", ["Все", "Новый", "В работе", "Закрыт"], key="status_filter")
        with col2:
            categories = ["Все"] + sorted(set(t.get('category', '') for t in st.session_state.tickets if t.get('category')))
            category_filter = st.selectbox("Категория", categories, key="category_filter")
        
        filtered_tickets = st.session_state.tickets
        if status_filter != "Все":
            filtered_tickets = [t for t in filtered_tickets if t.get('status') == status_filter]
        if category_filter != "Все":
            filtered_tickets = [t for t in filtered_tickets if t.get('category') == category_filter]
        
        if filtered_tickets:
            df_data = []
            for t in filtered_tickets:
                df_data.append({
                    "ID": t.get('id', ''),
                    "Имя": t.get('name', ''),
                    "Категория": t.get('category', ''),
                    "Статус": t.get('status', ''),
                    "Ответ": t.get('admin_response', '')[:30] + "..." if t.get('admin_response') and len(t.get('admin_response', '')) > 30 else (t.get('admin_response', '') if t.get('admin_response') else "—")
                })
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("Детали обращения")
            
            ticket_options = []
            for t in filtered_tickets:
                option_text = f"ID: {t['id']} - {t.get('name', '')} ({t.get('category', '')}) - {t.get('status', '')}"
                ticket_options.append(option_text)
            
            selected_option = st.selectbox(
                "Выберите обращение:",
                ticket_options,
                key="ticket_selector"
            )
            
            if selected_option:
                selected_id = int(selected_option.split("ID: ")[1].split(" - ")[0])
                
                selected_ticket = None
                for t in st.session_state.tickets:
                    if t['id'] == selected_id:
                        selected_ticket = t
                        break
                
                if selected_ticket:
                    st.markdown(f"### Обращение № {selected_ticket['id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**От:** {selected_ticket.get('name', '')}")
                        if selected_ticket.get('email'):
                            st.write(f"**Email:** {selected_ticket.get('email', '')}")
                        st.write(f"**Время:** {selected_ticket.get('timestamp', '')}")
                    with col2:
                        st.write(f"**Категория:** {selected_ticket.get('category', '')}")
                        confidence = selected_ticket.get('confidence', 0)
                        if isinstance(confidence, (int, float)):
                            st.write(f"**Уверенность:** {confidence:.1%}")
                        else:
                            st.write(f"**Уверенность:** {confidence}")
                        st.write(f"**Статус:** {selected_ticket.get('status', '')}")
                    
                    st.markdown("**Текст обращения:**")
                    text = selected_ticket.get('text', '')
                    if text:
                        st.info(text)
                    else:
                        st.warning("Текст обращения отсутствует")
                    
                    st.markdown("---")
                    
                    with st.form(key=f"response_form_{selected_id}"):
                        st.markdown("### Ответ службы поддержки")
                        
                        response_text = st.text_area(
                            "Введите ответ:", 
                            value=selected_ticket.get('admin_response', ''), 
                            height=100,
                            placeholder="Введите ваш ответ здесь..."
                        )
                        
                        current_status = selected_ticket.get('status', 'Новый')
                        status_options = ["Новый", "В работе", "Закрыт"]
                        if current_status not in status_options:
                            current_status = "Новый"
                        
                        new_status = st.selectbox(
                            "Статус:", 
                            status_options,
                            index=status_options.index(current_status)
                        )
                        
                        submitted = st.form_submit_button("Сохранить изменения")
                        
                        if submitted:
                            for i, t in enumerate(st.session_state.tickets):
                                if t['id'] == selected_id:
                                    st.session_state.tickets[i]['status'] = new_status
                                    st.session_state.tickets[i]['admin_response'] = response_text
                                    break
                            
                            save_tickets(st.session_state.tickets)
                            st.success("Изменения сохранены!")
                            st.rerun()
                    
                    if selected_ticket.get('admin_response'):
                        st.markdown("**Текущий ответ:**")
                        st.success(selected_ticket['admin_response'])
        else:
            st.info("Нет обращений по выбранным фильтрам")
