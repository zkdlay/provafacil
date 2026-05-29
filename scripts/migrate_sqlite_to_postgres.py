import argparse
import os
import sqlite3
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "database" / "schema_postgres.sql"


TABLES = {
    "usuarios": ["id", "usuario", "senha", "criado_em"],
    "provas": ["id", "usuario_id", "materia", "titulo", "questoes", "criada_em"],
    "respostas": [
        "id",
        "prova_id",
        "nome_aluno",
        "respostas",
        "nota",
        "respondida_em",
        "tentativas_screenshot",
        "alertas_fraude",
    ],
    "eventos": ["id", "prova_id", "nome_aluno", "evento", "detalhe", "timestamp"],
    "acessos_prova": ["token", "prova_id", "ativo", "criado_em", "expira_em"],
}


def sqlite_rows(sqlite_conn, table_name):
    existing_columns = {
        row["name"] for row in sqlite_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if not existing_columns:
        return []

    selected_columns = [col for col in TABLES[table_name] if col in existing_columns]
    rows = sqlite_conn.execute(
        f"SELECT {', '.join(selected_columns)} FROM {table_name}"
    ).fetchall()

    normalized = []
    for row in rows:
        item = dict(row)
        for col in TABLES[table_name]:
            item.setdefault(col, None)
        normalized.append(item)
    return normalized


def insert_rows(pg_conn, table_name, rows):
    if not rows:
        return 0

    columns = TABLES[table_name]
    placeholders = ", ".join(["%s"] * len(columns))
    conflict_target = "token" if table_name == "acessos_prova" else "id"
    sql = f"""
        INSERT INTO {table_name} ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_target}) DO NOTHING
    """

    values = [tuple(row[col] for col in columns) for row in rows]
    with pg_conn.cursor() as cur:
        cur.executemany(sql, values)
    return len(values)


def migrate_usuarios(pg_conn, rows):
    id_map = {}
    if not rows:
        return id_map, 0, []

    warnings = []
    inserted = 0
    with pg_conn.cursor() as cur:
        for row in rows:
            old_id = row["id"]
            usuario = row["usuario"]
            cur.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
            existing = cur.fetchone()

            if existing:
                new_id = existing[0]
                id_map[old_id] = new_id
                if old_id != new_id:
                    warnings.append(
                        f"usuario '{usuario}' ja existia no PostgreSQL com id={new_id}; "
                        f"provas do SQLite usuario_id={old_id} serao remapeadas."
                    )
                continue

            cur.execute(
                """
                INSERT INTO usuarios (id, usuario, senha, criado_em)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
                """,
                (old_id, usuario, row["senha"], row["criado_em"]),
            )
            inserted_row = cur.fetchone()
            if inserted_row:
                id_map[old_id] = inserted_row[0]
                inserted += 1
                continue

            cur.execute(
                """
                INSERT INTO usuarios (usuario, senha, criado_em)
                VALUES (%s, %s, %s)
                ON CONFLICT (usuario) DO UPDATE
                SET usuario = EXCLUDED.usuario
                RETURNING id
                """,
                (usuario, row["senha"], row["criado_em"]),
            )
            fallback_row = cur.fetchone()
            new_id = fallback_row[0]
            id_map[old_id] = new_id
            warnings.append(
                f"nao foi possivel preservar id={old_id} para usuario '{usuario}'; "
                f"novo id usado: {new_id}. Provas relacionadas serao remapeadas."
            )
    return id_map, inserted, warnings


def remap_provas_usuario(rows, usuario_id_map):
    remapped = []
    warnings = []
    skipped = 0
    for row in rows:
        old_usuario_id = row.get("usuario_id")
        if old_usuario_id in usuario_id_map:
            new_row = dict(row)
            new_row["usuario_id"] = usuario_id_map[old_usuario_id]
            remapped.append(new_row)
            continue

        warnings.append(
            f"prova id={row.get('id')} referencia usuario_id={old_usuario_id}, "
            "mas esse usuario nao foi encontrado/importado; prova ignorada."
        )
        skipped += 1
    return remapped, skipped, warnings


def get_existing_prova_ids(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id FROM provas")
        return {row[0] for row in cur.fetchall()}


def filter_rows_by_existing_provas(table_name, rows, valid_prova_ids):
    filtered = []
    warnings = []
    skipped = 0

    for row in rows:
        prova_id = row.get("prova_id")
        if prova_id in valid_prova_ids:
            filtered.append(row)
            continue

        skipped += 1
        warnings.append(
            f"{table_name}: registro ignorado porque prova_id={prova_id} "
            "nao existe em provas."
        )

    return filtered, skipped, warnings


def reset_sequences(pg_conn):
    sequence_tables = ["usuarios", "turmas", "alunos", "prova_alunos_autorizados", "respostas", "eventos"]
    with pg_conn.cursor() as cur:
        for table_name in sequence_tables:
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                    (SELECT MAX(id) FROM {table_name}) IS NOT NULL
                )
                """
            )


def main():
    parser = argparse.ArgumentParser(description="Migra provas.db para PostgreSQL/Supabase.")
    parser.add_argument(
        "--sqlite",
        default=str(ROOT_DIR / "provas.db"),
        help="Caminho do banco SQLite antigo. Padrao: ./provas.db",
    )
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nao configurada no .env ou ambiente.")

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Banco SQLite nao encontrado: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(database_url)
    try:
        with pg_conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

        totals = {}
        warnings = []

        usuarios_rows = sqlite_rows(sqlite_conn, "usuarios")
        usuario_id_map, inserted_users, user_warnings = migrate_usuarios(pg_conn, usuarios_rows)
        totals["usuarios"] = len(usuarios_rows)
        warnings.extend(user_warnings)

        provas_rows = sqlite_rows(sqlite_conn, "provas")
        provas_rows, skipped_provas, prova_warnings = remap_provas_usuario(
            provas_rows, usuario_id_map
        )
        totals["provas"] = insert_rows(pg_conn, "provas", provas_rows)
        warnings.extend(prova_warnings)
        valid_prova_ids = get_existing_prova_ids(pg_conn)
        skipped_orphans = {"provas": skipped_provas}

        for table_name in ("respostas", "eventos", "acessos_prova"):
            rows = sqlite_rows(sqlite_conn, table_name)
            rows, skipped, orphan_warnings = filter_rows_by_existing_provas(
                table_name, rows, valid_prova_ids
            )
            skipped_orphans[table_name] = skipped
            warnings.extend(orphan_warnings)
            totals[table_name] = insert_rows(pg_conn, table_name, rows)

        reset_sequences(pg_conn)
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

    print("Migracao concluida.")
    for table_name, total in totals.items():
        print(f"- {table_name}: {total} registro(s) lido(s) do SQLite")
    if inserted_users:
        print(f"- usuarios inseridos no PostgreSQL: {inserted_users}")
    for table_name, skipped in skipped_orphans.items():
        if skipped:
            print(f"- {table_name}: {skipped} registro(s) orfao(s) ignorado(s)")
    if warnings:
        print("Avisos:")
        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
