# Degree Planning Assistant

An AI-assisted degree planning prototype for California Baptist University course advising. The project combines a FastAPI backend, a React frontend, and a Neo4j course graph to answer planning questions through a chat interface with streamed responses.

## Overview

This repo is a portfolio prototype focused on three ideas:

- modeling course relationships in Neo4j
- exposing degree-planning behavior through a lightweight FastAPI API
- delivering an interactive chat UI with streaming responses in React

The current implementation is a graph-backed planner rather than a full production advising system. It is best understood as an engineering prototype that demonstrates full-stack integration, graph data modeling, and LLM-assisted UX.

## Architecture

1. Frontend: React + Vite + Tailwind chat interface for submitting planning questions and rendering streamed markdown replies.
2. Backend: FastAPI service that seeds the course graph on startup and streams LLM output over Server-Sent Events.
3. Data layer: Neo4j stores course nodes plus prerequisite relationships derived from the course catalog JSON.
4. LLM layer: OpenAI-compatible chat completion client. The default local setup targets Ollama, but the backend can be pointed at another compatible endpoint through environment variables.

## Current Status

What is in good shape:

- frontend builds successfully with Vite
- Docker-based local development setup exists for frontend, backend, and Neo4j
- course catalog data and graph seeding flow are present in-repo
- the project has a coherent prototype story for a portfolio

What still needs polish:

- backend behavior has recently been refactored and should be smoke-tested end to end before public release
- there is no formal automated test suite yet
- the UI is functional but still minimal
- the planner is a prototype, not an authoritative advising tool

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Frontend: React, Vite, Tailwind CSS
- Data: Neo4j
- LLM integration: OpenAI-compatible API, local Ollama by default
- Dev environment: Docker, Docker Compose, Makefile

## Repository Layout

```text
degree_planning_agent/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── LLM/
│   │   ├── load.py
│   │   └── llm_config.py
│   ├── graph/
│   │   ├── course_data.json
│   │   ├── graph_query.py
│   │   ├── neo4j_connect.py
│   │   └── seed_graph.py
│   └── utility/
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   └── package.json
├── docker-compose.yml
├── Makefile
└── README.md
```

## Local Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ if running the frontend outside Docker
- Python 3.11+ if running the backend outside Docker
- An OpenAI-compatible LLM endpoint or Ollama running locally

### Environment

Create a local env file:

```bash
cp .env.example .env
```

Key variables:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `LLM_MODEL`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

### Run with Docker

```bash
make dev
```

Useful commands:

```bash
make logf
make devstop
make devclean
```

### Run Frontend Only

```bash
cd frontend
npm install
npm run dev
```

## API Surface

- `GET /` health check
- `GET /plan_stream?question=...` streamed planner response
- `GET /reset_session` clears the in-memory conversation state

## Portfolio Notes

This project shows:

- graph-oriented data modeling for prerequisite relationships
- a streaming chat UX over SSE
- full-stack coordination across React, FastAPI, Neo4j, and Docker
- pragmatic refactoring from a heavier RAG approach to a simpler graph-backed prototype

## Roadmap

- add a small automated smoke test for backend startup and graph queries
- improve planner grounding using structured graph-query tools
- strengthen the UI with starter prompts and conversation/session handling
- deploy a stable demo environment

## Disclaimer

This is an educational prototype and should not be treated as official academic advising.
