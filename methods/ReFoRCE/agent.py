"""
REFORCE class for generating, correcting, and refining SQL queries using
a prompt-based approach with chat models and an SQL execution environment.
Handles SQL exploration, self-correction, iterative self-refinement, and
voting to select the best SQL query result.
"""
from utils import hard_cut, get_values_from_table, get_api_name, filter_bijection_like_dict, compare_pandas_table, is_valid_result, get_sqlite_path, split_sql
from sql import SqlEnv
import pandas as pd
from io import StringIO
import os
import shutil
import csv
from prompt import Prompts
from typing import Type
from chat import GPTChat
import sys
csv.field_size_limit(sys.maxsize)

class REFORCE:
    def __init__(self, 
                db_path: str, 
                sql_data: dict, 
                search_directory: str, 
                prompt_class: Type[Prompts], 
                sql_env: Type[SqlEnv] = None, 
                chat_session_pre: Type[GPTChat] = None, 
                chat_session: Type[GPTChat] = None, 
                log_save_path: str = None, 
                db_id: str = None, 
                task: str = None) -> None:
        """
        :param db_path: Path to the database.
        :param sql_data: SQL related metadata.
        :param search_directory: Directory to save search outputs.
        :param prompt_class: Prompt generation class.
        :param sql_env: SQL environment instance/class.
        :param chat_session_pre: Pre-exploration chat session instance.
        :param chat_session: Main chat session instance.
        :param log_save_path: Path to save logs.
        :param db_id: Database identifier.
        :param task: Task description.
        """
        self.csv_save_name = "result.csv"
        self.sql_save_name = "result.sql"
        self.log_save_name = "log.log"
        self.log_vote_name = "vote.log"
        self.empty_result = "No data found for the specified query.\n"

        self.api = get_api_name(sql_data)
        self.sqlite_path = get_sqlite_path(db_path, sql_data, db_id, task)

        self.sql_id = log_save_path

        self.complete_csv_save_path = os.path.join(search_directory, self.csv_save_name)
        self.complete_sql_save_path = os.path.join(search_directory, self.sql_save_name)
        self.complete_log_save_path = os.path.join(search_directory, self.log_save_name)
        self.complete_vote_log_path = os.path.join(search_directory, self.log_vote_name)

        self.prompt_class = prompt_class
        self.max_try = 3
        self.csv_max_len = 500

        self.sql_env = sql_env
        self.chat_session_pre = chat_session_pre
        self.chat_session = chat_session


    def execute_sqls(self, sqls: list[str], logger: object) -> list[dict]:
        """
        Execute multiple SQL queries and collect their execution results.

        :param sqls: List of SQL query strings to execute.
        :param logger: Logger object to record execution details and errors.
        :return: List of dictionaries where each dictionary contains a SQL query and its result or error.
        """
        result_dic_list = []
        error_rec = []
        while sqls:
            if len(result_dic_list) > 10 or len(self.chat_session_pre.messages) > 20:
                break
            result_dic = {}
            sql = sqls[0]
            sqls = sqls[1:]
            logger.info("[Try to execute]\n" + sql + "\n[Try to execute]")
            results = self.sql_env.execute_sql_api(sql, self.sql_id, api=self.api, max_len=self.csv_max_len, sqlite_path=self.sqlite_path)

            if isinstance(results, str) and results != self.empty_result:
                result_dic['sql'] = sql
                result_dic['res'] = results
                # self.chat_session_pre.messages.append({"role": "user", "content": f"Successfully executed. SQL:\n{sql}\nResults:\n{results}"})
                logger.info("[Successfully executed]\n" +  f"Successfully executed. SQL:\n{sql}\nResults:\n{results}" + "\n[Successfully executed]")
                result_dic_list.append(result_dic)
            else:
                logger.info("[Error occurred]\n" + str(results) + "\n[Error occurred]")
                max_try = self.max_try
                simplify = False
                corrected_sql = None
                while not isinstance(results, str) or results == self.empty_result:
                    error_rec.append(0)
                    if max_try == 0:
                        break
                    if results == self.empty_result:
                        simplify = True
                    corrected_sql = self.self_correct(sql, results, logger, simplify=simplify)
                    if not isinstance(corrected_sql, list) or len(corrected_sql) < 1:
                        print(f"{self.sql_id}: Not a valid SQL: {corrected_sql}")
                        continue
                    corrected_sql = max(corrected_sql, key=len)
                    results = self.sql_env.execute_sql_api(corrected_sql, self.sql_id, api=self.api, max_len=self.csv_max_len, sqlite_path=self.sqlite_path)
                    logger.info("[Results for corrected sql]\n"+str(results)+"\n[Results for corrected sql]")
                    max_try -= 1
                    simplify = False

                if isinstance(results, str) and results != self.empty_result:
                    error_rec.append(1)
                    if sqls != []:
                        response = self.chat_session_pre.get_model_response(self.prompt_class.get_exploration_refine_prompt(sql, corrected_sql, sqls), "sql")

                        if isinstance(response, list) and response != []:
                            response_sqls = []
                            for s in response:
                                try:
                                    queries = split_sql(s)
                                    response_sqls += queries
                                except:
                                    pass
                            if len(response_sqls) >= len(sqls) // 2:
                                sqls = response_sqls
                                logger.info("[Corrected other sqls]\n"+self.chat_session_pre.messages[-1]['content']+"\n[Corrected other sqls]")
                else:
                    error_rec.append(0)
                    # Many times error, return
                    if len(error_rec) > 3 and sum(error_rec[-3:]) == 0:
                        return result_dic_list
                    continue
                if not corrected_sql:
                    continue
                result_dic['sql'] = corrected_sql
                result_dic['res'] = results
                # self.chat_session_pre.messages.append({"role": "user", "content": f"Successfully corrected. SQL:\n{corrected_sql}\nResults:\n{results}"})
                logger.info("[Successfully corrected]\n" +  f"Successfully executed. SQL:\n{sql}\nResults:\n{results}" + "\n[Successfully corrected]")
        return result_dic_list

    def self_correct(
        self, 
        sql: str, 
        error: str, 
        logger: object, 
        simplify: bool = False
    ) -> str | list[str] | None:
        """
        Attempt to automatically fix a SQL query based on the error message received.

        :param sql: The original SQL query string that caused an error.
        :param error: Error message returned from the failed SQL execution.
        :param logger: Logger object for recording correction attempts.
        :param simplify: Flag indicating whether to simplify the SQL during correction.
        :return: The corrected SQL string, a list of alternative SQL strings, or None if correction was not possible.
        """
        prompt = self.prompt_class.get_exploration_self_correct_prompt(sql, error)
        if simplify:
            prompt += "Since the output is empty, please simplify some conditions of the past sql.\n"
        response = self.chat_session_pre.get_model_response(prompt, "sql")

        max_try = self.max_try
        while max_try > 0 and (not isinstance(response, str) or len(response) > 1):
            response = self.chat_session_pre.get_model_response("Please generate only one SQL with thinking process.", "sql")
            max_try -= 1
        logger.info("[Corrected SQL]\n" + self.chat_session_pre.messages[-1]['content'] + "\n[Corrected SQL]")
        return response

    def format_answer(self, task: str, chat_session: type[GPTChat]) -> str:
        """
        Convert the output of a chat session into a formatted CSV string.

        :param task: Description or identifier of the current task.
        :param chat_session: Instance of the chat session containing the output to format.
        :return: A string formatted as CSV representing the chat session’s answer.
        """
        format_prompt = self.prompt_class.get_format_prompt()
        response_csv = chat_session.get_model_response("Task: " + task + format_prompt, "csv")
        response_csv = "```csv\n"+response_csv[0].split("\n")[0]+"\n```"
        return response_csv

    def exploration(
        self, 
        task: str, 
        table_struct: dict, 
        table_info: str, 
        logger: object
    ) -> tuple[str, str, int]:
        """
        Conduct the initial exploration to generate candidate SQL queries.

        :param task: Description of the task or question to explore.
        :param table_struct: Dictionary representing the database tables and schema.
        :param table_info: Informational string describing tables or database.
        :param logger: Logger to track exploration progress and issues.
        :return: A tuple containing:
            - A preparation information string,
            - The generated exploration SQL query as text,
            - The number of remaining retry attempts allowed.
        """
        pre_info = ''
        task = table_info + "\nTask: " + task + "\n"
        max_try = self.max_try
        while max_try > 0:
            exploration_prompt = task + self.prompt_class.get_exploration_prompt(self.api, table_struct)

            response_pre = self.chat_session_pre.get_model_response(exploration_prompt, "sql")
            response_pre_txt = self.chat_session_pre.messages[-1]['content']
            logger.info("[Exploration]\n" + response_pre_txt + "\n[Exploration]")
            if not isinstance(response_pre, list):
                max_try -= 1
                continue
            
            if len(response_pre) == 1:
                response_pre = split_sql(response_pre[0])
            if len(response_pre) < 3:
                max_try -= 1
                print(f"{self.sql_id}: Few sqls, retry preparation.")
                continue
            results_pre_dic_list = self.execute_sqls(response_pre, logger)
            sql_count = 0
            for dic in results_pre_dic_list:
                pre_info += "Query:\n" + dic['sql'] + "\nAnswer:\n" + str(dic['res'])
                if isinstance(dic['res'], str):
                    sql_count += 1

            if sql_count == 0:
                print(f"{self.sql_id}: sql_count: {sql_count}, len(response_pre): {len(response_pre)}. Inadequate preparation, break.")
                max_try = 0
                break

            if len(pre_info) < 1e5:
                break
            print(f"{self.sql_id}: Too long, retry preparation.")
            pre_info = ''
            max_try -= 1

        return pre_info, response_pre_txt, max_try

    def self_refine(
        self, 
        args: object, 
        logger: object, 
        question: str, 
        format_csv: str, 
        table_struct: dict, 
        table_info: str, 
        response_pre_txt: str, 
        pre_info: str, 
        csv_save_path: str, 
        sql_save_path: str, 
        task: str | None = None
    ) -> None:
        """
        Improve SQL queries iteratively using feedback from previous runs to refine results.

        :param args: Configuration or parameters controlling the refinement process.
        :param logger: Logger for recording refinement steps and outcomes.
        :param question: The original natural language question or task statement.
        :param format_csv: CSV formatting string template used for output.
        :param table_struct: Database table structure dictionary.
        :param table_info: String describing table information.
        :param response_pre_txt: Text response from the preliminary exploration phase.
        :param pre_info: Supplementary info from the pre-exploration.
        :param csv_save_path: File path to save the refined results as CSV.
        :param sql_save_path: File path to save refined SQL queries.
        :param task: Optional task description or identifier.
        """
        itercount = 0
        results_values = []
        results_tables = []

        self_refine_prompt = self.prompt_class.get_self_refine_prompt(table_info, task, pre_info, question, self.api, format_csv, table_struct, args.omnisql_format_pth)

        error_rec = []
        while itercount < args.max_iter:
            logger.info(f"itercount: {itercount}")
            logger.info("[Self-refine]\n" + self_refine_prompt + "\n[Self-refine]")
            
            max_try = self.max_try
            while max_try > 0:
                response = self.chat_session.get_model_response(self_refine_prompt, "sql")
                if not isinstance(response, list) or len(response) != 1:
                    self_refine_prompt = "Please output one SQL only."
                else:
                    break
                max_try -= 1
            if not isinstance(response, list) or response == []:
                if os.path.exists(csv_save_path):
                    os.remove(csv_save_path)
                print(f"{self.sql_id}: Error when generating final SQL.")
                break
            logger.info("[Try to run SQL in self-refine]\n" +self.chat_session.messages[-1]['content'] + "\n[Try to run SQL in self-refine]")
            response = response[0]
            executed_result = self.sql_env.execute_sql_api(response, self.sql_id, csv_save_path, api=self.api, sqlite_path=self.sqlite_path)
            error_rec.append(str(executed_result))
            if args.early_stop and len(error_rec) > 3:
                # Eraly stop for repeatitive empty results
                if len(set(error_rec[-4:])) == 1 and error_rec[-1] == self.empty_result:
                    logger.info("No data found for the specified query, remove file.")                    
                    if os.path.exists(csv_save_path):
                        os.remove(csv_save_path)
                    break
            
            if executed_result == '0':
                if not args.do_self_consistency:
                    with open(sql_save_path, "w") as f:
                        f.write(response)
                        break                    
                self_consistency_prompt = self.prompt_class.get_self_consistency_prompt(question, format_csv)
                with open(csv_save_path) as f:
                    csv_data = f.readlines()
                    csv_data_str = ''.join(csv_data)
                logger.info(f"[Executed results in self-refine]\n{hard_cut(csv_data_str, self.csv_max_len)}\n[Executed results in self-refine]")
                self_consistency_prompt += "Current snswer: \n" + hard_cut(csv_data_str, self.csv_max_len)
                self_consistency_prompt += f"Current sql:\n{response}"
                if '"""' in csv_data_str:
                    self_consistency_prompt += 'Please remove """ in results. Use CAST: CAST(column_name AS STRING).\n'

                # Filter results with null columns
                csv_buffer = StringIO(csv_data_str)
                df_csv = pd.read_csv(csv_buffer).fillna("")

                nested_val = [(item) for i, row in enumerate(df_csv.values.tolist()) for j, item in enumerate(row) if isinstance(item, str) and '\n' in item in item]
                df_csv_copy = df_csv.copy()
                for col in df_csv.select_dtypes(include=['float']):
                    df_csv_copy[col] = df_csv[col].round(2)
                sort_col = df_csv_copy.columns[0]
                df_csv_copy_sorted = df_csv_copy[sort_col].astype(str)
                csv_data_str_round2 = df_csv_copy_sorted.to_string()
                df_csv_str = df_csv.astype(str)
                if get_values_from_table(csv_data_str_round2) not in results_values:
                    if nested_val:
                        self_consistency_prompt += f"Values {nested_val} are nested. Please correct them. e.g. Transfer '[\nA,\n B\n]' to 'A, B'.\n"
                    elif not ((df_csv_str == "0") | (df_csv_str == "")).all().any():
                            results_values.append(get_values_from_table(csv_data_str_round2))
                            results_tables.append(csv_data_str)
                    else:
                        empty_columns = df_csv_str.columns[((df_csv_str == "0") | (df_csv_str == "")).all()].to_list()
                        self_consistency_prompt += f"Empty results in Column {empty_columns}. Please correct them.\n"
                else:
                    # self-consistency
                    logger.info(f"[Consistent results]\n{hard_cut(csv_data_str, 500)}\n[Consistent results]")
                    with open(sql_save_path, "w") as f:
                        f.write(response)
                    break
                
                if any(keyword in response for keyword in self.prompt_class.get_condition_onmit_tables()):
                    self_consistency_prompt += self.prompt_class.get_prompt_dialect_list_all_tables(table_struct, self.api)
                if args.save_all_results:
                    save_path = save_path[:-4] + str(itercount) + save_path[-4:]
                self_refine_prompt = self_consistency_prompt
            
            else:
                self_refine_prompt = f"Input sql:\n{response}\nThe error information is:\n" + str(executed_result) + "\nPlease correct it and output only 1 complete SQL query."

            itercount += 1

        logger.info(f"Total iteration counts: {itercount}")
        if itercount == args.max_iter and not args.save_all_results:
            if os.path.exists(csv_save_path):
                os.remove(csv_save_path)
            logger.info("Max Iter, remove file")
        print(f"{self.sql_id}: chat_session len: {self.chat_session.get_message_len()}")

    def gen(
        self, 
        args: object, 
        logger: object, 
        question: str, 
        format_csv: str, 
        table_struct: dict, 
        table_info: str, 
        response_pre_txt: str, 
        pre_info: str, 
        csv_save_path: str, 
        sql_save_path: str, 
        task: str | None = None,
        print_output: bool = False
    ) -> None:
        """
        Generate SQL queries from natural language questions, including exploration and refinement phases.

        :param args: Parameters and configurations for generation.
        :param logger: Logger instance for tracking generation progress.
        :param question: Input natural language question.
        :param format_csv: CSV output formatting string.
        :param table_struct: Schema dictionary for tables.
        :param table_info: Textual information about database tables.
        :param response_pre_txt: Preliminary response text from exploration.
        :param pre_info: Additional info from exploration.
        :param csv_save_path: Destination path for CSV output.
        :param sql_save_path: Destination path for saving generated SQL.
        :param task: Optional task description.
        """
        gen_prompt = self.prompt_class.get_self_refine_prompt(table_info, task, pre_info, question, self.api, format_csv, table_struct, args.omnisql_format_pth)
        if logger:
            logger.info("[Gen]\n" + gen_prompt + "\n[Gen]")
        max_try = self.max_try
        while max_try > 0:
            response = self.chat_session.get_model_response(gen_prompt, "sql")
            if not isinstance(response, list) or len(response) != 1:
                gen_prompt = "Please output one SQL only."
            else:
                break
            max_try -= 1
        if not isinstance(response, list) or response == []:
            if os.path.exists(csv_save_path):
                os.remove(csv_save_path)
            print(f"{self.sql_id}: Error when generating final SQL.")
        if logger:
            logger.info("[Gen SQL]\n" +self.chat_session.messages[-1]['content'] + "\n[Gen SQL]")
        response = response[0]
        if print_output:
            print("Question", question)
            print("Response", response)
            return 

        executed_result = self.sql_env.execute_sql_api(response, self.sql_id, csv_save_path, api=self.api, sqlite_path=self.sqlite_path)
        if executed_result == '0':
            with open(sql_save_path, "w") as f:
                f.write(response)

    def model_vote(
        self,
        result: list[str],
        sql_paths: list[str],
        search_directory: str,
        args: object,
        table_info: str,
        task: str
    ) -> None:
        """
        Perform majority or weighted voting over generated SQL queries to select the best candidate.

        :param result: List of natural language questions or related outputs used to guide voting.
        :param sql_paths: List of file paths where generated SQL queries are stored.
        :param search_directory: Directory containing exploration results and related files.
        :param args: Arguments object containing configurations such as voting strategy, temperature, etc.
        :param table_info: String representation of the table schema and metadata.
        :param task: Task identifier or label for the current query generation context.
        """
        chat_session = GPTChat(args.azure, args.model_vote)
        max_value = max(result.values())
        max_dict = {k: v for k, v in result.items() if v == max_value}
        # print(max_dict)

        prompt = f"You are given DB info, task and candidate SQLs and thier results. You should choose the most correct one based on database info:\n{table_info}. The task is: {task}. Here are some candidate sqls and answers: \n"
        for sql, counts in max_dict.items():
            sql_path = os.path.join(search_directory, sql)
            csv_path = os.path.join(search_directory, sql_paths[sql])

            if os.path.exists(sql_path) and os.path.exists(csv_path):
                prompt += "SQL file name: " + sql + "\n"
                with open(sql_path) as f:
                    prompt += f.read()
                prompt += "CSV file name: " + sql_paths[sql] + "\n"
                with open(csv_path) as f:
                    prompt += hard_cut(f.read(), 5000)

        max_try = 3
        prompt += "Compare the SQL and results of each answer, think step by step and choose one SQL as the correct answer. Output thinking process and the name of sql in ```plaintext\nxxx.sql``` format. You should not ingnore 'plaintext'.\n"
        prompt += "For results with null or zero values, they tend to be wrong answer.\n"
        prompt += "You reasoning step should be: 1. Exclude unreasonable results. 2. Check results if aligning with task description. 3. Analyze SQL if aligning with task description.\n"
        response = chat_session.get_model_response(prompt, "plaintext")
        while max_try > 0:
            if not response or not isinstance(response, list) or ".sql" not in response[0]:
                print(f"{search_directory}, remained max_try for voting: {max_try}, {response}")
                response = chat_session.get_model_response("Please output the name of sql in ```plaintext\nxxx.sql``` format. You should not ingnore 'plaintext'.", "plaintext")
            else:
                break
            max_try -= 1
        if max_try == 0:
            print(f"{search_directory} Empty")
            return
        with open(os.path.join(search_directory, response[0].strip())) as f:
            selected_sql = f.read()
        sql_env = SqlEnv()
        if sql_env.execute_sql_api(selected_sql, self.sql_id, self.complete_csv_save_path, api=self.api, sqlite_path=self.sqlite_path) == '0':
            with open(self.complete_sql_save_path, "w") as f:
                f.write(selected_sql)
            with open(self.complete_vote_log_path, "w") as f:
                f.write("[Vote]\n"+prompt+"\n[Vote]")
                f.write(chat_session.messages[-1]['content'])
        sql_env.close_db()

    def vote_result(
        self,
        search_directory: str,
        args: object,
        sql_paths: dict[str, str],
        table_info: str,
        task: str
    ) -> None:
        """
        Perform result-level majority voting across multiple generated SQL outputs, 
        resolving ties if necessary, and selecting the final query output.

        :param search_directory: Directory containing SQL and result (.csv) files to vote on.
        :param args: Arguments object specifying configuration flags (e.g. `model_vote`, `final_choose`, `random_vote_for_tie`).
        :param sql_paths: Dictionary mapping SQL file keys to their respective relative paths.
        :param table_info: Serialized representation of the schema, used during model-based voting.
        :param task: Name of the current task (e.g. "lite", "BIRD") to contextualize voting behavior.
        """
        # filter answer
        result = {}
        result_name = {}
        result_all = {}
        all_values = []
        for v in sql_paths.values():
            if os.path.exists(os.path.join(search_directory, v)):
                all_values.append(os.path.join(search_directory, v))

        if len(all_values) > 1:
            for key, value in sql_paths.items():
                complete_value = os.path.join(search_directory, value)
                if os.path.exists(complete_value):
                    same_ans = 0
                    for v in all_values:
                        v_df = pd.read_csv(v)
                        c_df = pd.read_csv(complete_value)
                        if v != complete_value and is_valid_result(v_df) and compare_pandas_table(v_df, c_df, ignore_order=True) and v_df.shape == c_df.shape:
                            same_ans += 1
                            result_name[v] = result_name.get(v, []) + [complete_value]
                        # print(result)
                    result_all[key] = same_ans
            result_name = filter_bijection_like_dict(result_name)
            for key, value in result_name.items():
                result[key.split("/")[-1].replace(".csv", ".sql")] = len(value)
        if not result:
            if not result_all and not all_values:
                print(f"{search_directory} empty results")
                return
            elif args.model_vote:
                assert all(v == 0 for k, v in result_all.items()), result
                result_all = {k: v + 1 for k, v in result_all.items()}
                # print(result_all)
                self.model_vote(result_all, sql_paths, search_directory, args, table_info, task)
            elif args.final_choose:
                csv_pth = all_values[0]
                shutil.copy2(csv_pth.replace(".csv", ".sql"), self.complete_sql_save_path)
                shutil.copy2(csv_pth, self.complete_csv_save_path) 
                shutil.copy2(csv_pth.replace("result.csv", "log.log"), self.complete_log_save_path)               
            else:
                print(f"{search_directory} Empty, return")
            return

        sorted_dict = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
        first_key = next(iter(sorted_dict))

        vote_counts = list(sorted_dict.values())
        max_vote = max(vote_counts)
        num_with_max_vote = vote_counts.count(max_vote)
        has_tie = num_with_max_vote > (max_vote + 1)
        if has_tie:
            assert num_with_max_vote % (max_vote + 1) == 0, result_name
            if args.model_vote:
                self.model_vote(result, sql_paths, search_directory, args, table_info, task)
                return
            if not args.random_vote_for_tie:
                print(f"{search_directory} has_tie {sorted_dict}, return")
                return

        shutil.copy2(os.path.join(search_directory, first_key), self.complete_sql_save_path)
        shutil.copy2(os.path.join(search_directory, sql_paths[first_key]), self.complete_csv_save_path)
        shutil.copy2(os.path.join(search_directory, first_key.replace(self.sql_save_name, self.log_save_name)), self.complete_log_save_path)