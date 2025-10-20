# Degree Planning Assistant

A conversational AI-powered degree planning assistant for California Baptist University (CBU) students. This application helps students and advisors generate customized academic plans through a simple chat interface.

## 📜 Project Overview

This project is a full-stack application designed to provide intelligent and context-aware academic planning advice. It leverages a FastAPI backend, a React frontend, and a sophisticated Retrieval-Augmented Generation (RAG) pipeline built with LangChain. Course information and their complex relationships (prerequisites, corequisites) are stored and queried from a Neo4j graph database, allowing for nuanced and accurate responses.

The core of the application is a LangChain-powered RAG pipeline that uses a FAISS vector index for efficient similarity searches on course data, retrieves detailed information from a Neo4j graph database, and generates human-like responses using a large language model.

## 🏛️ Architecture

The application follows a modern, containerized architecture:

1.  **Frontend**: A responsive user interface built with **React** and **Vite**, styled with **Tailwind CSS**. It communicates with the backend via HTTP and Server-Sent Events (SSE) for real-time streaming of responses.
2.  **Backend**: A robust API built with **FastAPI** that orchestrates the degree planning logic.
3.  **LangChain RAG Pipeline**:
    *   Receives a user's question from the FastAPI endpoint.
    *   Uses a **FAISS** vector index (built from course data) to find the most relevant courses.
    *   Retrieves detailed information about these courses and their relationships from the **Neo4j graph database**.
    *   Constructs a detailed prompt with the retrieved context.
    *   Sends the prompt to a **Large Language Model (LLM)** (e.g., Mistral, GPT) to generate a comprehensive and helpful response.
4.  **Database**:
    *   **Neo4j**: A graph database that stores the CBU course catalog, including courses, prerequisites, corequisites, and other relationships. This allows for complex queries that a traditional relational database would struggle with.
    *   **PostgreSQL**: A relational database for storing student data (currently used for basic models, with room for future expansion).
5.  **Containerization**: The entire application is containerized using **Docker** and managed with **Docker Compose**, ensuring a consistent and reproducible development environment.

## 🚀 Setup and Installation

### Prerequisites

*   Docker and Docker Compose
*   Node.js and npm (for frontend development outside of Docker)
*   Python (for backend development outside of Docker)

### Quick Start with Makefile

The most convenient way to run the application is by using the provided `Makefile`:

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd degree_planning_agent
    ```

2.  **Create and configure your environment file**:
    ```bash
    cp .env.example .env
    ```
    Update the `.env` file with your API keys if you are using external LLMs (e.g., OpenAI, Anthropic).

3.  **Build and run the application**:
    ```bash
    make dev
    ```
    This command will build the Docker images and start all the services in detached mode.

4.  **View logs**:
    ```bash
    make logf
    ```

5.  **Stop the application**:
    ```bash
    make devstop
    ```

### Manual Setup

If you prefer to run the services manually, you can use Docker Compose directly:

```bash
docker-compose up --build
```

## 📁 Project Structure

```
degree_planning_agent/
├── backend/
│   ├── app.py              # FastAPI application, defines API endpoints
│   ├── db.py               # SQLAlchemy setup for PostgreSQL
│   ├── models.py           # SQLAlchemy models for students and courses
│   ├── graph/
│   │   ├── graph_langchain.py # Core LangChain RAG pipeline logic
│   │   ├── neo4j_connect.py   # Connection to the Neo4j database
│   │   ├── seed_graph.py      # Seeds the Neo4j database with course data
│   │   └── course_data.json   # Course catalog data in JSON format
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React application component
│   │   └── components/
│   │       ├── PlannerStream.jsx # Handles the chat interface and streaming
│   │       └── ChatBubble.jsx    # Renders individual chat messages
│   └── package.json        # Frontend dependencies
├── database/
│   └── init.sql            # (Optional) SQL initialization script
├── docker-compose.yml      # Defines and configures all services
├── Makefile                # Helper commands for development
└── README.md               # This file
```

## 🤖 LangChain RAG Flow

The heart of this application is the Retrieval-Augmented Generation pipeline in `backend/graph/graph_langchain.py`. Here’s how it works:

1.  **FAISS Index Creation**: On startup, a FAISS vector index is built from the course descriptions to enable fast similarity searches.
2.  **Similarity Search**: When a user asks a question, the pipeline encodes the question into a vector and uses the FAISS index to find the most similar courses.
3.  **Graph-Based Context Retrieval**: The application then queries the Neo4j database to retrieve detailed information about the courses identified in the previous step, including their prerequisites, units, and recommended semesters.
4.  **Prompt Engineering**: A system prompt, the retrieved context, and the user's question are combined to create a comprehensive prompt for the LLM.
5.  **LLM-Powered Generation**: The final prompt is sent to the LLM, which generates a helpful, context-aware response.
6.  **Streaming Response**: The response is streamed back to the user in real-time for a better user experience.

## 📈 Recent Updates

*   **2024-08-05**:
    *   Removed unused `graph_langgraph.py` file to simplify the project.
    *   Updated the `README.md` to accurately reflect the project's architecture and RAG pipeline.
*   **2024-08-04**:
    *   Implemented a streaming chat interface on the frontend using Server-Sent Events (SSE).
    *   Added a FAISS vector index for faster and more accurate course similarity searches.
*   **2024-08-03**:
    *   Successfully integrated the Neo4j graph database for storing and querying course data.
    *   Created a seeding script (`seed_graph.py`) to populate the Neo4j database from a JSON file.

## 🗺️ Future Roadmap

*   **Student Profile Integration**: Allow students to log in and save their academic progress, enabling more personalized recommendations.
*   **Multi-Semester Planning**: Enhance the agent to generate a full multi-semester degree plan based on a student's major and progress.
*   **Prerequisite Validation**: Add a feature to automatically check if a student has met the prerequisites for a given course.
*   **UI/UX Enhancements**: Improve the chat interface with features like suggested questions, conversation history, and the ability to export plans.
*   **Deployment**: Create a production-ready deployment configuration using a cloud provider (e.g., AWS, Google Cloud).

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, LangChain, Uvicorn
*   **Frontend**: React, Vite, Tailwind CSS
*   **Databases**: Neo4j, PostgreSQL
*   **LLM**: Mistral (via Ollama), with support for OpenAI/Anthropic models
*   **Vector Search**: FAISS
*   **Containerization**: Docker, Docker Compose
*   **Linting/Formatting**: ESLint, Prettier