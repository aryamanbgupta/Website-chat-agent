"use client";

import { ExternalLink, Wrench } from "lucide-react";
import type { ProductCardData } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { StarRating } from "@/components/shared/StarRating";
import { StockBadge } from "@/components/shared/StockBadge";

interface ProductCardProps {
  data: ProductCardData;
}

export function ProductCard({ data }: ProductCardProps) {
  return (
    <div className="border border-border bg-white my-2 overflow-hidden animate-fade-in">
      <div className="flex flex-col sm:flex-row">
        {data.image_url && (
          <div className="sm:w-32 w-full h-32 sm:h-auto flex-shrink-0 bg-bg-light flex items-center justify-center p-2">
            <img
              src={data.image_url}
              alt={data.name}
              className="max-h-full max-w-full object-contain"
              loading="lazy"
            />
          </div>
        )}
        <div className="flex-1 p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-sm text-body-text leading-tight">
                {data.name}
              </h3>
              <p className="text-xs text-muted-text mt-0.5">
                {data.brand} | {data.ps_number}
              </p>
            </div>
            <p className="text-lg font-bold text-body-text whitespace-nowrap">
              {formatPrice(data.price)}
            </p>
          </div>

          <div className="flex items-center gap-3 mt-2">
            {data.rating && <StarRating rating={data.rating} />}
            {data.review_count && (
              <span className="text-xs text-muted-text">
                ({data.review_count} reviews)
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <StockBadge inStock={data.in_stock} />
            {data.installation_difficulty && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-text">
                <Wrench size={12} />
                {data.installation_difficulty}
              </span>
            )}
          </div>

          {data.symptoms_fixed && data.symptoms_fixed.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {data.symptoms_fixed.slice(0, 4).map((symptom) => (
                <span
                  key={symptom}
                  className="text-[10px] bg-teal-light text-primary-teal px-1.5 py-0.5"
                >
                  Fixes: {symptom}
                </span>
              ))}
            </div>
          )}

          {data.source_url && (
            <a
              href={data.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-primary-teal hover:text-teal-dark transition-colors"
            >
              View on PartSelect
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
