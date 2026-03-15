"use client";

import { Star } from "lucide-react";

interface StarRatingProps {
  rating: string | number;
  size?: number;
}

export function StarRating({ rating, size = 14 }: StarRatingProps) {
  const numRating = typeof rating === "string" ? parseFloat(rating) : rating;
  if (isNaN(numRating)) return null;

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={
            star <= Math.round(numRating)
              ? "fill-star-filled text-star-filled"
              : "fill-star-empty text-star-empty"
          }
        />
      ))}
      <span className="ml-1 text-xs text-muted-text">
        {numRating.toFixed(1)}
      </span>
    </div>
  );
}
