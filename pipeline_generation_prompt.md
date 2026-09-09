# AI Prompt: Pipeline Architecture & Implementation Design

**To the User:** *Fill in the bracketed `[ ]` areas with your specific project details before feeding this prompt to the AI.*

---

## 🎭 Role
Act as a Principal AI Software Engineer and System Architect specializing in multi-agent orchestration, LLM applications, and RAG (Retrieval-Augmented Generation) systems. 

## 🎯 Objective
Your task is to design, architect, and provide the implementation code specifically for the **Pipeline Component** of our overarching software system. 

## 🌐 System Context (The "Whole System")
To understand where this pipeline fits, here is the context of the entire software system:
*   **System Purpose:** [Insert a 1-2 sentence description of what your overall software does, e.g., an automated legal document review system, an internal HR assistant, etc.]
*   **Upstream (Inputs to the pipeline):** [Describe where the data comes from, e.g., user queries from a React frontend, webhook events, PDF uploads.]
*   **Downstream (Outputs from the pipeline):** [Describe what happens after the pipeline finishes, e.g., sends a JSON response to an API, updates a Postgres database, triggers an email.]

## 🚧 Scope Boundaries & Constraints
*   **STRICT FOCUS:** You must focus **ONLY** on the pipeline logic and its internal orchestration. 
*   **OUT OF SCOPE:** Do not generate code for the front-end UI, external overarching APIs (like FastAPI/Express boilerplate), user authentication, or non-vector core databases unless they directly interact with the pipeline state.

## ⚙️ Core Requirements

The pipeline must integrate the following specific patterns:

### 1. Multi-Agent Workflows
Design a multi-agent orchestration setup (using frameworks like LangGraph, CrewAI, AutoGen, or raw Python with LangChain). 
*   Define specific agents with distinct roles (e.g., Router Agent, Retrieval Agent, Summarization Agent, Quality Assurance/Critic Agent).
*   Show how state is passed between these agents (state graph or sequential flow).

### 2. Advanced RAG Implementation
Integrate a robust RAG mechanism into the agentic workflow. You must provide concrete development examples covering:
*   **Ingestion & Chunking:** Strategies for parsing and chunking the expected input data.
*   **Retrieval Mechanism:** How the retrieval agent queries the vector store (include examples of hybrid search or query expansion if applicable).
*   **Generation & Synthesis:** How the context is passed to the LLM to generate the final response.

## 📝 Instructions for Your Output

Please structure your response as a comprehensive technical design document:

1.  **Architecture Flow (Visual):** Start with a Mermaid.js diagram illustrating the pipeline architecture, showing the step-by-step flow from input -> multi-agent orchestration -> RAG retrieval -> final output.
2.  **Agent & Tool Definitions:** List the exact agents being used, their system prompts/roles, and the specific tools they have access to (e.g., `VectorSearchTool`, `WebSearchTool`).
3.  **Code Implementation:** Provide well-documented, production-ready Python code snippets for:
    *   Setting up the Multi-Agent graph/workflow.
    *   The RAG ingestion and retrieval logic.
    *   The execution loop of the pipeline.
4.  **Dependencies:** Briefly list the required Python libraries/frameworks (e.g., `langchain`, `langgraph`, `pinecone-client`).

---
