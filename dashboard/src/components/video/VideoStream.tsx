"use client";

import { useEffect, useRef } from "react";
import { User } from "lucide-react";

interface VideoStreamProps {
  stream: MediaStream | null;
  label: string;
  muted?: boolean;
}

export default function VideoStream({ stream, label, muted = false }: VideoStreamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <div className="relative flex-1 min-h-0 rounded-lg overflow-hidden bg-gray-900">
      {stream ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={muted}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="flex items-center justify-center h-full">
          <div className="text-center text-gray-500">
            <div className="w-14 h-14 mx-auto mb-2 rounded-full bg-gray-800 flex items-center justify-center">
              <User className="w-7 h-7 text-gray-600" />
            </div>
            <p className="text-xs">Waiting for {label}...</p>
          </div>
        </div>
      )}
      {/* Label overlay */}
      <div className="absolute bottom-2 left-2 rounded bg-black/60 px-2 py-0.5">
        <span className="text-xs font-medium text-white">{label}</span>
      </div>
      {/* Live indicator when stream is active */}
      {stream && (
        <div className="absolute top-2 right-2 flex items-center gap-1 rounded bg-red-600/90 px-1.5 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
          <span className="text-[10px] font-semibold text-white">LIVE</span>
        </div>
      )}
    </div>
  );
}
