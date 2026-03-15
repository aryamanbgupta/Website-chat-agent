"use client";

import { Check, X } from "lucide-react";

interface StockBadgeProps {
  inStock: boolean;
}

export function StockBadge({ inStock }: StockBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium ${
        inStock ? "text-success-green" : "text-error-red"
      }`}
    >
      {inStock ? <Check size={12} /> : <X size={12} />}
      {inStock ? "In Stock" : "Out of Stock"}
    </span>
  );
}
