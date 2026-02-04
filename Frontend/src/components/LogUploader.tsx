import { useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/hooks/use-toast";
import {
  Upload,
  FileText,
  Brain,
  CheckCircle,
  AlertCircle,
  Loader2,
  Calendar as CalendarIcon
} from "lucide-react";
import { useOpenMaintenanceLogs } from "@/hooks/useOpenMaintenanceLogs";
import { useEquipments } from "@/hooks/useEquipments";
import { PredictiveAnalysisLoader } from "@/components/PredictiveAnalysisLoader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { format } from "date-fns";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface LogEntry {
  id: string;
  equipment: string;
  timestamp: string;
  content: string;
  severity: string;
  analyzed: boolean;
}

interface EquipmentDetails {
  name: string;
  serial: string;
}

interface AnalysisReport {
  equipment_details: EquipmentDetails;
  priority: string;
  needs_maintenance: boolean;
  ai_summary: string;
  validation_feedback: string;
}

interface AIAnalysisValidationResponse {
  status: {
    analysis_report: AnalysisReport[];
  };
}

const LogUploader = () => {
  const queryClient = useQueryClient();
  const { data: openLogs } = useOpenMaintenanceLogs();
  const { data: equipments, isLoading: isLoadingEquipments } = useEquipments();

  // Form State
  const [selectedSerial, setSelectedSerial] = useState("");
  const [issueDescription, setIssueDescription] = useState("");
  const [severity, setSeverity] = useState<string>("");
  const [datePredicted, setDatePredicted] = useState<Date | undefined>(undefined);
  const [raisedBy, setRaisedBy] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisReport, setAnalysisReport] = useState<AnalysisReport[]>([]);

  const logs: LogEntry[] = useMemo(() => {
    if (!Array.isArray(openLogs)) return [];

    return openLogs
      .filter(log => !!log && log.raised_by !== "AI System")
      .sort((a, b) => {
        if (!a || !b) return 0;
        const dateA = new Date(a.date_reported || 0).getTime();
        const dateB = new Date(b.date_reported || 0).getTime();
        if (!isNaN(dateA) && !isNaN(dateB) && dateA !== dateB) return dateB - dateA;

        const priorityWeight: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
        const severityA = String(a.severity || "low").toLowerCase();
        const severityB = String(b.severity || "low").toLowerCase();
        return (priorityWeight[severityA] || 0) - (priorityWeight[severityB] || 0);
      })
      .map(log => ({
        id: String(log.id),
        equipment: log.equipment_serial || "Unknown",
        timestamp: log.date_reported,
        content: log.issue_description || "",
        severity: log.severity || "low",
        analyzed: Array.isArray(analysisReport) && analysisReport.some(report =>
          report?.equipment_details?.serial === log.equipment_serial
        )
      }));
  }, [openLogs, analysisReport]);





  const handleLogSubmission = async () => {
    if (!selectedSerial || !issueDescription || !severity || !raisedBy || !datePredicted) {
      toast({
        title: "Missing Information",
        description: "Please fill in all required fields (Equipment, Description, Severity, Reported By, Predicted Date)",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        raised_by: raisedBy,
        equipment_serial: selectedSerial,
        issue_description: issueDescription,
        date_reported: format(new Date(), "yyyy-MM-dd"), // Defaults to today
        severity: severity,
        date_predicted: datePredicted ? format(datePredicted, "yyyy-MM-dd") : null
      };

      const response = await fetch("http://localhost:8448/maintenance/logs/add", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to add maintenance log");
      }

      toast({
        title: "Success",
        description: "Maintenance log added successfully",
      });

      // Reset form
      setSelectedSerial("");
      setIssueDescription("");
      setSeverity("");
      setDatePredicted(undefined);
      setRaisedBy("");

      // Refresh open logs
      queryClient.invalidateQueries({ queryKey: ["openMaintenanceLogs"] });

    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisReport([]);

    try {
      const response = await fetch("http://localhost:8448/ai_validation");

      if (!response.ok) {
        throw new Error("Failed to fetch AI analysis results");
      }

      const data: AIAnalysisValidationResponse = await response.json();
      setAnalysisReport(data.status.analysis_report);

      toast({
        title: "Analysis Complete",
        description: `Successfully analyzed logs for ${data.status.analysis_report.length} open maintenance cases.`,
      });
    } catch (error) {
      toast({
        title: "Analysis Failed",
        description: "Unable to retrieve AI analysis results. Please try again.",
        variant: "destructive",
      });
      console.error("AI Analysis Error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    const safeSeverity = String(severity || "low");
    switch (safeSeverity.toLowerCase()) {
      case "critical":
        return <Badge variant="destructive">Critical</Badge>;
      case "high":
        return <Badge className="bg-orange-500 hover:bg-orange-600">High</Badge>;
      case "medium":
        return <Badge className="bg-yellow-500 hover:bg-yellow-600">Medium</Badge>;
      case "low":
        return <Badge className="bg-green-500 hover:bg-green-600">Low</Badge>;
      default:
        return <Badge variant="secondary">{safeSeverity}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Maintenance Log Management</h1>
            <p className="text-muted-foreground">Upload and analyze equipment maintenance logs with AI</p>
          </div>
          <Button
            onClick={handleBulkAnalysis}
            disabled={isAnalyzing}
            className="bg-gradient-corporate shadow-corporate"
          >
            {isAnalyzing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Brain className="mr-2 h-4 w-4" />
            )}
            {isAnalyzing ? "Analyzing..." : "Run AI Analysis"}
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Log Input Form */}
          <Card className="shadow-elevated">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Add New Log Entry
              </CardTitle>
              <CardDescription>
                Create a new maintenance record or incident report
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">

              {/* Equipment Selection */}
              <div>
                <label className="text-sm font-medium">Equipment <span className="text-red-500">*</span></label>
                <Select value={selectedSerial} onValueChange={setSelectedSerial}>
                  <SelectTrigger className="w-full mt-1">
                    <SelectValue placeholder="Select Equipment" />
                  </SelectTrigger>
                  <SelectContent>
                    {isLoadingEquipments ? (
                      <SelectItem value="loading" disabled>Loading equipments...</SelectItem>
                    ) : Array.isArray(equipments) ? equipments.map((eq) => (
                      <SelectItem key={eq.serial} value={eq.serial}>
                        {eq.name} ({eq.serial})
                      </SelectItem>
                    )) : null}
                  </SelectContent>
                </Select>
              </div>

              {/* Reported By */}
              <div>
                <label className="text-sm font-medium">Reported By <span className="text-red-500">*</span></label>
                <Input
                  value={raisedBy}
                  onChange={(e) => setRaisedBy(e.target.value)}
                  placeholder="Enter your name"
                  className="mt-1"
                />
              </div>

              {/* Issue Description */}
              <div>
                <label className="text-sm font-medium">Issue Description <span className="text-red-500">*</span></label>
                <Textarea
                  placeholder="Describe the issue, detailed maintenance log, or incident report..."
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  className="mt-1 min-h-[100px]"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Severity */}
                <div>
                  <label className="text-sm font-medium">Severity <span className="text-red-500">*</span></label>
                  <Select value={severity} onValueChange={setSeverity}>
                    <SelectTrigger className="w-full mt-1">
                      <SelectValue placeholder="Select Severity" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Predicted Date */}
                <div>
                  <label className="text-sm font-medium">Predicted Date <span className="text-red-500">*</span></label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant={"outline"}
                        className={cn(
                          "w-full mt-1 justify-start text-left font-normal",
                          !datePredicted && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {datePredicted ? format(datePredicted, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={datePredicted}
                        onSelect={setDatePredicted}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              <Button
                onClick={handleLogSubmission}
                className="w-full bg-gradient-corporate shadow-corporate"
                disabled={isSubmitting}
              >
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                Submit Log Entry
              </Button>
            </CardContent>
          </Card>

          {/* Log Entries */}
          <Card className="shadow-elevated">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Log Entries
              </CardTitle>
              <CardDescription>
                Latest maintenance logs and their analysis status
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-h-[600px] overflow-y-auto">
              {logs.map((log) => (
                <div key={log.id} className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold">{log.equipment}</h4>
                    <div className="flex items-center gap-2">
                      {getSeverityBadge(log.severity)}
                      {log.analyzed && (
                        <CheckCircle className="h-4 w-4 text-success" />
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {log.content}
                  </p>

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{new Date(log.timestamp).toLocaleString()}</span>
                    {log.analyzed && (
                      <span className="text-success">Analyzed</span>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* AI Insights Panel */}
        <Card className="shadow-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Analysis Insights
            </CardTitle>
            <CardDescription>
              Key patterns and recommendations identified from log analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {analysisReport.length > 0 ? (
              analysisReport.map((report, index) => (
                <div key={index} className={cn(
                  "rounded-lg p-4 flex flex-col md:flex-row gap-4 items-start",
                  String(report?.priority || "").toLowerCase() === "critical" ? "bg-red-50 border-l-4 border-l-red-500" :
                    String(report?.priority || "").toLowerCase() === "high" ? "bg-orange-50 border-l-4 border-l-orange-500" :
                      "bg-blue-50 border-l-4 border-l-blue-500"
                )}>
                  <div className="flex flex-col md:w-1/4 gap-2">
                    <h3 className="font-semibold text-foreground">{report?.equipment_details?.name || "Unknown Equipment"}</h3>
                    <div className="flex items-center gap-2">
                      {report && report.priority && (
                        <Badge variant={
                          String(report.priority).toLowerCase() === "critical" ? "destructive" :
                            String(report.priority).toLowerCase() === "high" ? "default" : "secondary"
                        }>
                          {String(report.priority).toUpperCase()}
                        </Badge>
                      )}
                      {report?.needs_maintenance && (
                        <span className="flex items-center text-xs font-semibold text-red-600">
                          <AlertCircle className="w-3 h-3 mr-1" />
                          Maintenance
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex-grow grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="text-sm">
                      <span className="font-semibold text-foreground">Summary:</span>
                      <p className="text-muted-foreground mt-1 text-sm">
                        {report?.ai_summary || "No summary available."}
                      </p>
                    </div>

                    <div className="text-sm">
                      <span className="font-semibold text-foreground">Analysis:</span>
                      <p className="text-muted-foreground mt-1 text-sm italic">
                        "{report?.validation_feedback || "No feedback."}"
                      </p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full flex flex-col items-center justify-center py-12 text-muted-foreground bg-muted/30 rounded-lg border-dashed border-2">
                <Brain className="h-12 w-12 mb-3 opacity-20" />
                <p>No analysis results yet.</p>
                <p className="text-sm">Click "Run AI Analysis" to generate insights from open logs.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <PredictiveAnalysisLoader open={isAnalyzing} />
    </div>
  );
};

export default LogUploader;