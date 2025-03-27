import datetime
import pandas as pd
import requests
import streamlit as st
import openai  # OpenAIのAPIを扱うためのライブラリをインポート

# OpenAIクライアントの初期化
client = openai.OpenAI(api_key=st.secrets["GPTAPI"].get("OPENAI_API_KEY"))

# Google Books APIキーの取得
books_api_key = st.secrets["google"]["books_api_key"]
# st.write(st.secrets)  # secretsの中身を確認
# books_api_key = st.secrets["google"]["books_api_key"]


# タイトル
st.title('📚 学びたい内容に合った本をおすすめ！')

# サイドバーでユーザー入力を取得
content_text_to_gpt = st.sidebar.text_input("🔍 学びたい内容を入力してください（例: Python, 心理学）")
content_current_to_gpt = st.sidebar.text_input("上記入力した学びに対してのあなたの理解度を教えてください（例：初学者、業務で使用している）")
content_goal_to_gpt = st.sidebar.text_input("上記入力した学びに対してのあなたがどの程度理解を深めたいか教えてください（例：業務で使えるレベル）")
content_others_to_gpt = st.sidebar.text_input("その他本の選定にあたり考慮して欲しい事項を記載してください（例：英語の本は除く、なるべく分かりやすい本、短い時間で読める本）")

# Google Books APIを使用して書籍を検索する関数
def search_books(query, books_api_key, max_results=5):
    base_url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": max_results,
        "printType": "books",
        "key": books_api_key
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # ← エラーがあれば例外を発生させる
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Google Books APIのリクエスト中にエラーが発生しました: {str(e)}")
        return []


# 生成AIを使用して推薦理由を生成する関数
def generate_recommendation_reason(book_title, content_text, content_current, content_goal, content_others):
    prompt = f"""
    ユーザーは「{content_text}」について学びたいと考えています。
    現在の理解度: {content_current}
    目標とする理解度: {content_goal}
    その他の考慮事項: {content_others}

    以下の書籍が推薦されています:
    書籍タイトル: {book_title}

    なぜこの書籍がユーザーにとって適切なのか、簡潔に説明してください。
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"生成AIからの推薦理由の生成中にエラーが発生しました: {str(e)}")
        return "推薦理由を生成できませんでした。"

# 検索ボタンが押された場合の処理
if st.sidebar.button("本を探す！"):
    if content_text_to_gpt:
        books = search_books(content_text_to_gpt, books_api_key)
        if books:
            st.subheader(f"🔎『{content_text_to_gpt}』に関するおすすめの本：")
            for book in books:
                volume_info = book.get("volumeInfo", {})
                title = volume_info.get("title", "タイトル不明")
                authors = ", ".join(volume_info.get("authors", ["著者不明"]))
                description = volume_info.get("description", "説明がありません")
                thumbnail = volume_info.get("imageLinks", {}).get("thumbnail", "")
                info_link = volume_info.get("infoLink", "#")

                st.markdown("---")
                st.subheader(f"📖 [{title}]({info_link})")
                st.write(f"**著者:** {authors}")
                st.write(f"**説明:** {description}")
                if thumbnail:
                    st.image(thumbnail, width=120)

                # 推薦理由の生成
                recommendation_reason = generate_recommendation_reason(title, content_text_to_gpt, content_current_to_gpt, content_goal_to_gpt, content_others_to_gpt)
                st.write(f"**推薦理由:** {recommendation_reason}")
        else:
            st.warning("❌ 該当する本が見つかりませんでした。別のキーワードを試してください。")
    else:
        st.info("🔍 検索ワードを入力してください。")
