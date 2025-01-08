from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import json
import asyncio
import ironcore_alloy as alloy
import base64
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndex,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)
from azure.search.documents import SearchClient
from azure.search.documents import SearchItemPaged
from azure.search.documents.models import VectorizedQuery,VectorizableTextQuery

async def print_results(results: SearchItemPaged[dict], alloy_client: alloy.Standalone, metadata: alloy.AlloyMetadata):
    semantic_answers = results.get_answers()
    if semantic_answers:
        for answer in semantic_answers:
            if answer.highlights:
                print(f"Semantic Answer: {answer.highlights}")
            else:
                print(f"Semantic Answer: {answer.text}")
            print(f"Semantic Answer Score: {answer.score}\n")

    for result in results:
  
        recreated_title = base64.b64decode(result['title'])  # type: ignore
        decrypted_title = await alloy_client.standard_attached().decrypt(
            recreated_title, metadata
        )
        recreated_content = base64.b64decode(result['content'])  # type: ignore
        decrypted_content = await alloy_client.standard_attached().decrypt(
            recreated_content, metadata
        )
        
        print(f"Title: {decrypted_title}")  
        print(f"Score: {result['@search.score']}")
        if result.get('@search.reranker_score'):
            print(f"Reranker Score: {result['@search.reranker_score']}")
        print(f"Content: {decrypted_content}")  
        print(f"Category: {result['category']}\n")

        captions = result["@search.captions"]
        if captions:
            caption = captions[0]
            if caption.highlights:
                print(f"Caption: {caption.highlights}\n")
            else:
                print(f"Caption: {caption.text}\n")

async def main():

  load_dotenv(override=True) # take environment variables from .env.
  
  # The following variables from your .env file are used in this notebook
  endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
  credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_ADMIN_KEY", "")) if len(os.getenv("AZURE_SEARCH_ADMIN_KEY", "")) > 0 else DefaultAzureCredential()
  index_name = os.getenv("AZURE_SEARCH_INDEX")
  azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
  azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
  azure_openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
  azure_openai_embedding_dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1024))
  embedding_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
  azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
  
  openai_credential = DefaultAzureCredential()
  token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")
  
  client = AzureOpenAI(
      azure_deployment=azure_openai_embedding_deployment,
      api_version=azure_openai_api_version,
      azure_endpoint=azure_openai_endpoint,
      api_key=azure_openai_key,
      azure_ad_token_provider=token_provider if not azure_openai_key else None
  )
  
  # Generate Document Embeddings using OpenAI 3 large
  # Read the text-sample.json
  path = os.path.join('data', 'text-sample.json')
  with open(path, 'r', encoding='utf-8') as file:
      input_data = json.load(file)
  
  titles = [item['title'] for item in input_data]
  content = [item['content'] for item in input_data]
  title_response = client.embeddings.create(input=titles, model=embedding_model_name, dimensions=azure_openai_embedding_dimensions)
  title_embeddings = [item.embedding for item in title_response.data]
  content_response = client.embeddings.create(input=content, model=embedding_model_name, dimensions=azure_openai_embedding_dimensions)
  content_embeddings = [item.embedding for item in content_response.data]
  
  # The symetrical key need to be strong ....
  # You can generate one with this command for a 128 bytes key: openssl rand -hex 128
  key_bytes = b"49cdae0806d2d5edc5d3fe05f2f535591100e8cf6c6905c86fbcd26859986dbdcd2e803ec130920ff78281358a316a14ae2ce5c90127eeac8ba7ca08df1de4874abfe9d04c6d8e1847dda513da3a1eaee7970c9165e7834230eb04cfb444755feea82dacceb8d4c6460f4a6baef73b2236cdcb9fb478e98812862ce92fe1b48f"
  standalone_secret = alloy.StandaloneSecret(1, alloy.Secret(key_bytes))
  approximation_factor = 2.5
  vector_secrets = {
      "text-samples": alloy.VectorSecret(
              approximation_factor,
              alloy.RotatableSecret(standalone_secret, None),
          )
      }
  standard_secrets = alloy.StandardSecrets(1, [standalone_secret])
  deterministic_secrets = {"text-samples": alloy.RotatableSecret(standalone_secret, None)}
  config = alloy.StandaloneConfiguration(
         standard_secrets, deterministic_secrets, vector_secrets
  )
  alloy_client = alloy.Standalone(config)
  metadata = alloy.AlloyMetadata.new_simple("tenant-one")
  secret_path = "text-samples"
  derivation_path = "sentence"
  print("Transforming sentence to vectors and encrypting them...")
  textsamples_objs = list()
  
  # Generate embeddings for title and content fields
  for i, item in enumerate(input_data):
  
      contentText_vector = alloy.PlaintextVector(
              content_embeddings[i], secret_path, derivation_path
          )
      titleText_vector = alloy.PlaintextVector(
              title_embeddings[i], secret_path, derivation_path
          )
          # Some questions contain HTML tags that muddle the results, so we'll skip inserting those ones
      
      # Encrypt Content and Vector
      (encrypted_contentVector, encrypted_contentContent) = await asyncio.gather(
          alloy_client.vector().encrypt(contentText_vector, metadata),
          alloy_client.standard_attached().encrypt(
              bytes(item['content'], "utf-8"), metadata
          ) )
      
  
      # Encrypt Title and Vector
      (encrypted_titlevector, encrypted_Titlecontent) =  await asyncio.gather(
          alloy_client.vector().encrypt(titleText_vector, metadata),
          alloy_client.standard_attached().encrypt(
              bytes(item['title'], "utf-8"), metadata
          )   
      )
      
      # Replace all the values with the encrypted ones
      item['title'] = base64.b64encode(encrypted_Titlecontent).decode()
      item['content'] =  base64.b64encode(encrypted_contentContent).decode()
      item['titleVector'] = encrypted_titlevector.encrypted_vector
      item['contentVector'] = encrypted_contentVector.encrypted_vector
  
  # Output embeddings to docVectorsEncrypted.json file
  output_path = os.path.join('output', 'docVectorsEncrypted.json')
  output_directory = os.path.dirname(output_path)
  if not os.path.exists(output_directory):
      os.makedirs(output_directory)
  with open(output_path, "w") as f:
      json.dump(input_data, f)


  # Create a search index
  index_client = SearchIndexClient(
      endpoint=endpoint, credential=credential)
  fields = [
      SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
      SearchableField(name="title", type=SearchFieldDataType.String),
      SearchableField(name="content", type=SearchFieldDataType.String),
      SearchableField(name="category", type=SearchFieldDataType.String,
                      filterable=True),
      SearchField(name="titleVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                  searchable=True, vector_search_dimensions=azure_openai_embedding_dimensions, vector_search_profile_name="myHnswProfile"),
      SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                  searchable=True, vector_search_dimensions=azure_openai_embedding_dimensions, vector_search_profile_name="myHnswProfile"),
  ]
  
  # Configure the vector search configuration  
  vector_search = VectorSearch(
      algorithms=[
          HnswAlgorithmConfiguration(
              name="myHnsw"
          )
      ],
      profiles=[
          VectorSearchProfile(
              name="myHnswProfile",
              algorithm_configuration_name="myHnsw",
              vectorizer_name="myVectorizer"
          )
      ],
      vectorizers=[
          AzureOpenAIVectorizer(
              vectorizer_name="myVectorizer",
              parameters=AzureOpenAIVectorizerParameters(
                  resource_url=azure_openai_endpoint,
                  deployment_name=azure_openai_embedding_deployment,
                  model_name=embedding_model_name,
                  api_key=azure_openai_key
              )
          )
      ]
  )
  
  semantic_config = SemanticConfiguration(
      name="my-semantic-config",
      prioritized_fields=SemanticPrioritizedFields(
          title_field=SemanticField(field_name="title"),
          keywords_fields=[SemanticField(field_name="category")],
          content_fields=[SemanticField(field_name="content")]
      )
  )
  
  # Create the semantic settings with the configuration
  semantic_search = SemanticSearch(configurations=[semantic_config])
  
  # Create the search index with the semantic settings
  index = SearchIndex(name=index_name, fields=fields,
                      vector_search=vector_search, semantic_search=semantic_search)
  result = index_client.create_or_update_index(index)
  print(f'{result.name} created')
  
  
  # Upload some documents to the index
  output_path = os.path.join('output', 'docVectorsEncrypted.json')
  output_directory = os.path.dirname(output_path)
  if not os.path.exists(output_directory):
      os.makedirs(output_directory)
  with open(output_path, 'r') as file:  
      documents = json.load(file)  
  search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
  result = search_client.upload_documents(documents)
  print(f"Uploaded {len(documents)} documents") 


  # Pure Vector Search
  query = "scalable storage solution"  
  query_emb = client.embeddings.create(input=query, model=embedding_model_name, dimensions=azure_openai_embedding_dimensions).data[0].embedding  
 
  print(f"\nQuerying database with input: '{query}'")

  plaintext_query = alloy.PlaintextVector(query_emb, secret_path, derivation_path)
  # `generate_query_vectors` returns a list because the secret involved may be in rotation. In that case you should
  # search for both resulting vectors.
  query_vector = (
      await alloy_client.vector().generate_query_vectors(
          {"vec_1": plaintext_query}, metadata
      )
  )["vec_1"][0].encrypted_vector

  #  50 is an optimal value for k_nearest_neighbors when performing vector search
  #  To learn more about how vector ranking works, please visit https://learn.microsoft.com/azure/search/vector-search-ranking
  # Use the encrypted embedded query for the search
  vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=50, fields="contentVector, titleVector")
 
  results = search_client.search(  
    search_text=None,  
    vector_queries= [vector_query],
    select=["title", "content", "category"],
    top=3
  )   
  
  await print_results(results, alloy_client, metadata)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())