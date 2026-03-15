"use client";

import { AlertCircle, ChevronRight, ExternalLink } from "lucide-react";
import type { DiagnosisData, DiagnosisCause } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { StockBadge } from "@/components/shared/StockBadge";

interface DiagnosisCardProps {
  data: DiagnosisData;
}

function LikelihoodIndicator({ likelihood }: { likelihood: string }) {
  const normalized = likelihood.toLowerCase();
  let color = "bg-muted-text";
  let label = likelihood;

  if (normalized.includes("high") || normalized.includes("very")) {
    color = "bg-error-red";
    label = "High";
  } else if (normalized.includes("medium") || normalized.includes("moderate")) {
    color = "bg-star-filled";
    label = "Medium";
  } else if (normalized.includes("low")) {
    color = "bg-success-green";
    label = "Low";
  }

  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium text-white ${color} px-1.5 py-0.5`}>
      {label}
    </span>
  );
}

function CauseItem({ cause }: { cause: DiagnosisCause }) {
  return (
    <div className="border border-border p-2.5 mb-2 last:mb-0">
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium text-sm text-body-text">{cause.cause}</h4>
        <LikelihoodIndicator likelihood={cause.likelihood} />
      </div>
      {cause.description && (
        <p className="text-xs text-muted-text mt-1 leading-relaxed">
          {cause.description}
        </p>
      )}
      {cause.recommended_parts && cause.recommended_parts.length > 0 && (
        <p className="text-xs text-primary-teal mt-1">
          Related parts: {cause.recommended_parts.join(", ")}
        </p>
      )}
    </div>
  );
}

export function DiagnosisCard({ data }: DiagnosisCardProps) {
  return (
    <div className="border border-border bg-white my-2 overflow-hidden animate-fade-in">
      <div className="bg-teal-light px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <AlertCircle size={16} className="text-primary-teal" />
          <h3 className="font-medium text-sm text-primary-teal">
            Diagnosis: {data.symptom}
          </h3>
        </div>
      </div>

      <div className="p-3">
        {data.causes && data.causes.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-text uppercase tracking-wide mb-1.5">
              Possible Causes
            </p>
            {data.causes.map((cause, i) => (
              <CauseItem key={i} cause={cause} />
            ))}
          </div>
        )}

        {data.recommended_parts && data.recommended_parts.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-text uppercase tracking-wide mb-1.5">
              Recommended Parts
            </p>
            <div className="grid gap-2">
              {data.recommended_parts.map((part) => (
                <div
                  key={part.ps_number}
                  className="flex items-center gap-2 border border-border p-2"
                >
                  {part.image_url && (
                    <img
                      src={part.image_url}
                      alt={part.name}
                      className="w-12 h-12 object-contain bg-bg-light flex-shrink-0"
                      loading="lazy"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-body-text truncate">
                      {part.name}
                    </p>
                    <p className="text-[10px] text-muted-text">
                      {part.brand} | {part.ps_number}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs font-bold">
                        {formatPrice(part.price)}
                      </span>
                      <StockBadge inStock={part.in_stock} />
                    </div>
                  </div>
                  {part.source_url && (
                    <a
                      href={part.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-teal hover:text-teal-dark flex-shrink-0"
                      aria-label={`View ${part.name} on PartSelect`}
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {data.follow_up_questions && data.follow_up_questions.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-text uppercase tracking-wide mb-1.5">
              To help diagnose further, please answer:
            </p>
            <ul className="flex flex-col gap-1">
              {data.follow_up_questions.map((q, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-body-text px-2 py-1"
                >
                  <ChevronRight size={12} className="flex-shrink-0 mt-0.5 text-primary-teal" />
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
