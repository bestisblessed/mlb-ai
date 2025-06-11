import streamlit as st
import os
import pandas as pd
import numpy as np
from openai import OpenAI
import time
st.set_page_config(page_title="MLB AI Chatbot", page_icon="🤖", layout="wide")
st.title("MLB AI Chatbot 🤖")
st.markdown("Ask me anything about MLB stats, players, or game predictions!")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"
if "OPENAI_API_KEY" not in st.session_state:
    st.session_state.OPENAI_API_KEY = st.secrets.get("openai", {}).get("api_key", None)
api_key = st.session_state.OPENAI_API_KEY
if not api_key:
    api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password")
    if api_key:
        st.session_state.OPENAI_API_KEY = api_key
#API_KEY = st.secrets["MY_FINAL_OPENAI_API_KEY_MORPHEUS"]
API_KEY = st.secrets["openai"]["openai_api_key"]
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your MLB AI Assistant. Ask me anything about baseball stats, players, or predictions!"}
    ]
def process_prompt(prompt, games_df, latest_date):
    if not prompt:
        return
    st.session_state.messages.append({"role": "user", "content": prompt})
    full_response = generate_response(prompt, games_df, latest_date)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
def load_game_data():
    dates = sorted((d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))), reverse=True)
    if not dates:
        return None, None
    latest_date = dates[0]
    sim_path = os.path.join(DATA_DIR, latest_date, "game_simulations.csv")
    if os.path.exists(sim_path):
        return pd.read_csv(sim_path), latest_date
    return None, latest_date

def generate_response(prompt, games_df=None, game_date=None):
    #if not st.session_state.OPENAI_API_KEY:
    #    return "Please add your OpenAI API key in the sidebar to continue."
    try:
        #client = OpenAI(api_key=st.session_state.OPENAI_API_KEY)
        client = OpenAI(api_key=API_KEY)
        system_message = "You are MLB AI, a helpful assistant that provides information about baseball. Be concise and informative."
        if games_df is not None:
            games_context = f"Today's games ({game_date}):\n"
            for _, game in games_df.iterrows():
                games_context += f"- {game['away_team']} @ {game['home_team']} at {game['time']}\n"
            system_message += f"\n\n{games_context}"
        messages = [
            {"role": "system", "content": system_message}
        ]
        conversation_history = st.session_state.messages[-10:]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"
games_df, latest_date = load_game_data()
examples = [
    "Who are the top home run hitters this season?",
    "What's the win probability for the Yankees today?",
    "Who is starting for the Dodgers tonight?",
    "Which team has the best bullpen ERA?",
    "What are the odds for the Astros game?"
]
user_input = st.chat_input("Ask about MLB stats, players, or predictions")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            full_response = generate_response(user_input, games_df, latest_date)
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": full_response})

st.sidebar.markdown("**Example Questions:**")
example_container = st.sidebar.container()
for example in examples:
    if example_container.button(example, key=f"example_{example}"):
        with st.chat_message("user"):
            st.markdown(example)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Thinking..."):
                full_response = generate_response(example, games_df, latest_date)
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "user", "content": example})
        st.session_state.messages.append({"role": "assistant", "content": full_response})
st.sidebar.markdown("---")
st.sidebar.markdown("MLB AI © 2025 | By Tyler Durette")
