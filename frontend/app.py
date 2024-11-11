import chainlit as cl
from chainlit.types import AskFileResponse
import requests
from typing import List
import os

from dotenv import load_dotenv

load_dotenv()


# fastapi host (local)
# API_BASE_URL = "http://localhost:8000"
API_BASE_URL = os.environ.get("API_BASE_URL")

class ChatSession:
    def __init__(self):
        self.session_cookie = None
        self.initialized = False

    async def initialize(self):
        """new chat session"""
        try:
            response = requests.post(f"{API_BASE_URL}/chat/init")
            if response.status_code == 200:
                self.session_cookie = response.cookies.get_dict()
                self.initialized = True
                return True
            return False
        except requests.RequestException as e:
            await cl.Message(
                content=f"Failed to initialize session: {str(e)}",
                author="System",
            ).send()
            return False

    async def prompt_for_reupload(self) -> List[AskFileResponse] | None:
        """prompt user to try uploading files again"""
        try:
            files = await cl.AskFileMessage(
                content="Please TRY AGAIN with valid PDFs",
                accept=["application/pdf"],
                author="System",
                max_size_mb=100,
                max_files=10,
                timeout=7200
            ).send()
            return files
        except Exception as e:
            await cl.Message(
                content=f"Error prompting for reupload: {str(e)}",
                author="System"
            ).send()
            return None

    async def upload_files(self, files: List[AskFileResponse], retry_count: int = 0, max_retries: int = 10) -> bool:
        """upload PDF files to the FastAPI backend with retry mechanism"""
        if not files or not self.initialized:
            return False

        try:
            # convert chainlit files to format expected by requests
            files_data = []
            for file in files:
                file_path = file.path
                files_data.append(
                    ("files", (file.name, open(file_path, "rb"), "application/pdf"))
                )

            # upload files
            response = requests.post(
                f"{API_BASE_URL}/store/upload",
                files=files_data,
                cookies=self.session_cookie
            )

            # clean up file handles
            for _, (_, file_obj, _) in files_data:
                file_obj.close()

            if response.status_code == 200:
                await cl.Message(
                    content="PDF files uploaded successfully!",
                    author="System"
                ).send()
                return True
            else:
                error_msg = f"Failed to upload PDF files. Status code: {response.status_code}"
                if retry_count < max_retries:
                    await cl.Message(
                        content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
                        author="System"
                    ).send()
                    
                    # prompt for re-upload
                    new_files = await self.prompt_for_reupload()
                    if new_files:
                        return await self.upload_files(new_files, retry_count + 1, max_retries)
                    return False
                else:
                    await cl.Message(
                        content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
                        author="System"
                    ).send()
                    return False

        except requests.RequestException as e:
            error_msg = f"Error uploading files: {str(e)}"
            if retry_count < max_retries:
                await cl.Message(
                    content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
                    author="System"
                ).send()
                
                # prompt for re-upload
                new_files = await self.prompt_for_reupload()
                if new_files:
                    return await self.upload_files(new_files, retry_count + 1, max_retries)
                return False
            else:
                await cl.Message(
                    content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
                    author="System"
                ).send()
                return False
                
        except Exception as e:
            error_msg = f"Unexpected error during file upload: {str(e)}"
            if retry_count < max_retries:
                await cl.Message(
                    content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
                    author="System"
                ).send()
                
                # prompt for re-upload
                new_files = await self.prompt_for_reupload()
                if new_files:
                    return await self.upload_files(new_files, retry_count + 1, max_retries)
                return False
            else:
                await cl.Message(
                    content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
                    author="System"
                ).send()
                return False

    async def send_message(self, message: str) -> str:
        """send a message to the backend and get the response"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/chat/query",
                json={"query": message},
                cookies=self.session_cookie
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Failed to get response from the chatbot. Status code: {response.status_code}"
        except requests.RequestException as e:
            return f"Error sending message: {str(e)}"

# global chat session
chat_session = ChatSession()

@cl.on_chat_start
async def start():
    """initialize chat session when a new chat starts."""
    # Session init
    success = await chat_session.initialize()
    if success:
        files = await cl.AskFileMessage(
            content="Welcome! You can now upload PDF documents and start chatting.",
            accept=["application/pdf"],
            author="Assistant",
            max_size_mb=100,
            max_files=10,
            timeout=7200
        ).send()
        
        if files:
            await chat_session.upload_files(files)        
    else:
        await cl.Message(
            content="Failed to initialize chat session. Please try refreshing the page.",
            author="System"
        ).send()

@cl.on_message
async def main(msg: cl.Message):
    """handle chat messages and process attached files if present."""
    if not chat_session.initialized:
        await cl.Message(content="Chat session not initialized. Please refresh the page.", author="System").send()
        return

    # get files attached in msg.elements (if any)
    if msg.elements:
        pdf_files = [file for file in msg.elements if file.mime == "application/pdf"]
        
        if pdf_files:
            files_uploaded = await chat_session.upload_files(pdf_files)
            
            if not files_uploaded:
                await cl.Message(content="Failed to process the attached files. Please try again.", author="System").send()
                return

    # process chat message after files (if any) are uploaded
    response = await chat_session.send_message(msg.content)
    await cl.Message(content=response).send()

# import chainlit as cl
# from chainlit.types import AskFileResponse
# import requests
# from typing import List
# import os

# from pydantic_settings import BaseSettings, SettingsConfigDict
# from uuid import uuid4
# from backend.app.core.database import SQLiteChatMessageHistory

# class Settings(BaseSettings):
#     api_base_url: str


#     model_config = SettingsConfigDict(env_file=".env")


# settings = Settings()


# # fastapi host (local)
# # API_BASE_URL = "http://localhost:8000"
# API_BASE_URL = settings.api_base_url

# class ChatSession:
#     def __init__(self):
#         self.session_cookie = None
#         self.initialized = False

#     async def initialize(self):
#         """new chat session"""
#         try:
#             response = requests.post(f"{API_BASE_URL}/chat/init")
#             if response.status_code == 200:
#                 self.session_cookie = response.cookies.get_dict()
#                 self.initialized = True
#                 return True
#             return False
#         except requests.RequestException as e:
#             await cl.Message(
#                 content=f"Failed to initialize session: {str(e)}",
#                 author="System",
#             ).send()
#             return False

#     async def prompt_for_reupload(self) -> List[AskFileResponse] | None:
#         """prompt user to try uploading files again"""
#         try:
#             files = await cl.AskFileMessage(
#                 content="Please TRY AGAIN with valid PDFs",
#                 accept=["application/pdf"],
#                 author="System",
#                 max_size_mb=100,
#                 max_files=10,
#                 timeout=7200
#             ).send()
#             return files
#         except Exception as e:
#             await cl.Message(
#                 content=f"Error prompting for reupload: {str(e)}",
#                 author="System"
#             ).send()
#             return None

#     async def upload_files(self, files: List[AskFileResponse], retry_count: int = 0, max_retries: int = 10) -> bool:
#         """upload PDF files to the FastAPI backend with retry mechanism"""
#         if not files or not self.initialized:
#             return False

#         try:
#             # convert chainlit files to format expected by requests
#             files_data = []
#             for file in files:
#                 file_path = file.path
#                 files_data.append(
#                     ("files", (file.name, open(file_path, "rb"), "application/pdf"))
#                 )

#             # upload files
#             response = requests.post(
#                 f"{API_BASE_URL}/store/upload",
#                 files=files_data,
#                 cookies=self.session_cookie
#             )

#             # clean up file handles
#             for _, (_, file_obj, _) in files_data:
#                 file_obj.close()

#             if response.status_code == 200:
#                 await cl.Message(
#                     content="PDF files uploaded successfully!",
#                     author="System"
#                 ).send()
#                 return True
#             else:
#                 error_msg = f"Failed to upload PDF files. Status code: {response.status_code}"
#                 if retry_count < max_retries:
#                     await cl.Message(
#                         content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
#                         author="System"
#                     ).send()
                    
#                     # prompt for re-upload
#                     new_files = await self.prompt_for_reupload()
#                     if new_files:
#                         return await self.upload_files(new_files, retry_count + 1, max_retries)
#                     return False
#                 else:
#                     await cl.Message(
#                         content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
#                         author="System"
#                     ).send()
#                     return False

#         except requests.RequestException as e:
#             error_msg = f"Error uploading files: {str(e)}"
#             if retry_count < max_retries:
#                 await cl.Message(
#                     content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
#                     author="System"
#                 ).send()
                
#                 # prompt for re-upload
#                 new_files = await self.prompt_for_reupload()
#                 if new_files:
#                     return await self.upload_files(new_files, retry_count + 1, max_retries)
#                 return False
#             else:
#                 await cl.Message(
#                     content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
#                     author="System"
#                 ).send()
#                 return False
                
#         except Exception as e:
#             error_msg = f"Unexpected error during file upload: {str(e)}"
#             if retry_count < max_retries:
#                 await cl.Message(
#                     content=f"{error_msg}\nAttempt {retry_count + 1} of {max_retries}",
#                     author="System"
#                 ).send()
                
#                 # prompt for re-upload
#                 new_files = await self.prompt_for_reupload()
#                 if new_files:
#                     return await self.upload_files(new_files, retry_count + 1, max_retries)
#                 return False
#             else:
#                 await cl.Message(
#                     content=f"{error_msg}\nMaximum retry attempts reached. Please start a new chat session.",
#                     author="System"
#                 ).send()
#                 return False

#     async def send_message(self, message: str) -> str:
#         """send a message to the backend and get the response"""
#         try:
#             response = requests.post(
#                 f"{API_BASE_URL}/chat/query",
#                 json={"query": message},
#                 cookies=self.session_cookie
#             )
            
#             if response.status_code == 200:
#                 return response.json()["response"]
#             else:
#                 return f"Failed to get response from the chatbot. Status code: {response.status_code}"
#         except requests.RequestException as e:
#             return f"Error sending message: {str(e)}"

# # global chat session
# chat_session = ChatSession()

# @cl.on_chat_start
# async def start():
#     """initialize chat session when a new chat starts."""
#     # Session init
#     success = await chat_session.initialize()
#     if success:
#         files = await cl.AskFileMessage(
#             content="Welcome! You can now upload PDF documents and start chatting.",
#             accept=["application/pdf"],
#             author="Assistant",
#             max_size_mb=100,
#             max_files=10,
#             timeout=7200
#         ).send()
        
#         if files:
#             await chat_session.upload_files(files)        
#     else:
#         await cl.Message(
#             content="Failed to initialize chat session. Please try refreshing the page.",
#             author="System"
#         ).send()

# @cl.on_message
# async def main(msg: cl.Message):
#     """handle chat messages and process attached files if present."""
#     if not chat_session.initialized:
#         await cl.Message(content="Chat session not initialized. Please refresh the page.", author="System").send()
#         return

#     # get files attached in msg.elements (if any)
#     if msg.elements:
#         pdf_files = [file for file in msg.elements if file.mime == "application/pdf"]
        
#         if pdf_files:
#             files_uploaded = await chat_session.upload_files(pdf_files)
            
#             if not files_uploaded:
#                 await cl.Message(content="Failed to process the attached files. Please try again.", author="System").send()
#                 return

#     # process chat message after files (if any) are uploaded
#     response = await chat_session.send_message(msg.content)
#     await cl.Message(content=response).send()
    
#     response_id = str(uuid4())
#     chat_history = SQLiteChatMessageHistory(session_id=chat_session.session_cookie)
#     # Get user feedback (thumbs up/down)
#     feedback = await cl.selectbox(
#         "What's your feedback on this response?",
#         options=[" Thumbs Down", " Thumbs Up"]
#     )
#     feedback_value = -1 if feedback == " Thumbs Down" else 1
    
#     # Optionally, collect a comment as well
#     feedback_comment = await cl.text_input(
#         label="Optional: Add a comment to your feedback",
#         placeholder="Explain your feedback (optional)"
#     )
    
#     # Save feedback to the database
#     chat_history.add_feedback(message_id=response_id, value=feedback_value, comment=feedback_comment)
    
#     return response