"use client";

import { CheckCircle, AlertTriangle, XCircle, ExternalLink } from "lucide-react";
import type { CompatibilityResultData } from "@/lib/types";

interface CompatibilityBadgeProps {
  data: CompatibilityResultData;
}

export function CompatibilityBadge({ data }: CompatibilityBadgeProps) {
  const isVerified = data.compatible === true && data.confidence === "verified";
  const isNotFound = data.confidence === "part_not_found" || data.confidence === "not_in_data";

  let icon: React.ReactNode;
  let bgColor: string;
  let borderColor: string;
  let textColor: string;
  let label: string;

  if (isVerified) {
    icon = <CheckCircle size={20} />;
    bgColor = "bg-green-50";
    borderColor = "border-success-green";
    textColor = "text-success-green";
    label = "Compatible";
  } else if (data.compatible === false) {
    icon = <XCircle size={20} />;
    bgColor = "bg-red-50";
    borderColor = "border-error-red";
    textColor = "text-error-red";
    label = "Not Compatible";
  } else {
    icon = <AlertTriangle size={20} />;
    bgColor = "bg-amber-50";
    borderColor = "border-amber-500";
    textColor = "text-amber-600";
    label = isNotFound ? "Unable to Verify" : "Unverified";
  }

  return (
    <div
      className={`${bgColor} border-l-4 ${borderColor} p-3 my-2 animate-fade-in`}
    >
      <div className="flex items-start gap-2">
        <span className={`${textColor} flex-shrink-0 mt-0.5`}>{icon}</span>
        <div className="flex-1 min-w-0">
          <p className={`font-medium text-sm ${textColor}`}>{label}</p>
          <p className="text-sm text-body-text mt-1">{data.message}</p>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-text flex-wrap">
            {data.part_number && <span>Part: {data.part_number}</span>}
            {data.model_number && <span>Model: {data.model_number}</span>}
          </div>
          {data.source_url && (
            <a
              href={data.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-1.5 text-xs text-primary-teal hover:text-teal-dark"
            >
              View Details
              <ExternalLink size={11} />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
