"use client";

import { MapPin, Check, X, ExternalLink, Phone, Clock, Pill, Truck, Building2, FileText } from "lucide-react";

interface MedicineCardProps {
  medicine: string;
  pharmacy: string;
  price: string;
  currency: string;
  address?: string;
  distance?: string;
  available: boolean;
  mapLink?: string;
  phoneNumber?: string;
  openingHours?: string;
  prescriptionRequired?: boolean;
  genericAlternative?: string;
  genericPrice?: string;
  deliveryAvailable?: boolean;
  pharmacyType?: string;
  dosageMatch?: string;
}

export default function MedicineCard({
  medicine,
  pharmacy,
  price,
  currency,
  address,
  distance,
  available,
  mapLink,
  phoneNumber,
  openingHours,
  prescriptionRequired,
  genericAlternative,
  genericPrice,
  deliveryAvailable,
  pharmacyType,
  dosageMatch,
}: MedicineCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 p-3 hover:border-blue-200 transition-colors">
      {/* Header: medicine name, pharmacy, price, availability */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="text-sm font-semibold text-gray-900">{medicine}</h4>
          <div className="flex items-center gap-1.5">
            <p className="text-xs text-gray-500">{pharmacy}</p>
            {pharmacyType && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">
                <Building2 className="h-2.5 w-2.5" />
                {pharmacyType}
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-gray-900">
            {price} {currency}
          </p>
          {available ? (
            <span className="inline-flex items-center gap-0.5 text-xs text-green-600">
              <Check className="h-3 w-3" />
              In Stock
            </span>
          ) : (
            <span className="inline-flex items-center gap-0.5 text-xs text-red-500">
              <X className="h-3 w-3" />
              Unavailable
            </span>
          )}
        </div>
      </div>

      {/* Generic alternative highlight */}
      {genericAlternative && (
        <div className="mb-2 rounded-md bg-green-50 border border-green-200 px-2.5 py-1.5">
          <div className="flex items-center gap-1.5">
            <Pill className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
            <span className="text-xs text-green-800">
              <span className="font-medium">Generic available:</span> {genericAlternative}
              {genericPrice && (
                <span className="font-bold ml-1">— {genericPrice}</span>
              )}
            </span>
          </div>
        </div>
      )}

      {/* Info rows */}
      <div className="space-y-1 text-xs text-gray-500">
        {/* Address + map */}
        {(address || distance) && (
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1 truncate">
              <MapPin className="h-3 w-3 flex-shrink-0" />
              {address || "Address not available"}
            </span>
            <div className="flex items-center gap-2 ml-2 flex-shrink-0">
              {distance && <span>{distance}</span>}
              {mapLink && (
                <a
                  href={mapLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-0.5 text-blue-600 hover:text-blue-800"
                >
                  <ExternalLink className="h-3 w-3" />
                  Map
                </a>
              )}
            </div>
          </div>
        )}

        {/* Phone */}
        {phoneNumber && (
          <div className="flex items-center gap-1">
            <Phone className="h-3 w-3 flex-shrink-0" />
            <a href={`tel:${phoneNumber}`} className="text-blue-600 hover:text-blue-800">
              {phoneNumber}
            </a>
          </div>
        )}

        {/* Hours */}
        {openingHours && (
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3 flex-shrink-0" />
            {openingHours}
          </div>
        )}

        {/* Dosage match */}
        {dosageMatch && (
          <div className="flex items-center gap-1">
            <Pill className="h-3 w-3 flex-shrink-0" />
            {dosageMatch}
          </div>
        )}
      </div>

      {/* Bottom badges */}
      <div className="flex flex-wrap items-center gap-1.5 mt-2">
        {prescriptionRequired !== undefined && (
          <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${
            prescriptionRequired
              ? "bg-amber-50 text-amber-700 border border-amber-200"
              : "bg-green-50 text-green-700 border border-green-200"
          }`}>
            <FileText className="h-2.5 w-2.5" />
            {prescriptionRequired ? "Rx Required" : "No Rx Needed"}
          </span>
        )}
        {deliveryAvailable && (
          <span className="inline-flex items-center gap-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 text-[10px] font-medium">
            <Truck className="h-2.5 w-2.5" />
            Delivery
          </span>
        )}
      </div>
    </div>
  );
}
