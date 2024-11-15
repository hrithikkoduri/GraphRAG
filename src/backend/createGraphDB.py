from langchain_community.graphs import Neo4jGraph
from langchain.document_loaders import PyPDFLoader
from pyprojroot import here
from py2neo import  Node
from langchain_openai import OpenAIEmbeddings
import sqlite3
import numpy as np
import uuid
from langchain_core.documents import Document
from langchain.text_splitter import SpacyTextSplitter
from py2neo import Graph, Node
from scipy.spatial.distance import cosine



# Constants
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USERNAME = 'neo4j'
NEO4J_PASSWORD = '12345678'

graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
# Initialize graph and LLM

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
text_splitter = SpacyTextSplitter(chunk_size=500, chunk_overlap=10)

# Function to load artists and sales agents from SQLite with embeddings
def load_artists_and_sales_agent_from_sqlite_with_embeddings(db_path, embeddings_model):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(""" 
        SELECT ar.Name AS ArtistName, SUM(il.UnitPrice * il.Quantity) AS Revenue
        FROM Artist ar
        JOIN Album al ON ar.ArtistId = al.ArtistId
        JOIN Track t ON al.AlbumId = t.AlbumId
        JOIN InvoiceLine il ON t.TrackId = il.TrackId
        GROUP BY ar.Name
        ORDER BY Revenue DESC
        LIMIT 10; 
    """)

    artist_names = []
    for ArtistName, Revenue in cursor.fetchall():
        artist_embedding = embeddings_model.embed_query(ArtistName)
        embedding_list = artist_embedding.tolist() if isinstance(artist_embedding, np.ndarray) else artist_embedding
        
        artist_node = Node("Artist", name=ArtistName, revenue=Revenue, embedding=embedding_list)
        graph.merge(artist_node, "Artist", "name")
        artist_names.append(ArtistName)

    artist_query = """
    MATCH (a:Artist)
    RETURN a.name as name
    """
    existing_artists = {record['name'] for record in graph.run(artist_query)}

    cursor.execute(""" 
    SELECT DISTINCT e.FirstName || ' ' || e.LastName AS SalesAgentName, a.Name AS ArtistName
    FROM Artist a
    JOIN Album al ON a.ArtistId = al.ArtistId
    JOIN Track t ON al.AlbumId = t.AlbumId
    JOIN InvoiceLine il ON t.TrackId = il.TrackId
    JOIN Invoice i ON il.InvoiceId = i.InvoiceId
    JOIN Customer c ON i.CustomerId = c.CustomerId
    JOIN Employee e ON c.SupportRepId = e.EmployeeId
    WHERE a.Name IN ('Iron Maiden', 'U2', 'Metallica', 'Led Zeppelin', 'Lost', 'The Office', 'Os Paralamas Do Sucesso', 'Deep Purple', 'Faith No More', 'Eric Clapton')
    LIMIT 100
    """)
    for SalesAgentName, ArtistName in cursor.fetchall():
        sales_agent_embedding = embeddings_model.embed_query(SalesAgentName)
        embedding_list = sales_agent_embedding.tolist() if isinstance(sales_agent_embedding, np.ndarray) else sales_agent_embedding
        
        sales_agent_node = Node("SalesAgent", name=SalesAgentName, embedding=embedding_list)
        graph.merge(sales_agent_node, "SalesAgent", "name")

        for artist_name in existing_artists:
            if artist_name.lower() == ArtistName.lower():
                cypher_query = """
                MATCH (a:Artist {name: $artist_name})
                MATCH (s:SalesAgent {name: $sales_agent_name})
                CREATE (s)-[:MANAGED]->(a)
                """
                graph.run(cypher_query, artist_name=artist_name, sales_agent_name=SalesAgentName)    

    conn.close()
    return artist_names

# Function to set up constraints in Neo4j
def setup_constraints():
    try:
        graph.run("DROP CONSTRAINT document_id IF EXISTS")
        graph.run("DROP CONSTRAINT document_unique IF EXISTS")
    except Exception as e:
        print(f"Error dropping constraints: {e}")
    
    try:
        graph.run("""
            CREATE CONSTRAINT document_unique IF NOT EXISTS 
            FOR (d:Document) REQUIRE d.doc_id IS UNIQUE
        """)
        print("Constraints set up successfully")
    except Exception as e:
        print(f"Error creating constraints: {e}")


def is_similar(embedding1, embedding2, threshold=0.8):
                    similarity = 1 - cosine(embedding1, embedding2)
                    return similarity > threshold

# Function to load PDF embeddings to Neo4j
def load_pdf_embeddings_to_neo4j(pdf_path):
    setup_constraints()

    artist_query = """
    MATCH (a:Artist)
    RETURN a.name as name
    """
    existing_artists = {record['name'] for record in graph.run(artist_query)}

    sales_agent_query = """
    MATCH (s:SalesAgent)
    RETURN s.name as name
    """
    existing_sales_agents = {record['name'] for record in graph.run(sales_agent_query)}

    loader = PyPDFLoader(pdf_path)
    pages = loader.load_and_split()
    for i, page in enumerate(pages):
        text = page.page_content
        if text:
            chunks = text_splitter.split_text(text)
            for j, chunk in enumerate(chunks):
                doc_id = str(uuid.uuid4())
                doc = Document(page_content=chunk)
                embedding_vector = embeddings.embed_query(chunk)
                embedding_list = embedding_vector.tolist() if isinstance(embedding_vector, np.ndarray) else embedding_vector

                doc_node = Node("Document", doc_id=doc_id, text=chunk, page_number=i, chunk_index=j, embedding=embedding_list)
                graph.create(doc_node)

                
                # Updated logic to create "RELATED_TO" relationships based on similarity
                for existing_doc in graph.run("MATCH (d:Document) RETURN d").data():
                    existing_embedding = existing_doc['d']['embedding']
                    if isinstance(existing_embedding, list) and is_similar(embedding_list, existing_embedding):
                        if existing_doc['d']['doc_id'] != doc_id:
                            cypher_query = """
                            MATCH (d1:Document {doc_id: $doc_id})
                            MATCH (d2:Document {doc_id: $existing_doc_id})
                            CREATE (d1)-[:RELATED_TO]->(d2)
                            """
                            graph.run(cypher_query, doc_id=doc_id, existing_doc_id=existing_doc['d']['doc_id'])


                for artist_name in existing_artists:
                    if artist_name.lower() in chunk.lower():
                        cypher_query = """
                        MATCH (a:Artist {name: $artist_name})
                        MATCH (d:Document {doc_id: $doc_id})
                        CREATE (d)-[:MENTIONS]->(a)
                        """
                        graph.run(cypher_query, artist_name=artist_name, doc_id=doc_id)

                for sales_agent in existing_sales_agents:
                    if sales_agent.lower() in chunk.lower():
                        cypher_query = """
                        MATCH (a:SalesAgent {name: $sales_agent})
                        MATCH (d:Document {doc_id: $doc_id})
                        CREATE (d)-[:MENTIONS]->(a)
                        """
                        graph.run(cypher_query, sales_agent=sales_agent, doc_id=doc_id)

    print(f"Successfully processed PDF: {pdf_path}")

# Load artists and sales agents from SQLite
artist_names = load_artists_and_sales_agent_from_sqlite_with_embeddings(here('/Users/ualguest/Desktop/Langchain_Projects/neo4j/Artists.db'), embeddings)
load_pdf_embeddings_to_neo4j(here('/Users/ualguest/Desktop/Langchain_Projects/neo4j/Artists.pdf')) 