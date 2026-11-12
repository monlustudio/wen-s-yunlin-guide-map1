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

# --- CSS 注入：自訂背景色、字體顏色、手機版主標題微調、頂部切齊與按鈕樣式優化 ---
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

    /* 🎲 「今天去哪兒？」抽卡按鈕樣式：維持醒目粗體與深框 */
    div.stButton > button[kind="secondary"], div.stButton > button {{
        background-color: #decfbd !important;
        color: #803c34 !important;
        border: 2px solid #803c34 !important;
        font-weight: 900 !important;
        font-size: 16px !important;
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

# 確保前台能完整動態讀取 tags.json 內的最新標籤
default_tags = {
    "district": ["虎尾", "斗六", "古坑", "斗南", "麥寮", "西螺", "土庫", "其他雲林鄉鎮", "外縣市"],
    "category": [
        "正餐", "小吃", "咖啡廳", "甜點", "飲料", "點心", "下午茶", 
        "喝酒", "手作體驗", "遊樂/景點", 
        "東方料理(中 日 韓  東南亞 中東)", "西方料理(美 義 歐 地中海)", "宵夜/深夜美食"
    ],
    "type": [
        "約會", "放鬆", "聚餐", "慶生", "獨處", 
        "拍照打卡", "質感空間", "安靜工作", "頂級味蕾饗宴", "出去玩", "日常吃飯"
    ],
    "tier": ["IG REELS拍攝店家", "LINE社群 金賞名單", "WEN日常美食推薦", "脆友/在地網友私房推薦"]
}
tags_data = load_json(TAGS_FILE, default_tags)

# ==========================================
# 🎲 隨機抽卡對話框設計（吃角子老虎機緩速漸停，且最後顯示即為中獎結果）
# ==========================================
@st.dialog("今天去哪兒？私藏行程盲盒")
def random_draw_dialog(stores, tags):
    st.markdown("不知道今天該去哪裡或吃什麼嗎？讓抽卡幫你決定吧！")
    
    # 1. 選擇地區
    dist_options = ["全雲林"] + tags.get("district", ["虎尾", "斗六"])
    draw_district = st.selectbox("📍 選擇想去的地區", dist_options, key="draw_dist")
    
    # 2. 選擇空間/氛圍類型
    type_options = ["不限"] + tags.get("type", ["聚餐", "約會", "放鬆"])
    draw_type = st.selectbox("🏷️ 選擇行程類型", type_options, key="draw_type")
    
    # 3. 選擇價位範圍
    price_options = ["不限", "$ 經濟平價 (200元以下)", "$$ 中等消費 (200~500元)", "$$$ 精緻質感 (500元以上)"]
    draw_price = st.selectbox("💰 選擇消費金額偏好", price_options, key="draw_price")
    
    st.markdown("---")
    
    if st.button("幫我決定今天要去哪！", type="primary", use_container_width=True):
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
            chosen = random.choice(pool)
            slot_placeholder = st.empty()
            all_names = [s.get("name") for s in pool]
            delays = [0.03, 0.04, 0.05, 0.07, 0.10, 0.14, 0.19, 0.25, 0.32, 0.40]
            
            for i, d in enumerate(delays):
                if i == len(delays) - 1:
                    temp_name = chosen.get("name")
                else:
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
                        <h2 style="margin: 0; color: #803c34; font-size: 22px;">抽籤中...</h2>
                        <p style="margin: 8px 0 0 0; font-size: 20px; font-weight: bold; color: #b62524;">✨ {temp_name} ✨</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(d)
            
            slot_placeholder.empty()
            st.success(f"今天就去這吧！為您推薦：**{chosen.get('name')}**")
            
            tier = chosen.get("tier", "")
            if "IG REELS" in tier:
                c_bg, c_border = "rgba(182, 37, 36, 0.22)", "#b62524"
            elif "LINE社群" in tier:
                c_bg, c_border = "rgba(185, 121, 38, 0.22)", "#b97926"
            elif "脆友" in tier or "網友" in tier:
                c_bg, c_border = "rgba(163, 155, 196, 0.25)", "#a39bc4"
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
            if chosen.get("reels_url"):
                btn_h += f"<a href='{chosen.get('reels_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 5px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🎬 Reels 介紹</a>"
            if chosen.get("map_url"):
                btn_h += f"<a href='{chosen.get('map_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 5px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_h += "</div></div>"
            
            st.markdown(card_box + btn_h, unsafe_allow_html=True)


# --- 側邊欄：進階篩選器 ---
st.sidebar.header("🔍 雲林美食探索")
st.sidebar.markdown("尋找在地私藏好味道與質感空間。")

district_options = ["全雲林"] + tags_data.get("district", ["虎尾", "斗六"])
selected_district = st.sidebar.selectbox("📍 選擇地區", district_options)

category_options = ["不指定"] + tags_data.get("category", ["正餐", "小吃", "甜點", "咖啡", "飲品"])
selected_category = st.sidebar.selectbox("🍽️ 料理類別", category_options)

type_options = tags_data.get("type", ["聚餐", "約會", "放鬆"])
selected_types = st.sidebar.multiselect("🏷️ 空間/氛圍類型 (可複選)", type_options, default=[])

tier_options = tags_data.get("tier", ["IG REELS拍攝店家", "LINE社群 金賞名單", "WEN日常美食推薦", "脆友/在地網友私房推薦"])
selected_tiers = st.sidebar.multiselect("⭐ 推薦等級 (可複選)", tier_options, default=tier_options)

# 💡 側邊欄下方新增可折疊的操作指南 (st.expander，包含愛心色彩圖例)
with st.sidebar.expander("💡 點我看地圖操作小撇步"):
    st.markdown(
        """
        **🎨 推薦等級與色彩圖例**：
        - ❤️ **紅棕色系**：IG REELS 獨家拍攝與影音開箱
        - 💛 **金棕色系**：LINE 社群金賞與口碑名單
        - 🩷 **粉棕色系**：WEN 日常美食推薦與私房愛店
        - 💜 **淡紫色系**：脆友 / 在地網友熱情網友私房推薦

        ---
        **🗺️ 快速操作指引**：
        - **📍 地區與類別**：點選下拉選單可快速過濾特定鄉鎮或料理風格。
        - **🏷️ 多選標籤**：空間與氛圍類型支援多重勾選，精準尋找符合當下心情的去處。
        - **🗺️ 地圖與清單連動**：點擊地圖標籤或右側卡片，快速開啟 **IG**、**Reels 短片** 或 **Google 導航**。
        - **🎲 隨機抽卡**：選擇障礙時, 點擊下方按鈕讓盲盒幫你決定今天去哪！
        """
    )

# 🎲 1. 將「今天去哪兒？抽卡盲盒」放在上方（維持抽卡按鈕的粗體與深框樣式）
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 13px; text-align: center; margin-bottom: 6px;'>不知道今天要吃什麼或去哪裡嗎？按這裡幫你決定吧</p>", unsafe_allow_html=True)
if st.sidebar.button("今天去哪兒？", use_container_width=True):
    random_draw_dialog(stores_data, tags_data)

# 💬 2. 將「加入 LINE 社群」改為較細的精緻邊框與字體，放在下方
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 13px; text-align: center; margin-bottom: 6px;'>想獲得最新私房情報或提供口袋名單嗎？</p>", unsafe_allow_html=True)
st.sidebar.markdown(
    """
    <a href="https://line.me/ti/g2/你的社群邀請連結" target="_blank" style="
        display: block;
        text-align: center;
        background-color: #decfbd;
        color: #803c34;
        padding: 6px 10px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 13.5px;
        font-weight: 500;
        border: 1px solid #803c34;
        margin-bottom: 10px;
    ">✨ 加入 Wen's life LINE 社群</a>
    """,
    unsafe_allow_html=True
)

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

if len(selected_types) > 0:
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
            description = store.get("description", "")
            tier = store.get("tier", "")
            district = store.get("district", "")
            ig_url = store.get("ig_url", "")
            reels_url = store.get("reels_url", "")
            map_url = store.get("map_url", "")
            
            if "IG REELS" in tier:
                tag_color = "#b62524"
            elif "LINE社群" in tier:
                tag_color = "#b97926"
            elif "脆友" in tier or "網友" in tier:
                tag_color = "#a39bc4"
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

            # 🗺️ 地圖上的 Popup 小視窗（同步支援 IG、Reels、Google 導航按鈕）
            popup_title = f"{name} <span style='font-size: 14px; font-weight: normal; color: #803c34;'>| {subtitle}</span>" if subtitle else name
            
            popup_html = f"""
            <div style="color: #803c34; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 200px; max-width: 260px; padding: 4px;">
                <h4 style="margin: 0 0 6px 0; color: #803c34; font-size: 16px; font-weight: bold;">{popup_title}</h4>
            """
            if description:
                popup_html += f"<p style='margin: 0 0 8px 0; font-size: 12px; color: #803c34; line-height: 1.3;'>{description}</p>"
            
            popup_html += f"<p style='margin: 0 0 8px 0; font-size: 11px; color: #803c34;'><b>📍 地區：</b>{district} | <b>⭐ 等級：</b>{tier}</p>"
            
            btn_h = "<div style='display: flex; gap: 6px; margin-top: 6px;'>"
            if ig_url:
                btn_h += f"<a href='{ig_url}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 6px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #803c34;'>📸 IG 介紹</a>"
            if reels_url:
                btn_h += f"<a href='{reels_url}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 6px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #803c34;'>🎬 Reels 介紹</a>"
            if map_url:
                btn_h += f"<a href='{map_url}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 6px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_h += "</div></div>"
            
            popup_html += btn_h

            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(html=html_label),
                popup=folium.Popup(popup_html, max_width=280)
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
            elif "脆友" in tier or "網友" in tier:
                card_bg = "rgba(163, 155, 196, 0.25)"
                card_border = "#a39bc4"
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
            if store.get("reels_url"):
                btn_html += f"<a href='{store.get('reels_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🎬 Reels 介紹</a>"
            if store.get("map_url"):
                btn_html += f"<a href='{store.get('map_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_html += "</div>"
            
            card_html += btn_html + "</div>"
            
            st.markdown(card_html, unsafe_allow_html=True)
