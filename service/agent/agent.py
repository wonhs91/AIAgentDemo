# %%
from dotenv import load_dotenv

import os
from typing import TypedDict, Annotated, Literal
from langchain_groq import ChatGroq
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.constants import Send
from langchain_pinecone import PineconeVectorStore
from langchain_community.tools import DuckDuckGoSearchResults
from langgraph.prebuilt import ToolNode
from langgraph.graph import add_messages, StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv(override=True)

def get_llama31_llm():
  from langchain_google_vertexai import ChatVertexAI
  vertex_llm = ChatVertexAI(  
      model="llama-3.1-70b-instruct-maas",
      max_retries=1,
      location="us-central1",
      max_tokens=4000,
  )
  return vertex_llm

class AIDemoAgent:
    def __init__(self,
                 groq_model="deepseek-r1-distill-llama-70b",
                 pinecone_ind_name="langgraph-docs",
                 embedding_model="models/text-embedding-004"):
        
        self.llm_model = os.environ.get('GROQ_MODEL', groq_model)
        self.pinecone_ind_name = os.environ.get('PINECONE_INDEX_NAME', pinecone_ind_name)
        self.embedding_model = os.environ.get('EMBEDDING_MODEL', embedding_model)
        
        self.llm = ChatGroq(model=self.llm_model)    
        # self.llm = get_llama31_llm()
        self.vectorstore = PineconeVectorStore(index_name=self.pinecone_ind_name, embedding=GoogleGenerativeAIEmbeddings(model=self.embedding_model))
    
        self.llm_with_tools = None
        self.tools = None
        self.bind_llm_with_tools()
        
        self.agent = None

        self.curr_docs = []
    
    def bind_llm_with_tools(self):
        
        @tool
        def vectordb_search(search_query: str):
            """Search the query from vectorstore db on langgraph

            Args:
                search_query: query to search in vectorstore db
            """

            retriever = self.vectorstore.as_retriever()
            retrieved_docs = retriever.invoke(search_query)
            # return evaluate_documents(search_query, retrieved_docs)
            self.curr_docs = retrieved_docs
            return retrieved_docs

        @ tool
        def internet_search(search_query: str):
            """Search the query from internet

            Args:
                user_question: original  user question to be addressed
                search_query: Exact search terms
            """
            search = DuckDuckGoSearchResults(output_format="list")
            retrieved_snippets = search.invoke(search_query)
            
            return retrieved_snippets
    

        @tool
        def user_ask(question: str):
            """Ask the user for any clarification or more information

            Args:
                question: question to ask the user
            """
            # # Probably will be replaced by api call
            # user_input = input(f"{question}\n\nanswer: ")
            # return user_input
            pass

        search_tools = [vectordb_search, internet_search, user_ask]
        self.tools = search_tools
        self.llm_with_tools = self.llm.bind_tools(search_tools, parallel_tool_calls=False)

    def build_agent(self):
        
        class State(TypedDict):
            messages: Annotated[list[AnyMessage], add_messages]
            sources: list[dict]
            
            # main agent
        def main_agent(state):
            sys_msg = """
1. **Role and Purpose**  
   - Define the AI’s role as a specialized assistant for LangGraph inquiries.  
   - Emphasize accuracy and clarity.  

2. **Core Functionality (ReAct Framework)**  
   - Explain the ReAct workflow: **Reason** (analyze query), **Act** (choose tool), **Repeat** (validate/critique).  
   - List the three tools and their purposes.  

3. **Tool Selection Guidelines**  
   - **VectorStore Search**:  
     - Mandatory for LangGraph-specific questions (APIs, workflows, concepts).  
     - Prohibited for non-LangGraph topics (e.g., general Python).  
   - **Internet Search**:  
     - Use only if VectorStore lacks info or for very recent/niche updates.  
     - Avoid redundancy (don’t use if VectorStore answers sufficiently).  
   - **Clarification Tool**:  
     - Trigger when the query is ambiguous, vague, or lacks context.  

4. **Response Workflow**  
   - Step 1: Check if the query is LangGraph-related.  
   - Step 2: Use VectorStore first; validate answer completeness.  
   - Step 3: If gaps exist, use Internet Search.  
   - Step 4: If unclear, ask the user for clarification.  

5. **Tone and Style**  
   - Concise, technical but approachable.  
   - Avoid assumptions; clarify jargon if needed.  

6. **Error Handling**  
   - If no results from tools: State uncertainty and offer alternatives (e.g., “Would you like me to search the web?”).  

7. **Ethical Boundaries**  
   - Refuse off-topic, harmful, or non-technical requests politely.  

"""

            response = self.llm_with_tools.invoke([SystemMessage(content=sys_msg)] + state['messages'])
            res_state = {
                'messages': [response]
            }
            if self.curr_docs:
                metadata_list = [item.metadata for item in self.curr_docs]
                res_state['sources'] = metadata_list
                # remove sources
                self.curr_docs = []

            return res_state

        class UserClarificationState(TypedDict):
            question: str
            tool_call_id: str
            
        def ask_user(state: UserClarificationState):
            question = state['question']
            tool_call_id = state['tool_call_id']
            
            return {
                'messages': [AIMessage(content=question)],
                'tool_call_id': tool_call_id
            }




        def tools_condition_route(state) -> Literal['tools', "ask_user", END]:
            ai_message = state['messages'][-1]
            if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                tool_calls = ai_message.tool_calls
                for tool_call in tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_call_id = tool_call['id']
                    if tool_name == 'user_ask':
                        return Send("ask_user", {'question': tool_args['question'], 'tool_call_id': tool_call_id})
                        # next_routes.append(Send("ask_user", {'orig_question': state['messages'][0], 'question': tool_args['question'], 'tool_call_id': tool_call_id}))
                    else: 
                        return "tools"
            else:
                return END


        agent_builder = StateGraph(State)

        agent_builder.add_node(main_agent)
        agent_builder.add_node(ToolNode(self.tools))
        agent_builder.add_node(ask_user)

        agent_builder.add_edge(START, 'main_agent')
        agent_builder.add_conditional_edges('main_agent', tools_condition_route)
        agent_builder.add_edge('tools', 'main_agent')
        agent_builder.add_edge('ask_user', END)

        memory = MemorySaver()

        self.agent = agent_builder.compile(memory)
                
    def draw_graph(self):
        if not self.agent:
            print("agent not yet built")    
        
        return self.agent.get_graph().draw_mermaid_png()  
    
    

# # %%
# from IPython.display import display, Image
# agent = AIDemoAgent()

# agent.build_agent()

# display(Image(agent.draw_graph()))


# state = {
#   "messages": [HumanMessage("how high can a window be?")]
# }
# config = {
#   "configurable": {
#     "thread_id": 1
#   }
# }
# agent.agent.invoke(state, config)

# # %%
