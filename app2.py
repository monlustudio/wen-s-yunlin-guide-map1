import streamlit as st
import pandas as pd
import json
import os
import re
import requests
import time
from supabase import create_client, Client

st.set_page_config(page_title="雲林美食後台管理系統", page_icon="🛠️", layout="wide")

# --- 初始化 Supabase 連線 ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 載入與儲存標籤（tags.json 維持本地或可依需求調整） ---
TAGS_FILE = "tags.json"

def load_json(file_path, default_value):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_value

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 從 Supabase 載入店家資料
def load_stores():
    try:
        response = supabase.table("stores").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"讀取雲端資料庫失敗: {e}")
        return []

stores_data = load_stores()

# --- Google Maps 網址解析 ---
def extract_lat_lon_from_url(url):
    if not url:
        return None, None
    try:
        if "goo.gl" in url or "maps.app.goo.gl" in url:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
            url = response.url

        match_3d4d = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
        if match_3d4d:
            return float(match_3d4d.group(1)), float(match_3d4d.group(2))
            
        match_at = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
        if match_at:
            return float(match_at.group(1)), float(match_at.group(2))
            
    except Exception as e:
        print(f"解析網址發生錯誤: {e}")
        
    return None, None

default_tags = {
    "district": ["虎尾", "斗六", "其他雲林鄉鎮", "外縣市"],
    "category": ["正餐", "小吃", "甜點", "咖啡", "飲品"],
    "type": ["聚餐", "約會", "放鬆"],
    "tier": ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]
}

tags_data = load_json(TAGS_FILE, default_tags)

if "tier" not in tags_data or not set(["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]).issubset(set(tags_data["tier"])):
    tags_data["tier"] = ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]
    save_json(TAGS_FILE, tags_data)

if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0

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

st.title("🛠️ 雲林美食後台管理系統")
st.markdown("管理所有店家資料與標籤分類（資料將直接同步至 Supabase 雲端資料庫）。")

tab1, tab2, tab3 = st.tabs(["➕ 新增店家", "📋 店家管理 (編輯/刪除)", "🏷️ 標籤管理"])

# ==========================================
# 頁面一：新增店家
# ==========================================
with tab1:
    st.subheader("新增一筆美食店家")
    st.markdown("🔴 標註 **(必填)** 為必要欄位，餐廳類型與空間類型均可**複選**。")
    
    form_key = f"add_store_form_{st.session_state['form_version']}"
    
    with st.form(form_key):
        name = st.text_input("店家名稱 (必填) *", placeholder="例：春山里舍")
        subtitle = st.text_input("副標 / 短評 (必填) *", placeholder="例：優雅老宅茶館")
        description = st.text_area("詳細介紹文案 (支援換行)", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            district = st.selectbox("地區 / 行政區 (必填) *", tags_data.get("district", ["虎尾", "斗六"]))
            category = st.multiselect("料理類別 (可複選)", tags_data.get("category", ["正餐", "小吃", "甜點", "咖啡", "飲品"]), default=["正餐"])
            store_types = st.multiselect("空間/氛圍類型 (可複選)", tags_data.get("type", ["聚餐", "約會", "放鬆"]))
            
        with col2:
            tier = st.selectbox("推薦等級", tags_data.get("tier", ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]))
            price_range = st.text_input("消費均消", placeholder="例：$200~$400/人")

        st.markdown("---")
        st.subheader("📍 網路連結與座標設定")
        
        ig_url = st.text_input("Instagram 連結 (URL)", placeholder="https://instagram.com/...")
        map_url = st.text_input("Google Maps 連結 / 地點網址 (必填) *", placeholder="https://maps.app.goo.gl/... 或包含 !3d...!4d 的網址")
        
        st.markdown("")
        submitted = st.form_submit_button("🚀 確認無誤，送出建立店家", type="primary", use_container_width=True)
        
        if submitted:
            missing_fields = []
            if not name or name.strip() == "":
                missing_fields.append("店名")
            if not subtitle or subtitle.strip() == "":
                missing_fields.append("副標")
            if not district or district.strip() == "":
                missing_fields.append("地區")
            if not map_url or map_url.strip() == "":
                missing_fields.append("Google Maps 連結")

            if missing_fields:
                st.error(f"❌ 建立失敗：缺少以下必填項目：**{', '.join(missing_fields)}**")
            else:
                f_lat, f_lon = extract_lat_lon_from_url(map_url)
                
                if not f_lat or not f_lon:
                    st.error("❌ 建立失敗：無法從 Google Maps 網址中解析出精準座標！")
                else:
                    new_store = {
                        "name": name,
                        "subtitle": subtitle,
                        "description": description,
                        "price_range": price_range,
                        "district": district,
                        "category": category,
                        "types": store_types,
                        "tier": tier,
                        "ig_url": ig_url,
                        "map_url": map_url,
                        "lat": float(f_lat),
                        "lon": float(f_lon)
                    }
                    
                    try:
                        # 寫入 Supabase
                        supabase.table("stores").insert(new_store).execute()
                        st.success(f"🎉 建立成功！已成功新增店家：{name}")
                        st.balloons()
                        
                        st.session_state["form_version"] += 1
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 寫入雲端資料庫失敗: {e}")

# ==========================================
# 頁面二：店家管理（編輯 / 刪除）
# ==========================================
with tab2:
    st.subheader("📋 現有店家列表與管理")
    
    if not stores_data:
        st.info("目前雲端尚無任何店家資料。")
    else:
        store_names = [s["name"] for s in stores_data]
        selected_store_name = st.selectbox("選擇要管理的店家", store_names, key="manage_select_store")
        
        store = next((s for s in stores_data if s["name"] == selected_store_name), None)
        
        if store:
            st.markdown(f"---")
            st.markdown(f"**正在編輯店家：** `{store['name']}`")
            
            e_name = st.text_input("店家名稱", value=store.get("name", ""), key=f"edit_name_{selected_store_name}")
            e_subtitle = st.text_input("副標 / 短評", value=store.get("subtitle", ""), key=f"edit_sub_{selected_store_name}")
            e_description = st.text_area("詳細介紹文案", value=store.get("description", ""), height=100, key=f"edit_desc_{selected_store_name}")
            
            col1, col2 = st.columns(2)
            with col1:
                dist_list = tags_data.get("district", [])
                d_idx = dist_list.index(store.get("district")) if store.get("district") in dist_list else 0
                e_district = st.selectbox("行政區", dist_list, index=d_idx, key=f"edit_dist_{selected_store_name}")
                
                cat_list = tags_data.get("category", [])
                old_cat = store.get("category", "正餐")
                default_cats = old_cat if isinstance(old_cat, list) else [old_cat]
                valid_default_cats = [c for c in default_cats if c in cat_list]
                e_category = st.multiselect("料理類別 (可複選)", cat_list, default=valid_default_cats, key=f"edit_cat_{selected_store_name}")
                
                type_list = tags_data.get("type", [])
                default_types = store.get("types", [])
                valid_default_types = [t for t in default_types if t in type_list]
                e_types = st.multiselect("空間/氛圍類型 (可複選)", type_list, default=valid_default_types, key=f"edit_types_{selected_store_name}")
            with col2:
                tier_list = tags_data.get("tier", [])
                current_tier = store.get("tier")
                t_idx = tier_list.index(current_tier) if current_tier in tier_list else 0
                e_tier = st.selectbox("推薦等級", tier_list, index=t_idx, key=f"edit_tier_{selected_store_name}")
                
                e_price_range = st.text_input("消費均消", value=store.get("price_range", ""), key=f"edit_price_{selected_store_name}")
            
            e_ig_url = st.text_input("Instagram 連結", value=store.get("ig_url", ""), key=f"edit_ig_{selected_store_name}")
            e_map_url = st.text_input("Google Maps 連結", value=store.get("map_url", ""), key=f"edit_map_{selected_store_name}")
            
            col_update, col_delete = st.columns(2)
            
            if col_update.button("💾 儲存修改", use_container_width=True, key=f"update_btn_{selected_store_name}"):
                new_lat, new_lon = store.get("lat"), store.get("lon")
                if e_map_url:
                    f_lat, f_lon = extract_lat_lon_from_url(e_map_url)
                    if f_lat and f_lon:
                        new_lat, new_lon = f_lat, f_lon

                updated_store_dict = {
                    "name": e_name,
                    "subtitle": e_subtitle,
                    "description": e_description,
                    "price_range": e_price_range,
                    "district": e_district,
                    "category": e_category,
                    "types": e_types,
                    "tier": e_tier,
                    "ig_url": e_ig_url,
                    "map_url": e_map_url,
                    "lat": float(new_lat),
                    "lon": float(new_lon)
                }
                
                try:
                    # 依據原本的 name 當作條件更新 Supabase 資料
                    supabase.table("stores").update(updated_store_dict).eq("name", selected_store_name).execute()
                    st.success(f"✅ 店家「{e_name}」更新成功！")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗: {e}")
                    
            # --- 安全確認刪除彈出視窗 (st.dialog) ---
            @st.dialog("⚠️ 確認刪除")
            def confirm_delete_dialog(s_name):
                st.markdown(f"你確定要永久刪除雲端資料庫中的店家 **「{s_name}」** 嗎？此動作無法復原。")
                c1, c2 = st.columns(2)
                if c1.button("🗑️ 是，確定刪除", type="primary", use_container_width=True):
                    try:
                        supabase.table("stores").delete().eq("name", s_name).execute()
                        st.success(f"🗑️ 已成功刪除店家：{s_name}")
                        time.sleep(1.0)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 刪除失敗: {e}")
                if c2.button("❌ 取消", use_container_width=True):
                    st.rerun()

            if col_delete.button("🗑️ 刪除此店家", type="secondary", use_container_width=True, key=f"delete_btn_{selected_store_name}"):
                confirm_delete_dialog(selected_store_name)

# ==========================================
# 頁面三：標籤管理（新增 / 刪除）
# ==========================================
with tab3:
    st.subheader("🏷️ 篩選標籤管理")
    
    tag_category_map = {
        "行政區 (district)": "district",
        "料理類別 (category)": "category",
        "類型 (type)": "type",
        "推薦等級 (tier)": "tier"
    }
    
    selected_tag_type_label = st.selectbox("選擇要管理的標籤種類", list(tag_category_map.keys()))
    tag_key = tag_category_map[selected_tag_type_label]
    
    current_tags = tags_data.get(tag_key, [])
    
    st.write(f"目前現有的標籤：`{current_tags}`")
    
    new_tag_name = st.text_input("新增標籤名稱", placeholder="例：早午餐", key="new_tag_input")
    if st.button("➕ 新增此標籤"):
        if new_tag_name and new_tag_name not in current_tags:
            current_tags.append(new_tag_name)
            tags_data[tag_key] = current_tags
            save_json(TAGS_FILE, tags_data)
            st.success(f"🎉 成功新增標籤：{new_tag_name}")
            st.rerun()
        else:
            st.warning("⚠️ 標籤名稱不可為空或已存在！")
            
    st.markdown("---")
    
    tag_to_delete = st.selectbox("選擇要刪除的標籤", current_tags, key="del_tag_select")
    if st.button("🗑️ 刪除選中的標籤", type="primary"):
        if len(current_tags) <= 1:
            st.error("⚠️ 每個分類至少要保留一個標籤！")
        else:
            current_tags.remove(tag_to_delete)
            tags_data[tag_key] = current_tags
            save_json(TAGS_FILE, tags_data)
            st.success(f"🗑️ 成功刪除標籤：{tag_to_delete}")
            st.rerun()
