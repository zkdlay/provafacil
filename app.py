"""
# app.py legado estava vazio.
"""

import streamlit as st

from routing import route_app


def main():
    st.set_page_config(page_title="Prova Fácil", layout="wide")
    route_app(st)


if __name__ == "__main__":
    main()
