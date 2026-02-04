import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/hooks/use-toast";
import {
  MessageSquare,
  Send,
  Bot,
  User,
  Clock,
  Search,
  TrendingUp,
  AlertTriangle
} from "lucide-react";

interface ChatMessage {
  id: string;
  type: "user" | "ai";
  content: string;
  timestamp: string;
  suggestedActions?: string[];
}

interface QuerySuggestion {
  id: string;
  category: "maintenance" | "equipment" | "schedule" | "analytics";
  text: string;
  description: string;
}

const QueryInterface = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      type: "ai",
      content: "Hello! I'm your AI maintenance assistant. I can help you with equipment status, maintenance history, scheduling recommendations, and predictive insights. What would you like to know?",
      timestamp: new Date().toISOString(),
      suggestedActions: ["Check equipment status", "View maintenance schedule", "Analyze failure patterns"]
    }
  ]);

  const [currentQuery, setCurrentQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const querySuggestions: QuerySuggestion[] = [
    {
      id: "1",
      category: "equipment",
      text: "What's the current status of Turbine Generator #3?",
      description: "Get real-time equipment health and performance metrics"
    },
    {
      id: "2",
      category: "maintenance",
      text: "When was the last maintenance on Conveyor Belt A-12?",
      description: "View maintenance history and records"
    },
    {
      id: "3",
      category: "schedule",
      text: "What maintenance is scheduled for this week?",
      description: "See upcoming maintenance tasks and priorities"
    },
    {
      id: "4",
      category: "analytics",
      text: "Show me failure patterns for hydraulic systems",
      description: "Analyze historical data for predictive insights"
    }
  ];

  // Auto-scroll logic
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async () => {
    if (!currentQuery.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: "user",
      content: currentQuery,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    const input = currentQuery;
    setCurrentQuery("");
    setIsLoading(true);

    try {
      const response = await fetch(`http://localhost:8448/response?input=${encodeURIComponent(input)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        throw new Error("Failed to get AI response");
      }

      const data = await response.json();

      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: data.message || "I apologize, but I couldn't process your request.",
        timestamp: new Date().toISOString(),
        // suggestedActions: ["View detailed report", "Schedule maintenance"] // Optional: Add if backend provides or keep static
      };

      setMessages(prev => [...prev, aiResponse]);

    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to communicate with AI Assistant",
        variant: "destructive"
      });

      // Optional: Add error message to chat
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: "Sorry, I'm having trouble connecting to the server right now. Please try again later.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: QuerySuggestion) => {
    setCurrentQuery(suggestion.text);
  };

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "equipment":
        return <Badge variant="default">Equipment</Badge>;
      case "maintenance":
        return <Badge variant="secondary">Maintenance</Badge>;
      case "schedule":
        return <Badge variant="outline">Schedule</Badge>;
      case "analytics":
        return <Badge className="bg-accent text-accent-foreground">Analytics</Badge>;
      default:
        return <Badge variant="secondary">{category}</Badge>;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "equipment":
        return <TrendingUp className="h-4 w-4" />;
      case "maintenance":
        return <Search className="h-4 w-4" />;
      case "schedule":
        return <Clock className="h-4 w-4" />;
      case "analytics":
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <MessageSquare className="h-4 w-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">AI Query Interface</h1>
          <p className="text-muted-foreground">Ask questions about equipment status, maintenance history, and get AI-powered insights</p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Query Suggestions */}
          <Card className="shadow-corporate">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Quick Queries
              </CardTitle>
              <CardDescription>
                Common questions and suggested queries
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {querySuggestions.map((suggestion) => (
                <div
                  key={suggestion.id}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="cursor-pointer rounded-lg border p-3 hover:bg-secondary/50 transition-colors"
                >
                  <div className="flex items-start gap-2 mb-2">
                    {getCategoryIcon(suggestion.category)}
                    {getCategoryBadge(suggestion.category)}
                  </div>
                  <h4 className="font-medium text-sm mb-1">{suggestion.text}</h4>
                  <p className="text-xs text-muted-foreground">{suggestion.description}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Chat Interface */}
          <Card className="lg:col-span-2 shadow-elevated">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                AI Assistant Chat
              </CardTitle>
              <CardDescription>
                Interactive conversation with your maintenance AI agent
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Messages */}
              <div className="h-[400px] overflow-y-auto space-y-4 p-4 border rounded-lg bg-muted/20">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg p-3 ${message.type === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card text-card-foreground shadow-sm'
                      }`}>
                      <div className="flex items-center gap-2 mb-2">
                        {message.type === 'user' ? (
                          <User className="h-4 w-4" />
                        ) : (
                          <Bot className="h-4 w-4" />
                        )}
                        <span className="text-xs opacity-80">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-sm">
                        {message.type === 'user' ? (
                          <div className="whitespace-pre-wrap">{message.content}</div>
                        ) : (
                          <div className="space-y-1">
                            {message.content.split('\n').map((line, i) => {
                              const trimmedLine = line.trim();

                              // Handle Horizontal Rule
                              if (trimmedLine === '---' || trimmedLine === '***') {
                                return <hr key={i} className="my-2 border-border" />;
                              }

                              // Handle Headers
                              if (trimmedLine.startsWith('### ')) {
                                return (
                                  <h3 key={i} className="text-sm font-bold mt-2 mb-1" dangerouslySetInnerHTML={{
                                    __html: line.replace(/^###\s+/, '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                  }} />
                                );
                              }

                              if (trimmedLine.startsWith('## ')) {
                                return (
                                  <h2 key={i} className="text-base font-bold mt-3 mb-1" dangerouslySetInnerHTML={{
                                    __html: line.replace(/^##\s+/, '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                  }} />
                                );
                              }

                              // Handle bullet points
                              if (trimmedLine.startsWith('- ') || trimmedLine.startsWith('• ')) {
                                return (
                                  <div key={i} className="flex gap-2 ml-2">
                                    <span className="text-muted-foreground">•</span>
                                    <span dangerouslySetInnerHTML={{
                                      __html: line.replace(/^[-•]\s+/, '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                    }} />
                                  </div>
                                );
                              }
                              // Handle headers or empty lines
                              if (!trimmedLine) return <div key={i} className="h-2" />;

                              // Handle standard text with bolding
                              return (
                                <div key={i} dangerouslySetInnerHTML={{
                                  __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                }} />
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {message.suggestedActions && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {message.suggestedActions.map((action, index) => (
                            <Button
                              key={index}
                              variant="outline"
                              size="sm"
                              className="text-xs"
                              onClick={() => setCurrentQuery(action)}
                            >
                              {action}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-card text-card-foreground rounded-lg p-3 shadow-sm">
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        <span className="text-sm">AI is thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="flex gap-2">
                <Input
                  placeholder="Ask about equipment status, maintenance history, or get recommendations..."
                  value={currentQuery}
                  onChange={(e) => setCurrentQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  className="flex-1"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={isLoading || !currentQuery.trim()}
                  className="bg-gradient-corporate shadow-corporate"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default QueryInterface;