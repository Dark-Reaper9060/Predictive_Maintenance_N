import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  Settings,
  TrendingUp,
  Wrench,
  Loader2
} from "lucide-react";
import { useEquipments } from "@/hooks/useEquipments";
import { useOpenMaintenanceLogs } from "@/hooks/useOpenMaintenanceLogs";
import { MonitoringDialog } from "./MonitoringDialog";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { MaintenanceDialog } from "./MaintenanceDialog";
import { PastMaintenanceDialog } from "./PastMaintenanceDialog";
import { PredictiveAnalysisLoader } from "./PredictiveAnalysisLoader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface MaintenanceItem {
  id: string;
  equipment: string;
  priority: "high" | "medium" | "low";
  scheduledDate: string;
  status: "pending" | "in-progress" | "completed";
  predictedIssue: string;
  generatedBy?: string;
}



import { useMaintenanceList } from "@/hooks/useMaintenanceList";

const Dashboard = () => {
  const { data: equipments, isLoading, error } = useEquipments();
  const [showAllEquipments, setShowAllEquipments] = useState(false);
  const [selectedSerial, setSelectedSerial] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [logType, setLogType] = useState<"monitoring" | "maintenance">("monitoring");
  const [showAllSchedule, setShowAllSchedule] = useState(false);
  const [isPastMaintenanceOpen, setIsPastMaintenanceOpen] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isPredicting, setIsPredicting] = useState(false);

  const handlePredictMaintenance = async () => {
    setIsPredicting(true);
    try {
      const response = await fetch("/ai_analysis");
      if (!response.ok) {
        throw new Error("Failed to run AI analysis");
      }

      const data = await response.json();

      if (data.status?.created_logs?.length === 0) {
        toast({
          title: "Analysis Complete",
          description: "Seems that equipments are in good state or already maintenance has been scheduled",
        });
      } else {
        toast({
          title: "Analysis Complete",
          description: "AI prediction analysis has been successfully completed.",
        });
      }

      // Refresh maintenance logs
      queryClient.invalidateQueries({ queryKey: ["openMaintenanceLogs"] });
      queryClient.invalidateQueries({ queryKey: ["maintenanceList"] });

    } catch (error) {
      toast({
        title: "Analysis Failed",
        description: "Failed to run AI analysis. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsPredicting(false);
    }
  };

  const handleEquipmentClick = (serial: string, name: string) => {
    setSelectedSerial(serial);
    setSelectedName(name);
    setIsDialogOpen(true);
  };

  const displayedEquipments = Array.isArray(equipments)
    ? (showAllEquipments ? equipments : equipments.slice(0, 3))
    : [];

  const { data: openMaintenanceList } = useOpenMaintenanceLogs();
  const { data: maintenanceList } = useMaintenanceList();

  const activeEquipmentsCount = Array.isArray(equipments) ? equipments.length : 0;
  const pendingMaintenanceCount = Array.isArray(openMaintenanceList) ? openMaintenanceList.length : 0;
  const criticalAlertsCount = Array.isArray(openMaintenanceList)
    ? openMaintenanceList.filter(item => ['critical', 'high'].includes(item.severity?.toLowerCase())).length
    : 0;

  const completedMaintenanceCount = Array.isArray(maintenanceList)
    ? maintenanceList.filter(item => item.status === "closed").length
    : 0;

  // Helper to find equipment name by serial
  const getEquipmentName = (serial: string) => {
    const eq = equipments?.find(e => e.serial === serial);
    return eq ? eq.name : serial;
  };

  // Helper for priority sorting
  const getSeverityWeight = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical": return 4;
      case "high": return 3;
      case "medium": return 2;
      case "low": return 1;
      default: return 0;
    }
  };

  const maintenanceItems = Array.isArray(openMaintenanceList)
    ? openMaintenanceList
      .sort((a, b) => {
        // Primary sort: Severity (Higher first)
        const severityDiff = getSeverityWeight(b.severity) - getSeverityWeight(a.severity);
        if (severityDiff !== 0) return severityDiff;

        // Secondary sort: Date Reported (Newest first)
        return new Date(b.date_reported).getTime() - new Date(a.date_reported).getTime();
      })
      .slice(0, showAllSchedule ? undefined : 3)
      .map(item => ({
        id: item.id.toString(),
        equipment: getEquipmentName(item.equipment_serial),
        priority: item.severity,
        scheduledDate: item.date_predicted || item.date_reported,
        status: "pending",
        predictedIssue: item.issue_description,
        generatedBy: item.raised_by
      }))
    : [];



  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "critical":
      case "high":
        return <Badge variant="destructive">{priority.charAt(0).toUpperCase() + priority.slice(1)} Priority</Badge>;
      case "medium":
        return <Badge className="bg-amber-500 hover:bg-amber-600 text-white border-amber-500">Medium Priority</Badge>;
      case "low":
        return <Badge className="bg-yellow-500 hover:bg-yellow-600 text-white border-yellow-500">Low Priority</Badge>;
      default:
        return <Badge variant="secondary">{priority}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "critical":
        return <Badge variant="destructive">Critical</Badge>;
      case "warning":
        return <Badge variant="default">Warning</Badge>;
      case "operational":
        return <Badge variant="outline">Operational</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "critical":
        return <AlertTriangle className="h-4 w-4 text-error" />;
      case "warning":
        return <Clock className="h-4 w-4 text-warning" />;
      case "operational":
        return <CheckCircle className="h-4 w-4 text-success" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Predictive Maintenance Dashboard</h1>
            <p className="text-muted-foreground">AI-powered maintenance scheduling and equipment monitoring</p>
          </div>
          <Button
            variant="default"
            className="bg-gradient-corporate shadow-corporate transition-all duration-300 hover:shadow-lg hover:scale-[1.02]"
            onClick={handlePredictMaintenance}
            disabled={isPredicting}
          >
            {isPredicting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Activity className="mr-2 h-4 w-4" />
            )}
            {isPredicting ? "Analyzing..." : "Predict Maintenance"}
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card className="shadow-corporate">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Equipment</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{activeEquipmentsCount}</div>
              <p className="text-xs text-muted-foreground">+2.1% from last month</p>
            </CardContent>
          </Card>

          <Card className="shadow-corporate">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Maintenance</CardTitle>
              <Wrench className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pendingMaintenanceCount}</div>
              <p className="text-xs text-muted-foreground">-8.3% from last week</p>
            </CardContent>
          </Card>

          <Card className="shadow-corporate">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Alerts</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-error">{criticalAlertsCount}</div>
              <p className="text-xs text-muted-foreground">Requires immediate attention</p>
            </CardContent>
          </Card>

          <Card className="shadow-corporate">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Maintenance Completed</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-success">{completedMaintenanceCount}</div>
              <p className="text-xs text-muted-foreground">Total closed tickets</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* AI-Generated Maintenance Schedule */}
          <Card className="shadow-elevated">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                AI-Generated Maintenance Schedule
              </CardTitle>
              <CardDescription>
                Prioritized maintenance recommendations based on predictive analysis
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {maintenanceItems.map((item) => (
                <div key={item.id} className="flex items-start space-x-4 rounded-lg border p-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold inline-block mr-2">{item.equipment}</h4>
                        {item.generatedBy && (
                          <span className="text-xs text-muted-foreground font-normal ">
                            (Generated by: {item.generatedBy})
                          </span>
                        )}
                      </div>
                      {getPriorityBadge(item.priority)}
                    </div>
                    <p className="text-sm text-muted-foreground">{item.predictedIssue}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      Scheduled: {item.scheduledDate}
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowAllSchedule(!showAllSchedule)}
                >
                  {showAllSchedule ? "Show Less" : "View Full Schedule"}
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setIsPastMaintenanceOpen(true)}
                >
                  View Past Maintenance
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Equipment Status Overview */}
          <Card className="shadow-elevated">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div className="flex flex-col space-y-1.5">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Equipment Status Overview
                </CardTitle>
                <CardDescription>
                  Real-time monitoring of critical equipment health
                </CardDescription>
              </div>
              <Select value={logType} onValueChange={(value: "monitoring" | "maintenance") => setLogType(value)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select log type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monitoring">Monitoring Logs</SelectItem>
                  <SelectItem value="maintenance">Maintenance Logs</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <div className="flex justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : error ? (
                <div className="text-center p-8 text-error">
                  Failed to load equipment data
                </div>
              ) : (
                displayedEquipments.map((equipment) => (
                  <div
                    key={equipment.id}
                    className="flex items-center justify-between rounded-lg border p-4 cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleEquipmentClick(equipment.serial, equipment.name)}
                  >
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(equipment.status)}
                      <div>
                        <h4 className="font-medium">{equipment.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          {equipment.manufacturer} {equipment.model}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          SN: {equipment.serial}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {getStatusBadge(equipment.status)}
                      {/* <p className="text-xs text-muted-foreground mt-1">
                        {equipment.maintenance_status}
                      </p> */}
                    </div>
                  </div>
                )))}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowAllEquipments(!showAllEquipments)}
              >
                {showAllEquipments ? "Show Less" : "View All Equipment"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
      {logType === "monitoring" ? (
        <MonitoringDialog
          serialNumber={selectedSerial}
          equipmentName={selectedName}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
        />
      ) : (
        <MaintenanceDialog
          serialNumber={selectedSerial}
          equipmentName={selectedName}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
        />
      )}

      <PastMaintenanceDialog
        open={isPastMaintenanceOpen}
        onOpenChange={setIsPastMaintenanceOpen}
        getEquipmentName={getEquipmentName}
      />

      <PredictiveAnalysisLoader open={isPredicting} />
    </div>
  );
};

export default Dashboard;