import streamlit as st
import pandas as pd
import json
import os
import random
import time
import folium
from streamlit_folium import st_folium

# 設定頁面佈局為寬螢幕
st.set_page_config(page_title="雲林美食地圖 | Monlu Studio", page_icon="☁️", layout="wide")

# --- CSS 注入：自訂背景色、字體顏色、手機版主標題微調、頂部切齊與加大圓角卡片 ---
st.markdown(
    f"""
    <style>
    /* 全局背景色 */
    .stApp {{
        background-color: #e3bdaf;
    }}
    /* 側邊欄背景色 */
    [data-testid="stSidebar"] {{
        background-color: #d8af9c;
    }}
    /* 所有標題、文字、Markdown 預設字體顏色 */
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        color: #803c34 !important;
    }}
    /* 側邊欄文字顏色 */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div {{
        color: #803c34 !important;
    }}
    /* 側邊欄多選框 (multiselect) 已選取的標籤底色改為 #deb37f，文字維持 #803c34 */
    [data-testid="stSidebar"] span[data-baseweb="tag"] {{
        background-color: #deb37f !important;
    }}
    [data-testid="stSidebar"] span[data-baseweb="tag"] span {{
        color: #803c34 !important;
    }}

    /* 🎲 自訂淡金色抽卡按鈕樣式 */
    div.stButton > button[kind="secondary"], div.stButton > button {{
        background-color: #decfbd !important;
        color: #803c34 !important;
        border: 1.5px solid #803c34 !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }}
    div.stButton > button:hover {{
        background-color: #d2c0ab !important;
        color: #803c34 !important;
        border-color: #803c34 !important;
    }}

    /* 📱 手機版主標題優化：字體放大，確保單行顯示不換行 */
    h1 {{
        font-size: 7.5vw !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 0.2rem !important;
    }}
    @media (min-width: 768px) {{
        h1 {{
            font-size: 2.2rem !important;
        }}
    }}

    /* 🖥️ 電腦版：讓右側「店家清單」的頂部與左側地圖完美切齊 */
    @media (min-width: 768px) {{
        div.block-container {{
            padding-top: 2rem;
        }}
        div[data-testid="column"]:nth-of-type(2) {{
            margin-top: -38px;
        }}
    }}

    /* 📱 手機版響應式設定：當螢幕寬度小於 768px 時，強制縮小地圖容器高度約 1/3 螢幕 (約 300px) */
    @media (max-width: 768px) {{
        iframe[title="streamlit_folium.st_folium"] {{
            height: 300px !important;
        }}
        div[data-testid="stIFrame"] {{
            height: 300px !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)

DATA_FILE = "stores.json"
TAGS_FILE = "tags.json"

# --- 輔助函數：讀取資料並自動依店名去重 ---
def load_json(file_path, default_value):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if file_path == DATA_FILE and isinstance(data, list):
                unique_stores = {}
                for store in data:
                    name = store.get("name")
                    if name:
                        unique_stores[name] = store
                return list(unique_stores.values())
            return data
    except:
        return default_value

stores_data = load_json(DATA_FILE, [])
default_tags = {
    "district": ["虎尾", "斗六", "其他雲林鄉鎮", "外縣市"],
    "category": ["正餐", "小吃", "甜點", "咖啡", "飲品"],
    "type": ["聚餐", "約會", "放鬆"],
    "tier": ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"]
}
tags_data = load_json(TAGS_FILE, default_tags)

# ==========================================
# 🎲 隨機抽卡對話框設計（內含吃角子老虎機緩速漸停特效）
# ==========================================
@st.dialog("🎲 今天去哪兒？私藏行程盲盒")
def random_draw_dialog(stores, tags):
    st.markdown("不知道今天該去哪裡嗎？讓隨機抽卡幫你決定靈感！")
    
    # 1. 選擇地區
    dist_options = ["全雲林"] + tags.get("district", ["虎尾", "斗六"])
    draw_district = st.selectbox("📍 選擇想去的地區", dist_options, key="draw_dist")
    
    # 2. 選擇空間/氛圍類型
    type_options = ["不限"] + tags.get("type", ["聚餐", "約會", "放鬆"])
    draw_type = st.selectbox("🏷️ 選擇空間或氛圍類型", type_options, key="draw_type")
    
    # 3. 選擇價位範圍
    price_options = ["不限", "$ 經濟平價 (200元以下)", "$$ 中等消費 (200~500元)", "$$$ 精緻質感 (500元以上)"]
    draw_price = st.selectbox("💰 選擇消費均消偏好", price_options, key="draw_price")
    
    st.markdown("---")
    
    if st.button("🚀 開始抽卡！幫我決定", type="primary", use_container_width=True):
        # 篩選符合條件的店家池
        pool = stores
        if draw_district != "全雲林":
            pool = [s for s in pool if s.get("district") == draw_district]
            
        if draw_type != "不限":
            pool = [s for s in pool if draw_type in s.get("types", [])]
            
        if draw_price != "不限":
            if "經濟平價" in draw_price:
                pool = [s for s in pool if any(c in s.get("price_range", "") for c in ["1", "2", "百", "平", "50", "70", "100"])]
            elif "精緻質感" in draw_price:
                pool = [s for s in pool if any(c in s.get("price_range", "") for c in ["5", "6", "7", "8", "9", "千", "1000"])]

        if not pool:
            st.warning("⚠️ 找不到符合條件的店家耶！放寬條件再抽一次看看吧～")
        else:
            # 🎰 模擬吃角子老虎機特效：前快後慢（漸歇減速機制）
            slot_placeholder = st.empty()
            all_names = [s.get("name") for s in stores]
            
            # 設定遞增延遲時間清單（愈後面間隔愈大，營造煞車緩速感）
            delays = [0.03, 0.04, 0.05, 0.07, 0.10, 0.14, 0.19, 0.25, 0.32, 0.40]
            
            for d in delays:
                temp_name = random.choice(all_names)
                slot_placeholder.markdown(
                    f"""
                    <div style="
                        text-align: center;
                        background-color: #decfbd;
                        border: 2px dashed #803c34;
                        border-radius: 12px;
                        padding: 16px;
                        margin: 10px 0;
                    ">
                        <h2 style="margin: 0; color: #803c34; font-size: 22px;">🎰 拉霸抽籤中...</h2>
                        <p style="margin: 8px 0 0 0; font-size: 20px; font-weight: bold; color: #b62524;">✨ {temp_name} ✨</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(d)
            
            slot_placeholder.empty()
            
            # 隨機抽出一張最終店家
            chosen = random.choice(pool)
            st.success(f"🎉 抽中啦！為您推薦：**{chosen.get('name')}**")
            
            tier = chosen.get("tier", "")
            if "IG REELS" in tier:
                c_bg, c_border = "rgba(182, 37, 36, 0.22)", "#b62524"
            elif "LINE社群" in tier:
                c_bg, c_border = "rgba(185, 121, 38, 0.22)", "#b97926"
            else:
                c_bg, c_border = "rgba(204, 165, 155, 0.35)", "#cca59b"
                
            c_name = chosen.get('name', '')
            c_sub = chosen.get('subtitle', '')
            c_title = f"{c_name} <span style='font-size: 14.5px; font-weight: normal; color: #803c34;'>| {c_sub}</span>" if c_sub else c_name
            
            card_box = f"""
            <div style="
                background-color: {c_bg};
                border: 1.5px solid {c_border};
                border-radius: 14px;
                padding: 12px 14px;
                margin-top: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            ">
                <h3 style="margin: 0 0 6px 0; font-size: 17px; color: #803c34;">{c_title}</h3>
            """
            if chosen.get("description"):
                card_box += f"<p style='margin: 0 0 6px 0; font-size: 12px; color: #803c34; line-height: 1.3;'>{chosen.get('description')}</p>"
                
            c_cat = chosen.get("category", "")
            c_cat_str = ", ".join(c_cat) if isinstance(c_cat, list) else c_cat
            tags_h = f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; border: 1px solid #803c34;'>📍 {chosen.get('district')}</span> "
            tags_h += f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; border: 1px solid #803c34;'>🍽️ {c_cat_str}</span> "
            for t in chosen.get("types", []):
                tags_h += f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; border: 1px solid #803c34;'>🏷️ {t}</span> "
            card_box += f"<div style='margin-bottom: 6px;'>{tags_h}</div>"
            
            if chosen.get("price_range"):
                card_box += f"<p style='margin: 0 0 6px 0; font-size: 12px; color: #803c34;'>💰 消費均消：{chosen.get('price_range')}</p>"
                
            btn_h = "<div style='display: flex; gap: 6px; margin-top: 8px;'>"
            if chosen.get("ig_url"):
                btn_h += f"<a href='{chosen.get('ig_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 5px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>📸 IG 介紹</a>"
            if chosen.get("map_url"):
                btn_h += f"<a href='{chosen.get('map_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 5px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_h += "</div></div>"
            
            st.markdown(card_box + btn_h, unsafe_allow_html=True)


# --- 側邊欄：進階篩選器 ---
st.sidebar.header("🔍 雲林美食探索")
st.sidebar.markdown("尋找在地私藏好味道與拍攝空間。")

district_options = ["全雲林"] + tags_data.get("district", ["虎尾", "斗六"])
selected_district = st.sidebar.selectbox("📍 選擇地區", district_options)

category_options = ["不指定"] + tags_data.get("category", ["正餐", "小吃", "甜點", "咖啡", "飲品"])
selected_category = st.sidebar.selectbox("🍽️ 料理類別", category_options)

type_options = ["不指定"] + tags_data.get("type", ["聚餐", "約會", "放鬆"])
selected_types = st.sidebar.multiselect("🏷️ 空間/氛圍類型 (可複選)", type_options, default=["不指定"])

tier_options = tags_data.get("tier", ["IG REELS拍攝店家", "LINE社群 上榜名單", "WEN日常美食推薦"])
selected_tiers = st.sidebar.multiselect("⭐ 推薦等級 (可複選)", tier_options, default=tier_options)

# 🎲 將「今天去哪兒」抽卡按鈕放置於側邊欄的最下方
st.sidebar.markdown("---")
if st.sidebar.button("今天去哪兒？", use_container_width=True):
    random_draw_dialog(stores_data, tags_data)

# --- 過濾資料邏輯 ---
filtered_stores = stores_data

if selected_district != "全雲林":
    filtered_stores = [s for s in filtered_stores if s.get("district") == selected_district]

if selected_category != "不指定":
    filtered_stores = [
        s for s in filtered_stores 
        if (isinstance(s.get("category"), list) and selected_category in s.get("category")) or 
           (not isinstance(s.get("category"), list) and s.get("category") == selected_category)
    ]

if "不指定" not in selected_types and len(selected_types) > 0:
    filtered_stores = [
        s for s in filtered_stores 
        if any(t in s.get("types", []) for t in selected_types)
    ]

if selected_tiers:
    filtered_stores = [s for s in filtered_stores if s.get("tier") in selected_tiers]

# --- 主畫面佈局 ---
st.title("Wen's life 雲林美食地圖")

if not filtered_stores:
    st.info("💡 目前沒有符合篩選條件的店家，請嘗試調整側邊欄的篩選條件。")
else:
    map_col, list_col = st.columns([1.2, 1])

    with map_col:
        lats = [s.get("lat", 23.708) for s in filtered_stores]
        lons = [s.get("lon", 120.431) for s in filtered_stores]
        center_lat = sum(lats) / len(lats) if lats else 23.7080
        center_lon = sum(lons) / len(lons) if lons else 120.4312

        m = folium.Map(
            location=[center_lat, center_lon], 
            zoom_start=13,
            tiles="OpenStreetMap"
        )

        for store in filtered_stores:
            lat = store.get("lat")
            lon = store.get("lon")
            name = store.get("name", "")
            subtitle = store.get("subtitle", "")
            tier = store.get("tier", "")
            district = store.get("district", "")
            
            cat_val = store.get("category", "")
            cat_str = ", ".join(cat_val) if isinstance(cat_val, list) else cat_val
            
            types = ", ".join(store.get("types", [])) if store.get("types") else "無"
            price = store.get("price_range", "未標註")
            
            if "IG REELS" in tier:
                tag_color = "#b62524"
            elif "LINE社群" in tier:
                tag_color = "#b97926"
            else:
                tag_color = "#803c34"

            html_label = f"""
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                transform: translate(-50%, -100%);
                pointer-events: none;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            ">
                <div style="
                    background-color: #decfbd;
                    color: {tag_color};
                    font-weight: bold;
                    font-size: 12px;
                    padding: 4px 10px;
                    border: 1.5px solid {tag_color};
                    border-radius: 12px;
                    white-space: nowrap;
                    box-shadow: 0 3px 8px rgba(0,0,0,0.15);
                    margin-bottom: 6px;
                ">
                    {name}
                </div>
                <div style="
                    width: 14px;
                    height: 14px;
                    background-color: {tag_color};
                    border: 2px solid #ffffff;
                    border-radius: 50%;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                "></div>
            </div>
            """

            popup_html = f"""
            <div style="color: #803c34; font-family: sans-serif; min-width: 180px; padding: 4px;">
                <h4 style="margin: 0 0 6px 0; color: #803c34; font-size: 15px;">【 {name} 】</h4>
                <p style="margin: 4px 0; font-size: 13px;"><b>副標：</b>{subtitle}</p>
                <p style="margin: 4px 0; font-size: 13px;"><b>等級：</b>{tier}</p>
                <p style="margin: 4px 0; font-size: 13px;"><b>地區：</b>{district} | <b>類別：</b>{cat_str}</p>
                <p style="margin: 4px 0; font-size: 13px;"><b>類型：</b>{types}</p>
                <p style="margin: 4px 0; font-size: 13px;"><b>均消：</b>{price}</p>
            </div>
            """

            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(html=html_label),
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(m)

        st_folium(m, width=None, height=550, use_container_width=True)
        
        st.markdown(f"📍 目前為您篩選出 **{len(filtered_stores)}** 間精選店家：")

    with list_col:
        st.subheader("📋 店家清單")
        
        for store in filtered_stores:
            tier = store.get("tier", "")
            if "IG REELS" in tier:
                card_bg = "rgba(182, 37, 36, 0.22)"
                card_border = "#b62524"
            elif "LINE社群" in tier:
                card_bg = "rgba(185, 121, 38, 0.22)"
                card_border = "#b97926"
            else:
                card_bg = "rgba(204, 165, 155, 0.35)"
                card_border = "#cca59b"

            store_name = store.get('name', '')
            store_sub = store.get('subtitle', '')
            title_display = f"{store_name} <span style='font-size: 14.5px; font-weight: normal; color: #803c34;'>| {store_sub}</span>" if store_sub else store_name

            card_html = f"""
            <div style="
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-radius: 14px;
                padding: 10px 12px;
                margin-bottom: 10px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            ">
                <h3 style="margin: 0 0 6px 0; font-size: 16px; color: #803c34;">{title_display}</h3>
            """
            
            if store.get("description"):
                card_html += f"<p style='margin: 0 0 6px 0; font-size: 12px; color: #803c34; line-height: 1.3;'>{store.get('description')}</p>"
            
            cat_val = store.get("category", "")
            cat_display = ", ".join(cat_val) if isinstance(cat_val, list) else cat_val
            
            tags_html = f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; border: 1px solid #803c34;'>📍 {store.get('district')}</span> "
            tags_html += f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; border: 1px solid #803c34;'>🍽️ {cat_display}</span> "
            
            store_types = store.get("types", [])
            for t in store_types:
                tags_html += f"<span style='background-color:#decfbd; color:#803c34; padding:2px 6px; border-radius:4px; font-size:11px; border: 1px solid #803c34;'>🏷️ {t}</span> "
            
            card_html += f"<div style='margin-bottom: 6px;'>{tags_html}</div>"
            
            if store.get("price_range"):
                card_html += f"<p style='margin: 0 0 6px 0; font-size: 12px; color: #803c34;'>💰 消費均消：{store.get('price_range')}</p>"
            
            btn_html = "<div style='display: flex; gap: 6px; margin-top: 6px;'>"
            if store.get("ig_url"):
                btn_html += f"<a href='{store.get('ig_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>📸 IG 介紹</a>"
            if store.get("map_url"):
                btn_html += f"<a href='{store.get('map_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_html += "</div>"
            
            card_html += btn_html + "</div>"
            
            st.markdown(card_html, unsafe_allow_html=True)
