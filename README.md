# aisearch-encryption

## Pre-requisites

* Azure OpenAI Instance with embeddings model deployed
  * text-embedding-3-large

Rename the **.env_sample** to **.env** and set the according values : 

| Parameter | Optional | Note |
| --- | --- | ------------- |
|AZURE_SEARCH_SERVICE_ENDPOINT|No|Endpoint of the Ai Search Service|
|AZURE_SEARCH_ADMIN_KEY|No|Api Key of the Ai Search| 
|AZURE_SEARCH_INDEX|No|Name of the Ai Search Index|
|AZURE_OPENAI_ENDPOINT|No|Endpoint of the Azure OpenAI Instance|
|AZURE_OPENAI_KEY|No|Api Key of the Azure OpenAI Service|
|AZURE_OPENAI_EMBEDDING_DEPLOYMENT|No|Deployment model used for embeddings|
|AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME|No|Name of he embeddings deployment in Azure OpenAI|
|AZURE_OPENAI_API_VERSION|No|Azure OpenAI API version|

Install all the pip packages

    pip install -r requirements

**For ironcore-alloy, you need to have glibc > 2.33 to use the package**  
Ubuntu >= 22.x provide glibc 2.35 at least

You can update or install the version of glibc with those commands (in Ubuntu) : 

    sudo apt udate
    sudo apt upgrade
    sudo apt install glibc-source

## How it works

Run the code :

    python aisearch-encrypted.py

What happens ?

* It will read the text-sample.json file in the ./data directory
* Generate an ouput file in the ./output directory
  * In this file, the content of the fields are encrypted and the vectors too
* Creation/Update of the index in Ai Search
* Insertion of the data (encrypted) in the index
* Do a search in AI Search (pure Vector search not a hybrid one) **directly on the encrypted datas** (Property Based Encryption)

You can check directly in your AI Search index that the data and vector are encrypted (you may need to switch beteen API Key authentication and System Managed Indentity on the Ai Search to be able to see the vector. The 2 vectors fields are not retrievable by default, so you have to enable it too)



