
import os
import sqlite3
import argparse
from agent import REFORCE
from chat import GPTChat
from utils import get_table_info, get_dictionary
from prompt import Prompts
from sql import SqlEnv
from reconstruct_data import compress_ddl, make_folder
from schema_linking import reduce_ddl, ask_model_sl, ask_model_sl2

def create_dummy_db(db_path: str) -> None:
    """
    Creates a dummy SQLite database with sample tables.
    
    :param db_path: Path to the SQLite database file
    """
    dir_path = os.path.dirname(db_path)
    os.makedirs(dir_path, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create sample tables
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);")
    cursor.execute("CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL);")
    
    # Insert sample data
    cursor.execute("INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30), (2, 'Bob', 25), (3, 'Charlie', 35);")
    cursor.execute("INSERT INTO orders (order_id, user_id, amount) VALUES (101, 1, 99.99), (102, 2, 149.99);")
    
    conn.commit()
    conn.close()
    print(f"Database created at {db_path}")

def setup_example_structure(db_path: str, example_path: str) -> None:
    """
    Sets up the required folder structure for reconstruct_data functions.
    
    :param db_path: Path to SQLite database
    :param example_path: Path to example folder structure
    """
    # Create example folder structure
    os.makedirs(os.path.join(example_path, "dummy_db"), exist_ok=True)
    
    # Copy DB to example structure
    db_name = os.path.basename(db_path)
    target_path = os.path.join(example_path, "dummy_db", db_name)
    if not os.path.exists(target_path):
        os.symlink(db_path, target_path)
        print(f"Linked database to {target_path}")

def main():
    # Configuration
    db_path = "./data/db.sqlite"
    example_path = "./examples"
    output_dir = "./output"
    search_dir = os.path.join(output_dir, "search")
    log_path = os.path.join(output_dir, "logs")
    
    question = "Show me all users older than 30 years"
    task = "lite"
    
    # Create directories
    os.makedirs(example_path, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    """
    # Step 1: Create dummy database
    create_dummy_db(db_path)
    
    # Step 2: Setup example folder structure
    setup_example_structure(db_path, example_path)
    
    # Step 3: Run reconstruct_data functions
    print("\nRunning database reconstruction...")
    make_folder(argparse.Namespace(example_folder=example_path))
    compress_ddl(
        example_folder=example_path,
        add_description=True,
        add_sample_rows=True,
        rm_digits=False,
        schema_linked=False,
        clear_long_eg_des=True
    )
    
    # Step 4: Run schema linking
    print("\nRunning schema linking...")
    linked_json_path = os.path.join(output_dir, "linked.json")
    dictionaries, _ = get_dictionary(example_path, task)
    ask_model_sl2(example_path, linked_json_path, dictionaries)
    reduce_ddl(example_path, dictionaries, linked_json_path)
    
    # Step 5: Get table info
    print("\nGetting table information...")
    sql_data = "dummy_db"  # Matches our example folder name
    table_info = get_table_info(example_path, sql_data, api=None, clear_des=True)
    
    """
    table_info = """
Database schema for dummy_db:

Table full name: users
Column name: id Type: INTEGER, PRIMARY KEY
Column name: name Type: TEXT
Column name: age Type: INTEGER
Sample rows from users:
| id | name   | age |
|----|--------|-----|
| 1  | Alice  | 30  |
| 2  | Bob    | 25  |
| 3  | Charlie| 35  |

--------------------------------------------------
Table full name: orders
Column name: order_id Type: INTEGER, PRIMARY KEY
Column name: user_id Type: 
	INTEGER, FOREIGN KEY REFERENCES users(id))
Column name: amount Type: REAL
Sample rows from orders:
| order_id | user_id | amount |
|----------|---------|--------|
| 101      | 1       | 99.99  |
| 102      | 2       | 149.99 |

The table structure information is:
{
    "users": ["id", "name", "age"],
    "orders": ["order_id", "user_id", "amount"]
}
"""
    # Step 6: Initialize components
    chat_session_pre = GPTChat(model="Snowflake/Arctic-Text2SQL-R1-7B", temperature=0.7)
    chat_session = GPTChat(model="Snowflake/Arctic-Text2SQL-R1-7B", temperature=0.7)
    sql_env_instance = SqlEnv()
    
    # Step 7: Initialize agent
    agent = REFORCE(
        db_path=example_path,
        sql_data="localdummy",
        search_directory=search_dir,
        prompt_class=Prompts(),
        sql_env=sql_env_instance,
        chat_session_pre=chat_session_pre,
        chat_session=chat_session,
        log_save_path=log_path,
        db_id="dummy_db",
        task=task
    )
    
    print("\nRunning SQL generation...")
    agent.gen(
        args=argparse.Namespace(
            do_self_consistency=False,
            early_stop=True,
            max_iter=3,
            temperature=0.7,
            save_all_results=True,
            task=task,
            omnisql_format_pth=None
        ),
        logger=None,  # Simplified for demo
        question=question,
        format_csv=None,
        table_struct=table_info,
        table_info=table_info,
        response_pre_txt=None,
        pre_info=None,
        csv_save_path=os.path.join(output_dir, "result.csv"),
        sql_save_path=os.path.join(output_dir, "result.sql"),
        task=task
    )
    
    print("\nPipeline complete. Results in output directory.")

if __name__ == "__main__":
    main()
