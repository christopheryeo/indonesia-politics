import type { Metadata } from "next";
import Dashboard from "./dashboard-client";

export const metadata: Metadata = {
  title: "Sentient.io Media Intelligence",
  description: "Deterministic intelligence from the Indonesia-politics knowledge vault.",
};

export default function Home() {
  return <Dashboard />;
}
