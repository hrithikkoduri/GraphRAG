from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from py2neo import Graph
import numpy as np
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


class QueryInput(BaseModel):
    query: str = Field(..., description="User question to process")

class Response(BaseModel):
    response: str = Field(..., description="Response to user question")

class Neo4jSearchEngine:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0) 
        self.NEO4J_URI = 'bolt://localhost:7687'
        self.NEO4J_USERNAME = 'neo4j'
        self.NEO4J_PASSWORD = '12345678'
        self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        self.graph = Graph(self.NEO4J_URI, auth=(self.NEO4J_USERNAME, self.NEO4J_PASSWORD))

    def find_similar_content(self, query_text: str, similarity_threshold: float = 0.7, limit: int = 5):
        try:
            query_embedding = self.embeddings.embed_query(query_text)
            query_embedding_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
            
            search_query = """
            MATCH (a:Artist)
            WITH a, gds.similarity.cosine(a.embedding, $query_embedding) AS artist_similarity
            WHERE artist_similarity > $threshold
            
            OPTIONAL MATCH (s:SalesAgent)-[:MANAGED]->(a)
            WITH a, s, artist_similarity,
                 CASE 
                    WHEN s IS NOT NULL 
                    THEN gds.similarity.cosine(s.embedding, $query_embedding)
                    ELSE 0 
                 END AS agent_similarity
            
            OPTIONAL MATCH (d:Document)-[:MENTIONS]->(a)
            WITH a, s, d, artist_similarity, agent_similarity,
                 CASE 
                    WHEN d IS NOT NULL 
                    THEN gds.similarity.cosine(d.embedding, $query_embedding)
                    ELSE 0 
                 END AS doc_similarity
            
            WITH a, 
                 artist_similarity,
                 COLLECT(DISTINCT {
                    agent_name: s.name,
                    agent_similarity: agent_similarity
                 }) AS managing_agents,
                 COLLECT(DISTINCT {
                    text: d.text,
                    page: d.page_number,
                    similarity: doc_similarity
                 }) AS related_documents
            
            RETURN 
                a.name AS artist_name,
                a.revenue AS artist_revenue,
                artist_similarity,
                managing_agents,
                related_documents
            ORDER BY artist_similarity DESC
            LIMIT $limit
            """
            
            results = self.graph.run(
                search_query, 
                query_embedding=query_embedding_list,
                threshold=similarity_threshold,
                limit=limit
            ).data()
            
            return [
                {
                    'artist': {
                        'name': result['artist_name'],
                        'revenue': result['artist_revenue'],
                        'relevance_score': round(result['artist_similarity'], 3)
                    },
                    'sales_agents': [
                        {
                            'name': agent['agent_name'],
                            'relevance_score': round(agent['agent_similarity'], 3)
                        }
                        for agent in result['managing_agents']
                        if agent['agent_name'] is not None
                    ],
                    'supporting_documents': [
                        doc for doc in result['related_documents']
                        if doc['text'] is not None
                    ]
                }
                for result in results
            ]
            
        except Exception as e:
            print(f"Error in enhanced search: {e}")
            return []

    def generate_response_from_results(self, query: str, results: list) -> Response:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert music database analyst. Present information in a clear, structured format:

                        Guidelines:
                        • Use bullet points for listing information
                        • Bold key terms using **text**
                        • Format numbers with appropriate symbols ($1,000)
                        • Keep responses concise and focused
                        
                        If no relevant information is found, respond with:
                        "I don't have enough information to answer your question about [topic]."

                        Remember: Only use information from the provided search results."""),
            ("user", """Question: {user_question}
                        
                        Search Results: {search_results}
                        
                        Please provide a structured answer using bullet points and clear formatting.""")
        ])

        response_structured_llm = self.llm.with_structured_output(Response)
        formatted_prompt = prompt.invoke({"user_question": query, "search_results": results})
        return response_structured_llm.invoke(formatted_prompt)

app = FastAPI()
app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Adjust this to your frontend's URL in production
       allow_credentials=True,
       allow_methods=["*"],  # Allow all methods
       allow_headers=["*"],  # Allow all headers
   )
search_engine = Neo4jSearchEngine()

@app.post("/generate-response", response_model=Response)
async def generate_response(query_input: QueryInput):
    try:
        results = search_engine.find_similar_content(query_input.query)
        response = search_engine.generate_response_from_results(query_input.query, results)
        print(response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)