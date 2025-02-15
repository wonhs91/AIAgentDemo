"use client"

import { useState } from "react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react"

interface Source {
  description: string
  keywords: string
  title: string
  url: string
}

interface Message {
  role: "user" | "assistant"
  content: string
  sources?: Source[]
}

const Sources = ({ sources }: { sources: Source[] }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center text-sm text-gray-500 hover:text-gray-700"
      >
        {isExpanded ? <ChevronUp className="mr-1" /> : <ChevronDown className="mr-1" />}
        {isExpanded ? "Hide" : "Show"} Sources ({sources.length})
      </Button>
      {isExpanded && (
        <ul className="mt-2 space-y-2">
          {sources.map((source, index) => (
            <li key={index} className="text-sm">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-blue-500 hover:underline"
              >
                {source.title}
                <ExternalLink className="ml-1" size={12} />
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
const MessageContent = ({ content, sources }: { content: string; sources?: Source[] }) => (
    <div>
      <ReactMarkdown
        components={{
          h1: ({ node, ...props }) => <h1 className="text-2xl font-bold my-4" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-xl font-bold my-3" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-lg font-bold my-2" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2" {...props} />,
          li: ({ node, ...props }) => <li className="my-1" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
      {sources && <Sources sources={sources} />}
    </div>
  )

export default function ChatDemo() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [threadId, setThreadId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = { role: "user", content: input }
    setMessages((prevMessages) => [...prevMessages, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const apiUrl = threadId
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/demo-agent/${threadId}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/demo-agent`

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage.content }),
      })

      if (!response.ok) {
        throw new Error("API request failed")
      }

      const data = await response.json()
      setThreadId(data.thread_id)

      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      }
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
    } catch (error) {
      console.error("Error:", error)
      // Handle error (e.g., show an error message to the user)
    } finally {
      setIsLoading(false)
    }
  }


  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <Card className="w-full max-w-4xl">
        <CardHeader>
          <CardTitle className="text-xl">AI Agent Demo</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[80vh] pr-4">
            {" "}
            {/* Added pr-4 for right padding */}
            <div className="space-y-4">
              {" "}
              {/* Added a container div with vertical spacing */}
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[80%] p-2 rounded-lg ${
                      message.role === "user" ? "bg-blue-500 text-white" : "bg-gray-200 text-black"
                    }`}
                  >
                      <MessageContent content={message.content} sources={message.sources} />                
                    </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-center">
                  <span className="inline-block p-2 rounded-lg bg-gray-200 text-black">AI is thinking...</span>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
        <CardFooter>
          <form onSubmit={handleSubmit} className="flex w-full space-x-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-grow"
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading}>
              Send
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  )
}

