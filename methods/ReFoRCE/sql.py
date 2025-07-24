import sqlite3
import io
import csv
from typing import Optional, Any, Dict, List, Union
from utils import hard_cut
from google.cloud import bigquery
from google.oauth2 import service_account
import snowflake.connector
import json
import pandas as pd
from func_timeout import func_timeout, FunctionTimedOut

class SqlEnv:
    def __init__(self):
        """Initializes the SqlEnv with an empty dictionary of connections."""
        self.conns: Dict[str, Any] = {}

    def get_rows(self, cursor: Any, max_len: int) -> List[Any]:
        """
        Retrieves rows from the cursor until max_len of string representation is reached.

        :param cursor: Database cursor.
        :param max_len: Maximum total string length of rows.
        :return: List of rows.
        """
        rows = []
        current_len = 0
        for row in cursor:
            row_str = str(row)
            rows.append(row)
            if current_len + len(row_str) > max_len:
                break
            current_len += len(row_str)
        return rows

    def get_csv(self, columns: List[str], rows: List[Any]) -> str:
        """
        Converts rows and column headers to CSV format.

        :param columns: List of column names.
        :param rows: List of row tuples.
        :return: CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        csv_content = output.getvalue()
        output.close()
        return csv_content

    def start_db_sqlite(self, sqlite_path: str) -> None:
        """
        Opens a read-only connection to a SQLite database.

        :param sqlite_path: Path to SQLite file.
        """
        if sqlite_path not in self.conns:
            uri = f"file:{sqlite_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self.conns[sqlite_path] = conn

    def start_db_sf(self, ex_id: str) -> None:
        """
        Starts a Snowflake connection using credentials from JSON file.

        :param ex_id: Experiment or connection ID.
        """
        if ex_id not in self.conns:
            snowflake_credential = json.load(open("./snowflake_credential.json"))
            self.conns[ex_id] = snowflake.connector.connect(**snowflake_credential)

    def close_db(self) -> None:
        """
        Closes all open database connections.
        """
        for key, conn in list(self.conns.items()):
            try:
                if conn:
                    conn.close()
                    del self.conns[key]
            except Exception as e:
                print(f"When closing DB for {key}: {e}")

    def exec_sql_sqlite(
        self, sql_query: str, save_path: Optional[str] = None, max_len: int = 30000, sqlite_path: Optional[str] = None
    ) -> Union[str, int]:
        """
        Executes a SQL query on a SQLite database.

        :param sql_query: SQL query string.
        :param save_path: Optional path to save CSV output.
        :param max_len: Max length of result string.
        :param sqlite_path: Path to SQLite database file.
        :return: CSV string, error string, or 0 if saved to file.
        """
        cursor = self.conns[sqlite_path].cursor()
        try:
            cursor.execute(sql_query)
            column_info = cursor.description
            rows = self.get_rows(cursor, max_len)
            columns = [desc[0] for desc in column_info]
        except Exception as e:
            return "##ERROR##" + str(e)
        finally:
            try:
                cursor.close()
            except Exception as e:
                print("Failed to close cursor:", e)

        if not rows:
            return "No data found for the specified query.\n"
        else:
            csv_content = self.get_csv(columns, rows)
            if save_path:
                with open(save_path, 'w', newline='') as f:
                    f.write(csv_content)
                return 0
            else:
                return hard_cut(csv_content, max_len)

    def exec_sql_sf(
        self, sql_query: str, save_path: Optional[str], max_len: int, ex_id: str
    ) -> Union[str, int]:
        """
        Executes a SQL query on a Snowflake database.

        :param sql_query: SQL query string.
        :param save_path: Path to save CSV output.
        :param max_len: Max output length.
        :param ex_id: Experiment or connection ID.
        :return: CSV string, error string, or 0 if saved to file.
        """
        with self.conns[ex_id].cursor() as cursor:
            try:
                cursor.execute(sql_query)
                column_info = cursor.description
                rows = self.get_rows(cursor, max_len)
                columns = [desc[0] for desc in column_info]
            except Exception as e:
                return "##ERROR##" + str(e)

        if not rows:
            return "No data found for the specified query.\n"
        else:
            csv_content = self.get_csv(columns, rows)
            if save_path:
                with open(save_path, 'w', newline='') as f:
                    f.write(csv_content)
                return 0
            else:
                return hard_cut(csv_content, max_len)

    def exec_sql_bq(
        self, sql_query: str, save_path: Optional[str], max_len: int
    ) -> Union[str, int]:
        """
        Executes a SQL query on Google BigQuery.

        :param sql_query: SQL query string.
        :param save_path: Path to save CSV output.
        :param max_len: Max output length.
        :return: CSV string, error string, or 0 if saved to file.
        """
        bigquery_credential = service_account.Credentials.from_service_account_file("./bigquery_credential.json")
        client = bigquery.Client(credentials=bigquery_credential, project=bigquery_credential.project_id)
        query_job = client.query(sql_query)
        try:
            result_iterator = query_job.result()
        except Exception as e:
            return "##ERROR##" + str(e)

        rows = []
        current_len = 0
        for row in result_iterator:
            if current_len > max_len:
                break
            current_len += len(str(dict(row)))
            rows.append(dict(row))
        df = pd.DataFrame(rows)

        if df.empty:
            return "No data found for the specified query.\n"
        else:
            if save_path:
                df.to_csv(save_path, index=False)
                return 0
            else:
                return hard_cut(df.to_csv(index=False), max_len)

    def execute_sql_api(
        self,
        sql_query: str,
        ex_id: str,
        save_path: Optional[str] = None,
        api: str = "sqlite",
        max_len: int = 30000,
        sqlite_path: Optional[str] = None,
        timeout: int = 300
    ) -> Union[str, Dict[str, str]]:
        """
        Executes a SQL query using the specified API.

        :param sql_query: SQL query string.
        :param ex_id: Experiment or connection ID.
        :param save_path: Path to save CSV output.
        :param api: API to use: 'sqlite', 'snowflake', or 'bigquery'.
        :param max_len: Max output length.
        :param sqlite_path: Path to SQLite file.
        :param timeout: Timeout in seconds.
        :return: CSV string, or error dictionary.
        """
        if api == "bigquery":
            result = self.exec_sql_bq(sql_query, save_path, max_len)
        elif api == "snowflake":
            if ex_id not in self.conns:
                self.start_db_sf(ex_id)
            result = self.exec_sql_sf(sql_query, save_path, max_len, ex_id)
        elif api == "sqlite":
            if sqlite_path not in self.conns:
                self.start_db_sqlite(sqlite_path)
            result = self.execute_sqlite_with_timeout(sql_query, save_path, max_len, sqlite_path, timeout=timeout)

        if "##ERROR##" in str(result):
            return {"status": "error", "error_msg": str(result)}
        else:
            return str(result)

    def execute_sqlite_with_timeout(
        self,
        sql_query: str,
        save_path: Optional[str],
        max_len: int,
        sqlite_path: Optional[str],
        timeout: int = 300
    ) -> Union[str, Dict[str, str]]:
        """
        Executes a SQLite query with a timeout.

        :param sql_query: SQL query string.
        :param save_path: Path to save CSV output.
        :param max_len: Max output length.
        :param sqlite_path: Path to SQLite file.
        :param timeout: Timeout in seconds.
        :return: CSV string, or error dictionary.
        """
        try:
            result = func_timeout(timeout, self.exec_sql_sqlite, args=(sql_query, save_path, max_len, sqlite_path))
            return str(result)
        except FunctionTimedOut:
            print(f"##ERROR## {sql_query} Timed out")
            return {"status": "error", "error_msg": f"##ERROR## {sql_query} Timed out\n"}
        except Exception as e:
            print(f"##ERROR## {sql_query} Exception: {e}")
            return {"status": "error", "error_msg": f"##ERROR## {sql_query} Exception: {e}\n"}
