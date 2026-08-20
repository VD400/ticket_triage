import cohere
import os
from dotenv import load_dotenv

load_dotenv()

cohere_api = os.getenv("COHERE_API_KEY")

co = cohere.Client(cohere_api)

def embed_text(text: str, input_type:str="search_document")->list[float]:
    response = co.embed(
        texts = [text],
        model = "embed-english-light-v3.0",
        input_type=input_type
    )
    
    return response.embeddings[0]

def embed_texts_batch(texts: list[str], input_type: str = "search_document") -> list[list[float]]:
    response = co.embed(
        texts = texts,
        model="embed-english-light-v3.0",
        input_type=input_type
    )
    return response.embeddings

