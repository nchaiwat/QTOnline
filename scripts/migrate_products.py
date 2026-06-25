"""Utility script to align the `products` table schema with the SQLAlchemy Product model.

- ตรวจสอบว่าตาราง products มีคอลัมน์ครบตามโมเดลหรือไม่
- เพิ่มคอลัมน์ที่หายไปอัตโนมัติ (ALTER TABLE)
- ถ้ารันด้วย --recreate จะ drop ตาราง products แล้วสร้างใหม่ทันที

การรันสคริปต์นี้ควรทำในสภาพแวดล้อมที่ตั้งค่า `DATABASE_URL` (หรือใช้ค่าดีฟอลต์จากแอป)
และควรสำรองข้อมูลก่อนทุกครั้ง
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateColumn  # type: ignore

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# นำเข้าแอปและโมเดลจากโปรเจกต์หลัก
from app import app, db, Product  # type: ignore  # pylint: disable=wrong-import-position


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync products table schema with model definition")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop existing products table and create a fresh one (ข้อมูลเดิมจะหายหมด)",
    )
    return parser


def recreate_table() -> None:
    with app.app_context():
        engine = db.engine
        conn = engine.connect()
        trans = conn.begin()
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if Product.__table__.name in tables:
                print("- Dropping existing table 'products' ...")
                Product.__table__.drop(bind=engine)
            print("- Creating table 'products' ...")
            Product.__table__.create(bind=engine)
            trans.commit()
            print("✔ Recreated table successfully")
        except SQLAlchemyError as exc:  # pragma: no cover
            trans.rollback()
            print("✘ Failed to recreate table:", exc)
            sys.exit(1)
        finally:
            conn.close()


def sync_missing_columns() -> None:
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if Product.__table__.name not in existing_tables:
            print("ตาราง 'products' ยังไม่มีในฐานข้อมูล ใช้ --recreate เพื่อสร้างใหม่")
            sys.exit(1)

        existing_columns: Dict[str, str] = {
            col["name"].lower(): col["name"] for col in inspector.get_columns(Product.__table__.name)
        }
        target_columns = {col.name: col for col in Product.__table__.columns}

        rename_pairs: List[Tuple[str, str]] = []
        for target_name in target_columns.keys():
            lower = target_name.lower()
            existing = existing_columns.get(lower)
            if existing and existing != target_name:
                rename_pairs.append((existing, target_name))

        if rename_pairs:
            print("พบคอลัมน์ที่ต้อง rename เพื่อให้ตรงกับโมเดล:")
            conn = engine.connect()
            trans = conn.begin()
            try:
                for old_name, new_name in rename_pairs:
                    ddl = text(
                        f'ALTER TABLE {Product.__table__.name} RENAME COLUMN "{old_name}" TO "{new_name}"'
                    )
                    print(f"  • Executing: {ddl.text}")
                    conn.execute(ddl)
                    existing_columns[new_name.lower()] = new_name
                trans.commit()
                print("✔ Rename คอลัมน์เรียบร้อย")
            except SQLAlchemyError as exc:  # pragma: no cover
                trans.rollback()
                print("✘ Rename คอลัมน์ไม่สำเร็จ:", exc)
                sys.exit(1)
            finally:
                conn.close()

        missing: List[str] = [name for name in target_columns.keys() if name.lower() not in existing_columns]
        if not missing:
            print("✔ ไม่มีคอลัมน์ที่หายไป ตาราง products พร้อมใช้งานแล้ว")
            return

        print(f"พบคอลัมน์ที่ต้องเพิ่ม {len(missing)} รายการ:\n  - " + "\n  - ".join(missing))
        conn = engine.connect()
        trans = conn.begin()
        try:
            for col_name in missing:
                column = target_columns[col_name]
                column_sql = CreateColumn(column).compile(dialect=engine.dialect)
                ddl = text(
                    f"ALTER TABLE {Product.__table__.name} ADD COLUMN {column_sql}"
                )
                print(f"  • Executing: {ddl.text}")
                conn.execute(ddl)
            trans.commit()
            print("✔ เพิ่มคอลัมน์ที่หายไปเสร็จแล้ว")
        except SQLAlchemyError as exc:  # pragma: no cover
            trans.rollback()
            print("✘ เพิ่มคอลัมน์ไม่สำเร็จ:", exc)
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    args = build_arg_parser().parse_args()
    if args.recreate:
        recreate_table()
    else:
        sync_missing_columns()
