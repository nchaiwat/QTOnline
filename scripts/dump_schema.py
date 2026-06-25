
import os
import sys
from sqlalchemy import text
from app import app, db

def dump_db_info():
    with app.app_context():
        try:
            # Get list of tables (excluding internal postgres tables)
            query_tables = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = db.session.execute(query_tables).fetchall()
            
            print("=" * 60)
            print(f"DATABASE DUMP: {os.environ.get('POSTGRES_DB', 'po_online_db')}")
            print("=" * 60)
            
            for table in tables:
                table_name = table[0]
                print(f"\n[TABLE: {table_name}]")
                
                # Get columns info
                query_cols = text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                cols = db.session.execute(query_cols).fetchall()
                
                print(f"{'Column':<30} | {'Type':<20} | {'Null':<5} | {'Default'}")
                print("-" * 80)
                for col in cols:
                    cname, dtype, nullable, default = col
                    print(f"{cname:<30} | {dtype:<20} | {nullable:<5} | {default}")
                
                # Get Row Count
                count_query = text(f"SELECT COUNT(*) FROM \"{table_name}\"")
                count = db.session.execute(count_query).scalar()
                print(f"\nTotal Rows: {count}")
                
                # Sample Row (if any)
                if count > 0:
                    sample_query = text(f"SELECT * FROM \"{table_name}\" LIMIT 1")
                    sample = db.session.execute(sample_query).fetchone()
                    print("Sample Row Keys and Values:")
                    keys = sample._fields
                    values = sample
                    for k, v in zip(keys, values):
                        # Truncate long strings for readability
                        val_str = str(v)
                        if len(val_str) > 50:
                            val_str = val_str[:47] + "..."
                        print(f"  {k}: {val_str}")
                else:
                    print(" (Table is empty)")
                
                print("-" * 60)
                
        except Exception as e:
            print(f"Error during dump: {e}")

if __name__ == "__main__":
    dump_db_info()
