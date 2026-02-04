import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Loader2 } from "lucide-react";
import { useMonitoringLogs } from "@/hooks/useMonitoringLogs";

interface MonitoringDialogProps {
    serialNumber: string | null;
    equipmentName: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const MonitoringDialog = ({
    serialNumber,
    equipmentName,
    open,
    onOpenChange,
}: MonitoringDialogProps) => {
    const { data: logs, isLoading, error } = useMonitoringLogs(serialNumber);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[800px] max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Monitoring Logs: {equipmentName} ({serialNumber})</DialogTitle>
                    <DialogDescription>
                        Real-time sensor data and performance metrics
                    </DialogDescription>
                </DialogHeader>

                {isLoading ? (
                    <div className="flex justify-center p-8">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : error ? (
                    <div className="p-4 text-center text-error">
                        Failed to load monitoring logs. Please try again.
                    </div>
                ) : !logs || logs.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground">
                        No monitoring data available for this equipment.
                    </div>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Timestamp</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Value</TableHead>
                                <TableHead>Location</TableHead>
                                <TableHead>Status</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {logs.map((log) => (
                                <TableRow key={log.id}>
                                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                                    <TableCell className="capitalize">{log.reading_type}</TableCell>
                                    <TableCell>
                                        {log.value} {log.unit}
                                        <span className="text-xs text-muted-foreground ml-2">
                                            (Range: {log.threshold_min}-{log.threshold_max})
                                        </span>
                                    </TableCell>
                                    <TableCell className="capitalize">{log.location}</TableCell>
                                    <TableCell>
                                        <span
                                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${log.status === "normal"
                                                ? "bg-success/10 text-success"
                                                : log.status === "warning"
                                                    ? "bg-warning/10 text-warning"
                                                    : "bg-error/10 text-error"
                                                }`}
                                        >
                                            {log.status}
                                        </span>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </DialogContent>
        </Dialog>
    );
};
