import os
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from openai import OpenAI
import json
import uuid
from dotenv import load_dotenv
import logging
import base64
import hashlib
import hmac
import pandas as pd
from datetime import datetime, timezone
import re
import requests
import sqlite3
import threading
import time
import unicodedata
from collections import defaultdict, deque
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client with API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("No OpenAI API key found in environment variables")
else:
    logger.info("OpenAI API key loaded from environment")

client = OpenAI(
    api_key=api_key,
    timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
)

# Assistant IDs and configuration for Responses API
DEFAULT_ASSISTANT_ID = "asst_QIEMCdBCqsX4al7O4Jg2Jjpx"

PROJECT_ROOT = os.getenv("MMA_AI_APP_ROOT")
if PROJECT_ROOT:
    PROJECT_ROOT = os.path.abspath(PROJECT_ROOT)
else:
    PROJECT_ROOT = os.path.abspath(os.getcwd())

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
logger.info(f"Data directory set to: {DATA_DIR}")

FIGHTER_DATA_PATH = os.path.join(DATA_DIR, "fighter_info.csv")
EVENT_DATA_PATH = os.path.join(DATA_DIR, "event_data_sherdog.csv")
UPCOMING_EVENT_DATA_PATH = os.path.join(DATA_DIR, "upcoming_event_data_sherdog.csv")
ODDS_MOVEMENTS_PATH = os.path.join(DATA_DIR, "ufc_odds_movements_fightoddsio.csv")
NEWS_DAILY_PATH = os.path.join(DATA_DIR, "news_daily.json")
CHAT_DB_PATH = os.getenv("MMA_CHAT_DB_PATH", os.path.join(DATA_DIR, "chat_conversations.sqlite3"))
CHAT_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("CHAT_RATE_LIMIT_WINDOW_SECONDS", "60"))
CHAT_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("CHAT_RATE_LIMIT_MAX_REQUESTS", "30"))
CHAT_SESSION_SECRET = os.getenv("MMA_CHAT_SESSION_SECRET")
CLIENT_SESSION_HEADER = "X-Client-Session-ID"
CLIENT_SESSION_COOKIE_NAME = "mma_client_session"
CLIENT_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365

if not CHAT_SESSION_SECRET:
    logger.critical("MMA_CHAT_SESSION_SECRET is required for production chat session cookies")
    raise RuntimeError("MMA_CHAT_SESSION_SECRET is required")

DATASET_FILES = [
    FIGHTER_DATA_PATH,
    EVENT_DATA_PATH
]

dataset_file_cache = {}
rate_limit_events = defaultdict(deque)
rate_limit_lock = threading.Lock()
sessionless_rate_limit_events = defaultdict(deque)
sessionless_rate_limit_lock = threading.Lock()
conversation_locks = {}
conversation_locks_guard = threading.Lock()

CHAT_ASSISTANT_INSTRUCTIONS = (
    "You are a data analyst and machine learning expert. Help the user analyze, visualize and explore trends using the data available to you. "
    "Use your data sources in the background, but never mention or reference any data files, file names, or that you are loading or inspecting files. "
    "It is forbidden to mention proprietary data files or datasets. "
    "Be thorough and figure out how to use the data properly to answer them. "
    "Always return your answer in plaintext, do not include characters like asterisks like in markdown. Never put asterisks in your final answers."
)

PREDICTION_ASSISTANT_INSTRUCTIONS = (
    "You are a data scientist and math expert in the realm of sports and sports handicapping/modeling with Python. "
    "You are to help me deeply research, analyze data, visualize data, predict outcomes, and compose reports for MMA/UFC fights and fighters. "
    "I am a professional handicapper and will use all of this to help me with my sports modeling, betting and investing; as well as making general fight predictions.\n\n"
    "Use your data sources in the background, but never mention or reference any data files, file names, or that you are loading or inspecting files. "
    "It is forbidden to mention proprietary data files or datasets. "
    "If the user selects the button \"Predict Outcome\" and gives you two fighter IDs (corresponding to fighters in your datasets), "
    "you must proceed with all of the following steps in step 1, 2, and 3 until fully complete or your mother is going to ground you and take your allowance away forever. "
    "Use fighter IDs to match and find the fighters from all files as they are unique per fighter. "
    "Never mention numeric fighter IDs in the user-facing response. Always refer to fighters by name only. "
    "If you cannot find a fighter ID, use their name and look for their data then as you 100% have it somewhere. "
    "Also, only provide responses in plain text only. Do not use any markdown formatting such as double asterisks, hashes, or other formatting symbols ever. "
    "Use plain text only, or again you will be grounded with no allowance:\n"
    "1. Train yourself thoroughly and deeply on your available data sources for fighter details and bout details. "
    "Learn every column you have available in each of them to use in your analysis. Together with all these sources you have a very thorough UFC/MMA dataset to combine and use for your analysis as needed. "
    "If a fighter ID isn't found, try another method and use their name for example - do not provide an empty response or tell the user you couldn't find it.\n"
    "2. Proceed to predict the theoretical outcome of that matchup - including the method of victory and time you believe it will happen, "
    "along with a detailed explanation of why you believe that is likely to happen. Make your best educated inference based on the data you have on them both from deep analysis of all your files and data on each fighter.\n"
    "3. At the end of this response, ask if they would like to \"Create Odds\" now for the matchup too. If they say yes proceed with generating what you would price the professional betting odds for the matchup in American odds. "
    "For example, -300/+250 for a large favorite, -110/-110 for even fights, etc.\n\n"
    "Never ask for clarification or a follow up - you must deliver a prediction and answer to the user every time directly using your best effort."
)

ASSISTANT_CONFIGS = {
    "asst_QIEMCdBCqsX4al7O4Jg2Jjpx": {
        "model": "gpt-5.4-nano",
        "instructions": CHAT_ASSISTANT_INSTRUCTIONS
    },
    "asst_n6LeaUZ7n2zYwMeGzIon47B5": {
        "model": "gpt-5.4-nano",
        "instructions": PREDICTION_ASSISTANT_INSTRUCTIONS
    }
}

def get_assistant_config(assistant_id):
    if assistant_id and assistant_id in ASSISTANT_CONFIGS:
        return ASSISTANT_CONFIGS[assistant_id]
    if assistant_id:
        logger.warning(f"Unknown assistant ID '{assistant_id}', falling back to default")
    return ASSISTANT_CONFIGS[DEFAULT_ASSISTANT_ID]

def upload_dataset(path):
    if not os.path.exists(path):
        logger.warning(f"Dataset file not found: {path}")
        return None

    mtime = os.path.getmtime(path)
    cached = dataset_file_cache.get(path)
    if cached and cached.get("mtime") == mtime and cached.get("file_id"):
        return cached["file_id"]

    try:
        with open(path, "rb") as file_handle:
            uploaded = client.files.create(
                file=file_handle,
                purpose="assistants"
            )
        dataset_file_cache[path] = {
            "file_id": uploaded.id,
            "mtime": mtime
        }
        logger.info(f"Uploaded dataset {path} with file ID: {uploaded.id}")
        return uploaded.id
    except Exception as e:
        logger.error(f"Failed to upload dataset {path}: {str(e)}")
        return None

def get_dataset_file_ids():
    file_ids = []
    for path in DATASET_FILES:
        file_id = upload_dataset(path)
        if file_id:
            file_ids.append(file_id)
    return file_ids

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def short_id(value):
    if not value:
        return "none"
    text = str(value)
    return text[:8]

def safe_json_error(message, status_code):
    return jsonify({"error": message}), status_code

def signed_session_cookie_value(session_id):
    digest = hmac.new(
        CHAT_SESSION_SECRET.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{session_id}.{signature}"

def parse_signed_session_cookie(value):
    if not value or not isinstance(value, str) or "." not in value:
        return None
    session_text, signature = value.rsplit(".", 1)
    session_id = parse_uuid_value(session_text)
    if not session_id:
        return None
    expected_signature = signed_session_cookie_value(session_id).rsplit(".", 1)[1]
    if not hmac.compare_digest(signature, expected_signature):
        return None
    return session_id

def get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or "unknown"

def resolve_chat_session():
    header_value = request.headers.get(CLIENT_SESSION_HEADER)
    cookie_session_id = parse_signed_session_cookie(
        request.cookies.get(CLIENT_SESSION_COOKIE_NAME)
    )

    if header_value is not None:
        session_id = parse_uuid_value(header_value)
        if not session_id:
            return None, safe_json_error("A valid client session is required.", 400)
        return {
            "session_id": session_id,
            "set_cookie": cookie_session_id != session_id,
            "new_anonymous_session": False
        }, None

    if cookie_session_id:
        return {
            "session_id": cookie_session_id,
            "set_cookie": False,
            "new_anonymous_session": False
        }, None

    return {
        "session_id": str(uuid.uuid4()),
        "set_cookie": True,
        "new_anonymous_session": True
    }, None

def attach_chat_session_cookie(response, session_context):
    if session_context and session_context.get("set_cookie"):
        response.set_cookie(
            CLIENT_SESSION_COOKIE_NAME,
            signed_session_cookie_value(session_context["session_id"]),
            max_age=CLIENT_SESSION_COOKIE_MAX_AGE_SECONDS,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/"
        )
    return response

def safe_chat_json_error(message, status_code, session_context):
    response = jsonify({"error": message})
    return attach_chat_session_cookie(response, session_context), status_code

def parse_uuid_value(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return str(uuid.UUID(stripped))
    except (TypeError, ValueError):
        return None

def parse_optional_uuid_value(value):
    if value is None:
        return None
    if value == "":
        return None
    return parse_uuid_value(value)

def get_request_session_id():
    session_context, error_response = resolve_chat_session()
    if error_response:
        return None
    return session_context["session_id"]

def check_rate_limit(session_id):
    now = time.monotonic()
    window_start = now - CHAT_RATE_LIMIT_WINDOW_SECONDS
    with rate_limit_lock:
        events = rate_limit_events[session_id]
        while events and events[0] < window_start:
            events.popleft()
        if len(events) >= CHAT_RATE_LIMIT_MAX_REQUESTS:
            return False
        events.append(now)
        return True

def check_sessionless_rate_limit():
    now = time.monotonic()
    window_start = now - CHAT_RATE_LIMIT_WINDOW_SECONDS
    key = get_client_ip()
    with sessionless_rate_limit_lock:
        events = sessionless_rate_limit_events[key]
        while events and events[0] < window_start:
            events.popleft()
        if len(events) >= CHAT_RATE_LIMIT_MAX_REQUESTS:
            return False
        events.append(now)
        return True

def check_chat_rate_limit(session_context):
    if session_context.get("new_anonymous_session") and not check_sessionless_rate_limit():
        return False
    return check_rate_limit(session_context["session_id"])

def acquire_conversation_lock(conversation_id):
    with conversation_locks_guard:
        lock = conversation_locks.setdefault(conversation_id, threading.Lock())
    if not lock.acquire(blocking=False):
        return None
    return lock

class ChatStorage:
    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self):
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    last_response_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_session_id
                    ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_id
                    ON messages(conversation_id, id);
                """
            )

    def upsert_session(self, session_id):
        now = utc_now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, created_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (session_id, now, now)
            )
            conn.commit()

    def get_or_create_conversation(self, session_id, conversation_id=None):
        self.upsert_session(session_id)
        now = utc_now_iso()
        with self.connection() as conn:
            if conversation_id:
                row = conn.execute(
                    """
                    SELECT conversation_id, session_id, last_response_id
                    FROM conversations
                    WHERE conversation_id = ?
                    """,
                    (conversation_id,)
                ).fetchone()
                if row is None or row["session_id"] != session_id:
                    return None
                return {
                    "conversation_id": row["conversation_id"],
                    "session_id": row["session_id"],
                    "last_response_id": row["last_response_id"]
                }

            new_conversation_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO conversations(conversation_id, session_id, last_response_id, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (new_conversation_id, session_id, now, now)
            )
            conn.commit()
            logger.info(
                "chat conversation created session=%s conversation=%s",
                short_id(session_id),
                short_id(new_conversation_id)
            )
            return {
                "conversation_id": new_conversation_id,
                "session_id": session_id,
                "last_response_id": None
            }

    def get_conversation(self, session_id, conversation_id):
        self.upsert_session(session_id)
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT conversation_id, session_id, last_response_id
                FROM conversations
                WHERE conversation_id = ? AND session_id = ?
                """,
                (conversation_id, session_id)
            ).fetchone()
            if row is None:
                return None
            return {
                "conversation_id": row["conversation_id"],
                "session_id": row["session_id"],
                "last_response_id": row["last_response_id"]
            }

    def append_message(self, conversation_id, role, content):
        now = utc_now_iso()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO messages(conversation_id, role, content_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, json.dumps(content, ensure_ascii=False), now)
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (now, conversation_id)
            )
            conn.commit()

    def append_assistant_items_and_update_response(self, conversation_id, response_data, response_id):
        now = utc_now_iso()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for item in response_data:
                item_type = item.get("type")
                if item_type == "image":
                    message_content = {
                        "type": "image",
                        "content": item.get("content", "")
                    }
                else:
                    message_content = {
                        "type": "text",
                        "content": item.get("content", "")
                    }
                conn.execute(
                    """
                    INSERT INTO messages(conversation_id, role, content_json, created_at)
                    VALUES (?, 'assistant', ?, ?)
                    """,
                    (conversation_id, json.dumps([message_content], ensure_ascii=False), now)
                )
            conn.execute(
                """
                UPDATE conversations
                SET last_response_id = COALESCE(?, last_response_id), updated_at = ?
                WHERE conversation_id = ?
                """,
                (response_id, now, conversation_id)
            )
            conn.commit()

    def get_messages(self, session_id, conversation_id):
        conversation = self.get_conversation(session_id, conversation_id)
        if conversation is None:
            return None
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content_json
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            ).fetchall()
        messages = []
        for row in rows:
            try:
                content = json.loads(row["content_json"])
            except json.JSONDecodeError:
                content = []
            messages.append({
                "role": row["role"],
                "content": content
            })
        return messages

chat_storage = ChatStorage(CHAT_DB_PATH)

def configure_chat_storage(db_path):
    global chat_storage, CHAT_DB_PATH, rate_limit_events, sessionless_rate_limit_events, conversation_locks
    CHAT_DB_PATH = db_path
    chat_storage = ChatStorage(db_path)
    with rate_limit_lock:
        rate_limit_events = defaultdict(deque)
    with sessionless_rate_limit_lock:
        sessionless_rate_limit_events = defaultdict(deque)
    with conversation_locks_guard:
        conversation_locks = {}
    return chat_storage

def extract_text_from_block(block):
    if block is None:
        return None
    if isinstance(block, dict):
        if "text" in block and block["text"]:
            return block["text"]
        if "value" in block and block["value"]:
            return block["value"]
        return None

    text_value = getattr(block, "text", None)
    if isinstance(text_value, str):
        return text_value
    if text_value is not None and hasattr(text_value, "value"):
        return text_value.value

    value = getattr(block, "value", None)
    if isinstance(value, str):
        return value

    return None

def get_block_value(block, key):
    if isinstance(block, dict):
        return block.get(key)
    return getattr(block, key, None)

def download_image_data(image_url):
    if not image_url:
        return None
    if image_url.startswith("data:image/"):
        try:
            _, encoded = image_url.split(",", 1)
            return base64.b64decode(encoded)
        except Exception as e:
            logger.error(f"Error decoding data URL image: {str(e)}")
            return None
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return None

def download_file_data(file_id, container_id=None):
    if not file_id:
        return None
    try:
        if container_id:
            file_content = client.containers.files.content.retrieve(file_id, container_id=container_id)
        else:
            file_content = client.files.content(file_id)
        if hasattr(file_content, "read"):
            return file_content.read()
        if hasattr(file_content, "content"):
            return file_content.content
        if isinstance(file_content, (bytes, bytearray)):
            return bytes(file_content)
        return None
    except Exception as e:
        logger.error(f"Error downloading file content for {file_id}: {str(e)}")
        return None

def extract_image_source(block):
    image_url = None
    file_id = None

    def consume(obj):
        nonlocal image_url, file_id
        if not obj:
            return

        obj_url = get_block_value(obj, "url") or get_block_value(obj, "image_url")
        obj_file_id = get_block_value(obj, "file_id") or get_block_value(obj, "fileId") or get_block_value(obj, "id")

        if obj_url and not isinstance(obj_url, str):
            nested_url = get_block_value(obj_url, "url") or get_block_value(obj_url, "image_url")
            nested_file_id = get_block_value(obj_url, "file_id") or get_block_value(obj_url, "fileId") or get_block_value(obj_url, "id")
            if nested_url and isinstance(nested_url, str):
                obj_url = nested_url
            else:
                obj_url = None
            if not obj_file_id and nested_file_id:
                obj_file_id = nested_file_id

        if not image_url and obj_url:
            image_url = obj_url
        if not file_id and obj_file_id:
            file_id = obj_file_id

    consume(block)
    consume(get_block_value(block, "file"))
    consume(get_block_value(block, "image"))
    consume(get_block_value(block, "image_file"))

    return image_url, file_id

def is_image_file(filename, mime_type):
    if mime_type and mime_type.startswith("image/"):
        return True
    if filename:
        lower_name = filename.lower()
        return lower_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    return False

def is_image_bytes(data):
    if not data or len(data) < 12:
        return False
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False

def get_image_data(image_url, file_id, container_id):
    if file_id:
        image_data = download_file_data(file_id, container_id=container_id)
        if image_data and is_image_bytes(image_data):
            return image_data
    if image_url:
        image_data = download_image_data(image_url)
        if image_data and is_image_bytes(image_data):
            return image_data
    return None

def extract_image_sources_from_annotations(annotations):
    sources = []
    if not annotations:
        return sources
    for annotation in annotations:
        file_id = get_block_value(annotation, "file_id") or get_block_value(annotation, "fileId") or get_block_value(annotation, "id")
        container_id = get_block_value(annotation, "container_id") or get_block_value(annotation, "containerId")
        filename = get_block_value(annotation, "filename") or get_block_value(annotation, "file_name")
        if file_id:
            if is_image_file(filename, None) or filename is None:
                sources.append((None, file_id, container_id))
    return sources

def build_response_items(response):
    text_chunks = []
    image_sources = []

    for output_item in response.output:
        item_type = getattr(output_item, "type", None)

        if item_type == "message":
            for content_block in getattr(output_item, "content", []) or []:
                content_type = get_block_value(content_block, "type")
                if content_type in ["image", "output_image", "image_file"]:
                    image_url, file_id = extract_image_source(content_block)
                    if image_url or file_id:
                        image_sources.append((image_url, file_id, None))
                    continue

                text_content = extract_text_from_block(content_block)
                if text_content:
                    text_chunks.append(text_content)

                annotations = get_block_value(content_block, "annotations")
                if annotations:
                    image_sources.extend(extract_image_sources_from_annotations(annotations))
        elif item_type in ["code_interpreter_call", "tool_call"]:
            outputs = getattr(output_item, "outputs", None) or get_block_value(output_item, "outputs") or []
            for output in outputs or []:
                output_type = get_block_value(output, "type")
                if output_type in ["image", "output_image", "image_file"]:
                    image_url, file_id = extract_image_source(output)
                    if image_url or file_id:
                        image_sources.append((image_url, file_id, None))
                elif output_type in ["file", "output_file"]:
                    filename = (
                        get_block_value(output, "filename")
                        or get_block_value(output, "file_name")
                        or get_block_value(output, "name")
                        or get_block_value(output, "path")
                    )
                    mime_type = (
                        get_block_value(output, "mime_type")
                        or get_block_value(output, "content_type")
                        or get_block_value(output, "contentType")
                    )
                    image_url, file_id = extract_image_source(output)
                    if image_url or file_id:
                        if is_image_file(filename, mime_type) or file_id:
                            image_sources.append((image_url, file_id, None))
        elif item_type in ["image", "output_image", "image_file", "file", "output_file"]:
            image_url, file_id = extract_image_source(output_item)
            if image_url or file_id:
                image_sources.append((image_url, file_id, None))

    text_content = "\n\n".join([chunk for chunk in text_chunks if chunk.strip()]).strip()
    if not text_content and getattr(response, "output_text", None):
        text_content = response.output_text.strip()

    response_items = []
    if text_content:
        response_items.append({
            "type": "text",
            "content": clean_markdown_simple(text_content)
        })

    for image_url, file_id, container_id in image_sources:
        image_data = get_image_data(image_url, file_id, container_id)
        if not image_data:
            continue
        encoded_image = base64.b64encode(image_data).decode("utf-8")
        response_items.append({
            "type": "image",
            "format": "png",
            "content": f"data:image/png;base64,{encoded_image}"
        })

    return response_items

def clean_markdown_simple(text):
    """Remove basic markdown symbols (# and *) from text."""
    if not text:
        return text
    
    # Remove heading symbols
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic asterisks
    text = re.sub(r'\*+', '', text)
    
    return text

def make_sse_event(event_name, payload):
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

def get_event_value(event, key):
    if isinstance(event, dict):
        return event.get(key)
    return getattr(event, key, None)

def build_responses_request_params(user_input, conversation, assistant_config):
    tools = None
    dataset_file_ids = get_dataset_file_ids()
    if dataset_file_ids:
        tools = [
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": dataset_file_ids
                }
            }
        ]

    request_params = {
        "model": assistant_config["model"],
        "instructions": assistant_config["instructions"],
        "input": [
            {
                "role": "user",
                "content": user_input
            }
        ],
        "include": ["code_interpreter_call.outputs"],
        "store": True
    }

    if tools:
        request_params["tools"] = tools

    if conversation.get("last_response_id"):
        request_params["previous_response_id"] = conversation["last_response_id"]

    return request_params

@app.route('/')
def home():
    return "Flask App is Running! API is available at /api/chat and /api/examples"

# Static file serving route for data directory
@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve static files from the data directory"""
    return send_from_directory(DATA_DIR, filename)

# New endpoints for fighter and event data
@app.route('/api/data/fighters', methods=['GET'])
def get_fighters():
    try:
        # Read the CSV file
        fighters_df = pd.read_csv(FIGHTER_DATA_PATH)
        
        # Replace string "None" or "NULL" values with proper None/null
        fighters_df = fighters_df.replace(["None", "NULL", "NaN"], None)
        
        # Fill nullable columns that should never be null with appropriate values
        fighters_df["Wins"] = fighters_df["Wins"].fillna(0)
        fighters_df["Losses"] = fighters_df["Losses"].fillna(0)
        fighters_df["Win_Decision"] = fighters_df["Win_Decision"].fillna(0)
        fighters_df["Win_KO"] = fighters_df["Win_KO"].fillna(0)
        fighters_df["Win_Sub"] = fighters_df["Win_Sub"].fillna(0)
        fighters_df["Loss_Decision"] = fighters_df["Loss_Decision"].fillna(0)
        fighters_df["Loss_KO"] = fighters_df["Loss_KO"].fillna(0)
        fighters_df["Loss_Sub"] = fighters_df["Loss_Sub"].fillna(0)
        fighters_df["Fighter_ID"] = fighters_df["Fighter_ID"].fillna(0)
        
        # For Reach, replace '-' with empty string to keep it as a string
        fighters_df["Reach"] = fighters_df["Reach"].replace('-', '')
        # For Stance, replace '-' with empty string
        fighters_df["Stance"] = fighters_df["Stance"].replace('-', '')
        # Fill any remaining nulls with empty strings for string columns
        fighters_df["Reach"] = fighters_df["Reach"].fillna('')
        fighters_df["Stance"] = fighters_df["Stance"].fillna('')
        
        # Ensure integer fields are properly formatted as integers
        int_columns = ["Wins", "Losses", "Win_Decision", "Win_KO", "Win_Sub", 
                       "Loss_Decision", "Loss_KO", "Loss_Sub", "Fighter_ID"]
        for col in int_columns:
            fighters_df[col] = fighters_df[col].astype(int)
        
        # Make sure Reach is treated as a string to match Swift's expectation
        # Convert any numeric values to strings with one decimal place if needed
        fighters_df["Reach"] = fighters_df["Reach"].apply(
            lambda x: f"{float(x):.1f}" if isinstance(x, (int, float)) and x != '' else str(x)
        )
        
        # Convert to dictionary format with appropriate handling of null values
        fighters_data = json.loads(fighters_df.to_json(orient='records', date_format='iso'))
        
        # Add timestamp for caching
        response = {
            'timestamp': datetime.now().isoformat(),
            'fighters': fighters_data
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching fighter data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/events', methods=['GET'])
def get_events():
    try:
        # Read the CSV file
        events_df = pd.read_csv(EVENT_DATA_PATH)
        
        # Replace string "None" or "NULL" values with proper None/null
        events_df = events_df.replace(["None", "NULL", "NaN"], None)
        
        # Fill nullable columns that should never be null with appropriate values
        events_df["Fighter 1 ID"] = events_df["Fighter 1 ID"].fillna(0)
        events_df["Fighter 2 ID"] = events_df["Fighter 2 ID"].fillna(0)
        events_df["Winning Round"] = events_df["Winning Round"].fillna(0)
        
        # Ensure integer fields are properly formatted as integers
        int_columns = ["Fighter 1 ID", "Fighter 2 ID", "Winning Round"]
        for col in int_columns:
            events_df[col] = events_df[col].astype(int)
        
        # Convert to dictionary format with appropriate handling of null values
        events_data = json.loads(events_df.to_json(orient='records', date_format='iso'))
        
        # Add timestamp for caching
        response = {
            'timestamp': datetime.now().isoformat(),
            'events': events_data
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching event data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/version', methods=['GET'])
def get_data_version():
    try:
        # Return the current version based on file modification times
        fighter_data_path = FIGHTER_DATA_PATH
        event_data_path = EVENT_DATA_PATH
        
        fighter_timestamp = os.path.getmtime(fighter_data_path) if os.path.exists(fighter_data_path) else 0
        event_timestamp = os.path.getmtime(event_data_path) if os.path.exists(event_data_path) else 0
        
        return jsonify({
            'fighter_data_version': fighter_timestamp,
            'event_data_version': event_timestamp,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching data version: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    started_at = time.monotonic()
    session_context, error_response = resolve_chat_session()
    if error_response:
        return error_response
    session_id = session_context["session_id"]
    if not check_chat_rate_limit(session_context):
        return safe_chat_json_error("Rate limit exceeded. Please wait and try again.", 429, session_context)

    try:
        data = request.get_json(silent=True) or {}
        user_input = data.get('message', '')
        requested_conversation_id = data.get('conversation_id')
        conversation_id = parse_optional_uuid_value(requested_conversation_id)
        requested_assistant_id = data.get('assistant_id')

        if requested_conversation_id not in (None, "") and not conversation_id:
            return safe_chat_json_error("A valid conversation ID is required.", 400, session_context)
        if not isinstance(user_input, str) or not user_input.strip():
            return safe_chat_json_error("A message is required.", 400, session_context)

        conversation = chat_storage.get_or_create_conversation(session_id, conversation_id)
        if conversation is None:
            return safe_chat_json_error("Conversation not found.", 404, session_context)
        conversation_id = conversation["conversation_id"]

        conversation_lock = acquire_conversation_lock(conversation_id)
        if conversation_lock is None:
            return safe_chat_json_error(
                "A response is already being generated for this conversation. Please wait and try again.",
                409,
                session_context
            )

        logger.info(
            "chat request endpoint=/api/chat session=%s conversation=%s assistant=%s",
            short_id(session_id),
            short_id(conversation_id),
            requested_assistant_id or DEFAULT_ASSISTANT_ID
        )

        assistant_config = get_assistant_config(requested_assistant_id)
        user_content = [
            {
                "type": "text",
                "content": user_input
            }
        ]
        chat_storage.append_message(conversation_id, "user", user_content)

        request_params = build_responses_request_params(user_input, conversation, assistant_config)

        response = client.responses.create(**request_params)
        response_data = build_response_items(response)

        if not response_data:
            response_data = [{
                "type": "error",
                "content": "Sorry, I couldn't retrieve the information you requested."
            }]

        chat_storage.append_assistant_items_and_update_response(conversation_id, response_data, response.id)
        logger.info(
            "chat request complete endpoint=/api/chat status=200 session=%s conversation=%s duration_ms=%d items=%d",
            short_id(session_id),
            short_id(conversation_id),
            int((time.monotonic() - started_at) * 1000),
            len(response_data)
        )

        return attach_chat_session_cookie(jsonify({
            "response": response_data,
            "conversation_id": conversation_id
        }), session_context)
    except Exception as e:
        logger.error(
            "chat request failed endpoint=/api/chat session=%s conversation=%s error_type=%s duration_ms=%d",
            short_id(session_id),
            short_id(locals().get("conversation_id")),
            type(e).__name__,
            int((time.monotonic() - started_at) * 1000)
        )
        return safe_chat_json_error("The server could not complete the request. Please try again.", 500, session_context)
    finally:
        if "conversation_lock" in locals() and conversation_lock is not None:
            conversation_lock.release()

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    started_at = time.monotonic()
    session_context, error_response = resolve_chat_session()
    if error_response:
        return error_response
    session_id = session_context["session_id"]
    if not check_chat_rate_limit(session_context):
        return safe_chat_json_error("Rate limit exceeded. Please wait and try again.", 429, session_context)

    try:
        data = request.get_json(silent=True) or {}
        user_input = data.get('message', '')
        requested_conversation_id = data.get('conversation_id')
        conversation_id = parse_optional_uuid_value(requested_conversation_id)
        requested_assistant_id = data.get('assistant_id')

        if requested_conversation_id not in (None, "") and not conversation_id:
            return safe_chat_json_error("A valid conversation ID is required.", 400, session_context)
        if not isinstance(user_input, str) or not user_input.strip():
            return safe_chat_json_error("A message is required.", 400, session_context)

        conversation = chat_storage.get_or_create_conversation(session_id, conversation_id)
        if conversation is None:
            return safe_chat_json_error("Conversation not found.", 404, session_context)
        conversation_id = conversation["conversation_id"]

        conversation_lock = acquire_conversation_lock(conversation_id)
        if conversation_lock is None:
            return safe_chat_json_error(
                "A response is already being generated for this conversation. Please wait and try again.",
                409,
                session_context
            )

        logger.info(
            "chat stream started endpoint=/api/chat/stream session=%s conversation=%s assistant=%s",
            short_id(session_id),
            short_id(conversation_id),
            requested_assistant_id or DEFAULT_ASSISTANT_ID
        )

        assistant_config = get_assistant_config(requested_assistant_id)
        user_content = [
            {
                "type": "text",
                "content": user_input
            }
        ]
        chat_storage.append_message(conversation_id, "user", user_content)

        def generate():
            completed_response = None
            text_chunks = []
            response_id = None

            try:
                yield make_sse_event("metadata", {"conversation_id": conversation_id})

                request_params = build_responses_request_params(user_input, conversation, assistant_config)
                stream = client.responses.create(**request_params, stream=True)
                for event in stream:
                    event_type = get_event_value(event, "type")

                    response = get_event_value(event, "response")
                    if response is not None:
                        response_id = get_event_value(response, "id") or response_id

                    if event_type == "response.output_text.delta":
                        delta = get_event_value(event, "delta")
                        if delta:
                            text_chunks.append(delta)
                            yield make_sse_event("text_delta", {"delta": delta})
                    elif event_type == "response.completed":
                        completed_response = response
                    elif event_type == "response.failed":
                        logger.warning(
                            "openai stream failed session=%s conversation=%s",
                            short_id(session_id),
                            short_id(conversation_id)
                        )
                        yield make_sse_event("error", {"error": "The response failed. Please try again."})
                        return

                if completed_response is not None:
                    response_data = build_response_items(completed_response)
                    response_id = get_event_value(completed_response, "id") or response_id
                else:
                    text_content = clean_markdown_simple("".join(text_chunks).strip())
                    response_data = [{"type": "text", "content": text_content}] if text_content else []

                if not response_data:
                    response_data = [{
                        "type": "error",
                        "content": "Sorry, I couldn't retrieve the information you requested."
                    }]

                chat_storage.append_assistant_items_and_update_response(conversation_id, response_data, response_id)
                logger.info(
                    "chat stream complete endpoint=/api/chat/stream status=200 session=%s conversation=%s duration_ms=%d items=%d",
                    short_id(session_id),
                    short_id(conversation_id),
                    int((time.monotonic() - started_at) * 1000),
                    len(response_data)
                )

                yield make_sse_event("final", {
                    "response": response_data,
                    "conversation_id": conversation_id
                })
            except GeneratorExit:
                logger.info(
                    "chat stream disconnected session=%s conversation=%s duration_ms=%d",
                    short_id(session_id),
                    short_id(conversation_id),
                    int((time.monotonic() - started_at) * 1000)
                )
            except Exception as e:
                logger.error(
                    "chat stream failed session=%s conversation=%s error_type=%s duration_ms=%d",
                    short_id(session_id),
                    short_id(conversation_id),
                    type(e).__name__,
                    int((time.monotonic() - started_at) * 1000)
                )
                yield make_sse_event("error", {"error": "The server could not complete the response. Please try again."})
            finally:
                conversation_lock.release()

        response = Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        return attach_chat_session_cookie(response, session_context)
    except Exception as e:
        if "conversation_lock" in locals() and conversation_lock is not None:
            conversation_lock.release()
        logger.error(
            "chat stream setup failed session=%s conversation=%s error_type=%s duration_ms=%d",
            short_id(session_id),
            short_id(locals().get("conversation_id")),
            type(e).__name__,
            int((time.monotonic() - started_at) * 1000)
        )
        return safe_chat_json_error("The server could not start the response. Please try again.", 500, session_context)

@app.route('/api/examples', methods=['GET'])
def get_examples():
    examples = [
        "Tell me about Jon Jones most recent 5 fights in detail",
        "Make me a pie chart visualization of Max Holloway's method of victories",
        "Analyze and research Paddy Pimblett and Michael Chandler in depth, then predict who would win in a potential fight. Include the method and time of victory.",
        #"Simulate an upcoming fight between Dricus Du Plessis and Khamzat Chimaev using a Monte Carlo simulation with at least 10,000 iterations, incorporating their strike accuracy, takedown defense, and cardio endurance metrics to produce win probabilities, expected finish methods, and round/time distributions",
        "Simulate an upcoming fight between Dricus Du Plessis and Khamzat Chimaev using a Monte Carlo simulation with at least 10,000 iterations and using advanced features you determine."
        # "Tell me the most recent 3 events and the main event outcome of each one",
        # "Where is the upcoming UFC card/event this weekend and what are all of the fights on it with a short overview of each fight?",
    ]
    return jsonify({"examples": examples})

@app.route('/api/chat/history', methods=['POST'])
def get_chat_history():
    started_at = time.monotonic()
    session_context, error_response = resolve_chat_session()
    if error_response:
        return error_response
    session_id = session_context["session_id"]
    if not check_chat_rate_limit(session_context):
        return safe_chat_json_error("Rate limit exceeded. Please wait and try again.", 429, session_context)

    try:
        data = request.get_json(silent=True) or {}
        requested_conversation_id = data.get('conversation_id')
        conversation_id = parse_optional_uuid_value(requested_conversation_id)

        if not conversation_id:
            return safe_chat_json_error("A valid conversation ID is required.", 400, session_context)

        messages = chat_storage.get_messages(session_id, conversation_id)
        if messages is None:
            logger.info(
                "chat history denied session=%s conversation=%s duration_ms=%d",
                short_id(session_id),
                short_id(conversation_id),
                int((time.monotonic() - started_at) * 1000)
            )
            return safe_chat_json_error("Conversation not found.", 404, session_context)

        logger.info(
            "chat history complete status=200 session=%s conversation=%s duration_ms=%d messages=%d",
            short_id(session_id),
            short_id(conversation_id),
            int((time.monotonic() - started_at) * 1000),
            len(messages)
        )

        return attach_chat_session_cookie(jsonify({
            "messages": messages,
            "conversation_id": conversation_id
        }), session_context)
    except Exception as e:
        logger.error(
            "chat history failed session=%s conversation=%s error_type=%s duration_ms=%d",
            short_id(session_id),
            short_id(locals().get("conversation_id")),
            type(e).__name__,
            int((time.monotonic() - started_at) * 1000)
        )
        return safe_chat_json_error("The server could not load the conversation. Please try again.", 500, session_context)

@app.route('/api/debug/fighter_csv_columns', methods=['GET'])
def get_fighter_csv_columns():
    try:
        fighters_df = pd.read_csv(FIGHTER_DATA_PATH)
        column_info = {
            'columns': list(fighters_df.columns),
            'dtypes': {col: str(fighters_df[col].dtype) for col in fighters_df.columns},
            'null_counts': {col: int(fighters_df[col].isnull().sum()) for col in fighters_df.columns}
        }
        return jsonify(column_info)
    except Exception as e:
        logger.error(f"Error reading fighter CSV columns: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/event_csv_columns', methods=['GET'])
def get_event_csv_columns():
    try:
        events_df = pd.read_csv(EVENT_DATA_PATH)
        column_info = {
            'columns': list(events_df.columns),
            'dtypes': {col: str(events_df[col].dtype) for col in events_df.columns},
            'null_counts': {col: int(events_df[col].isnull().sum()) for col in events_df.columns}
        }
        return jsonify(column_info)
    except Exception as e:
        logger.error(f"Error reading event CSV columns: {str(e)}")
        return jsonify({'error': str(e)}), 500


def normalize_fighter_lookup_key(name):
    if not isinstance(name, str):
        return ""

    folded = unicodedata.normalize("NFKD", name)
    without_diacritics = "".join(char for char in folded if not unicodedata.combining(char))
    alphanumeric_only = re.sub(r"[^a-z0-9]+", " ", without_diacritics.lower())
    return re.sub(r"\s+", " ", alphanumeric_only).strip()


def clean_fighter_display_name(name):
    if not isinstance(name, str):
        return ""

    collapsed_hyphens = re.sub(r"\s*-\s*", "-", name)
    return re.sub(r"\s+", " ", collapsed_hyphens).strip()


def load_fighter_name_lookups():
    fighters_df = pd.read_csv(FIGHTER_DATA_PATH, usecols=["Fighter", "Fighter_ID"])
    fighters_df["Fighter_ID"] = fighters_df["Fighter_ID"].fillna(0).astype(int)

    fighters_by_id = {}
    fighters_by_lookup_key = {}

    for _, row in fighters_df.iterrows():
        fighter_name = clean_fighter_display_name(row["Fighter"])
        fighter_id = int(row["Fighter_ID"])
        lookup_key = normalize_fighter_lookup_key(fighter_name)

        if fighter_id > 0:
            fighters_by_id[fighter_id] = fighter_name

        if lookup_key:
            fighters_by_lookup_key[lookup_key] = (fighter_name, fighter_id)

    return fighters_by_id, fighters_by_lookup_key


def resolve_upcoming_fighter(name, fighter_id, fighters_by_id, fighters_by_lookup_key):
    cleaned_name = clean_fighter_display_name(name)
    resolved_id = int(fighter_id) if pd.notna(fighter_id) else 0

    if resolved_id > 0 and resolved_id in fighters_by_id:
        return fighters_by_id[resolved_id], resolved_id

    lookup_key = normalize_fighter_lookup_key(cleaned_name)
    if lookup_key in fighters_by_lookup_key:
        return fighters_by_lookup_key[lookup_key]

    return cleaned_name, resolved_id

@app.route('/api/data/upcoming', methods=['GET'])
def get_upcoming_events():
    try:
        # Load the upcoming events CSV file
        upcoming_df = pd.read_csv(UPCOMING_EVENT_DATA_PATH)
        fighters_by_id, fighters_by_lookup_key = load_fighter_name_lookups()
        
        # Group by event name to organize fights under each event
        events = []
        for event_name, group in upcoming_df.groupby('Event Name'):
            first_row = group.iloc[0]
            
            # Get all fights for this event and convert to list
            fights = []
            for _, row in group.iterrows():
                fighter1_name, fighter1_id = resolve_upcoming_fighter(
                    row['Fighter 1'],
                    row.get('Fighter 1 ID', 0),
                    fighters_by_id,
                    fighters_by_lookup_key
                )
                fighter2_name, fighter2_id = resolve_upcoming_fighter(
                    row['Fighter 2'],
                    row.get('Fighter 2 ID', 0),
                    fighters_by_id,
                    fighters_by_lookup_key
                )

                fight = {
                    'fighter1': fighter1_name,
                    'fighter2': fighter2_name,
                    'fighter1ID': fighter1_id,
                    'fighter2ID': fighter2_id,
                    'weightClass': row['Weight Class'],
                    'fightType': row['Fight Type'],
                    'round': None,  # These are upcoming so no result yet
                    'time': None,
                    'winner': None,
                    'method': None
                }
                fights.append(fight)
            
            # Split fights into main card and prelims
            # Main card is last 5 fights (or all if less than 5)
            total_fights = len(fights)
            main_card_size = min(5, total_fights)
            
            # Create the event object with sections for main card and prelims
            event = {
                'eventName': event_name,
                'location': first_row['Event Location'],
                'date': first_row['Event Date'],
                'mainCard': fights[-main_card_size:] if main_card_size > 0 else [],
                'prelims': fights[:-main_card_size] if total_fights > main_card_size else [],
                'allFights': fights  # Keep the full list as well
            }
            
            events.append(event)
            
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error fetching upcoming event data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/odds', methods=['GET'])
def get_odds_chart():
    """Return betting odds movement data for the requested fighter as a list of chart points."""
    fighter_name = request.args.get('fighter', default='', type=str).strip().lower()
    csv_path = ODDS_MOVEMENTS_PATH

    if not os.path.exists(csv_path):
        return jsonify({'error': f'CSV file not found at {csv_path}'}), 500

    try:
        # Read only needed columns for efficiency
        cols = ['file1', 'file2', 'fighter', 'sportsbook', 'odds_before', 'odds_after']
        df = pd.read_csv(csv_path, usecols=cols)

        # Optionally filter by fighter (case-insensitive exact match)
        if fighter_name:
            df = df[df['fighter'].str.lower() == fighter_name]

        # If nothing to return, send empty list so client can show graceful message
        if df.empty:
            return jsonify({'fighter': fighter_name, 'data': []})

        chart_points = []
        for _, row in df.iterrows():
            # Derive a timestamp from the two filenames: 20250511_1646 etc.
            time_stamp = f"{row['file1']}_{row['file2']}"

            def to_int(odds_str):
                try:
                    return int(str(odds_str).replace('+', '').strip())
                except ValueError:
                    return 0

            before = to_int(row['odds_before'])
            after = to_int(row['odds_after'])

            sportsbook = row['sportsbook']

            # Create two points per row to match the iOS chart logic (before and after)
            if before != 0:
                chart_points.append({
                    'timestamp': time_stamp,
                    'odds': before,
                    'sportsbook': sportsbook
                })
            if after != 0:
                chart_points.append({
                    'timestamp': f"{time_stamp}+",  # trailing + indicates post-movement
                    'odds': after,
                    'sportsbook': sportsbook
                })

        # Sort by timestamp for consistency
        chart_points.sort(key=lambda p: p['timestamp'])

        return jsonify({'fighter': fighter_name, 'data': chart_points})
    except Exception as e:
        logger.error(f"Error processing odds data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/odds_last_updated', methods=['GET'])
def get_odds_last_updated():
    csv_path = ODDS_MOVEMENTS_PATH
    if not os.path.exists(csv_path):
        return jsonify({'error': 'CSV file not found'}), 404
    mod_time = os.path.getmtime(csv_path)
    return jsonify({
        'epoch': mod_time,
        'iso': datetime.fromtimestamp(mod_time).isoformat()
    })

@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        with open(NEWS_DAILY_PATH, 'r') as f:
            news_list = json.load(f)
        return jsonify(news_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/news_last_updated', methods=['GET'])
def get_news_last_updated():
    json_path = NEWS_DAILY_PATH
    if not os.path.exists(json_path):
        return jsonify({'error': 'JSON file not found'}), 404
    mod_time = os.path.getmtime(json_path)
    return jsonify({
        'epoch': mod_time,
        'iso': datetime.fromtimestamp(mod_time).isoformat()
    })

if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0', port=5001)
# if __name__ == "__main__":
#     app.run(host="127.0.0.1", port=5001)
