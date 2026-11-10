import streamlit as st
import pandas as pd
import json
import os
import folium
from streamlit_folium import st_folium

# 設定頁面佈局為寬螢幕
st.set_page_config(page_title="雲林美食地圖 | Monlu Studio", page_icon="🍲", layout="wide")

# --- CSS 注入：自訂背景色、字體顏色與標籤色 #deb37f ---
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
    </style>
    """,
    unsafe_allow_html=True
)

DATA_FILE = "stores.json"
TAGS_FILE = "tags.json"

# --- 輔助函數：讀取資料 ---
def load_json(file_path, default_value):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
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
st.title("Wen's life 雲林推薦美食地圖")
st.markdown(f"目前為您篩選出 **{len(filtered_stores)}** 間精選店家：")

if not filtered_stores:
    st.info("💡 目前沒有符合篩選條件的店家，請嘗試調整側邊欄的篩選條件。")
else:
    map_col, list_col = st.columns([1.2, 1])

    with map_col:
        st.subheader("🗺️ 地圖導覽")
        
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
                dot_color = "#b62524"
            elif "LINE社群" in tier:
                dot_color = "#b97926"
            else:
                dot_color = "#cca59b"

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
                    color: #803c34;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 4px 10px;
                    border: 1px solid #803c34;
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
                    background-color: {dot_color};
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

    with list_col:
        st.subheader("📋 店家清單")
        
        for store in filtered_stores:
            tier = store.get("tier", "")
            
            if "IG REELS" in tier:
                card_border = "#b62524"
            elif "LINE社群" in tier:
                card_border = "#b97926"
            else:
                card_border = "#cca59b"

            name = store.get('name', '')
            subtitle = store.get('subtitle', '')
            
            # 店名與副標（垂直線分隔）
            header_html = f"""
            <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px;">
                <h3 style="margin: 0; font-size: 18px; color: #803c34;">{name}</h3>
                <span style="font-size: 14px; color: #a6635b; font-weight: 500;">│ {subtitle}</span>
            </div>
            """

            card_html = f"""
            <div style="
                background-color: #f7dad2;
                border: 1.5px solid {card_border};
                border-radius: 10px;
                padding: 14px 16px;
                margin-bottom: 14px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            ">
                {header_html}
            """
            
            # 介紹文字（放標籤上方、店名下方）
            if store.get("description"):
                card_html += f"<p style='margin: 0 0 10px 0; font-size: 13px; color: #4a403f !important; line-height: 1.4;'>{store.get('description')}</p>"
            
            cat_val = store.get("category", "")
            cat_display = ", ".join(cat_val) if isinstance(cat_val, list) else cat_val
            
            tags_html = f"<span style='background-color:#d8af9c; color:#803c34; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;'>📍 {store.get('district')}</span> "
            tags_html += f"<span style='background-color:#d8af9c; color:#803c34; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;'>🍽️ {cat_display}</span> "
            
            store_types = store.get("types", [])
            for t in store_types:
                tags_html += f"<span style='background-color:#803c34; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px;'>🏷️ {t}</span> "
            
            card_html += f"<div style='margin-bottom: 6px;'>{tags_html}</div>"
            
            if store.get("price_range"):
                card_html += f"<p style='margin: 0 0 6px 0; font-size: 12px; color: #803c34;'>💰 消費均消：{store.get('price_range')}</p>"
            
            # 內嵌按鈕
            btn_html = "<div style='display: flex; gap: 8px; margin-top: 10px;'>"
            if store.get("ig_url"):
                btn_html += f"<a href='{store.get('ig_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 6px 10px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid #803c34;'>📸 IG 介紹</a>"
            if store.get("map_url"):
                btn_html += f"<a href='{store.get('map_url')}' target='_blank' style='flex: 1; text-align: center; background-color: #decfbd; color: #803c34; padding: 6px 10px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid #803c34;'>🗺️ Google 導航</a>"
            btn_html += "</div>"
            
            card_html += btn_html + "</div>"
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            st.markdown(card_html, unsafe_allow_html=True)
