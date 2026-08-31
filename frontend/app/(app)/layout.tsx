import type { ReactNode } from "react";

import { ProtectedShell } from "@/components/ProtectedShell";

// Every route in this group requires authentication and renders inside the
// app shell (branding, nav, current user, logout).
export default function AppGroupLayout({ children }: { children: ReactNode }) {
  return <ProtectedShell>{children}</ProtectedShell>;
}
