import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import os

# --- ส่วนตั้งค่า Font ---
FONT_FILE = 'THSarabunNew.ttf'
FONT_NAME = 'THSarabunNew'

# --- 1. ฟังก์ชันสร้าง PDF (ปรับปรุงเป็นแนวนอน + ตัดคำ) ---
# --- 1. ฟังก์ชันสร้าง PDF (ฉบับแก้ไข Error) ---
def create_pdf(dataframe, title="Data Report"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    if os.path.exists(FONT_FILE):
        pdf.add_font(FONT_NAME, '', FONT_FILE, uni=True)
        pdf.set_font(FONT_NAME, size=12) 
    else:
        pdf.set_font("Arial", size=10)
    
    pdf.cell(0, 10, title, ln=True, align='L') 
    
    page_width = 280 
    if dataframe.empty:
        pdf.cell(0, 10, "No Data Found", ln=True, align='C')
        # แก้ไขจุดที่ 1
        return pdf.output(dest='S').encode('latin-1')

    num_columns = len(dataframe.columns)
    col_width = page_width / num_columns if num_columns > 0 else page_width
    row_height = 8
    
    # Header
    for col in dataframe.columns:
        text = str(col)
        while pdf.get_string_width(text) > col_width - 2:
            text = text[:-1]
        pdf.cell(col_width, row_height, text, border=1, align='C')
    pdf.ln(row_height)
    
    # Rows
    for index, row in dataframe.iterrows():
        for item in row:
            text = str(item)
            while pdf.get_string_width(text) > col_width - 2:
                text = text[:-1]
            pdf.cell(col_width, row_height, text, border=1, align='L')
        pdf.ln(row_height)
        
    # แก้ไขจุดที่ 2: ใช้ .encode('latin-1') แทนการครอบด้วย bytes() เปล่าๆ
    return pdf.output(dest='S').encode('latin-1')

# --- 2. ฟังก์ชันสร้าง Excel ---
def create_excel(dataframe, sheet_name='Sheet1'):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 3. ฟังก์ชันช่วยจัดรูปแบบเงิน ---
def try_format_currency(val):
    try:
        if pd.isna(val) or str(val).lower() == 'nan' or str(val).strip() == '':
            return ""
        clean_val = str(val).replace(',', '')
        return "{:,.2f}".format(float(clean_val))
    except:
        return val

# ==========================================
# 🖥️ ส่วนหน้าเว็บไซต์
# ==========================================
st.set_page_config(page_title="Excel & CSV Smart Filter", layout="wide") # เปลี่ยน layout เป็น wide เพื่อให้ดูกว้างขึ้น
st.title("📊 Excel & CSV Smart Filter")
st.markdown("---")

# 1. Sidebar: อัปโหลดไฟล์ (รองรับทั้ง xlsx และ csv)
st.sidebar.header("📂 1. Input File")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ (Excel หรือ CSV)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        df = None
        
        # ตรวจสอบประเภทไฟล์
        if uploaded_file.name.endswith('.csv'):
            # อ่าน CSV
            df = pd.read_csv(uploaded_file, dtype=str, encoding='utf-8-sig')
        else:
            # อ่าน Excel
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            selected_sheet = st.sidebar.selectbox("เลือก Sheet:", sheet_names)
            if selected_sheet:
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, dtype=str)
        
        if df is not None:
            # Auto Format เงิน
            money_keywords = ['AMT', 'NET', 'VAT', 'PRICE', 'COST', 'TOTAL', 'DEPTOT']
            for col in df.columns:
                if any(keyword in col.upper() for keyword in money_keywords):
                    df[col] = df[col].apply(try_format_currency)

            df_original = df.copy() 

            # ==========================================
            # 🎯 ส่วนกรองข้อมูล (FILTER SECTION)
            # ==========================================
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 2. ตัวกรอง (Filter)")
            
            filter_columns = st.sidebar.multiselect(
                "เลือกคอลัมน์ที่ต้องการกรอง:",
                options=df.columns,
                default=[]
            )
            
            for col in filter_columns:
                st.sidebar.markdown(f"**กรองข้อมูล: {col}**")

                # ดึงค่า Unique
                all_values = df[col].dropna().unique()
                
                # ช่องค้นหา (Search Box)
                search_text = st.sidebar.text_input(f"🔎 ค้นหา '{col}':", key=f"search_{col}")
                
                # --- 🔥 แก้ไข Logic การค้นหา (เฉพาะ 3 ตัวอักษรแรก) 🔥 ---
                if search_text:
                    # ค้นหาคำ search_text ใน 3 ตัวอักษรแรก (slice [:3]) ของแต่ละค่า
                    filtered_options = [val for val in all_values if search_text.lower() in str(val)[:3].lower()]
                else:
                    filtered_options = all_values

                #Multiselect
                selected_values = st.sidebar.multiselect(
                    f"เลือกค่าใน '{col}':",
                    options=filtered_options,
                    default=filtered_options,
                    key=f"multi_{col}"
                )
                
                if selected_values:
                    df = df[df[col].isin(selected_values)]
            
            # ==========================================
            # 📊 คำนวณตาราง (Split Data)
            # ==========================================
            df_excluded = df_original.drop(df.index)

            # ==========================================
            # 📋 แสดงผลลัพธ์ (Display Section)
            # ==========================================
            st.subheader("เลือกคอลัมน์ที่ต้องการแสดงผล")
            
            # ใช้ลำดับจากไฟล์ต้นฉบับ
            all_columns = df_original.columns.tolist()
            display_columns = st.multiselect("Column Selection:", all_columns, default=all_columns)
            
            if display_columns:
                # เลือกคอลัมน์ที่จะโชว์
                df_final = df[display_columns]
                df_excluded_final = df_excluded[display_columns]
                
                # --- TABS ---
                tab1, tab2 = st.tabs(["✅ ตารางที่ 1: ข้อมูลที่ค้นหาเจอ", "🚫 ตารางที่ 2: ข้อมูลส่วนที่เหลือ"])
                
                # --- TAB 1 ---
                with tab1:
                    st.success(f"พบข้อมูลจำนวน: {len(df_final)} รายการ")
                    st.dataframe(df_final, use_container_width=True)
                    
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        if not df_final.empty:
                            pdf_bytes = create_pdf(df_final, title="Filtered Data (Table 1)")
                            st.download_button("📄 Download PDF (ตาราง 1)", pdf_bytes, "filtered_data.pdf", "application/pdf")
                    with col1_2:
                        if not df_final.empty:
                            excel_bytes = create_excel(df_final, "FilteredData")
                            st.download_button("📈 Download Excel (ตาราง 1)", excel_bytes, "filtered_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # --- TAB 2 ---
                with tab2:
                    st.warning(f"ข้อมูลส่วนที่เหลือจำนวน: {len(df_excluded_final)} รายการ")
                    
                    if not df_excluded_final.empty:
                        st.dataframe(df_excluded_final, use_container_width=True)
                        
                        col2_1, col2_2 = st.columns(2)
                        with col2_1: 
                             pdf_bytes_ex = create_pdf(df_excluded_final, title="Excluded Data (Table 2)")
                             st.download_button("📄 Download PDF (ตาราง 2)", pdf_bytes_ex, "excluded_data.pdf", "application/pdf")
                        
                        with col2_2: 
                             excel_bytes_excluded = create_excel(df_excluded_final, "ExcludedData")
                             st.download_button("📉 Download Excel (ตาราง 2)", excel_bytes_excluded, "excluded_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.info("ไม่มีข้อมูลตกค้าง")

    except Exception as e:

        st.error(f"เกิดข้อผิดพลาด: {e}")
