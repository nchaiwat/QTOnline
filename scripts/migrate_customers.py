"""Utility script to align the `customers` table schema with the SQLAlchemy Customer model.

- ตรวจสอบว่าตาราง customers มีคอลัมน์ครบตามโมเดลหรือไม่
- เพิ่มคอลัมน์ที่หายไปอัตโนมัติ (ALTER TABLE)
- ถ้ารันด้วย --recreate จะ drop ตาราง customers แล้วสร้างใหม่ทันที
"""

import argparse
import os
import sys
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# นำเข้าแอปและโมเดลจากโปรเจกต์หลัก
from app import app, db, Customer  # type: ignore


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync customers table schema with model definition")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop existing customers table and create a fresh one (ข้อมูลเดิมจะหายหมด)",
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
            if Customer.__table__.name in tables:
                print("- Dropping existing table 'customers' ...")
                Customer.__table__.drop(bind=engine)
            print("- Creating table 'customers' ...")
            Customer.__table__.create(bind=engine)
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

        if Customer.__table__.name not in existing_tables:
            print("ตาราง 'customers' ยังไม่มีในฐานข้อมูล ใช้ --recreate เพื่อสร้างใหม่")
            sys.exit(1)

        existing_columns = {col["name"] for col in inspector.get_columns(Customer.__table__.name)}
        target_columns = {col.name: col for col in Customer.__table__.columns}

        missing: List[str] = [name for name in target_columns.keys() if name not in existing_columns]
        if not missing:
            print("✔ ไม่มีคอลัมน์ที่หายไป ตาราง customers พร้อมใช้งานแล้ว")
            return

        print(f"พบคอลัมน์ที่ต้องเพิ่ม {len(missing)} รายการ:\n  - " + "\n  - ".join(missing))
        conn = engine.connect()
        trans = conn.begin()
        try:
            for col_name in missing:
                column = target_columns[col_name]
                ddl_type = column.type.compile(engine.dialect)  # type: ignore[attr-defined]
                ddl = text(
                    f"ALTER TABLE {Customer.__table__.name} "
                    f"ADD COLUMN {column.name} {ddl_type}"
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
