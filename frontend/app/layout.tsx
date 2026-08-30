import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PromptDNA",
  description:
    "An intelligent knowledge database for prompt engineering and large language models.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
        {children}
      </body>
    </html>
  );
}
