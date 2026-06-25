
import os
import pandas as pd
from sqlalchemy import text
from app import app, db

def export_to_excel():
    output_file = "db_dump_all_tables.xlsx"
    with app.app_context():
        try:
            # Get list of tables
            query_tables = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = db.session.execute(query_tables).fetchall()
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for table in tables:
                    table_name = table[0]
                    print(f"Exporting table: {table_name}...")
                    
                    # Read table data into DataFrame
                    df = pd.read_sql_table(table_name, db.engine)
                    
                    # Write to a separate sheet (sheet names limited to 31 chars)
                    sheet_name = table_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"\nSUCCESS: Exported all tables to {output_file}")
            
        except Exception as e:
            print(f"Error during export: {e}")

if __name__ == "__main__":
    export_to_excel()
