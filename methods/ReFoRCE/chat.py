from typing import Dict, List, Optional, Union
from openai import OpenAI, AzureOpenAI
from utils import extract_all_blocks
import os
import sys
import mlflow

# Mock client simulating openai client behavior
class MockOpenAIClient:
    def __init__(self):
        self.chat = self.Chat()

    class Chat:
        class Completions:
            def create(self, *, model, messages, temperature, max_output_tokens):
                # Return a fixed response structure similar to OpenAI chat completion
                return type("Response", (), {
                    "choices": [
                        type("Choice", (), {
                            "message": type("Message", (), {
                                "content": "Mocked response to: " + messages[-1]["content"][:30]
                            })()
                        })()
                    ]
                })()
        def __init__(self):
            self.completions = self.Completions()

class GPTChat:
    def __init__(self,
                 azure: bool = False,
                 model: str = "gpt-4o",   # mock
                 temperature: Union[int, float] = 1,
                 max_context_tokens: Optional[int] = None,
                 max_response_tokens: Optional[int] = None):
        # the mock argument is to mock the OpenAI client. This can
        # be used to test the code without needing a model.
        # The mocked response is the first 30 characters in the prompt.
        # 

        if model == "mock":
            self.client = MockOpenAIClient()
        elif not azure:
            if model in ["o1-preview", "o1-mini"]:
                self.client = OpenAI(
                    api_key=os.environ.get("OPENAI_API_KEY"),
                    api_version="2024-12-01-preview"
                )
            elif model in ["deepseek-reasoner"]:
                self.client = OpenAI(
                    base_url="https://api.deepseek.com",
                    api_key=os.environ.get("DS_API_KEY"),
                )                
            else: 
                # Use a locally hosted model
                self.client = OpenAI(
                    base_url="http://localhost:8080/v1",
                    api_key="-"
                )
            # else:
            #     raise NotImplementedError("Unsupported API Key")  
        else:
            if model in ["o1-preview", "o1-mini", "o3", "o4-mini"]:
                self.client = AzureOpenAI(
                    azure_endpoint = os.environ.get("AZURE_ENDPOINT"),
                    api_key=os.environ.get("AZURE_OPENAI_KEY"),
                    api_version="2024-12-01-preview"
                )
            elif model in ["o3-pro"]:
                self.client = AzureOpenAI(
                    azure_endpoint = os.environ.get("AZURE_ENDPOINT"),
                    api_key=os.environ.get("AZURE_OPENAI_KEY"),
                    api_version="2025-03-01-preview"
                )             
            else:
                self.client = AzureOpenAI(
                    azure_endpoint = os.environ.get("AZURE_ENDPOINT"),
                    api_key=os.environ.get("AZURE_OPENAI_KEY"),
                    api_version="2024-05-01-preview"
                )

        self.messages = []
        self.model = model
        self.temperature = float(temperature)

        self.max_context_tokens = max_context_tokens
        self.max_response_tokens = max_response_tokens

    def get_response(self, prompt: str) -> str:
        self.messages.append({"role": "user", "content": prompt})
        if self.model in ["o3-pro"]:
            response = self.client.responses.create(
                model=self.model,
                input=self.messages,
                temperature=self.temperature
                # max_tokens=self.max_response_tokens
            )
            main_content = response.output_text
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature
                # max_tokens=self.max_response_tokens
            )
            main_content = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": main_content})
        return main_content

    def get_model_response(self, prompt: str, code_format: Optional[str] = None) -> List[str]:
        code_blocks = []
        max_try = 3
        while code_blocks == [] and max_try > 0:
            max_try -= 1
            try:
                response = self.get_response(prompt)
            except Exception as e:
                print(f"max_try: {max_try}, exception: {e}")
                continue
            code_blocks = extract_all_blocks(response, code_format)
        if max_try == 0 or code_blocks == []:
            print(f"get_model_response() exit, max_try: {max_try}, code_blocks: {code_blocks}")
            sys.exit(0)
            
        return code_blocks

    def get_model_response_txt(self, prompt: str) -> str:
        max_try = 3
        while max_try > 0:
            max_try -= 1
            try:
                response = self.get_response(prompt)
            except Exception as e:
                print(f"max_try: {max_try}, exception: {e}")
                continue
            break
        if max_try == 0:
            print(f"get_model_response_txt() exit, max_try: {max_try}")
            sys.exit(0)
        
        return response

    def get_message_len(self) -> Dict[str, int]:
        return {
            "prompt_len": sum(len(item["content"]) for item in self.messages if item["role"] == "user"),
            "response_len": sum(len(item["content"]) for item in self.messages if item["role"] == "assistant"),
            "num_calls": len(self.messages) // 2
        }
    
    def init_messages(self) -> None:
        self.messages = []

if __name__ == "__main__":
    chat = GPTChat(model="mock")
    print(chat.get_response("Hello from mock"))
    print(chat.get_response("Give me some code"))
    print(chat.get_message_len())