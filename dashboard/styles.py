import streamlit as st


def apply_custom_style():
    st.markdown(
        """
        <style>
            div[data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
            }

            .block-container {
                padding-top: 2.2rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #5A8FC2 0%, #477DAF 55%, #356A9B 100%);
            }

            [data-testid="stSidebar"] * {
                color: white;
            }

            [data-testid="stSidebar"] [data-testid="stImage"] {
                text-align: left;
            }

            [data-testid="stSidebar"] [data-testid="stImage"] img {
                display: block;
                margin-left: 0px !important;
                margin-right: auto !important;
                margin-bottom: 14px;
            }

            .sidebar-title {
                font-size: 27px;
                font-weight: 800;
                margin-bottom: 8px;
                line-height: 1.3;
                text-align: left;
            }

            .sidebar-subtitle {
                font-size: 13px;
                opacity: 0.88;
                margin-bottom: 28px;
                line-height: 1.45;
                text-align: left;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] {
                width: 100%;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label {
                width: 100% !important;
                min-width: 100% !important;
                background-color: rgba(255, 255, 255, 0.12);
                padding: 12px 14px !important;
                border-radius: 10px;
                margin-bottom: 10px;
                border: 1px solid rgba(255, 255, 255, 0.14);
                transition: all 0.2s ease;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background-color: rgba(255, 255, 255, 0.22);
                border: 1px solid rgba(255, 255, 255, 0.35);
            }

            .main-title {
                display: block;
                font-size: 34px;
                font-weight: 800;
                color: #2F3A4A;
                margin: 0 0 6px 0;
                padding-top: 6px;
                line-height: 1.25;
                overflow: visible;
            }

            .main-subtitle {
                font-size: 15px;
                color: #6B7280;
                margin-bottom: 26px;
                line-height: 1.5;
            }

            .card {
                background-color: #FFFFFF;
                padding: 24px 24px;
                border-radius: 16px;
                border-left: 1px solid #E5E7EB;
                border-right: 1px solid #E5E7EB;
                border-bottom: 1px solid #E5E7EB;
                box-shadow: 0px 8px 22px rgba(15, 23, 42, 0.06);
                min-height: 135px;
            }

            .card-title {
                font-size: 14px;
                color: #6B7280;
                margin-bottom: 10px;
                font-weight: 600;
            }

            .card-value {
                font-size: 31px;
                font-weight: 800;
                color: #263238;
                margin-bottom: 7px;
                line-height: 1.2;
            }

            .card-subtitle {
                font-size: 13px;
                color: #9CA3AF;
                line-height: 1.4;
            }

            .info-panel {
                background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
                padding: 22px 24px;
                border-radius: 16px;
                border: 1px solid #E5E7EB;
                box-shadow: 0px 8px 22px rgba(15, 23, 42, 0.05);
                margin-top: 18px;
            }

            .info-panel-title {
                font-size: 18px;
                font-weight: 800;
                color: #2F3A4A;
                margin-bottom: 8px;
            }

            .info-panel-text {
                font-size: 14px;
                color: #64748B;
                line-height: 1.7;
            }

            h3 {
                color: #2F3A4A;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True
    )