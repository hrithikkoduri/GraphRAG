# GraphRAG System Architecture

## System Overview

GraphRAG combines knowledge graphs with RAG (Retrieval-Augmented Generation) to provide intelligent responses by leveraging both structured and unstructured data relationships.

## Architecture
```mermaid
        graph TB
        subgraph Frontend["Frontend (Next.js)"]
            UI[Chat Interface]
            State[React State Management]
            API[Axios API Client]
        end

        subgraph Backend["Backend (FastAPI)"]
            FastAPI[FastAPI Server]
            SearchEngine[Neo4j Search Engine]
            LLM[GPT-4 Integration]
            QueryEmbedding[Query Embedding Service]
        end

        subgraph DataSources["Data Sources"]
            SQL[(SQLite Database)]
            PDF[PDF Documents]
        end

        subgraph EmbeddingProcess["Embedding Process"]
            ArtistEmbed[Artist Embedding]
            AgentEmbed[Sales Agent Embedding]
            DocEmbed[Document Embedding]
            TextSplitter[Text Splitter]
        end

        subgraph Database["Knowledge Graph (Neo4j)"]
            Neo4j[(Neo4j Database)]
            Artists[Artist Nodes]
            Agents[Sales Agent Nodes]
            Documents[Document Nodes]
            Relationships{Graph Relationships}
        end

        %% Frontend Flow
        UI --> State
        State --> API
        API -->|HTTP POST| FastAPI

        %% Data Source Processing
        SQL -->|Extract Data| ArtistEmbed
        SQL -->|Extract Data| AgentEmbed
        PDF -->|Load| TextSplitter
        TextSplitter -->|Chunks| DocEmbed

        %% Embedding Process
        ArtistEmbed -->|Embedded Data| Artists
        AgentEmbed -->|Embedded Data| Agents
        DocEmbed -->|Embedded Data| Documents

        %% Query Processing
        FastAPI -->|User Query| QueryEmbedding
        QueryEmbedding -->|Search Similar| SearchEngine
        SearchEngine -->|Graph Query| Neo4j
        SearchEngine -->|Generate Response| LLM

        %% Database Relationships
        Artists -->|MANAGED| Relationships
        Agents -->|MENTIONS| Relationships
        Documents -->|RELATED_TO| Relationships

        %% Response Flow
        LLM -->|Structured Response| FastAPI
        FastAPI -->|JSON| API
        API -->|Update| State
        State -->|Render| UI

        classDef frontend fill:#6366f1,color:#fff,stroke:#4338ca
        classDef backend fill:#16a34a,color:#fff,stroke:#15803d
        classDef database fill:#0891b2,color:#fff,stroke:#0e7490
        classDef process fill:#8b5cf6,color:#fff,stroke:#7c3aed
        classDef datasource fill:#ea580c,color:#fff,stroke:#c2410c

        class UI,State,API frontend
        class FastAPI,SearchEngine,LLM,QueryEmbedding backend
        class Neo4j,Artists,Agents,Documents,Relationships database
        class ArtistEmbed,AgentEmbed,DocEmbed,TextSplitter process
        class SQL,PDF datasource
```


## Architectural Flow

### 1. Data Ingestion and Embedding Phase

#### Raw Data Sources
- **SQLite Database**: Contains structured data about artists and sales agents
- **PDF Documents**: Holds unstructured contextual information

#### Data Processing
- Artist and agent data extraction from SQLite
- PDF documents are processed through Text Splitter for chunking
- Each data type undergoes specialized embedding creation

### 2. Knowledge Graph Population

#### Node Creation
- **Artist Nodes**: Contain embedded artist information and metadata
- **Sales Agent Nodes**: Store embedded agent data and relationships
- **Document Nodes**: Hold embedded document chunks with context

#### Relationship Establishment
- `MANAGED`: Links between agents and artists
- `MENTIONS`: Connections between documents and entities
- `RELATED_TO`: Inter-document relationships based on similarity

### 3. Query and Response Flow

#### User Interaction Layer
1. User inputs query through Chat Interface
2. React State Management handles input state
3. Axios API Client formats and sends HTTP POST request

#### Backend Processing
1. FastAPI server receives and processes query
2. Query Embedding Service creates vector embedding
3. Neo4j Search Engine:
   - Performs similarity search
   - Retrieves relevant graph context
   - Prepares data for LLM

#### Response Generation
1. GPT-4 generates contextual response
2. FastAPI formats response as JSON
3. Frontend receives and processes response
4. UI updates to display new information

### 4. System Benefits

- **Semantic Search**: Efficient similarity-based retrieval
- **Contextual Understanding**: Graph relationships enhance response relevance
- **Scalable Architecture**: Modular design for easy expansion
- **Real-time Processing**: Optimized for quick response times

### 5. Technical Stack

#### Frontend
- Next.js with TypeScript
- React State Management
- Axios for API communication
- TailwindCSS for styling

#### Backend
- FastAPI server
- OpenAI GPT-4 integration
- Neo4j Graph Database
- OpenAI Embeddings (Ada-002)

#### Data Processing
- Text splitting and chunking
- Vector embeddings
- Graph relationship management
- Similarity computation

## Conclusion

This architecture provides a robust foundation for:
- Efficient information retrieval
- Contextual response generation
- Scalable data processing
- Real-time user interactions

The system's modular design allows for easy updates and maintenance while ensuring optimal performance through its various specialized components.