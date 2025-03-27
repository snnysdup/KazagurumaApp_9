import streamlit as st
import openai
import requests
import pandas as pd
import sqlite3
import os

# タイトル
st.title("📚 AIが選ぶ！おすすめ書籍検索")

# APIキーを取得
books_api_key = st.secrets.get("google", {}).get("books_api_key", "")
openai_api_key = st.secrets.get("openai", {}).get("api_key", "")

# APIキーを手動入力できるようにする
books_api_key = st.text_input("Google Books APIキー", value=books_api_key)
openai_api_key = st.text_input("OpenAI APIキー", value=openai_api_key, type="password")

# 検索用の入力フィールド
query = st.text_input("学びたい内容を入力してください")

# 検索結果の数をスライダーで設定
max_results = st.slider("検索結果の数", min_value=1, max_value=20, value=10)

# SQLiteデータベースの作成
DB_PATH = "books.db"

def initialize_db():
    """データベースがない場合は作成する"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                authors TEXT,
                link TEXT,
                image TEXT,
                recommendation TEXT
            )
        """)
        conn.commit()
        conn.close()

initialize_db()  # データベースを初期化

def search_books(api_key, query, max_results=10):
    """Google Books APIで本を検索する関数"""
    if not api_key:
        st.error("❌ Google Books APIキーが設定されていません")
        return []

    if not query:
        st.warning("⚠️ 検索キーワードを入力してください")
        return []

    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"❌ エラー: {response.status_code} - {response.text}")
        return []

def recommend_books_with_chatgpt(api_key, books):
    """ChatGPTを使っておすすめの3冊を選ぶ"""
    if not api_key:
        st.error("❌ OpenAI APIキーが設定されていません")
        return []
    
    if not books:
        st.warning("⚠️ 本のリストがありません")
        return []

    book_descriptions = "\n".join(
        [f"{i+1}. {b['volumeInfo'].get('title', '不明')} - {', '.join(b['volumeInfo'].get('authors', ['不明']))}" for i, b in enumerate(books)]
    )

    prompt = f"""
    以下は本のリストです。あなたは読書アドバイザーとして、学びの目的に最適な3冊を選び、その理由を教えてください。
    {book_descriptions}
    
    選んだ本のタイトルとその推薦理由を出力してください。
    """

    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "あなたは読書の専門家です。"},
                  {"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]

def save_book_to_db(title, authors, link, image, recommendation):
    """本をデータベースに保存（重複チェックあり）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # すでに同じ本が登録されているかチェック
    cursor.execute("SELECT id FROM books WHERE title = ?", (title,))
    existing_book = cursor.fetchone()

    if existing_book is None:
        cursor.execute("""
            INSERT INTO books (title, authors, link, image, recommendation)
            VALUES (?, ?, ?, ?, ?)
        """, (title, authors, link, image, recommendation))
        conn.commit()
        st.success(f"✅ 『{title}』を保存しました！")
    else:
        st.warning(f"⚠️ 『{title}』はすでに登録済みです。")

    conn.close()

def get_saved_books():
    """データベースから保存された本を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, authors, link, image, recommendation FROM books")
    books = cursor.fetchall()
    conn.close()
    return books

# 検索ボタン
if st.button("🔍 検索") and books_api_key and query:
    books = search_books(books_api_key, query, max_results)
    
    if books:
        st.subheader("📖 検索結果")
        for book in books:
            title = book["volumeInfo"].get("title", "タイトル不明")
            authors = book["volumeInfo"].get("authors", ["不明"])
            thumbnail = book["volumeInfo"].get("imageLinks", {}).get("thumbnail", "")
            info_link = book["volumeInfo"].get("infoLink", "#")

            with st.container():
                st.markdown(f"### [{title}]({info_link})")
                st.write(f"著者: {', '.join(authors)}")
                if thumbnail:
                    st.image(thumbnail, width=150)
                st.write("---")
        
        # ChatGPT のおすすめ機能
        if st.button("🤖 ChatGPTのおすすめ"):
            st.subheader("✨ ChatGPTのおすすめ")
            recommended_text = recommend_books_with_chatgpt(openai_api_key, books)
            st.write(recommended_text)

            # 「読みたい」ボタンで保存
            for book in books:
                title = book["volumeInfo"].get("title", "タイトル不明")
                authors = book["volumeInfo"].get("authors", ["不明"])
                thumbnail = book["volumeInfo"].get("imageLinks", {}).get("thumbnail", "")
                info_link = book["volumeInfo"].get("infoLink", "#")

                if st.button(f"📌 『{title}』を読みたい"):
                    save_book_to_db(title, ", ".join(authors), info_link, thumbnail, recommended_text)

# 保存された本の一覧を表示
saved_books = get_saved_books()
if saved_books:
    st.subheader("📚 読みたい本リスト")
    df = pd.DataFrame(saved_books, columns=["タイトル", "著者", "リンク", "画像", "推薦理由"])
    st.table(df)
