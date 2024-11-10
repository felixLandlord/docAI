import chainlit as cl
from chainlit.types import AskFileResponse
import requests
from typing import List
import os

# Constants
API_BASE_URL = "http://localhost:8000"

class ChatSession:
    def __init__(self):
        self.session_cookie = None
        self.initialized = False

    async def initialize(self):
        """Initialize a new chat session."""
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

    async def upload_files(self, files: List[AskFileResponse]) -> bool:
        """Upload files to the backend."""
        if not files or not self.initialized:
            return False

        try:
            # Convert chainlit files to format expected by requests
            files_data = []
            for file in files:
                # Get the file path from AskFileResponse
                file_path = file.path
                files_data.append(
                    ("files", (file.name, open(file_path, "rb"), "application/pdf"))
                )

            # Upload files
            response = requests.post(
                f"{API_BASE_URL}/store/upload",
                files=files_data,
                cookies=self.session_cookie
            )

            # Clean up file handles
            for _, (_, file_obj, _) in files_data:
                file_obj.close()

            if response.status_code == 200:
                await cl.Message(
                    content="Files uploaded successfully!",
                    author="System"
                ).send()
                return True
            else:
                await cl.Message(
                    content=f"Failed to upload files. Status code: {response.status_code}",
                    author="System",
                ).send()
                return False

        except requests.RequestException as e:
            await cl.Message(
                content=f"Error uploading files: {str(e)}",
                author="System",
            ).send()
            return False
        except Exception as e:
            await cl.Message(
                content=f"Unexpected error during file upload: {str(e)}",
                author="System",
            ).send()
            return False

    async def send_message(self, message: str) -> str:
        """Send a message to the backend and get the response."""
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

# Global chat session
chat_session = ChatSession()

@cl.on_chat_start
async def start():
    """Initialize the chat session when a new chat starts."""
    # Initialize new session
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
    """Handle incoming messages and process attached files if present."""
    if not chat_session.initialized:
        await cl.Message(content="Chat session not initialized. Please refresh the page.", author="System").send()
        return

    # Check if there are files attached in msg.elements
    if msg.elements:
        pdf_files = [file for file in msg.elements if file.mime == "application/pdf"]
        
        if pdf_files:
            files_uploaded = await chat_session.upload_files(pdf_files)
            if not files_uploaded:
                await cl.Message(content="Failed to process the attached files. Please try again.", author="System").send()
                return

    # Process the message content after files (if any) are uploaded
    response = await chat_session.send_message(msg.content)
    await cl.Message(content=response).send()