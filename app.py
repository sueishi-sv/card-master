import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image
import pytesseract
import os

# --- ページ設定 ---
st.set_page_config(page_title="My Business Card App", layout="centered")

# --- データベース初期化 ---
def init_db():
    conn = sqlite3.connect('cards.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS companies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cards 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, 
                  person_name TEXT, role TEXT, email TEXT, 
                  FOREIGN KEY(company_id) REFERENCES companies(id))''')
    conn.commit()
    return conn

conn = init_db()

# --- OCR処理関数 ---
def extract_info(image):
    # OCR実行 (日本語と英語に対応)
    text = pytesseract.image_to_string(image, lang='jpn+eng')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 簡易的な抽出ロジック（実際はもっと高度なパースが必要）
    info = {"company": "不明", "name": "不明", "role": "不明"}
    if len(lines) > 0:
        info["company"] = lines[0] # 1行目を会社名と仮定
    if len(lines) > 1:
        info["name"] = lines[1]    # 2行目を氏名と仮定
        
    return info, text

# --- UI構築 ---
st.title("🗂️ 名刺管理アプリ (OSS版)")

tab1, tab2 = st.tabs(["名刺を登録", "会社別一覧"])

with tab1:
    st.header("名刺を撮影")
    # スマホのカメラを起動
    img_file = st.camera_input("カメラで名刺を撮ってください")
    
    if img_file is not None:
        image = Image.open(img_file)
        st.image(image, caption="撮影された画像", use_container_width=True)
        
        with st.spinner('解析中...'):
            info, raw_text = extract_info(image)
        
        st.success("解析完了！内容を確認してください")
        
        # 編集用フォーム
        with st.form("edit_form"):
            company_name = st.text_input("会社名", value=info["company"])
            person_name = st.text_input("氏名", value=info["name"])
            role = st.text_input("役職", value=info["role"])
            
            submitted = st.form_submit_button("データベースに保存")
            if submitted:
                # 会社登録または取得
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO companies (name) VALUES (?)", (company_name,))
                c.execute("SELECT id FROM companies WHERE name = ?", (company_name,))
                company_id = c.fetchone()[0]
                
                # 名刺登録
                c.execute("INSERT INTO cards (company_id, person_name, role) VALUES (?, ?, ?)", 
                          (company_id, person_name, role))
                conn.commit()
                st.balloons()
                st.info(f"{company_name} の {person_name} さんを登録しました。")

with tab2:
    st.header("登録済み名刺")
    
    # データの読み込み
    df = pd.read_sql_query('''
        SELECT c.name as 会社名, p.person_name as 氏名, p.role as 役職
        FROM cards p
        JOIN companies c ON p.company_id = c.id
        ORDER BY c.name
    ''', conn)
    
    if df.empty:
        st.write("まだ名刺が登録されていません。")
    else:
        # 会社ごとにフィルタリングできる機能
        companies = ["すべて"] + list(df["会社名"].unique())
        selected_company = st.selectbox("会社で絞り込む", companies)
        
        if selected_company == "すべて":
            st.dataframe(df, use_container_width=True)
        else:
            filtered_df = df[df["会社名"] == selected_company]
            st.dataframe(filtered_df, use_container_width=True)

# セキュリティ注意喚起
st.sidebar.markdown("---")
st.sidebar.caption("🔒 Security Note")
st.sidebar.caption("このデモではSQLiteを同じサーバーに保存しています。本格運用時はクラウドDBの接続を推奨します。")
