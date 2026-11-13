/** View props only: these are not HTTP contracts or an authoritative store.
 * The backend adapter projects its published contract into these components.
 * Pending form text is never treated as a confirmed clinic requirement.
 */
import type { SimulationResponse } from "../../../../contracts/api";
export type OverviewSection = "activities" | "weather" | "energy" | "solutions";
export interface EvidenceOption {
  label: string;
  simulation: SimulationResponse;
}
export interface ActivityView {
  id: string;
  name: string;
  date: string;
  operatingWindow: string;
  status: "draft" | "confirmed";
  equipment: { id: string; name: string; specifications: string[] }[];
  missing: string[];
  affectedRequirements: string[];
}
