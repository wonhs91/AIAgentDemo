"use client"

import { useState } from "react"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  role: "user" | "assistant"
  content: string
}

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

      const assistantMessage: Message = { role: "assistant", content: data.answer }
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
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>AI Agent Demo</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[60vh] pr-4">
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
                    {message.content}
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

