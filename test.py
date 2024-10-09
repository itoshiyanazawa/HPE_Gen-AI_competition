# -*- coding: utf-8 -*-


# Commented out IPython magic to ensure Python compatibility.
# %%capture
# 
# # install packages
# !python3 -m pip install -qU elasticsearch==8.11.1 langchain \
# sentence_transformers openai pypdf python-dotenv
# 
# # import generic modules
# from IPython.display import display
# from dotenv import load_dotenv
# from getpass import getpass
# from urllib.request import urlretrieve
# import os
# from openai import OpenAI

!pip install tiktoken

!pip install dropbox


from enum import Enum

# let's setup a simple enum to help us keep track of our ES connection type
class ESConnection(Enum):
    NONE = 0
    BINARY = 1
    DOCKER = 2
    CLOUD = 3

es_connection = ESConnection.NONE
print(f"es_connection: {es_connection.name}")



# Commented out IPython magic to ensure Python compatibility.
# %%capture
# 
# # remove any previous elasticsearch installations, download and export es version 8.11.1
# !rm -rf elasticsearch*
# # !wget -q https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.1-linux-x86_64.tar.gz
# url = "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.1-linux-x86_64.tar.gz"
# file_name = 'es_download'
# urlretrieve(url, file_name)
# 
# !tar -xzf es_download
# # elasticsearch-8.11.1-linux-x86_64.tar.gz
# 
# # set up user to run ES daemon and configure cgroups
# !sudo chown -R daemon:daemon elasticsearch-8.11.1/
# !umount /sys/fs/cgroup
# !apt install cgroup-tools
# 
# es_connection=ESConnection.BINARY

"""Disable security and set elasticsarch.yml parameters"""

# Disable security and allow anonymous users
# WARNING: this is for demo purposes only. Always use security and authentication for real world applications
with open('./elasticsearch-8.11.1/config/elasticsearch.yml', 'a') as writefile:
    writefile.write("xpack.security.enabled: false\n")
    writefile.write("xpack.security.authc:\n")
    writefile.write("  " + "anonymous:\n")
    writefile.write("    " + "username: anonymous_user\n")
    writefile.write("    " + "roles: superuser\n")
    writefile.write("    " + "authz_exception: true")

# if you want to verify that the elasticsearch.yml file is written to correctly, uncomment this code block
#with open('./elasticsearch-8.11.1/config/elasticsearch.yml', 'r') as readfile:
#    print(readfile.read())

"""Start ES Daemon in Background"""

# Commented out IPython magic to ensure Python compatibility.
# %%bash --bg
# 
# sudo -H -u daemon elasticsearch-8.11.1/bin/elasticsearch

"""It takes ES a while to get running, so be sure to wait a few seconds, or just run the manual 30 second sleep command below."""

!sleep 30

"""#### Check Elasticearch Binary
We'll run a few checks to make sure Elasticsearch is up and running, and accessible
"""

# Check if elasticsearch is running
# There should be 3 daemon elasticsearch processes and 3 root processes in the list when grepping for elasticsearch
!ps -ef | grep elastic

# curl the cluster once with the elastic superuser and default password so that we can do anonymous calls moving forward
# WARNING: do not pass user passwords like this in real life. This. is. a. demo.
!curl -u elastic:password -H 'Content-Type: application/json' -XGET http://localhost:9200/?pretty=true



# uncomment and run this block to use Docker connection

#es_connection=ESConnection.DOCKER

"""### Elastic Cloud

Many organizations may already have an Elastic Cloud cluster to connect to. Or maybe you have a free trial. In either case, we can simply pass in the cloud id and api key to create a client.

Please refer to the [Elasticsearch documentation](https://www.elastic.co/guide/en/cloud/current/ec-api-keys.html) for retreiving this information. We will pass these values in securely when we setup environment variables in our next step.
"""

# uncomment and run this block to use Elastic Cloud connection

#es_connection=ESConnection.CLOUD

"""## Setup Environment Variables

To integrate our RAG app with OpenAI and Elasticsearch, we need to pass some sensitive data, like api keys and passwords. We'll use python's getpass package to input the sensitve info, and store it in a .env file that we can then use in our code.

It's a bit of a roundabout approach, but better than pasting senstive data directly into the code. You can skip to the `load_dotenv()` function if running locally and have your own .env file at the root directory, next to the ipynb file.
"""

# create .env file
!touch .env

with open('.env', 'a') as envFile:
  # write openai api key
  envFile.write("OPENAI_API_KEY=" + getpass(prompt="enter your openai api key ") + "\n")
  # if running es binary or docker, add the es_url
  if es_connection == ESConnection.BINARY or es_connection == ESConnection.DOCKER:
    envFile.write("ELASTICSEARCH_URL=http://localhost:9200" + "\n")
  # if running es cloud, enter cloud id and api key
  elif es_connection == ESConnection.CLOUD:
    envFile.write("ELASTIC_CLOUD_ID=" + getpass(prompt="enter your ES cloud id ")+ "\n")
    envFile.write("ELASTIC_API_KEY=" + getpass(prompt="enter your ES cloud api key "))

# uncomment this section if you need to double check the .env file
# with open('.env', 'r') as readfile:
#     print(readfile.read())

# Load variables from .env file
load_dotenv('.env')

# Set local variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")

"""## Final Elasticsearch Check

Instantiate Elasticsearch python client based on installation type and double check connection.
"""

from elasticsearch import Elasticsearch

# determine what connection data to pass to the client init
if ELASTICSEARCH_URL:
    elasticsearch_client = Elasticsearch(
        hosts=[ELASTICSEARCH_URL],
    )
elif ELASTIC_CLOUD_ID:
    elasticsearch_client = Elasticsearch(
        cloud_id=ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY
    )
else:
    raise ValueError(
        "Please provide either ELASTICSEARCH_URL or ELASTIC_CLOUD_ID and ELASTIC_API_KEY"
    )

print(elasticsearch_client.info())


from langchain_community.document_loaders import DropboxLoader

# Generate access token: https://www.dropbox.com/developers/apps/create.
dropbox_access_token = "ACCESS TOKEN"
# Dropbox root folder
dropbox_folder_path = ""

loader = DropboxLoader(
    dropbox_access_token=dropbox_access_token,
    dropbox_folder_path=dropbox_folder_path,
    recursive=False,
)

documents = loader.load()

for document in documents:
    print(document)

"""#### Get the PDF and Split into Pages"""

from langchain.document_loaders import PyPDFLoader

# get the us code pdf on the president and unzip it
from urllib.request import urlretrieve
url = "https://uscode.house.gov/download/releasepoints/us/pl/118/22u1/pdf_usc03@118-22u1.zip"
file_name = "president.pdf.zip"
urlretrieve(url, file_name)
!unzip president.pdf.zip

# now load the pdf as text and break into pages
loader = PyPDFLoader("usc03@118-22.pdf")
pages = loader.load_and_split()

from langchain.document_loaders import PyPDFLoader

# get the us code pdf on the president and unzip it
from urllib.request import urlretrieve
# url = "https://uscode.house.gov/download/releasepoints/us/pl/118/22u1/pdf_usc03@118-22u1.zip"
# file_name = "president.pdf.zip"
# urlretrieve(url, file_name)
# !unzip president.pdf.zip

# now load the pdf as text and break into pages
loader = PyPDFLoader("/content/manual_data1.pdf")
pages = loader.load_and_split()



from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import ElasticsearchStore

# set our embedding model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# instantiate vectorstore from documents
esVectorStore = ElasticsearchStore.from_documents(
    pages,
    es_connection=elasticsearch_client,
    index_name="the-president",
    embedding=embeddings
)

# verify the ElasticsearchStore was created
esVectorStore

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import ElasticsearchStore

# Set our embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# Instantiate vectorstore from documents
esVectorStore = ElasticsearchStore.from_documents(
    pages,
    es_connection=elasticsearch_client,
    index_name="the-president",
    embedding=embeddings
)

# Verify the ElasticsearchVectorStore was created
esVectorStore


# helper function
def showResults(results):
  print("Total results: ", len(results))
  for i in range(len(results)):
    print(results[i])

"""`showResults()` is a just a helper function to help display our results later.

#### Similarty Search
"""

query = "who succeeds the president"
result = esVectorStore.similarity_search(query=query)

showResults(result)

query = "Give me emergency stop procedure for ACU RITE MILLPWR"
result = esVectorStore.similarity_search(query=query)

showResults(result)


from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

retriever = esVectorStore.as_retriever(search_kwargs={"k": 3})

template = """Answer the question with the following context:
{context}

Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(openai_api_key=OPENAI_API_KEY)
    | StrOutputParser()
)

q = input("Question: ") or "What is the electoral college?"
print("\n")
reply = chain.invoke(q)
display("Answer: " + reply)

q = input("Question: ") or "What is the electoral college?"
print("\n")
reply = chain.invoke(q)
display("Answer: " + reply)



