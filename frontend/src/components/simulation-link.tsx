"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { updateDemo } from "@/lib/store";

export function SimulationLink({ children }: { children: ReactNode }) {
  return (
    <Link
      href="/simulate"
      className="button primary"
      onNavigate={() =>
        updateDemo((state) => ({
          ...state,
          draft: { ...state.draft, step: 0 },
        }))
      }
    >
      {children}
    </Link>
  );
}
