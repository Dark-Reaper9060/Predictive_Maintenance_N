import { useEffect, useState } from "react";
import { Loader2, BrainCircuit } from "lucide-react";

interface PredictiveAnalysisLoaderProps {
    open: boolean;
}

const LOADING_MESSAGES = [
    "Fetching Equipment Data",
    "Reading Status Logs",
    "Analyzing Sensor Patterns",
    "Predicting Failure Modes",
    "Optimizing Maintenance Schedule",
    "Finalizing Recommendations"
];

export const PredictiveAnalysisLoader = ({ open }: PredictiveAnalysisLoaderProps) => {
    const [currentMessageIndex, setCurrentMessageIndex] = useState(0);

    useEffect(() => {
        if (!open) {
            setCurrentMessageIndex(0);
            return;
        }

        const interval = setInterval(() => {
            setCurrentMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
        }, 2000); // Change text every 2 seconds

        return () => clearInterval(interval);
    }, [open]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
            <div className="flex flex-col items-center space-y-4 p-8 bg-card border rounded-lg shadow-xl max-w-md w-full animate-in fade-in zoom-in duration-300">
                <div className="relative">
                    <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
                    <BrainCircuit className="h-16 w-16 text-primary animate-pulse relative z-10" />
                </div>

                <h3 className="text-xl font-semibold text-foreground">AI Analysis in Progress</h3>

                <div className="flex items-center space-x-3 text-muted-foreground min-h-[24px]">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <p className="text-sm font-medium animate-pulse">
                        {LOADING_MESSAGES[currentMessageIndex]}...
                    </p>
                </div>

                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-primary/50 w-full animate-progress origin-left"
                        style={{ animation: 'shimmer 2s infinite linear' }}
                    />
                </div>
            </div>
        </div>
    );
};
