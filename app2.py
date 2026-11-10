import streamlit as st
import json
import os
from supabase import create_client, Client

st.set_page_config(page_title="後台管理 | 雲林美食地圖", page_icon="⚙️", layout="wide")

# --- 初始化 Supabase 連線 ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# 載入雲端店家資料
def load_stores():
    try:
        response = supabase.table("stores").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"讀取雲端資料庫失敗: {e}")
        return []

stores_data = load_stores()

# --- CSS 視覺風格一致化 ---
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: #f7dad2;
    }}
    [data-testid="stSidebar"] {{
        background-color: #d8af9c;
    }}
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        color: #803c34 !important;
    }}
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div {{
        color: #803c34 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

TAGS_FILE = "tags.json"
def load_tags(file_path, default_value):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_value

default_tags = {
    "district": ["虎尾", "斗六", "其他雲林鄉鎮", "外縣市"],
    "category": ["正餐", "小吃", "甜點", "咖啡", "飲品"],
    "type": ["聚餐", "約會", "放鬆"],
    "tier": ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]
}
tags_data = load_tags(TAGS_FILE, default_tags)

st.title("⚙️ 雲林美食地圖 - 後台管理系統")
st.markdown("在這裡新增、編輯或刪除地圖上的店家資料，變更將直接儲存至雲端資料庫。")

tab1, tab2 = st.tabs(["➕ 新增店家", "📋 管理現有店家"])

# --- 標籤 1：新增店家 ---
with tab1:
    st.subheader("新增一間精選店家")
    
    with st.form("add_store_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("店家名稱 *")
            subtitle = st.text_input("副標說明（例如：高分居酒屋）")
            district = st.selectbox("地區 *", tags_data.get("district", ["虎尾", "斗六"]))
            category = st.multiselect("料理類別 *", tags_data.get("category", ["正餐", "小吃", "甜點"]))
            types = st.multiselect("空間/氛圍類型", tags_data.get("type", ["聚餐", "約會", "放鬆"]))
            tier = st.selectbox("推薦等級 *", tags_data.get("tier", ["IG REELS拍攝店家"]))
            
        with col2:
            price_range = st.text_input("消費均消（例如：300-600）")
            lat = st.number_input("緯度 (Latitude) *", value=23.7080, format="%.6f")
            lon = st.number_input("經度 (Longitude) *", value=120.4312, format="%.6f")
            ig_url = st.text_input("IG 介紹連結 (URL)")
            map_url = st.text_input("Google 導航連結 (URL)")
            
        description = st.text_area("店家詳細介紹 (點擊卡片時顯示)")
        
        submitted = st.form_submit_button("🚀 確認送出並新增")
        
        if submitted:
            if not name:
                st.error("❌ 店家名稱為必填欄位！")
            else:
                new_store = {
                    "name": name,
                    "subtitle": subtitle,
                    "description": description,
                    "price_range": price_range,
                    "district": district,
                    "category": category,
                    "types": types,
                    "tier": tier,
                    "ig_url": ig_url,
                    "map_url": map_url,
                    "lat": float(lat),
                    "lon": float(lon)
                }
                
                try:
                    # 寫入 Supabase 雲端資料庫
                    supabase.table("stores").insert(new_store).execute()
                    st.success(f"🎉 成功新增店家：【{name}】！資料已同步至雲端。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗，發生錯誤：{e}")

# --- 標籤 2：管理現有店家 ---
with tab2:
    st.subheader("檢視與刪除店家")
    
    if not stores_data:
        st.info("目前雲端資料庫沒有任何店家。")
    else:
        store_names = [s.get("name") for s in stores_data]
        store_to_delete = st.selectbox("選擇要刪除的店家", store_names)
        
        if st.button("🗑️ 確定刪除此店家", type="primary"):
            try:
                # 從 Supabase 雲端資料庫刪除
                supabase.table("stores").delete().eq("name", store_to_delete).execute()
                st.success(f"🗑️ 已經成功刪除店家：{store_to_delete}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 刪除失敗：{e}")
                
        st.markdown("---")
        st.markdown("### 現有店家列表預覽")
        for s in stores_data:
            st.markdown(f"- **{s.get('name')}** ({s.get('district')} / {s.get('tier')})")
