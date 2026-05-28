"""
# auth_professor.py
# login/registro em bloco de tela
"""

import hashlib

from psycopg2 import IntegrityError, errors

from database.queries import Queries


class AuthService:
    @staticmethod
    def hash_senha(senha):
        return hashlib.sha256(senha.encode()).hexdigest()

    @staticmethod
    def registrar_professor(usuario, senha):
        try:
            Queries.criar_usuario(usuario, AuthService.hash_senha(senha))
            return True, "Cadastro realizado com sucesso!"
        except (errors.UniqueViolation, IntegrityError):
            return False, "Este usuário já existe. Escolha outro nome."
        except Exception as exc:
            return False, f"Erro: {exc}"

    @staticmethod
    def verificar_login(usuario, senha):
        row = Queries.buscar_usuario_login(usuario, AuthService.hash_senha(senha))
        if row:
            return True, row["id"]
        return False, None


def render_auth_professor(st):
    if "usuario_id" in st.session_state:
        return True

    st.markdown("## Prova Fácil")
    st.caption("Sistema de provas online com correção automática")
    tab_login, tab_reg = st.tabs(["Login", "Criar conta"])

    with tab_login:
        usuario = st.text_input("Nome de usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", type="primary", width="stretch"):
            if not usuario or not senha:
                st.warning("Preencha usuário e senha.")
            else:
                ok, uid = AuthService.verificar_login(usuario, senha)
                if ok:
                    st.session_state.usuario_id = uid
                    st.session_state.usuario_nome = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

    with tab_reg:
        nu = st.text_input("Nome de usuário", key="reg_user")
        ns = st.text_input("Senha", type="password", key="reg_pass")
        nc = st.text_input("Confirmar senha", type="password", key="reg_pass_conf")
        if st.button("Criar conta", type="primary", width="stretch"):
            if not nu or not ns:
                st.warning("Preencha todos os campos.")
            elif len(ns) < 4:
                st.warning("Senha mínima de 4 caracteres.")
            elif ns != nc:
                st.warning("As senhas não conferem.")
            else:
                ok, msg = AuthService.registrar_professor(nu, ns)
                (st.success if ok else st.error)(msg)

    st.stop()
