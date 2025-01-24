import os
import sys
from typing import Any, Optional, List
import asyncio

# Path to your virtual environment
venv_path = "C:\\Users\\Hp\\Desktop\\Rapid_Innovation\\MCP\\weather\\venv"
python_path = os.path.join(venv_path, "Scripts", "python.exe")

# Ensure the script uses the Python executable from the virtual environment
if sys.executable != python_path:
    print(f"Please activate your virtual environment and run this script with: {python_path}")
    sys.exit(1)

# Imports that depend on the virtual environment
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("mongodb_connector")

# MongoDB Configuration
MONGO_URI = "YOUR MONGO DB URL"
DATABASE_NAME = "test"
COLLECTION_NAME = "books"

def connect_to_db() -> Optional[Any]:
    """
    Connect to MongoDB and return the collection.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        return collection
    except PyMongoError as e:
        print(f"Failed to connect to MongoDB: {e}")
        return None

@mcp.tool()
async def insert_document(document: dict) -> str:
    """
    Insert a document into the specified collection.
    """
    collection = connect_to_db()
    if collection is None:
        return "Failed to connect to the database."

    try:
        result = collection.insert_one(document)
        return f"Document inserted successfully with ID: {result.inserted_id}"
    except PyMongoError as e:
        return f"An error occurred while inserting the document: {e}"

@mcp.tool()
def find_document_by_id(document_id: str) -> Any:
    """
    Find a document by its ID.
    """
    collection = connect_to_db()
    if collection is None:
        return {"error": "Failed to connect to the database."}

    try:
        result = collection.find_one({"_id": ObjectId(document_id)})
        if not result:
            return {"error": "Document not found."}
        return result
    except PyMongoError as e:
        return {"error": f"An error occurred while retrieving the document: {e}"}

@mcp.tool()
def find_documents_by_field(field: str, value: Any) -> List[Any]:
    """
    Find documents that match a specific field and value.
    """
    collection = connect_to_db()
    if collection is None:
        return [{"error": "Failed to connect to the database."}]

    try:
        results = collection.find({field: value})
        return list(results)
    except PyMongoError as e:
        return [{"error": f"An error occurred while retrieving documents: {e}"}]

@mcp.tool()
def update_document_by_id(document_id: str, updates: dict) -> str:
    """
    Update a document by its ID.
    """
    collection = connect_to_db()
    if collection is None:
        return "Failed to connect to the database."

    try:
        result = collection.update_one({"_id": ObjectId(document_id)}, {"$set": updates})
        if result.matched_count:
            return f"Document with ID {document_id} updated successfully."
        return "Document not found."
    except PyMongoError as e:
        return f"An error occurred while updating the document: {e}"

@mcp.tool()
def delete_document_by_id(document_id: str) -> str:
    """
    Delete a document by its ID.
    """
    collection = connect_to_db()
    if collection is None:
        return "Failed to connect to the database."

    try:
        result = collection.delete_one({"_id": ObjectId(document_id)})
        if result.deleted_count:
            return f"Document with ID {document_id} deleted successfully."
        return "Document not found."
    except PyMongoError as e:
        return f"An error occurred while deleting the document: {e}"

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")
