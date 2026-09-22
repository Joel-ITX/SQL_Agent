import streamlit as st
from pathlib import Path
from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_classic.agents.agent_types import AgentType
from langchain_classic.callbacks import StreamlitCallbackHandler
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq

st.set_page_config(page_title='Chat with SQL DB',page_icon='🦜')
st.title('🦜 Chat with your SQL Database')

LOCALDB='USE_LOCALDB'
MYSQL='USE_MYSQL'

radio_opt=['Use SQLLite3 Database - Student.db','Connect to any other MySQL Database']

selected_opt=st.sidebar.radio(label='Choose the Database of your choice:', options=radio_opt)

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input('MySQL Host:')
    mysql_user=st.sidebar.text_input('MySQL User:')
    mysql_password=st.sidebar.text_input('MySQL Password:',type='password')
    mysql_db=st.sidebar.text_input('MySQL Database:')
else:
    db_uri=LOCALDB

api_key=st.sidebar.text_input(label='Groq API Key:',type='password')

if not db_uri:
    st.info('Please enter the database information and URI')
    st.stop()
if not api_key:
    st.info('Please enter the LLM API Key')
    st.stop()

#LLM
llm = ChatGroq(
    groq_api_key=api_key,
    model="qwen/qwen3.8-27b",
    temperature=0,
    streaming=True,
)

@st.cache_resource(ttl='2h')
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/'student.db').absolute()
        creator=lambda:sqlite3.connect(f'file:{dbfilepath}?mode=ro',uri=True)
        return SQLDatabase(create_engine('sqlite:///',creator=creator))
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error('Please provide all SQL Connection details')
            st.stop()
        return SQLDatabase(create_engine(f'mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}'))
    
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)

#Initializing the Toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    max_iterations=25,
)

if 'messages' not in st.session_state or st.sidebar.button('Clear message history'):
    st.session_state['messages']=[{'role':'assistant','content':'How may I help you?'}]

for msg in st.session_state.messages:
    st.chat_message(msg['role']).write(msg['content'])

user_query = st.chat_input(placeholder='Ask about anything in the Database')

if user_query:
    st.session_state.messages.append({'role':'user','content':user_query})
    st.chat_message('user').write(user_query)

    with st.chat_message('assistant'):
        streamlit_callback=StreamlitCallbackHandler(st.container(),expand_new_thoughts=True)
        answer=agent.run(user_query,callbacks=[streamlit_callback])
        st.session_state.messages.append({'role':'assistant','content':answer})
        st.write(answer)

