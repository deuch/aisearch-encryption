# aisearch-encryption

This repo is a demonstration to use [cloakedAI from ironcorelabs](https://ironcorelabs.com/products/cloaked-ai/) with AI Search to do some pure Vector search on encrypted datas.  
Those datas are encrypted with Property-preserving Encryption and let the AI Search engine to do some cosine similarity on the encrypted vector.  
Content of the chunks are encrypted too, so it is not possible to do a hybrid search with a text on them.  

## Pre-requisites

* Azure OpenAI Instance with embeddings model deployed
  * text-embedding-3-large

Rename the **.env_sample** to **.env** and set the according values : 

| Parameter | Optional | Note |
| --- | --- | ------------- |
|AZURE_SEARCH_SERVICE_ENDPOINT|No|Endpoint of the AI Search Service|
|AZURE_SEARCH_ADMIN_KEY|No|Api Key of the AI Search| 
|AZURE_SEARCH_INDEX|No|Name of the AI Search Index|
|AZURE_OPENAI_ENDPOINT|No|Endpoint of the Azure OpenAI Instance|
|AZURE_OPENAI_KEY|No|Api Key of the Azure OpenAI Service|
|AZURE_OPENAI_EMBEDDING_DEPLOYMENT|No|Deployment model used for embeddings|
|AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME|No|Name of the embeddings deployment in Azure OpenAI|
|AZURE_OPENAI_API_VERSION|No|Azure OpenAI API version|

Install all the pip packages

    pip install -r requirements

**For ironcore-alloy, you need to have glibc > 2.33 to use the package if your are running on LINUX**  
Ubuntu >= 22.x provide glibc 2.35 at least

You can update or install the version of glibc with those commands (in Ubuntu for eg) : 

    sudo apt udate
    sudo apt upgrade
    sudo apt install glibc-source

## How it works

Run the code :

    python aisearch-encrypted.py

What happens ?

* It will read the text-sample.json file in the ./data directory
* Generate an output file in the ./output directory
  * In this file, the content of the fields title and vector are encrypted and the according vectors too
* Creation/Update of the index in Ai Search
* Insertion of the data (encrypted) in the index
* Do a search in AI Search (*pure Vector search not a hybrid one*) **directly on the encrypted datas** (Property-preserving Encryption)

You can check directly in your AI Search index that the data and vector are encrypted (you may need to switch beteen API Key authentication and System Managed Indentity on the Ai Search to be able to see the vector. The 2 vectors fields are not retrievable by default, so you have to enable it too. Maybe something to improve in the future :))

Some changes can be made to use determinist encryption to be able to use filter in the request (to filter on category for example). In the code, i use a non deterministic encryption for chuncks so you can not search within this data in "plaintext" mode. (Available soon :))





