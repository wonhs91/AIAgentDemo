from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import uuid
from mangum import Mangum

from agent.agent import AIDemoAgent

app = FastAPI()

research_agent = AIDemoAgent()
research_agent.build_agent()
agent = research_agent.agent

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_headers=["*"],
  allow_methods=["*"]
)

handler = Mangum(app)

@app.get("/")
async def get():
  return {"message": "AI Demo"}

class ConstructionQuery(BaseModel):
  message: str
  
@app.post("/api/demo-agent")
async def start_chat(req_body: ConstructionQuery):
  thread_id = str(uuid.uuid4())
  config = {"configurable": {"thread_id": thread_id}}
  state = {
    "messages": [HumanMessage(content=req_body.message)]
  }
  
  response = agent.invoke(state, config=config)
  
  for m in response['messages']:
    print(m.pretty_print())
    
  return {"answer": response['messages'][-1].content, "thread_id": thread_id}


@app.post("/api/demo-agent/{thread_id}")
async def continue_chat(req_body: ConstructionQuery, thread_id: str):
  config = {"configurable": {"thread_id": thread_id}}
  state = {
    "messages": [HumanMessage(content=req_body.message)]
  }
  
  response = agent.invoke(state, config=config)
  
  return {"answer": response['messages'][-1].content, "thread_id": thread_id}
