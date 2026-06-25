"""Utility to shift naive UTC timestamps to Asia/Bangkok local time."""
from __future__ import annotations

import argparse
import os
from datetime import timedelta

from app import app, db, PurchaseOrder, Comment, now_bangkok

DEFAULT_OFFSET = timedelta(hours=7)
MARKER_NAME = "timezone_migrated.txt"


def summarize(records: list[tuple[str, int, str]]) -> None:
    for model, count, note in records:
        print(f"- {model}: {count} records {note}")


def migrate(offset: timedelta, apply_changes: bool, force: bool) -> None:
    with app.app_context():
        marker_path = os.path.join(app.instance_path, MARKER_NAME)
        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except OSError:
            pass

        if os.path.exists(marker_path) and not force:
            print(f"⚠️  Marker '{MARKER_NAME}' already exists. Use --force to ignore the marker.")
            return

        purchase_orders = PurchaseOrder.query.filter(PurchaseOrder.created.isnot(None)).all()
        comments = Comment.query.filter(Comment.created.isnot(None)).all()

        summary_data = [
            ("PurchaseOrder", len(purchase_orders), "will be shifted" if apply_changes else "candidates"),
            ("Comment", len(comments), "will be shifted" if apply_changes else "candidates"),
        ]
        print("Timezone migration summary (Asia/Bangkok, UTC+7):")
        summarize(summary_data)

        for sample in purchase_orders[:3]:
            print(
                f"  Example PO #{sample.id}: {sample.created} -> {sample.created + offset}"
            )
        for sample in comments[:3]:
            print(
                f"  Example Comment #{sample.id}: {sample.created} -> {sample.created + offset}"
            )

        if not purchase_orders and not comments:
            print("No records found. Nothing to migrate.")
            return

        if not apply_changes:
            print("Dry run complete. Re-run with --apply once you verify the preview above.")
            return

        for record in purchase_orders:
            record.created = record.created + offset
        for record in comments:
            record.created = record.created + offset

        db.session.commit()
        with open(marker_path, "w", encoding="utf-8") as marker:
            marker.write(now_bangkok().isoformat())
        print(f"✅ Migration complete. Marker written to '{marker_path}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert stored timestamps to Asia/Bangkok time.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the timestamp shift. Without this flag, the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the existing migration marker and re-run the migration.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=7,
        help="Hour offset to apply (default: 7).",
    )
    args = parser.parse_args()

    migrate(timedelta(hours=args.hours), apply_changes=args.apply, force=args.force)


if __name__ == "__main__":
    main()
