import { useState } from "react";
import Dashboard from "@/components/Dashboard";
import LogUploader from "@/components/LogUploader";
import QueryInterface from "@/components/QueryInterface";
import { Button } from "@/components/ui/button";
import { 
  LayoutDashboard, 
  Upload, 
  MessageSquare, 
  Brain,
  Menu,
  X
} from "lucide-react";

const Index = () => {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navigation = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "logs", label: "Log Management", icon: Upload },
    { id: "query", label: "AI Assistant", icon: MessageSquare },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return <Dashboard />;
      case "logs":
        return <LogUploader />;
      case "query":
        return <QueryInterface />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 shadow-corporate">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-gradient-corporate p-2 rounded-lg shadow-accent">
                <Brain className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-corporate bg-clip-text text-transparent">
                  PredictiveMaint AI
                </h1>
                <p className="text-xs text-muted-foreground">
                  Intelligent Manufacturing Maintenance
                </p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    variant={activeTab === item.id ? "default" : "ghost"}
                    className={activeTab === item.id ? "bg-gradient-corporate shadow-corporate" : ""}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    {item.label}
                  </Button>
                );
              })}
            </nav>

            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>

          {/* Mobile Navigation */}
          {isMobileMenuOpen && (
            <nav className="mt-4 flex flex-col gap-2 md:hidden">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id);
                      setIsMobileMenuOpen(false);
                    }}
                    variant={activeTab === item.id ? "default" : "ghost"}
                    className={`justify-start ${
                      activeTab === item.id ? "bg-gradient-corporate shadow-corporate" : ""
                    }`}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    {item.label}
                  </Button>
                );
              })}
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main>
        {renderContent()}
      </main>
    </div>
  );
};

export default Index;
