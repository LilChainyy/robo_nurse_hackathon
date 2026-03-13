"use client";

import { useState, useEffect } from "react";
import { Search, Loader2, MapPin, Hash } from "lucide-react";
import PricingTable from "./PricingTable";

interface PriceLookupPanelProps {
  prescription: any;
  intakeSession?: any;
  noteConfirmed: boolean;
  onLookupComplete: () => void;
}

export default function PriceLookupPanel({
  prescription,
  intakeSession,
  noteConfirmed,
  onLookupComplete,
}: PriceLookupPanelProps) {
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>(prescription?.priceLookupResults || []);
  const [zipcode, setZipcode] = useState("");
  const [country, setCountry] = useState("Mexico");

  // Auto-populate zipcode from patient intake
  useEffect(() => {
    if (intakeSession?.zipcode && !zipcode) {
      setZipcode(intakeSession.zipcode);
    }
  }, [intakeSession?.zipcode]);

  const handleLookup = async () => {
    if (!prescription?.prescribedMedications?.length) return;

    setIsSearching(true);
    try {
      const res = await fetch("/api/pricing/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          medicines: prescription.prescribedMedications,
          zipcode,
          country,
          prescriptionId: prescription._id,
        }),
      });
      const data = await res.json();
      setResults(data.results || []);
      onLookupComplete();
    } catch (err) {
      console.error("Price lookup failed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  // Sync existing results from server
  useEffect(() => {
    if (prescription?.priceLookupCompleted && prescription?.priceLookupResults?.length > 0) {
      setResults(prescription.priceLookupResults);
    }
  }, [prescription?.priceLookupCompleted, prescription?.priceLookupResults]);

  if (!noteConfirmed) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
        <Search className="h-8 w-8 text-gray-300" />
        <p className="text-sm">Confirm the doctor note to enable price lookup</p>
        <p className="text-xs">Medication prices will be searched at local pharmacies</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Controls */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5">
          <Hash className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <input
            type="text"
            value={zipcode}
            onChange={(e) => setZipcode(e.target.value)}
            placeholder="Zipcode"
            className="w-28 rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1.5 flex-1">
          <MapPin className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <input
            type="text"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="Country"
            className="w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={handleLookup}
          disabled={isSearching || !prescription?.prescribedMedications?.length}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {isSearching ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Search className="h-3.5 w-3.5" />
          )}
          {isSearching ? "Searching..." : "Look Up Prices"}
        </button>
      </div>

      {/* Medications being searched */}
      {prescription?.prescribedMedications?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {prescription.prescribedMedications.map((med: string, i: number) => (
            <span key={i} className="inline-flex rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {med}
            </span>
          ))}
        </div>
      )}

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {results.length > 0 ? (
          <PricingTable results={results} />
        ) : isSearching ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
            <Loader2 className="h-6 w-6 animate-spin" />
            <p className="text-sm">Searching nearby pharmacies...</p>
            <p className="text-xs text-gray-300">Checking prices, generics, availability & hours</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
            <p className="text-sm">Enter zipcode and click &quot;Look Up Prices&quot; to search nearby pharmacies</p>
          </div>
        )}
      </div>
    </div>
  );
}
